# import important libraries
import cv2
import mediapipe as mp
import math
import time
import pyautogui

from gestures import rightclick
from gestures import openhand
from gestures import scrollup
from gestures import leftclick
from settings_window import SettingsWindow

pyautogui.FAILSAFE = False

# create settings window
settings = SettingsWindow()
settings.create_window()

# --- Setup ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    min_detection_confidence=settings.min_detection_confidence, 
    min_tracking_confidence=settings.min_tracking_confidence
)
mp_drawing = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
pyautogui.PAUSE = 0 

# --- Gesture State Tracking ---
last_fist_action_time = 0
last_gesture = None  # Track previous gesture to detect state changes
scroll_frame_counter = 0  # Frame counter for scroll throttling
SCROLL_EVERY_N_FRAMES = 2  # Execute scroll every N frames
pinch_active = False  # Track if pinch is currently active
debug = True
program_active = True  # Track if program is active or paused
pointer_was_up = False  # Track if pointer finger was up in previous frame

# --- Helper Functions ---

def get_distance(lm1, lm2):
    """Calculates the 2D distance between two landmarks."""
    return math.hypot(lm1.x - lm2.x, lm1.y - lm2.y)

def get_hand_label(index, hand, results):
    """
    Returns 'Right' or 'Left' for the given hand.
    (We don't need this for finger states anymore, but
     it's good to keep for other logic).
    """
    label = None
    if results.multi_handedness:
        classification = results.multi_handedness[index]
        if classification.classification:
            label = classification.classification[0].label
    return label

def get_finger_states(hand_landmarks):
    """
    Returns a list [Thumb, Index, Middle, Ring, Pinky]
    with 1 for 'Open' and 0 for 'Closed'.
    This version uses distance from the wrist and is
    rotation-invariant.
    """
    if hand_landmarks is None:
        return None

    fingers = []
    lms = hand_landmarks.landmark
    
    # Get the wrist landmark
    wrist_lm = lms[mp_hands.HandLandmark.WRIST]
    
    # Landmark IDs for tips and their corresponding middle (PIP) joints
    tip_ids = [
        mp_hands.HandLandmark.THUMB_TIP,
        mp_hands.HandLandmark.INDEX_FINGER_TIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
        mp_hands.HandLandmark.RING_FINGER_TIP,
        mp_hands.HandLandmark.PINKY_TIP
    ]
    
    # Using IP for thumb, PIP for other fingers
    pip_ids = [
        mp_hands.HandLandmark.THUMB_IP, # Interphalangeal joint
        mp_hands.HandLandmark.INDEX_FINGER_PIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_PIP,
        mp_hands.HandLandmark.RING_FINGER_PIP,
        mp_hands.HandLandmark.PINKY_PIP
    ]
    
    # --- Thumb Logic ---
    # Thumb is 'Open' if the tip is farther from the wrist than the IP joint.
    tip_dist = get_distance(lms[tip_ids[0]], wrist_lm)
    pip_dist = get_distance(lms[pip_ids[0]], wrist_lm)
    fingers.append(1 if tip_dist > pip_dist else 0)

    # --- Four Fingers Logic ---
    # Finger is 'Open' if the tip is farther from the wrist than the PIP joint.
    for i in range(1, 5):
        tip_dist = get_distance(lms[tip_ids[i]], wrist_lm)
        pip_dist = get_distance(lms[pip_ids[i]], wrist_lm)
        fingers.append(1 if tip_dist > pip_dist else 0)
            
    return fingers

def is_thumbs_up(hand_landmarks, fingers_list):
    """Check if gesture is thumbs up (thumb pointing upward)."""
    if fingers_list != [1, 0, 0, 0, 0]:
        return False
    lms = hand_landmarks.landmark
    return lms[4].y < lms[2].y - 0.05

def is_thumbs_down(hand_landmarks, fingers_list):
    """Check if gesture is thumbs down (thumb pointing downward)."""
    if fingers_list != [1, 0, 0, 0, 0]:
        return False
    lms = hand_landmarks.landmark
    return lms[4].y > lms[2].y + 0.05

