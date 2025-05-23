import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import requests
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db 
import cv2
from PIL import Image, ImageTk
import tkinter.filedialog as filedialog
import tkinter.messagebox as msg
from tkcalendar import DateEntry  # Add this import at the top with other imports
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


# --- Setup ---
root = tk.Tk()
root.title("Mood Attend - Attendance")
root.geometry("1000x650")
root.configure(bg='#f3f6fc')

# --- Modern Fonts ---
FONT_HEADER = ('Segoe UI', 18, 'bold')
FONT_SUBHEADER = ('Segoe UI', 12, 'bold')
FONT_NORMAL = ('Segoe UI', 11)
FONT_BUTTON = ('Segoe UI', 10, 'bold')
FONT_CARD = ('Segoe UI', 10)

# --- Header Bar ---
header_frame = tk.Frame(root, bg='#6366f1', height=60)
header_frame.pack(fill='x')
header_label = tk.Label(header_frame, text="📝 Mood Attend - Attendance System", font=FONT_HEADER, fg='white', bg='#6366f1', pady=10)
header_label.pack(side='left', padx=20)

cred_path = r'C:\Users\pc\Downloads\database.json'
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://moodattend-default-rtdb.asia-southeast1.firebasedatabase.app/'
})
ref = db.reference('/')
# --- Colors ---
COLORS = {
    "present": "#d4f5d2",
    "absent": "#fbd6d6",
    "late": "#fff4c2",
    "total": "#e3d9fb",
    "card_bg": "white",
    "button": "#e0e7ff",
    "navbar": "#e5efff",
    "purple": "#6366f1",
    "gray": "#6b7280"
}

# --- Tabs ---
notebook = ttk.Notebook(root, style='Custom.TNotebook')
notebook.pack(fill='both', expand=True, padx=20, pady=(10, 20))

attendance_tab = tk.Frame(notebook, bg='#f3f6fc')
faces_tab = tk.Frame(notebook, bg='#f3f6fc')
notebook.add(attendance_tab, text='Attendance')
notebook.add(faces_tab, text='Student Faces')

# --- Top Bar (Attendance Tab) ---
top_frame = tk.Frame(attendance_tab, bg=COLORS['navbar'], height=50)
top_frame.pack(fill='x', pady=(0, 10))

def on_date_change(event):
    selected_date = date_picker.get_date()
    populate_student_cards(selected_date)

# Add a DateEntry (date picker)
date_picker = DateEntry(top_frame, width=18, font=FONT_NORMAL, background=COLORS['purple'], foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
date_picker.set_date(datetime.now())
date_picker.pack(side='left', padx=25, pady=10)
date_picker.bind("<<DateEntrySelected>>", on_date_change)

# Add a button to confirm/show attendance for the selected date
show_date_btn = tk.Button(
    top_frame,
    text="Show Attendance",
    bg=COLORS['purple'],
    fg="white",
    font=FONT_BUTTON,
    command=lambda: populate_student_cards(date_picker.get_date()),
    relief='flat',
    padx=12,
    pady=6,
    bd=0,
    activebackground='#4f46e5'
)
show_date_btn.pack(side='left', padx=8, pady=10)

def on_show_date_enter(e):
    show_date_btn['bg'] = '#4f46e5'
def on_show_date_leave(e):
    show_date_btn['bg'] = COLORS['purple']
show_date_btn.bind("<Enter>", on_show_date_enter)
show_date_btn.bind("<Leave>", on_show_date_leave)

def export_attendance():
    students = fetch_students()
    if not students:
        msg.showwarning("Export Attendance", "No attendance data to export.")
        return
    filetypes = [("Excel files", "*.xlsx"), ("Text files", "*.txt")]
    file = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=filetypes)
    if not file:
        return
    if file.endswith('.xlsx') and HAS_PANDAS:
        df = pd.DataFrame(students, columns=["Name", "Status", "Emoji", "Photo Path"])
        df.to_excel(file, index=False)
        msg.showinfo("Export Attendance", f"Attendance exported to {file}")
    else:
        with open(file, 'w', encoding='utf-8') as f:
            f.write("Name\tStatus\tEmoji\tPhoto Path\n")
            for row in students:
                f.write("\t".join(str(x) for x in row) + "\n")
        msg.showinfo("Export Attendance", f"Attendance exported to {file}")

