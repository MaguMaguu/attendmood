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
import glob

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
root.geometry("850x500") 
root.configure(bg="#f2f2f2")

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    messagebox.showerror("Camera Error", "Cannot open camera. Please check your camera connection and permissions.")
    root.destroy()
    exit()
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FPS, 30)

# Header with logo and text
header_frame = tk.Frame(root, bg="#f2f2f2")
header_frame.pack(pady=10)

# Load and display logo
logo_img = Image.open("logo.png")
logo_img = logo_img.resize((40, 40), Image.LANCZOS)
logo_photo = ImageTk.PhotoImage(logo_img)
logo_label = tk.Label(header_frame, image=logo_photo, bg="#f2f2f2")
logo_label.image = logo_photo  
logo_label.pack(side=tk.LEFT, padx=(0, 10))

header = tk.Label(header_frame, text="MoodAttend", font=("Helvetica", 18, "bold"), bg="#f2f2f2", fg="#333")
header.pack(side=tk.LEFT)

camera_frame = tk.Frame(root, width=400, height=300, bg="#1e1e1e", highlightbackground="black", highlightthickness=1)
camera_frame.place(x=50, y=80)

camera_label = tk.Label(camera_frame, bg="#1e1e1e")
camera_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

# Add pose image beside the camera
try:
    pose_img = Image.open("pose.png")
    pose_img = pose_img.resize((250, 200), Image.LANCZOS)
    pose_photo = ImageTk.PhotoImage(pose_img)
    pose_frame = tk.Frame(root, bg="#f2f2f2")
    pose_frame.place(x=470, y=200)  # Position to the right of the camera, vertically centered
    pose_label = tk.Label(pose_frame, image=pose_photo, bg="#f2f2f2")
    pose_label.image = pose_photo
    pose_label.pack()
    pose_text = tk.Label(pose_frame, text="Align your face as shown", font=("Helvetica", 10), bg="#f2f2f2", fg="#555")
    pose_text.pack(pady=(2, 0))
except Exception as e:
    print(f"Could not load pose image: {e}")

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
encodings = []
names = []
registered_faces_dir = 'registered_faces'
for img_path in glob.glob(os.path.join(registered_faces_dir, '*.jpg')):
    # Extract name from filename (remove timestamp and extension)
    base = os.path.basename(img_path)
    name_part = base.rsplit('_', 1)[0]  # Remove last _timestamp.jpg
    name = name_part.replace('_', ' ').title()
    image = cv2.imread(img_path)
    if image is None:
        print(f"Warning: Could not read image {img_path}")
        continue
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    face_encs = face_recognition.face_encodings(rgb_image)
    if len(face_encs) == 0:
        print(f"Warning: No face found in {img_path}")
        continue
    encodings.append(face_encs[0])
    names.append(name)
print(f"Loaded {len(names)} registered faces: {names}")

# --- Emotion to Emoji Mapping ---
EMOTION_EMOJI = {
    'angry': '😠',
    'happy': '😊',
    'sad': '😢',
    'neutral': '😐',
    'Detecting...': '😐',
    'Neutral': '😐',
}

def has_attended_today(name):
    try:
        url = f"{FIREBASE_URL}/students.json"
        response = requests.get(url)
        if response.status_code == 200 and response.json():
            data = response.json()
            today = datetime.datetime.now().date()
            for key, value in data.items():
                if value.get('name') == name:
                    timestamp = value.get('timestamp')
                    if timestamp:
                        try:
                            date = datetime.datetime.fromisoformat(timestamp).date()
                        except Exception:
                            continue
                        if date == today:
                            return True
        return False
    except Exception as e:
        print(f"Error checking attendance: {e}")
        return False

