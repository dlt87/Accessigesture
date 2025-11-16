# import important libraries
import cv2
import mediapipe as mp
import math
import time
import pyautogui
import tkinter as tk 

# --- pywin32 for window control ---
try:
    import win32api
    import win32con
    import win32gui
except ImportError:
    print("pywin32 not found. Window style cannot be changed.")
    print("Run: pip install pywin32")
# --- END NEW ---

from gestures import rightclick
from gestures import openhand
from gestures import scrollup
from gestures import scrolldown
from gestures import leftclick
from settings_window import SettingsWindow

# --- Global running flag ---
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

# --- Pass the quit function to the settings window ---
settings = SettingsWindow(on_quit=quit_program)
settings.create_window()

# --- Setup ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,  # Only track one hand for better performance
    model_complexity=0,  # Use lightweight model for speed (0=fastest, 1=balanced)
    min_detection_confidence=settings.min_detection_confidence, 
    min_tracking_confidence=settings.min_tracking_confidence
)
mp_drawing = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)
# Optimize for low latency
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)  # Lower resolution = faster processing
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize camera buffer lag
cap.set(cv2.CAP_PROP_FPS, 60)  # Request higher FPS if camera supports it
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

# --- NEW: Track window style state ---
last_lock_state = None
# --- END NEW ---

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
cv2.namedWindow(window_name)
cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
cv2.moveWindow(window_name, 0, 0)

while cap.isOpened() and running:
    success, image = cap.read()
    if not success: 
        running = False
        continue

    # Optimize: Flip and convert in one step, process immediately
    image = cv2.flip(image, 1)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Process hand detection (this is the main bottleneck)
    results = hands.process(image_rgb)
    
    # Continue using the BGR image for display (skip unnecessary conversion back)
    # image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)  # Not needed!

    gesture_detected = "None" 
    action_to_perform = "None" 

    if results.multi_hand_landmarks:
        for hand_index, hand_landmarks in enumerate(results.multi_hand_landmarks):
            
            # Only draw landmarks if debug mode is on (saves processing time)
            if debug:
                mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            fingers_list = get_finger_states(hand_landmarks) 
            if fingers_list is None: continue
            
            lms = hand_landmarks.landmark
            current_time = time.time()
            
            # --- (All gesture detection and action logic remains the same) ---
            
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
            else:
                pointer_was_up = False
                
            # 4. --- EXECUTE ACTIONS (if active) ---
            if program_active and gesture_detected != "TOGGLE":
                action_function = AVAILABLE_ACTIONS.get(action_to_perform)

                if action_function:
                    if action_to_perform == "Move Cursor":
                        action_function(hand_landmarks) 
                    
                    elif action_to_perform == "Left Click (Hold)":
                        # NEW PINCH TIMING LOGIC
                        if not pinch_active:
                            # First frame of pinch detected
                            pinch_start_time = current_time
                            pinch_active = True
                            pinch_is_held = False
                        else:
                            # Pinch is being held
                            pinch_duration = current_time - pinch_start_time
                            
                            # If held for more than 1 second and not yet transitioned to hold
                            if pinch_duration >= 0.3 and not pinch_is_held:
                                action_function()  # Press and hold
                                pinch_is_held = True
                                
                        
                        # Always move cursor while pinching
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

    # --- (Click release logic remains the same) ---
    if 'current_mappings' in locals(): 
        click_hold_gesture = current_mappings.get("Left Click (Hold)", "None")
        if gesture_detected != click_hold_gesture and pinch_active:
            # Pinch gesture ended
            pinch_duration = current_time - pinch_start_time if pinch_start_time else 0
            
            if pinch_duration < 0.5:
                # Quick pinch (< 1 second) - perform single click
                pyautogui.click()  # Single click action
            elif pinch_is_held:
                # Long pinch was held - release the held button
                AVAILABLE_ACTIONS["Left Click (Release)"]()
            
            # Reset pinch state
            pinch_active = False
            pinch_start_time = None
            pinch_is_held = False

    scroll_frame_counter += 1
    
    state_text = "ACTIVE" if program_active else "PAUSED"
    state_color = (0, 255, 0) if program_active else (0, 0, 255) 
    cv2.putText(image, f"Program: {state_text}", (10, 30), 
                cv2.FONT_HERSHEY_PLAIN, 2, state_color, 3)

    cv2.imshow(window_name, image)
    
    # Ensure window stays on top every frame
    try:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
    except:
        pass
    
    # --- NEW: DYNAMIC WINDOW STYLE ---
    # Check if the state has changed
    current_lock_state = settings.camera_window_locked
    if current_lock_state != last_lock_state:
        try:
            hwnd = win32gui.FindWindow(None, window_name)
            if hwnd:
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

                if current_lock_state:
                    # LOCK THE WINDOW
                    # Add click-through and remove title bar
                    style = style & ~win32con.WS_CAPTION & ~win32con.WS_SYSMENU
                    ex_style = ex_style | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED
                    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
                else:
                    # UNLOCK THE WINDOW
                    # Add title bar and remove click-through
                    style = style | win32con.WS_CAPTION | win32con.WS_SYSMENU
                    ex_style = ex_style & ~win32con.WS_EX_TRANSPARENT & ~win32con.WS_EX_LAYERED
                    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
                
                # Force window to update its frame
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0,0,0,0, 
                                     win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED)
                print(f"Window locked: {current_lock_state}")

            last_lock_state = current_lock_state
        except Exception as e:
            print(f"Error setting window style: {e}")
    # --- END NEW ---

    # Reduce waitKey to absolute minimum for lower latency
    # 1ms is the minimum, any lower and OpenCV won't process events
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        running = False 
    
    try:
        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            running = False
    except cv2.error:
        running = False
    
    if not settings.thread.is_alive():
        running = False 

# --- Cleanup ---
cap.release()
cv2.destroyAllWindows()