# --- Save Button with Hover Effect ---
def on_enter(e):
    save_btn['bg'] = '#4f46e5'
def on_leave(e):
    save_btn['bg'] = COLORS['purple']

save_btn = tk.Button(top_frame, text="💾 Save Attendance", bg=COLORS['purple'], fg="white", font=FONT_BUTTON, command=export_attendance, relief='flat', padx=16, pady=6, bd=0, activebackground='#4f46e5')
save_btn.pack(side='right', padx=20, pady=10)
save_btn.bind("<Enter>", on_enter)
save_btn.bind("<Leave>", on_leave)

# --- Summary (Attendance Tab) ---
summary_frame = tk.Frame(attendance_tab, bg='#f3f6fc')
summary_frame.pack(fill='x', padx=20, pady=10)

summary_labels = {}
summaries = [
    ("Present", 0, COLORS['present']),
    ("Absent", 0, COLORS['absent']),
    ("Late", 0, COLORS['late']),
    ("Total", 0, COLORS['total'])
]

for title, count, color in summaries:
    card = tk.Frame(summary_frame, bg=color, width=120, height=70, padx=16, pady=10, relief='ridge', bd=2, highlightbackground='#e0e7ff', highlightthickness=1)
    card.pack(side='left', padx=15, pady=5)
    tk.Label(card, text=title, font=FONT_SUBHEADER, bg=color).pack()
    value_label = tk.Label(card, text=str(count), font=('Segoe UI', 18, 'bold'), bg=color)
    value_label.pack()
    summary_labels[title] = value_label

# --- Filter (Attendance Tab) ---
filter_frame = tk.Frame(attendance_tab, bg='#f3f6fc')
filter_frame.pack(fill='x', padx=20, pady=(0, 10))
tk.Label(filter_frame, text="Filter:", font=FONT_NORMAL, bg='#f3f6fc').pack(side='left')
filter_dropdown = ttk.Combobox(filter_frame, values=["All Students", "Present", "Absent", "Late"], state='readonly', font=FONT_NORMAL, width=15)
filter_dropdown.set("All Students")
filter_dropdown.pack(side='left', padx=8)

# --- Student Cards Grid (Attendance Tab) ---
cards_frame = tk.Frame(attendance_tab, bg='#f3f6fc')
cards_frame.pack(padx=20, pady=10, fill='both', expand=True)

FIREBASE_URL = "https://moodattend-default-rtdb.asia-southeast1.firebasedatabase.app"

# --- Emotion to Emoji Mapping ---
EMOTION_EMOJI = {
    'angry': '😠',
    'disgust': '🤢',
    'fear': '😨',
    'happy': '😊',
    'sad': '😢',
    'surprise': '😲',
    'neutral': '😐',
    'detecting...': '😐',
    'neutral': '😐',
}