def is_pinch(hand_landmarks, threshold=0.05):
    """Check if thumb and index finger are pinched together."""
    lms = hand_landmarks.landmark
    thumb_tip = lms[mp_hands.HandLandmark.THUMB_TIP]
    index_tip = lms[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    distance = get_distance(thumb_tip, index_tip)
    return distance < threshold

# --- Main Loop ---
while cap.isOpened():
    success, image = cap.read()
    if not success: continue

    # Flip image for selfie view and convert BGR to RGB
    image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
    
    # Process the image to find hands
    results = hands.process(image)
    
    # Convert back to BGR for OpenCV
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    if results.multi_hand_landmarks:
        # Loop through each detected hand
        for hand_index, hand_landmarks in enumerate(results.multi_hand_landmarks):
            
            # Draw landmarks
            mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # --- Get Hand and Finger Data ---
            hand_label = get_hand_label(hand_index, hand_landmarks, results)
            
            # ** NEW FUNCTION CALL **
            # Notice we don't need to pass hand_label anymore!
            fingers_list = get_finger_states(hand_landmarks) 
            
            if fingers_list is None:
                continue

            lms = hand_landmarks.landmark
            
            # --- Gesture Recognition & Actions ---
            current_time = time.time()
            gesture_detected = "None"

            # Toggle program on/off
            if fingers_list == [1, 1, 0, 0, 1]:
                gesture_detected = "POINTER"
                # Only toggle if pointer finger just went up (state change)
                if not pointer_was_up:
                    program_active = not program_active
                    pointer_was_up = True
                    status = "ACTIVE" if program_active else "PAUSED"
                    print(f"Program {status}")
            else:
                # Reset the flag when pointer finger goes down
                pointer_was_up = False
            
            # Only execute other gestures if program is active
            if program_active:
                
                # PINCH: Left click hold/release
                if is_pinch(hand_landmarks, settings.pinch_threshold):
                    gesture_detected = "PINCH"
                    if not pinch_active:
                        leftclick.left_click_down()
                        pinch_active = True
                else:
                    if pinch_active:
                        leftclick.left_click_up()
                        pinch_active = False
                
                # FIST: Single right-click with cooldown
                if fingers_list == [0, 0, 0, 0, 0] or fingers_list == [1, 0, 0, 0, 0]:
                    gesture_detected = "FIST"
                    if current_time - last_fist_action_time > settings.fist_cooldown:
                        rightclick.rightclick()
                        last_fist_action_time = current_time
                
                # THUMBS UP: Continuous scroll up
                elif is_thumbs_up(hand_landmarks, fingers_list):
                    gesture_detected = "THUMBS_UP"
                    scrollup.scroll_up(settings.scroll_speed)
                
                # THUMBS DOWN: Continuous scroll down
                elif is_thumbs_down(hand_landmarks, fingers_list):
                    gesture_detected = "THUMBS_DOWN"
                    scrolldown.scroll_down(settings.scroll_speed)
                
                # OPEN HAND: Move cursor
                if fingers_list == [1, 1, 1, 1, 1]:
                    gesture_detected = "OPEN"
                    openhand.move_cursor(hand_landmarks, settings)

            
            
            last_gesture = gesture_detected
            
            # --- Display Debug Info ON SCREEN ---
            
            # 1. Show Gesture Detected
            if debug:
                cv2.putText(image, f"Gesture: {gesture_detected}", (10, 50), 
                            cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)
                
                # 2. Show Finger States
                cv2.putText(image, f"Fingers: {fingers_list}", (10, 90), 
                            cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
                
                # 3. Show Pinch Distance
                tip_4 = lms[mp_hands.HandLandmark.THUMB_TIP]
                tip_8 = lms[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                distance = get_distance(tip_4, tip_8)
                cv2.putText(image, f"Pinch Dist: {distance:.3f}", (10, 130), 
                            cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)

                # 4. Show Pointing Vector (if index is up)
                if fingers_list == [0, 1, 0, 0, 0]:
                    vec_x = lms[8].x - lms[5].x
                    vec_y = lms[8].y - lms[5].y
                    cv2.putText(image, f"Point Vec: ({vec_x:.2f}, {vec_y:.2f})", (10, 170), 
                                cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
                
                # 5. Show Thumb Vector (if thumb is extended)
                if fingers_list == [1, 0, 0, 0, 0]:
                    vec_y = lms[4].y - lms[2].y
                    cv2.putText(image, f"Thumb Vec Y: {vec_y:.2f}", (10, 210), 
                                cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)

                # 6. Show Hand Label
                cv2.putText(image, f"Hand: {hand_label}", (10, 250), 
                            cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)

    # Increment frame counter
    scroll_frame_counter += 1
    
    # Display program state (always visible, not just in debug mode)
    state_text = "ACTIVE" if program_active else "PAUSED"
    state_color = (0, 255, 0) if program_active else (0, 0, 255)  # Green if active, Red if paused
    cv2.putText(image, f"Program: {state_text}", (10, 30), 
                cv2.FONT_HERSHEY_PLAIN, 2, state_color, 3)

    cv2.imshow('Gesture Detector - DEBUG MODE', image)
    
    # Set window to always stay on top
    cv2.setWindowProperty('Gesture Detector - DEBUG MODE', cv2.WND_PROP_TOPMOST, 1)
    
    if cv2.waitKey(5) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()