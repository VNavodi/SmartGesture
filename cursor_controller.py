import pyautogui
import numpy as np
import time
from collections import deque

# Safety: disable pyautogui failsafe (move mouse to corner to stop)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0  # Remove built-in delay for responsiveness

SCREEN_W, SCREEN_H = pyautogui.size()

# ── Tuning knobs ────────────────────────────────────────────────
# Webcam active zone (fraction of frame used for mapping).
# Crop the edges so you don't have to reach the literal border.
CAM_MARGIN = 0.15          # 15 % margin on every side

# Smoothing: larger buffer = smoother but more latency
SMOOTH_BUFFER = 6          # number of recent positions to average

# Stabilization: minimum pixel movement (in screen coords) to update
DEAD_ZONE = 4              # pixels — ignore jitter smaller than this
# ────────────────────────────────────────────────────────────────

# ── Scroll tuning ───────────────────────────────────────────────
SCROLL_DEAD_ZONE   = 0.012   # normalised Y delta to ignore micro-jitter
SCROLL_ACCEL_MIN   = 8      # scroll clicks at slowest movement
SCROLL_ACCEL_MAX   = 60       # scroll clicks at fastest movement
SCROLL_SPEED_LOW   = 0.005   # norm-Y delta → min acceleration
SCROLL_SPEED_HIGH  = 0.02   # norm-Y delta → max acceleration
# ────────────────────────────────────────────────────────────────


class CursorController:
    def __init__(self):
        self._history = deque(maxlen=SMOOTH_BUFFER)
        self._last_screen_x = None
        self._last_screen_y = None
        self._last_left_click = 0.0   # epoch time of last left click
        self._last_right_click= 0.0   # epoch time of last right click
        self.PINCH_THRESHOLD = 0.05      # normalised distance to trigger a click
        self.CLICK_COOLDOWN = 0.4       # seconds between repeated clicks

        self._scroll_prev_y   = None   # last index-finger Y while scrolling
        self._scroll_active   = False  # True while two-finger gesture held

    def _map_to_screen(self, norm_x: float, norm_y: float):
        """
        Map a normalised webcam coordinate (0‥1) → screen pixel,
        after cropping the outer margin so the active zone is smaller.
        """
        lo = CAM_MARGIN
        hi = 1.0 - CAM_MARGIN

        # Clamp into the active zone, then re-normalise to 0‥1
        mapped_x = (np.clip(norm_x, lo, hi) - lo) / (hi - lo)
        mapped_y = (np.clip(norm_y, lo, hi) - lo) / (hi - lo)

        screen_x = int(mapped_x * SCREEN_W)
        screen_y = int(mapped_y * SCREEN_H)
        return screen_x, screen_y

    def _smooth(self, screen_x: int, screen_y: int):
        """Return the rolling average position over the last N samples."""
        self._history.append((screen_x, screen_y))
        avg_x = int(np.mean([p[0] for p in self._history]))
        avg_y = int(np.mean([p[1] for p in self._history]))
        return avg_x, avg_y

    def _is_significant(self, sx: int, sy: int) -> bool:
        """Return True only if movement exceeds the dead-zone threshold."""
        if self._last_screen_x is None:
            return True
        dx = abs(sx - self._last_screen_x)
        dy = abs(sy - self._last_screen_y)
        return (dx * dx + dy * dy) ** 0.5 >= DEAD_ZONE

    def move(self, norm_x: float, norm_y: float):
        """
        Full pipeline:
          normalised webcam coord
          → screen mapping
          → smoothing
          → dead-zone filter
          → pyautogui.moveTo
        """
        sx, sy = self._map_to_screen(norm_x, norm_y)
        sx, sy = self._smooth(sx, sy)

        if self._is_significant(sx, sy):
            pyautogui.moveTo(sx, sy)
            self._last_screen_x = sx
            self._last_screen_y = sy


    @staticmethod
    def _pinch_distance(lm_a, lm_b) -> float:
        """Euclidean distance between two normalised landmarks."""
        return ((lm_a.x - lm_b.x) ** 2 + (lm_a.y - lm_b.y) ** 2) ** 0.5

    def handle_clicks(self, thumb, index, middle):
        """
        thumb, index, middle — MediaPipe landmark objects (normalised).
        Left click  : thumb ↔ index  pinch
        Right click : thumb ↔ middle pinch
        Cooldown prevents repeated firing while fingers stay close.
        """
        now = time.time()

        left_dist  = self._pinch_distance(thumb, index)
        right_dist = self._pinch_distance(thumb, middle)

        if left_dist < self.PINCH_THRESHOLD:
            if now - self._last_left_click > self.CLICK_COOLDOWN:
                pyautogui.click(button="left")
                self._last_left_click = now

        elif right_dist < self.PINCH_THRESHOLD:
            if now - self._last_right_click > self.CLICK_COOLDOWN:
                pyautogui.click(button="right")
                self._last_right_click = now


    def handle_scroll(self, index, middle, hand_landmarks) -> bool:
        """
        Two-finger scroll (index + middle only).
        Detects the gesture by checking that ONLY index & middle are
        extended while the other three fingers are curled.
        Uses frame-to-frame Y delta — no screen-edge dependency.
        Smooth acceleration: faster hand movement → more scroll clicks.

        Returns True when scroll is active (caller can suppress cursor move).
        """
        # ── Landmark shortcuts ───────────────────────────────────────
        lm = hand_landmarks.landmark
        # Finger tip / pip (proximal knuckle) indices for curl detection
        TIPS = [8, 12, 16, 20]   # index, middle, ring, pinky tips
        PIPS = [6, 10, 14, 18]   # corresponding PIP joints

        # ── Curl detection ──────────────────────────────────────────
        # A finger is "up" when its tip is above (lower Y) its PIP joint
        fingers_up = [lm[tip].y < lm[pip].y for tip, pip in zip(TIPS, PIPS)]
        # fingers_up = [index_up, middle_up, ring_up, pinky_up]

        two_finger_mode = fingers_up[0] and fingers_up[1] \
                        and not fingers_up[2] and not fingers_up[3]

        if not two_finger_mode:
            # Gesture broken — reset state
            self._scroll_prev_y = None
            self._scroll_active = False
            return False

        # ── First frame of gesture ──────────────────────────────────
        if self._scroll_prev_y is None:
            self._scroll_prev_y = index.y
            self._scroll_active = True
            return True

        # ── Delta from previous frame ───────────────────────────────
        dy = index.y - self._scroll_prev_y   # positive = finger moved down
        self._scroll_prev_y = index.y

        if abs(dy) < SCROLL_DEAD_ZONE:
            return True   # gesture active but finger is still — no scroll

        # ── Smooth acceleration ─────────────────────────────────────
        speed = np.clip(abs(dy), SCROLL_SPEED_LOW, SCROLL_SPEED_HIGH)
        # Linear interpolation: slow → ACCEL_MIN clicks, fast → ACCEL_MAX
        t      = (speed - SCROLL_SPEED_LOW) / (SCROLL_SPEED_HIGH - SCROLL_SPEED_LOW)
        clicks = int(round(SCROLL_ACCEL_MIN + t * (SCROLL_ACCEL_MAX - SCROLL_ACCEL_MIN)))

        direction = -clicks if dy < 0 else clicks   # up = negative pyautogui scroll
        pyautogui.scroll(direction)

        return True