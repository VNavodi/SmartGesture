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

class CursorController:
    def __init__(self):
        self._history = deque(maxlen=SMOOTH_BUFFER)
        self._last_screen_x = None
        self._last_screen_y = None
        self._last_left_click = 0.0   # epoch time of last left click
        self._last_right_click= 0.0   # epoch time of last right click
        self.PINCH_THRESHOLD = 0.05      # normalised distance to trigger a click
        self.CLICK_COOLDOWN = 0.4       # seconds between repeated clicks

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