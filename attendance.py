import tkinter as tk
from tkinter import ttk
from datetime import datetime
import requests
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db 
import cv2
from PIL import Image, ImageTk
import tkinter.filedialog as filedialog
import tkinter.messagebox as msg
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


# --- Setup ---
root = tk.Tk()
root.title("Mood Attend - Attendance")
root.geometry("900x600")
root.configure(bg='#f3f6fc')

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

# --- Top Bar ---
top_frame = tk.Frame(root, bg=COLORS['navbar'], height=50)
top_frame.pack(fill='x')

date_label = tk.Label(top_frame, text=datetime.now().strftime("%A, %B %d, %Y"), font=('Segoe UI', 10), bg=COLORS['navbar'])
date_label.pack(side='left', padx=10, pady=10)

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

save_btn = tk.Button(top_frame, text="💾 Save Attendance", bg=COLORS['purple'], fg="white", font=('Segoe UI', 10, 'bold'), command=export_attendance)
save_btn.pack(side='right', padx=10, pady=10)

# --- Summary ---
summary_frame = tk.Frame(root, bg='#f3f6fc')
summary_frame.pack(fill='x', padx=20, pady=10)

summary_labels = {}
summaries = [
    ("Present", 0, COLORS['present']),
    ("Absent", 0, COLORS['absent']),
    ("Late", 0, COLORS['late']),
    ("Total", 0, COLORS['total'])
]

for title, count, color in summaries:
    card = tk.Frame(summary_frame, bg=color, width=100, height=60, padx=10, pady=10)
    card.pack(side='left', padx=10)
    tk.Label(card, text=title, font=('Segoe UI', 10, 'bold'), bg=color).pack()
    value_label = tk.Label(card, text=str(count), font=('Segoe UI', 14), bg=color)
    value_label.pack()
    summary_labels[title] = value_label

# --- Filter ---
filter_frame = tk.Frame(root, bg='#f3f6fc')
filter_frame.pack(fill='x', padx=20)
tk.Label(filter_frame, text="Filter:", font=('Segoe UI', 10), bg='#f3f6fc').pack(side='left')
filter_dropdown = ttk.Combobox(filter_frame, values=["All Students", "Present", "Absent", "Late"], state='readonly')
filter_dropdown.set("All Students")
filter_dropdown.pack(side='left', padx=5)

# --- Student Cards Grid ---
cards_frame = tk.Frame(root, bg='#f3f6fc')
cards_frame.pack(padx=20, pady=10, fill='both', expand=True)

FIREBASE_URL = "https://moodattend-default-rtdb.asia-southeast1.firebasedatabase.app"

def fetch_students():
    try:
        url = f"{FIREBASE_URL}/students.json"
        response = requests.get(url)
        if response.status_code == 200 and response.json():
            data = response.json()
            students = []
            for key, value in data.items():
                name = value.get('name', 'Unknown')
                checkin_time = value.get('checkin_time', None)
                if checkin_time:
                    hour, minute = map(int, checkin_time.split(":"))
                    if hour > 8 or (hour == 8 and minute > 0):
                        status = "Late"
                    else:
                        status = "Present"
                else:
                    status = value.get('status', 'Absent')
                emoji = value.get('emoji',)
                face_image = value.get('face_image', None)
                students.append((name, status, emoji, face_image))
            return students
        else:
            return []
    except Exception as e:
        print(f"Error fetching students: {e}")
        return []

def populate_student_cards():
    for widget in cards_frame.winfo_children():
        widget.destroy()
    students = fetch_students()
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

def create_card(parent, name, status, emoji, photo_path=None):
    frame = tk.Frame(parent, bg=COLORS['card_bg'], relief='solid', bd=1)
    if photo_path:
        try:
            img = Image.open(photo_path)
            img = img.resize((80, 80))
            photo = ImageTk.PhotoImage(img)
            img_label = tk.Label(frame, image=photo, bg=COLORS['card_bg'])
            img_label.image = photo  # Keep a reference!
            img_label.pack(anchor='w', padx=10, pady=5)
        except Exception as e:
            # If image fails to load, fallback to icon
            tk.Label(frame, text=f"👤 {name}", font=('Segoe UI', 10, 'bold'), bg=COLORS['card_bg']).pack(anchor='w', padx=10, pady=5)
    else:
        tk.Label(frame, text=f"👤 {name}", font=('Segoe UI', 10, 'bold'), bg=COLORS['card_bg']).pack(anchor='w', padx=10, pady=5)

    status_frame = tk.Frame(frame, bg=COLORS['card_bg'])
    status_frame.pack(anchor='w', padx=10)
    for s in ["Present", "Absent", "Late"]:
        bg = "#10b981" if s == status else "#e5e7eb"
        tk.Label(status_frame, text=s, bg=bg, fg="white" if s == status else "black", padx=5).pack(side='left', padx=2)

    tk.Label(frame, text="Emotional Status:", font=('Segoe UI', 9), bg=COLORS['card_bg']).pack(anchor='w', padx=10, pady=(5, 0))
    tk.Label(frame, text=emoji, font=('Segoe UI', 20), bg=COLORS['card_bg']).pack(anchor='w', padx=10)

    def show_attendance_history():
        import tkinter.messagebox as msg
        msg.showinfo("Previous Attendance", f"Previous attendance for {name} will be shown here.")

    see_prev_btn = tk.Button(frame, text="📅 See Previous Attendance", font=('Segoe UI', 9), bg=COLORS['button'], command=show_attendance_history)
    see_prev_btn.pack(padx=10, pady=5)
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

populate_student_cards()

root.mainloop()
