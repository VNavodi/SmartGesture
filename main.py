import cv2
import mediapipe as mp
import time
from cursor_controller import CursorController


# MediaPipe drawing utilities and hand tracking module
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

# Open the default webcam (camera index 0)
cap = cv2.VideoCapture(0)

# Set camera resolution to 1280x720
cap.set(3, 1280)
cap.set(4, 720)

def main():
    cursor = CursorController()

    with mp_hands.Hands(
        max_num_hands=1,   # Detect up to 1 hands
        min_detection_confidence=0.7,   # Minimum confidence for hand detection 
        min_tracking_confidence=0.7,
    )as hands:


        # Main loop to continuously capture and display video frames
        while True:
            attempt =0

            # Read a frame from the webcam
            success, image = cap.read()
            
            # Retry up to 5 times if frame capture fails
            while not success and attempt < 5:
                time.sleep(0.2)    # Wait for 0.2 seconds before retrying
                success, image = cap.read()
                attempt+=1

            # Exit the program if frame capture still fails    
            if not success:
                print("Failed to read frame")   
                break 
            
            # Flip the image horizontally for a mirror effect
            img=cv2.flip(image, 1)
            h, w, c = img.shape

            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            results = hands.process(rgb)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        img, 
                        hand_landmarks, 
                        mp_hands.HAND_CONNECTIONS, #draw the connections between the landmarks
                    )

                    finger_tips={
                        "Thumb" : hand_landmarks.landmark[4],
                        "Index" : hand_landmarks.landmark[8],
                        "Middle" : hand_landmarks.landmark[12],
                        "Ring" : hand_landmarks.landmark[16],
                        "Pinky" : hand_landmarks.landmark[20]
                    }

                    thumb  = finger_tips["Thumb"] # Get the normalized coordinates of the thumb tip
                    index = finger_tips["Index"]  # Get the normalized coordinates of the index fingertip
                    middle = finger_tips["Middle"] # Get the normalized coordinates of the middle fingertip

                    scrolling = cursor.handle_scroll(index, middle, hand_landmarks)
                    if not scrolling:
                            cursor.move(index.x, index.y) # Move the cursor based on the index fingertip's normalized coordinates
                            cursor.handle_clicks(thumb, index, middle)

                    for name, landmark in finger_tips.items():
                        x,y=int(landmark.x*w), int(landmark.y*h)

                        cv2.putText(
                            img, 
                            name, 
                            (x,y-10),#position of the text (10 pixels above the fingertip)
                            cv2.FONT_HERSHEY_SIMPLEX, #font type
                            0.5, #font scale
                            (255,255,255), #color of the text (white)
                            1  #thickness of the text
                        )

                        cv2.circle(
                            img,
                            (x,y),
                            5,
                            (0,255,0),
                            -1 
                        )

            

            # Display the frame in a window named "Image"
            cv2.imshow("Image", img)

            # Break the loop if the 'q' key is pressed
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()

# Entry point of the program
if __name__ == "__main__":
    main()
    