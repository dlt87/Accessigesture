# import important libraries
import cv2
import mediapipe as mp
import math
import time
import pyautogui
import tkinter as tk 

# --- NEW: pywin32 for click-through ---
# (Keep this if you still want the click-through window)
try:
    import win32api
    import win32con
    import win32gui
except ImportError:
    print("pywin32 not found. Window click-through will be disabled.")
# --- END NEW ---

from gestures import rightclick
from gestures import openhand
from gestures import scrollup
from gestures import scrolldown
from gestures import leftclick
from settings_window import SettingsWindow

# --- NEW: Global running flag ---
running = True

def quit_program():
    """Sets the global running flag to False."""
    global running
    print("Quit signal received. Shutting down...")
    running = False
# --- END NEW ---

# --- Action Function Dictionary ---
AVAILABLE_ACTIONS = {
    "None": (lambda: None),
    "Left Click (Hold)": leftclick.left_click_down,
    "Left Click (Release)": leftclick.left_click_up, 
    "Right Click (Once)": rightclick.rightclick,
    "Scroll Up": (lambda: scrollup.scroll_up(settings.scroll_speed)),
    "Scroll Down": (lambda: scrolldown.scroll_down(settings.scroll_speed)),
    "Move Cursor": (lambda hand_landmarks: openhand.move_cursor(hand_landmarks, settings))
}

pyautogui.FAILSAFE = False

# --- NEW: Pass the quit function to the settings window ---
settings = SettingsWindow(on_quit=quit_program)
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
last_gesture = None 
scroll_frame_counter = 0 
SCROLL_EVERY_N_FRAMES = 2 
pinch_active = False 
debug = True
program_active = True 
pointer_was_up = False 
window_name = "accessiGesture"
window_handle_set = False # For click-through

# --- Helper Functions (No changes) ---
def get_distance(lm1, lm2):
    return math.hypot(lm1.x - lm2.x, lm1.y - lm2.y)

def get_hand_label(index, hand, results):
    label = None
    if results.multi_handedness:
        classification = results.multi_handedness[index]
        if classification.classification:
            label = classification.classification[0].label
    return label

def get_finger_states(hand_landmarks):
    if hand_landmarks is None: return None
    fingers = []
    lms = hand_landmarks.landmark
    wrist_lm = lms[mp_hands.HandLandmark.WRIST]
    tip_ids = [
        mp_hands.HandLandmark.THUMB_TIP, mp_hands.HandLandmark.INDEX_FINGER_TIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_TIP, mp_hands.HandLandmark.RING_FINGER_TIP,
        mp_hands.HandLandmark.PINKY_TIP
    ]
    pip_ids = [
        mp_hands.HandLandmark.THUMB_IP, mp_hands.HandLandmark.INDEX_FINGER_PIP,
        mp_hands.HandLandmark.MIDDLE_FINGER_PIP, mp_hands.HandLandmark.RING_FINGER_PIP,
        mp_hands.HandLandmark.PINKY_PIP
    ]
    tip_dist = get_distance(lms[tip_ids[0]], wrist_lm)
    pip_dist = get_distance(lms[pip_ids[0]], wrist_lm)
    fingers.append(1 if tip_dist > pip_dist else 0)
    for i in range(1, 5):
        tip_dist = get_distance(lms[tip_ids[i]], wrist_lm)
        pip_dist = get_distance(lms[pip_ids[i]], wrist_lm)
        fingers.append(1 if tip_dist > pip_dist else 0)
    return fingers

def is_thumbs_up(hand_landmarks, fingers_list):
    if fingers_list != [1, 0, 0, 0, 0]: return False
    lms = hand_landmarks.landmark
    return lms[4].y < lms[2].y - 0.05

def is_thumbs_down(hand_landmarks, fingers_list):
    if fingers_list != [1, 0, 0, 0, 0]: return False
    lms = hand_landmarks.landmark
    return lms[4].y > lms[2].y + 0.05

