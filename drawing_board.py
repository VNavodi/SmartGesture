import cv2
import mediapipe as mp
import time
import numpy as np


# MediaPipe drawing utilities and hand tracking module
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

# Open the default webcam (camera index 0)
cap = cv2.VideoCapture(0)

# Set camera resolution to 1280x720
cap.set(3, 1280)
cap.set(4, 720)

def main():
    # Canvas to draw on
    canvas = None

    # Color palette: (B, G, R)
    colors = [
        (255, 0, 255),   # Purple
        (255, 0, 0),     # Blue
        (0, 255, 0),     # Green
        (0, 255, 255),   # Yellow
        (0, 0, 255),     # Red
        (0, 0, 0),       # Black
    ]
    selected_color_idx = 2  # Default: Green
    brush_size = 10

    # Palette circle positions (x, y) along top
    palette_x_start = 60
    palette_y = 50
    palette_gap = 80
    palette_radius = 28

    prev_x, prev_y = None, None

    with mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7,
    ) as hands:

        while True:
            attempt = 0
            success, image = cap.read()
            while not success and attempt < 5:
                time.sleep(0.2)
                success, image = cap.read()
                attempt += 1

            if not success:
                print("Failed to read frame")
                break

            img = cv2.flip(image, 1)
            h, w, c = img.shape

            if canvas is None:
                canvas = np.zeros_like(img)

            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb)

            # Draw palette circles
            for i, color in enumerate(colors):
                cx = palette_x_start + i * palette_gap
                cv2.circle(img, (cx, palette_y), palette_radius, color, -1)
                cv2.circle(img, (cx, palette_y), palette_radius, (255, 255, 255), 2)
                if i == selected_color_idx:
                    cv2.circle(img, (cx, palette_y), palette_radius + 6, (255, 255, 255), 3)

            # Brush size slider (right side)
            slider_x = w - 40
            slider_top = 100
            slider_bottom = h - 100
            cv2.rectangle(img, (slider_x - 8, slider_top), (slider_x + 8, slider_bottom), (80, 80, 80), -1)
            slider_pos = int(slider_bottom - (brush_size - 5) / 45 * (slider_bottom - slider_top))
            cv2.circle(img, (slider_x, slider_pos), 14, (0, 255, 0), -1)

            # Labels
            cv2.putText(img, "Press S to save image", (10, h - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(img, "Press Q to quit", (10, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(img, f"Brush: {brush_size}", (10, h - 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        img, hand_landmarks, mp_hands.HAND_CONNECTIONS
                    )

                    lm = hand_landmarks.landmark

                    # Fingertip positions
                    index_x = int(lm[8].x * w)
                    index_y = int(lm[8].y * h)

                    # Finger states (tip y < pip y = extended)
                    fingers_up = [
                        lm[4].x < lm[3].x,          # Thumb
                        lm[8].y < lm[6].y,           # Index
                        lm[12].y < lm[10].y,         # Middle
                        lm[16].y < lm[14].y,         # Ring
                        lm[20].y < lm[18].y,         # Pinky
                    ]

                    # Palm clear: all 5 fingers up
                    if all(fingers_up):
                        canvas = np.zeros_like(img)
                        prev_x, prev_y = None, None

                                # Color selection: index finger near palette
                    elif fingers_up[1] and not fingers_up[2]:
                        if index_y < palette_y + palette_radius + 20:  # Near palette row
                            for i in range(len(colors)):
                                cx = palette_x_start + i * palette_gap
                                if abs(index_x - cx) < palette_radius and abs(index_y - palette_y) < palette_radius:
                                    selected_color_idx = i
                            # Brush size via slider
                            if index_x > w - 80:
                                slider_val = (slider_bottom - index_y) / (slider_bottom - slider_top)
                                brush_size = int(np.clip(slider_val * 45 + 5, 5, 50))
                            prev_x, prev_y = None, None

                        else:  # Drawing zone
                            if prev_x is not None and prev_y is not None:
                                cv2.line(canvas, (prev_x, prev_y), (index_x, index_y),
                                        colors[selected_color_idx], brush_size)
                            prev_x, prev_y = index_x, index_y
                            cv2.circle(img, (index_x, index_y), 8, (0, 255, 0), -1)

                    else:
                        prev_x, prev_y = None, None
            # Merge canvas onto frame
            img_gray = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(img_gray, 10, 255, cv2.THRESH_BINARY)
            mask_inv = cv2.bitwise_not(mask)
            img_bg = cv2.bitwise_and(img, img, mask=mask_inv)
            canvas_fg = cv2.bitwise_and(canvas, canvas, mask=mask)
            img = cv2.add(img_bg, canvas_fg)

            # Re-draw palette on top of merged image
            for i, color in enumerate(colors):
                cx = palette_x_start + i * palette_gap
                cv2.circle(img, (cx, palette_y), palette_radius, color, -1)
                cv2.circle(img, (cx, palette_y), palette_radius, (255, 255, 255), 2)
                if i == selected_color_idx:
                    cv2.circle(img, (cx, palette_y), palette_radius + 6, (255, 255, 255), 3)

            cv2.imshow("Drawing Board", img)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                filename = f"drawing_{int(time.time())}.png"
                cv2.imwrite(filename, canvas)
                print(f"Saved: {filename}")

    cap.release()
    cv2.destroyAllWindows()
# Entry point of the program
if __name__ == "__main__":
    main()
    