def fetch_students(selected_date=None):
    try:
        url = f"{FIREBASE_URL}/students.json"
        response = requests.get(url)
        if response.status_code == 200 and response.json():
            data = response.json()
            students = []
            # Fetch emotion/attendance records for the selected date
            emotions_url = f"{FIREBASE_URL}/emotions.json"
            emotions_resp = requests.get(emotions_url)
            emotions_data = emotions_resp.json() if emotions_resp.status_code == 200 and emotions_resp.json() else {}
            # Build a map: name -> record for selected_date
            date_map = {}
            if selected_date:
                for key, value in emotions_data.items():
                    name = value.get('name', '').strip().lower()
                    ts = value.get('timestamp')
                    if ts:
                        try:
                            from datetime import datetime
                            # Try to parse ISO format, fallback to other formats
                            try:
                                dt = datetime.fromisoformat(ts[:19])
                            except Exception:
                                try:
                                    dt = datetime.strptime(ts[:10], '%Y-%m-%d')
                                except Exception:
                                    continue
                            # Ensure selected_date is a date object
                            if hasattr(selected_date, 'date'):
                                sel_date = selected_date.date()
                            else:
                                sel_date = selected_date
                            # Debug print
                            # print(f"Comparing record date {dt.date()} with selected {sel_date}")
                            if dt.date() == sel_date:
                                # Prefer the latest record for the day
                                if (name not in date_map) or (dt > date_map[name]['dt']):
                                    date_map[name] = {
                                        'status': value.get('status', ''),
                                        'emotion': value.get('emotion', ''),
                                        'emoji': value.get('emoji', ''),
                                        'dt': dt,
                                        'face_image': value.get('face_image', None)
                                    }
                        except Exception:
                            continue
            for key, value in data.items():
                name = value.get('name', 'Unknown')
                name_lc = name.strip().lower()
                if selected_date and name_lc in date_map:
                    rec = date_map[name_lc]
                    status = rec['status'] if rec['status'] else 'Absent'
                    emotion = rec['emotion']
                    emoji = rec['emoji'] if rec['emoji'] else EMOTION_EMOJI.get(str(emotion).lower(), EMOTION_EMOJI['neutral'])
                    face_image = rec['face_image']
                    timestamp = rec['dt']
                elif selected_date:
                    status = 'Absent'
                    emotion = None
                    emoji = EMOTION_EMOJI['neutral']
                    face_image = None
                    timestamp = None
                else:
                    checkin_time = value.get('checkin_time', None)
                    if checkin_time:
                        hour, minute = map(int, checkin_time.split(":"))
                        if hour > 8 or (hour == 8 and minute > 0):
                            status = "Late"
                        else:
                            status = "Present"
                    else:
                        status = value.get('status', 'Absent')
                    emotion = value.get('emotion', None)
                    emoji = value.get('emoji', None)
                    if not emoji and emotion:
                        mapped_emotion = str(emotion).lower()
                        emoji = EMOTION_EMOJI.get(mapped_emotion, EMOTION_EMOJI['neutral'])
                    face_image = value.get('face_image', None)
                    timestamp = None
                students.append((name, status, emoji, face_image, timestamp))
            return students
        else:
            return []
    except Exception as e:
        print(f"Error fetching students: {e}")
        return []