def is_pinch(hand_landmarks, threshold=0.05):
    lms = hand_landmarks.landmark
    thumb_tip = lms[mp_hands.HandLandmark.THUMB_TIP]
    index_tip = lms[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    distance = get_distance(thumb_tip, index_tip)
    return distance < threshold

def is_pinch_mid(hand_landmarks, threshold=0.05):
    lms = hand_landmarks.landmark
    thumb_tip = lms[mp_hands.HandLandmark.THUMB_TIP]
    index_tip = lms[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    distance = get_distance(thumb_tip, index_tip)
    return distance < threshold

# --- Main Loop ---
# --- NEW: Check the 'running' flag ---
while cap.isOpened() and running:
    success, image = cap.read()
    if not success: 
        running = False # Stop if camera fails
        continue

    image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
    results = hands.process(image)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    gesture_detected = "None" 
    action_to_perform = "None" 

    if results.multi_hand_landmarks:
        for hand_index, hand_landmarks in enumerate(results.multi_hand_landmarks):
            
            mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            fingers_list = get_finger_states(hand_landmarks) 
            if fingers_list is None: continue
            
            lms = hand_landmarks.landmark
            current_time = time.time()
            
            # --- (All the gesture detection and action logic remains the same) ---
            
            # 1. --- DETECT GESTURE ---
            if is_pinch(hand_landmarks, settings.pinch_threshold):
                gesture_detected = "PINCH"
            elif is_pinch_mid(hand_landmarks, settings.pinch_threshold):
                gesture_detected = "PINCH_MID"
            elif is_thumbs_up(hand_landmarks, fingers_list):
                gesture_detected = "THUMBS_UP"
            elif is_thumbs_down(hand_landmarks, fingers_list):
                gesture_detected = "THUMBS_DOWN"
            elif fingers_list == [1, 1, 1, 1, 1]:
                gesture_detected = "OPEN"
            elif fingers_list == [1, 1, 0, 0, 1]:
                gesture_detected = "TOGGLE" 

            # 2. --- LOOKUP ACTION ---
            current_mappings = {}
            if settings.action_mappings: 
                for action, var in settings.action_mappings.items():
                    current_mappings[action] = var.get()

            for action_name, gesture_name in current_mappings.items():
                if gesture_name == gesture_detected:
                    action_to_perform = action_name
                    break 
            
            # 3. --- HANDLE TOGGLE (ALWAYS) ---
            if gesture_detected == "TOGGLE":
                if not pointer_was_up:
                    program_active = not program_active
                    pointer_was_up = True
                    status = "ACTIVE" if program_active else "PAUSED"
                    print(f"Program {status}")
            else:
                pointer_was_up = False
                
            # 4. --- EXECUTE ACTIONS (if active) ---
            if program_active and gesture_detected != "TOGGLE":
                action_function = AVAILABLE_ACTIONS.get(action_to_perform)

                if action_function:
                    if action_to_perform == "Move Cursor":
                        action_function(hand_landmarks) 
                    
                    elif action_to_perform == "Left Click (Hold)":
                        if not pinch_active:
                            action_function()
                            pinch_active = True
                        
                        # --- CLICK AND DRAG FIX ---
                        move_action_func = AVAILABLE_ACTIONS.get("Move Cursor")
                        if move_action_func:
                            move_action_func(hand_landmarks)
                    
                    elif action_to_perform == "Right Click (Once)":
                        if current_time - last_fist_action_time > settings.fist_cooldown:
                            action_function()
                            last_fist_action_time = current_time
                            
                    elif action_to_perform in ["Scroll Up", "Scroll Down"]:
                        if scroll_frame_counter % SCROLL_EVERY_N_FRAMES == 0:
                            action_function()
            
            # --- (Debug text remains the same) ---
            if debug:
                cv2.putText(image, f"Gesture: {gesture_detected}", (10, 50), 
                            cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)
                cv2.putText(image, f"Action: {action_to_perform}", (10, 90), 
                            cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

    # --- (Click release logic remains the same) ---
    if 'current_mappings' in locals(): 
        click_hold_gesture = current_mappings.get("Left Click (Hold)", "None")
        if gesture_detected != click_hold_gesture and pinch_active:
            AVAILABLE_ACTIONS["Left Click (Release)"]()
            pinch_active = False

    scroll_frame_counter += 1
    
    state_text = "ACTIVE" if program_active else "PAUSED"
    state_color = (0, 255, 0) if program_active else (0, 0, 255) 
    cv2.putText(image, f"Program: {state_text}", (10, 30), 
                cv2.FONT_HERSHEY_PLAIN, 2, state_color, 3)

    cv2.imshow(window_name, image)
    
    # --- (Click-through logic remains the same) ---
    if not window_handle_set:
        try:
            hwnd = cv2.getWindowProperty(window_name, cv2.WND_PROP_HWND)
            style = win32api.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            style = style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
            win32api.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)
            win32gui.SetLayeredWindowAttributes(hwnd, 0, 250, win32con.LWA_ALPHA)
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0,0,0,0, 
                                 win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            window_handle_set = True
        except Exception as e:
            pass 

    # --- NEW: Check 'running' flag instead of 'q' key ---
    if cv2.waitKey(1) & 0xFF == ord('q'):
        running = False # 'q' key still works
    
    # Check if window was closed
    try:
        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            running = False # Stop if CV window is closed
    except cv2.error:
        running = False # Stop if CV window is destroyed
    
    # Check if the settings window thread is still alive
    if not settings.thread.is_alive():
        running = False # Stop if settings window was closed

# --- Cleanup ---
cap.release()
cv2.destroyAllWindows()
print("Main loop finished. Exiting.")