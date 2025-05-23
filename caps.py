import tkinter as tk
from tkinter import simpledialog, messagebox
from PIL import Image, ImageTk
import cv2
import face_recognition
import numpy as np
import os
import pickle
import time
import threading
from fer import FER
import requests
import datetime
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db 
import base64

FIREBASE_URL = "https://moodattend-default-rtdb.asia-southeast1.firebasedatabase.app"
cred_path = r'C:\Users\pc\Downloads\database.json'
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://moodattend-default-rtdb.asia-southeast1.firebasedatabase.app/'
})
# --- Utility Functions ---


def is_face_moving(threshold=10):
    positions = []
    for _ in range(5):
        with frame_lock:
            frame = current_frame.copy() if current_frame is not None else None
        if frame is None:
            return False
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        if len(face_locations) != 1:
            return False
        top, right, bottom, left = face_locations[0]
        center = ((left + right) // 2, (top + bottom) // 2)
        positions.append(center)
        time.sleep(0.2)
    movement = sum(
        np.linalg.norm(np.array(positions[i]) - np.array(positions[i - 1]))
        for i in range(1, len(positions))
    )
    return movement > threshold

# --- GUI Setup ---
root = tk.Tk()
root.title("Face Login/Register with Emotion Analysis")
root.geometry("800x500")
root.configure(bg="#f2f2f2")

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FPS, 30)

header = tk.Label(root, text="Emotion-Based Attendance System", font=("Helvetica", 18, "bold"), bg="#f2f2f2", fg="#333")
header.pack(pady=10)

camera_frame = tk.Frame(root, width=400, height=300, bg="#1e1e1e", highlightbackground="black", highlightthickness=1)
camera_frame.place(x=50, y=80)

camera_label = tk.Label(camera_frame, bg="#1e1e1e")
camera_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

emotion_label = tk.Label(root, text="Emotion: Detecting... (0.00)", font=("Helvetica", 12), bg="#f2f2f2", fg="#555")
emotion_label.place(x=50, y=400)

btn_frame = tk.Frame(root, bg="#f2f2f2")
btn_frame.place(x=500, y=150)

# Add timer and instruction labels to the UI
countdown_label = tk.Label(root, text="", font=("Helvetica", 16, "bold"), bg="#f2f2f2", fg="#d32f2f")
countdown_label.place(x=500, y=80)
stay_still_label = tk.Label(root, text="", font=("Helvetica", 14), bg="#f2f2f2", fg="#1976d2")
stay_still_label.place(x=500, y=120)

def create_button(master, text, bg_color, command=None):
    return tk.Button(master, text=text, width=20, height=2,
                     bg=bg_color, fg="white", font=("Helvetica", 12, "bold"),
                     relief="flat", activebackground="#444", command=command)

def send_to_firebase(path, data):
    url = f"{FIREBASE_URL}/{path}.json"
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            print(f"Data sent to Firebase at {path}.")
        else:
            print(f"Failed to send data to Firebase: {response.text}")
    except Exception as e:
        print(f"Firebase error: {e}")

# --- Persistent Face Data ---
FACES_PATH = 'faces.pkl'
try:
    with open(FACES_PATH, 'rb') as f:
        known_face_encodings, known_face_names = pickle.load(f)
except Exception:
    known_face_encodings, known_face_names = [], []

def register_face():
    if not is_face_moving():
        messagebox.showwarning("Liveness Check", "Please move your face slightly. Static images are not allowed.")
        return
    with frame_lock:
        frame = current_frame.copy() if current_frame is not None else None
    if frame is None:
        messagebox.showerror("Error", "Camera error.")
        return
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame)
    if len(face_encodings) != 1 or len(face_locations) != 1:
        messagebox.showwarning("Face Detection", "Ensure one real face is visible.")
        return
    
    # Now prompt for the name after face is detected
    name = simpledialog.askstring("Register", "Enter your full name:")
    if not name:
        return
    
    # Capture face image
    top, right, bottom, left = face_locations[0]
    face_image = frame[top:bottom, left:right]
    
    # Save face image locally
    save_dir = 'registered_faces'
    os.makedirs(save_dir, exist_ok=True)
    timestamp_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = "_".join(name.split())
    filename = f"{safe_name}_{timestamp_str}.jpg"
    save_path = os.path.join(save_dir, filename)
    cv2.imwrite(save_path, face_image)
    
    messagebox.showinfo("Success", f"Face registered for {name}\nSaved at: {save_path}")
    global known_face_encodings, known_face_names
    # Add to local face data and save
    known_face_encodings.append(face_encodings[0])
    known_face_names.append(name)
    with open(FACES_PATH, 'wb') as f:
        pickle.dump((known_face_encodings, known_face_names), f)
    

# --- Emotion to Emoji Mapping ---
EMOTION_EMOJI = {
    'angry': '😠',
    'disgust': '🤢',
    'fear': '😨',
    'happy': '😊',
    'sad': '😢',
    'surprise': '😲',
    'neutral': '😐',
    'Detecting...': '😐',
    'Neutral': '😐',
}

