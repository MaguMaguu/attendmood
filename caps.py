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
    
    # Convert face image to base64
    _, buffer = cv2.imencode('.jpg', face_image)
    face_base64 = base64.b64encode(buffer).decode('utf-8')
 
    messagebox.showinfo("Success", f"Face registered for {name}")
    global known_face_encodings, known_face_names
    # Add to local face data and save
    known_face_encodings.append(face_encodings[0])
    known_face_names.append(name)
    with open(FACES_PATH, 'wb') as f:
        pickle.dump((known_face_encodings, known_face_names), f)
    # Add student to Firebase for attendance system with face image
    send_to_firebase("students", {
        "name": name,
        "status": "Present",
        "emoji": "😊",
        "face_image": face_base64,
        "timestamp": datetime.datetime.now().isoformat()
    })

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
        messagebox.showwarning("Liveness Check", "Static images are not allowed. Please move your face.")
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
            # Capture face image for attendance
            top, right, bottom, left = face_locations[index]
            face_image = frame[top:bottom, left:right]
            _, buffer = cv2.imencode('.jpg', face_image)
            face_base64 = base64.b64encode(buffer).decode('utf-8')
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
                "face_image": face_base64,
                "timestamp": now.isoformat()
            })
            messagebox.showinfo("Login", f"Welcome back, {name}! Emotion: {emotion}")
            return
    messagebox.showerror("Login Failed", "Face not recognized.")

login_button = create_button(btn_frame, "✅ Take Attendance", "#4CAF50", login_face)
login_button.pack(pady=15)

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
        emotion_label.config(text=f"Emotion: {emotion} ({score:.2f})")

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

            with recognition_lock:
                latest_recognition["name"] = name
                latest_recognition["emotion"] = emotion
                latest_recognition["score"] = score

            print(f"{name} - Emotion: {emotion} ({score:.2f})")
            # Send emotion data to Firebase
            send_to_firebase("emotions", {
                "name": name,
                "emotion": emotion,
                "score": score,
                "timestamp": datetime.datetime.now().isoformat()
            })
            break

        time.sleep(0.5)

# --- Cleanup ---   
def on_close():
    cap.release()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

threading.Thread(target=capture_frames, daemon=True).start()
threading.Thread(target=process_faces, daemon=True).start()
update_camera()
root.mainloop()
