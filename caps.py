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

ENCODINGS_FILE = "encodings.pickle"

def save_encoding(name, encoding):
    if os.path.exists(ENCODINGS_FILE):
        with open(ENCODINGS_FILE, "rb") as f:
            data = pickle.load(f)
    else:
        data = {}
    data[name] = encoding.tolist()
    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump(data, f)

def load_encodings():
    if not os.path.exists(ENCODINGS_FILE):
        return [], []
    with open(ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)
    names = list(data.keys())
    encodings = [np.array(e) for e in data.values()]
    return encodings, names

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
root.geometry("700x450")
root.configure(bg='white')

cap = cv2.VideoCapture(0)

camera_frame = tk.Frame(root, width=300, height=250, bg='white', highlightbackground="black", highlightthickness=3)
camera_frame.place(x=30, y=30)
camera_label = tk.Label(camera_frame)
camera_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

emotion_label = tk.Label(root, text="Emotion: ", font=("Helvetica", 14), bg="white")
emotion_label.place(x=30, y=300)

known_face_encodings, known_face_names = load_encodings()
emotion_detector = FER(mtcnn=True)

# --- Frame Capture Thread Setup ---
frame_lock = threading.Lock()
current_frame = None

def capture_frames():
    global current_frame
    while True:
        ret, frame = cap.read()
        if ret:
            with frame_lock:
                current_frame = frame.copy()

def update_camera():
    with frame_lock:
        frame = current_frame.copy() if current_frame is not None else None

    if frame is not None:
        # Resize for display to improve performance
        resized_frame = cv2.resize(frame, (300, 250))
        rgb_display = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb_display)
        imgtk = ImageTk.PhotoImage(image=img)
        camera_label.imgtk = imgtk
        camera_label.configure(image=imgtk)

        # Use full-sized frame for recognition
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
            name = "Unknown"
            if True in matches:
                match_index = matches.index(True)
                name = known_face_names[match_index]

            face_image = rgb_frame[top:bottom, left:right]
            emotion, score = emotion_detector.top_emotion(face_image) or ("Neutral", 0.0)
            emotion_label.config(text=f"Emotion: {emotion} ({score:.2f})")
            print(f"{name} - Emotion: {emotion} ({score:.2f})")

    camera_label.after(30, update_camera)

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
    face_encodings = face_recognition.face_encodings(rgb_frame)
    if len(face_encodings) != 1:
        messagebox.showwarning("Face Detection", "Ensure one real face is visible.")
        return
    name = simpledialog.askstring("Register", "Enter your name:")
    if not name:
        return
    save_encoding(name, face_encodings[0])
    messagebox.showinfo("Success", f"Face registered for {name}")
    global known_face_encodings, known_face_names
    known_face_encodings, known_face_names = load_encodings()

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
    face_encodings = face_recognition.face_encodings(rgb_frame)
    if len(face_encodings) == 0:
        messagebox.showwarning("Face Detection", "No face detected.")
        return
    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"
        if True in matches:
            index = matches.index(True)
            name = known_face_names[index]
            messagebox.showinfo("Login", f"Welcome back, {name}!")
            return
    messagebox.showerror("Login Failed", "Face not recognized.")

login_button = tk.Button(root, text="Login", bg="green", fg="white", width=20, height=2, command=login_face)
login_button.place(x=400, y=60)

register_button = tk.Button(root, text="Register", bg="deepskyblue", fg="white", width=20, height=2, command=register_face)
register_button.place(x=400, y=140)

def on_close():
    cap.release()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

# Start camera update loop and frame capture thread
threading.Thread(target=capture_frames, daemon=True).start()
update_camera()
root.mainloop()
    