def login_face():
    if not is_face_moving():
        messagebox.showwarning("Liveness Check", "Images are not allowed. Please move your face.")
        return
    with frame_lock:
        frame = current_frame.copy() if current_frame is not None else None
    if frame is None:
        messagebox.showerror("Error", "Camera error.")
        return
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame)
    if len(face_encodings) == 0:
        messagebox.showwarning("Face Detection", "No face detected.")
        return
    for (face_location, face_encoding) in zip(face_locations, face_encodings):
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"
        if True in matches:
            index = matches.index(True)
            name = known_face_names[index]
            # Get latest emotion
            with recognition_lock:
                emotion = latest_recognition["emotion"]
                score = latest_recognition["score"]
            emoji = EMOTION_EMOJI.get(str(emotion).lower(), '😊')
            # Determine attendance status based on current time
            now = datetime.datetime.now()
            hour = now.hour
            minute = now.minute
            if hour < 8 or (hour == 8 and minute == 0):
                status = "Present"
            elif hour < 12:
                status = "Late"
            else:
                status = "Absent"
            send_to_firebase("students", {
                "name": name,
                "status": status,
                "emotion": emotion,
                "score": score,
                "emoji": emoji,
                "timestamp": now.isoformat()
            })
            messagebox.showinfo("Success", f"Welcome back, {name}! Emotion: {emotion}")
            return
    messagebox.showerror("Attendance Failed", "Face not recognized.")

register_button = create_button(btn_frame, "➕ Register", "#2196F3", register_face)
register_button.pack(pady=15)

# --- Shared State ---
emotion_detector = FER(mtcnn=True)

frame_lock = threading.Lock()
current_frame = None

latest_recognition = {
    "emotion": "Detecting...",
    "score": 0.0,
    "name": "Unknown"
}
recognition_lock = threading.Lock()

# Add timer and instruction labels to the UI
countdown_seconds = 5
countdown_active = False
countdown_remaining = 0
countdown_face_name = None
countdown_last_frame_time = 0

def start_countdown(name):
    global countdown_active, countdown_remaining, countdown_face_name
    countdown_active = True
    countdown_remaining = countdown_seconds
    countdown_face_name = name
    stay_still_label.config(text=f"Stay still, {name}! Taking attendance in...")
    update_countdown_label()

def stop_countdown():
    global countdown_active, countdown_remaining, countdown_face_name
    countdown_active = False
    countdown_remaining = 0
    countdown_face_name = None
    countdown_label.config(text="")
    stay_still_label.config(text="")

def update_countdown_label():
    global countdown_remaining
    if countdown_active and countdown_remaining > 0:
        countdown_label.config(text=f"{countdown_remaining} seconds")
        countdown_remaining -= 1
        root.after(1000, update_countdown_label)
    elif countdown_active:
        countdown_label.config(text="Taking attendance...")
    else:
        countdown_label.config(text="")

# --- Threads ---
def capture_frames():
    global current_frame
    while True:
        ret, frame = cap.read()
        if ret:
            with frame_lock:
                current_frame = frame
        time.sleep(0.01)

def update_camera():
    with frame_lock:
        frame = current_frame.copy() if current_frame is not None else None

    if frame is not None:
        resized_frame = cv2.resize(frame, (400, 300))
        rgb_display = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb_display)
        imgtk = ImageTk.PhotoImage(image=img)
        camera_label.imgtk = imgtk
        camera_label.configure(image=imgtk)

        with recognition_lock:
            emotion = latest_recognition["emotion"]
            score = latest_recognition["score"]
        safe_score = score if score is not None else 0.0
        emotion_label.config(text=f"Emotion: {emotion} ({safe_score:.2f})")

    camera_label.after(15, update_camera)

def process_faces():
    global latest_recognition
    while True:
        with frame_lock:
            frame = current_frame.copy() if current_frame is not None else None

        if frame is None:
            time.sleep(0.1)
            continue

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            name = "Unknown"
            matches = face_recognition.compare_faces( known_face_encodings, face_encoding)
            if True in matches:
                match_index = matches.index(True)
                name = known_face_names[match_index]

            face_image = rgb_frame[top:bottom, left:right]
            emotion, score = emotion_detector.top_emotion(face_image) or ("Neutral", 0.0)
            # Always map emotion to emoji using EMOTION_EMOJI
            mapped_emotion = str(emotion).lower() if emotion else "neutral"
            emoji = EMOTION_EMOJI.get(mapped_emotion, EMOTION_EMOJI["neutral"])

            with recognition_lock:
                latest_recognition["name"] = name
                latest_recognition["emotion"] = emotion
                latest_recognition["score"] = score

            print(f"{name} - Emotion: {emotion} ({score:.2f}) {emoji}")
            # Removed: send_to_firebase("emotions", {...})
            break

        time.sleep(0.5)

def auto_attendance_loop():
    last_name = None
    last_time = 0
    global countdown_active, countdown_remaining, countdown_face_name
    while True:
        with frame_lock:
            frame = current_frame.copy() if current_frame is not None else None
        detected_name = None
        if frame is not None:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame)
            if len(face_encodings) > 0:
                for (face_location, face_encoding) in zip(face_locations, face_encodings):
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                    if True in matches:
                        index = matches.index(True)
                        name = known_face_names[index]
                        detected_name = name
                        now = time.time()
                        # Only start countdown if not taken for this person in the last 30 seconds
                        if (name != last_name or (now - last_time) > 30):
                            if not countdown_active or countdown_face_name != name:
                                start_countdown(name)
                        # If countdown is active and for this face, and finished, take attendance
                        if countdown_active and countdown_face_name == name and countdown_remaining == 0:
                            login_face()
                            last_name = name
                            last_time = now
                            stop_countdown()
                        break
        # If no registered face detected, stop countdown
        if not detected_name or (countdown_active and detected_name != countdown_face_name):
            stop_countdown()
        time.sleep(0.5)

# --- Cleanup ---   
def on_close():
    cap.release()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

threading.Thread(target=capture_frames, daemon=True).start()
threading.Thread(target=process_faces, daemon=True).start()
threading.Thread(target=auto_attendance_loop, daemon=True).start()
update_camera()
root.mainloop()