def populate_student_cards(selected_date=None):
    for widget in cards_frame.winfo_children():
        widget.destroy()
    students = fetch_students(selected_date)
    # Count statuses
    present = sum(1 for s in students if s[1] == "Present")
    absent = sum(1 for s in students if s[1] == "Absent")
    late = sum(1 for s in students if s[1] == "Late")
    total = len(students)
    # Update summary labels
    summary_labels["Present"].config(text=str(present))
    summary_labels["Absent"].config(text=str(absent))
    summary_labels["Late"].config(text=str(late))
    summary_labels["Total"].config(text=str(total))
    cols = 3
    for i, student in enumerate(students):
        card = create_card(cards_frame, *student)
        card.grid(row=i//cols, column=i%cols, padx=10, pady=10, sticky='n')
    if not students:
        tk.Label(cards_frame, text="No students found in database.", font=('Segoe UI', 12), bg='#f3f6fc').pack(pady=20)

def create_card(parent, name, status, emoji, photo_path=None, timestamp=None):
    frame = tk.Frame(parent, bg=COLORS['card_bg'], relief='groove', bd=2, padx=10, pady=10, highlightbackground='#e0e7ff', highlightthickness=1)
    img_loaded = False
    if photo_path:
        try:
            img = Image.open(photo_path)
            img = img.resize((80, 80))
            photo = ImageTk.PhotoImage(img)
            img_label = tk.Label(frame, image=photo, bg=COLORS['card_bg'])
            img_label.image = photo  # Keep a reference!
            img_label.pack(anchor='w', padx=10, pady=5)
            img_loaded = True
        except Exception as e:
            pass  # Will try to load from registered_faces below
    if not img_loaded:
        # Try to load from registered_faces by name
        import os
        import glob
        safe_name = "_".join(name.split()).lower()
        face_dir = "registered_faces"
        pattern = os.path.join(face_dir, f"{safe_name}_*.jpg")
        matches = glob.glob(pattern)
        if matches:
            try:
                img = Image.open(matches[-1])  # Use the latest image
                img = img.resize((80, 80))
                photo = ImageTk.PhotoImage(img)
                img_label = tk.Label(frame, image=photo, bg=COLORS['card_bg'])
                img_label.image = photo
                img_label.pack(anchor='w', padx=10, pady=5)
                img_loaded = True
            except Exception as e:
                pass
    if not img_loaded:
        tk.Label(frame, text=f"👤 {name}", font=FONT_CARD, bg=COLORS['card_bg']).pack(anchor='w', padx=10, pady=5)

    status_frame = tk.Frame(frame, bg=COLORS['card_bg'])
    status_frame.pack(anchor='w', padx=10, pady=(0, 5))
    for s in ["Present", "Absent", "Late"]:
        bg = "#10b981" if s == status else "#e5e7eb"
        fg = "white" if s == status else "#6b7280"
        lbl = tk.Label(status_frame, text=s, bg=bg, fg=fg, padx=8, pady=2, font=FONT_CARD, relief='ridge', bd=1)
        lbl.pack(side='left', padx=3)

    # Add date and time display
    if timestamp:
        try:
            dt_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            dt_str = str(timestamp)
        tk.Label(frame, text=f"Date & Time: {dt_str}", font=FONT_CARD, bg=COLORS['card_bg'], fg='#6366f1').pack(anchor='w', padx=10, pady=(0, 5))
    else:
        tk.Label(frame, text="Date & Time: -", font=FONT_CARD, bg=COLORS['card_bg'], fg='#6366f1').pack(anchor='w', padx=10, pady=(0, 5))

    tk.Label(frame, text="Emotional Status:", font=FONT_CARD, bg=COLORS['card_bg']).pack(anchor='w', padx=10, pady=(5, 0))
    tk.Label(frame, text=emoji, font=('Segoe UI', 24), bg=COLORS['card_bg']).pack(anchor='w', padx=10)

    def show_attendance_history():
        import tkinter.messagebox as msg
        import requests
        from datetime import datetime, timedelta
        # Fetch all emotion records for this student from Firebase
        try:
            url = f"{FIREBASE_URL}/emotions.json"
            response = requests.get(url)
            if response.status_code == 200 and response.json():
                data = response.json()
                # Get today and the start of the week (Monday)
                today = datetime.now().date()
                week_start = today - timedelta(days=today.weekday())
                # Collect attendance for each day in the week
                days = [(week_start + timedelta(days=i)) for i in range(7)]
                day_map = {d: None for d in days}
                # Find all records for this student in the week
                for key, value in data.items():
                    if value.get('name', '').strip().lower() == name.strip().lower():
                        ts = value.get('timestamp')
                        if ts:
                            try:
                                dt = datetime.fromisoformat(ts[:19])
                            except Exception:
                                continue
                            day = dt.date()
                            if day in day_map:
                                # Prefer the latest record for the day
                                if (day_map[day] is None) or (dt > day_map[day]['dt']):
                                    day_map[day] = {
                                        'status': value.get('status', ''),
                                        'emotion': value.get('emotion', ''),
                                        'emoji': value.get('emoji', ''),
                                        'dt': dt
                                    }
                # Build the message
                msg_lines = []
                for d in days:
                    rec = day_map[d]
                    day_str = d.strftime('%A, %Y-%m-%d')
                    if rec:
                        status = rec['status'] if rec['status'] else 'N/A'
                        emotion = rec['emotion'] if rec['emotion'] else 'N/A'
                        emoji = rec['emoji'] if rec['emoji'] else ''
                        msg_lines.append(f"{day_str}: {status} {emoji} ({emotion})")
                    else:
                        msg_lines.append(f"{day_str}: No record")
                msg.showinfo("Previous Attendance", "\n".join(msg_lines))
            else:
                msg.showinfo("Previous Attendance", "No attendance history found for this student.")
        except Exception as e:
            msg.showerror("Error", f"Failed to fetch attendance history: {e}")

    see_prev_btn = tk.Button(frame, text="\ud83d\udcc5 See Previous Attendance", font=FONT_CARD, bg=COLORS['button'], relief='flat', padx=10, pady=4, bd=0, activebackground='#c7d2fe')
    see_prev_btn.pack(padx=10, pady=5)
    # Hover effect for card button
    def on_card_enter(e):
        see_prev_btn['bg'] = '#c7d2fe'
    def on_card_leave(e):
        see_prev_btn['bg'] = COLORS['button']
    see_prev_btn.bind("<Enter>", on_card_enter)
    see_prev_btn.bind("<Leave>", on_card_leave)
    return frame

def capture_face(student_id):
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        filename = f"faces/{student_id}.jpg"
        cv2.imwrite(filename, frame)
    cap.release()
    cv2.destroyAllWindows()
    return filename

# --- Registered Faces Tab ---
def populate_faces_tab():
    for widget in faces_tab.winfo_children():
        widget.destroy()
    import os
    import glob
    from PIL import Image, ImageTk
    face_dir = "registered_faces"
    files = glob.glob(os.path.join(face_dir, "*.jpg"))
    if not files:
        tk.Label(faces_tab, text="No registered faces found.", font=FONT_SUBHEADER, bg='#f3f6fc').pack(pady=20)
        return
    grid = tk.Frame(faces_tab, bg='#f3f6fc')
    grid.pack(padx=20, pady=20, fill='both', expand=True)
    cols = 4
    for i, file in enumerate(files):
        try:
            img = Image.open(file)
            img = img.resize((80, 80))
            photo = ImageTk.PhotoImage(img)
            frame = tk.Frame(grid, bg=COLORS['card_bg'], relief='groove', bd=2, padx=10, pady=10, highlightbackground='#e0e7ff', highlightthickness=1)
            img_label = tk.Label(frame, image=photo, bg=COLORS['card_bg'])
            img_label.image = photo
            img_label.pack(padx=10, pady=5)
            # Parse name from filename
            base = os.path.basename(file)
            name = base.split('_')[0].capitalize()
            tk.Label(frame, text=name, font=FONT_CARD, bg=COLORS['card_bg']).pack(padx=10, pady=5)
            frame.grid(row=i//cols, column=i%cols, padx=15, pady=15, sticky='n')
        except Exception as e:
            continue

# Call this after root.mainloop() to update faces tab when needed
notebook.bind("<<NotebookTabChanged>>", lambda e: populate_faces_tab() if notebook.index(notebook.select()) == 1 else None)

# Call with today's date by default
populate_student_cards(datetime.now().date())

def fetch_attendance_for_date(selected_date):
    """
    Fetch attendance records from Firebase for a specific date.
    selected_date: a datetime.date object
    Returns: list of records for that date
    """
    url = f"{FIREBASE_URL}/emotions.json"
    response = requests.get(url)
    if response.status_code != 200 or not response.json():
        return []

    data = response.json()
    records_for_date = []
    for key, value in data.items():
        ts = value.get('timestamp')
        if ts:
            try:
                dt = datetime.fromisoformat(ts[:19])
            except Exception:
                try:
                    dt = datetime.strptime(ts[:10], '%Y-%m-%d')
                except Exception:
                    continue
            if dt.date() == selected_date:
                records_for_date.append(value)
    return records_for_date

# Example usage:
# from datetime import date
# today = date.today()
# attendance_today = fetch_attendance_for_date(today)
# print(attendance_today)

root.mainloop()