def login_face(skip_liveness=False):
    if not skip_liveness and not is_face_moving():
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
        matches = face_recognition.compare_faces(encodings, face_encoding, tolerance=0.4)
        name = "Unknown"
        if True in matches:
            index = matches.index(True)
            name = names[index]
            # Check if already attended today
            if has_attended_today(name):
                messagebox.showinfo("Attendance", f"{name}, you have already taken attendance today.")
                return
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
            else:
                status = "Late"
            send_to_firebase("students", {
                "name": name,
                "status": status,
                "emotion": emotion,
                "score": score,
                "emoji": emoji,
                "timestamp": now.isoformat()
            })
            # Show a custom popup that disappears after 1 second
            def show_auto_close_popup(msg):
                popup = tk.Toplevel(root)
                popup.overrideredirect(True)
                popup.configure(bg="#d4edda")
                popup.attributes("-topmost", True)
                x = root.winfo_x() + 300
                y = root.winfo_y() + 200
                popup.geometry(f"300x60+{x}+{y}")
                label = tk.Label(popup, text=msg, font=("Helvetica", 14, "bold"), bg="#d4edda", fg="#155724", padx=20, pady=10)
                label.pack(expand=True, fill="both")
                popup.after(1000, popup.destroy)
            show_auto_close_popup(f"Welcome, {name}! Emotion: {emotion}")
            return
    messagebox.showerror("Attendance Failed", "Face not recognized.")

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
countdown_seconds = 3
countdown_active = False
countdown_remaining = 0
countdown_face_name = None
countdown_last_frame_time = 0

def start_countdown(first_name):
    global countdown_active, countdown_remaining, countdown_face_name
    countdown_active = True
    countdown_remaining = countdown_seconds
    countdown_face_name = first_name
    stay_still_label.config(text=f"Stay still, {first_name}! Taking attendance in...")
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
        frame = current_frame if current_frame is not None else None

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

    # Use after with a short interval for continuous updates
    camera_label.after(10, update_camera)

def process_faces():
    global latest_recognition
    allowed_emotions = {"happy", "sad", "angry"}
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
            matches = face_recognition.compare_faces(encodings, face_encoding, tolerance=0.4)
            if True in matches:
                match_index = matches.index(True)
                name = names[match_index]

            face_image = rgb_frame[top:bottom, left:right]
            result = emotion_detector.top_emotion(face_image)
            if result is not None:
                emotion, score = result
                if score is None:
                    score = 0.0
                # Only allow happy, sad, angry
                if str(emotion).lower() not in allowed_emotions:
                    emotion = "Neutral"
            else:
                emotion, score = "Neutral", 0.0
            mapped_emotion = str(emotion).lower() if emotion else "neutral"
            emoji = EMOTION_EMOJI.get(mapped_emotion, EMOTION_EMOJI["neutral"])

            with recognition_lock:
                latest_recognition["name"] = name
                latest_recognition["emotion"] = emotion
                latest_recognition["score"] = score

            print(f"{name} - Emotion: {emotion} ({score:.2f}) {emoji}")
            break

        time.sleep(0.05)

def auto_attendance_loop():
    last_name = None
    last_time = 0
    global countdown_active, countdown_remaining, countdown_face_name
    FACE_MATCH_THRESHOLD = 0.5  # Lower is stricter, typical values: 0.4-0.6
    while True:
        with frame_lock:
            frame = current_frame.copy() if current_frame is not None else None
        detected_name = None
        if frame is not None and len(encodings) > 0:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame)
            if len(face_encodings) > 0:
                for (face_location, face_encoding) in zip(face_locations, face_encodings):
                    distances = face_recognition.face_distance(encodings, face_encoding)
                    if len(distances) == 0:
                        continue
                    best_match_index = np.argmin(distances)
                    best_distance = distances[best_match_index]
                    if best_distance < FACE_MATCH_THRESHOLD:
                        name = names[best_match_index]
                        print(f"Attendance match: {name} (distance: {best_distance:.3f})")
                        detected_name = name
                        now = time.time()
                        # Extract first name for countdown
                        first_name = name.split()[0] if name else name
                        if (name != last_name or (now - last_time) > 10):
                            if not countdown_active or countdown_face_name != first_name:
                                start_countdown(first_name)
                        if countdown_active and countdown_face_name == first_name and countdown_remaining == 0:
                            login_face(skip_liveness=True)
                            last_name = name
                            last_time = now
                            stop_countdown()
                        break
        if not detected_name or (countdown_active and detected_name.split()[0] != countdown_face_name):
            stop_countdown()
        time.sleep(0.05)

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
