import tkinter as tk
from tkinter import messagebox, ttk
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import requests
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# Firebase Initialization (reuse from attendance.py)
cred_path = r'C:\Users\pc\Downloads\database.json'
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://moodattend-default-rtdb.asia-southeast1.firebasedatabase.app/'
    })

# Reference to students node
students_ref = db.reference('/students')
FIREBASE_URL = "https://moodattend-default-rtdb.asia-southeast1.firebasedatabase.app"

# --- Main Window ---
root = tk.Tk()
root.title("Admin Panel")
root.geometry("800x500")
root.configure(bg='#f3f6fc')

# Sidebar colors
SIDEBAR_BG = '#6366f1'  # purple
SIDEBAR_FG = 'white'
SIDEBAR_ACTIVE_BG = '#4f46e5'
SIDEBAR_BTN_FONT = ('Segoe UI', 12, 'bold')

# --- Sidebar Navigation ---
sidebar = tk.Frame(root, bg=SIDEBAR_BG, width=180)
sidebar.pack(side='left', fill='y')

# --- Main Content Frame ---
content_frame = tk.Frame(root, bg='#f3f6fc')
content_frame.pack(side='left', fill='both', expand=True)

# --- Tab Frames ---
tabs = {}
for tab_name in ['Add Student', 'Dashboard']:
    frame = tk.Frame(content_frame, bg='#f3f6fc')
    tabs[tab_name] = frame
    frame.place(relx=0, rely=0, relwidth=1, relheight=1)

# --- Sidebar Buttons ---
sidebar_btns = {}
def show_tab(tab_name):
    for name, frame in tabs.items():
        frame.lower()
    tabs[tab_name].lift()
    for name, btn in sidebar_btns.items():
        btn.configure(bg=SIDEBAR_BG)
    sidebar_btns[tab_name].configure(bg=SIDEBAR_ACTIVE_BG)

for i, tab_name in enumerate(['Add Student', 'Dashboard']):
    btn = tk.Button(
        sidebar, text=tab_name, font=SIDEBAR_BTN_FONT, bg=SIDEBAR_BG, fg=SIDEBAR_FG,
        relief='flat', bd=0, activebackground=SIDEBAR_ACTIVE_BG, activeforeground=SIDEBAR_FG,
        command=lambda n=tab_name: show_tab(n)
    )
    btn.pack(fill='x', pady=(20 if i == 0 else 0, 0), padx=0, ipady=16)
    sidebar_btns[tab_name] = btn

# --- Add Student Tab Content ---
add_tab = tabs['Add Student']
FONT_LABEL = ('Segoe UI', 11)
FONT_BUTTON = ('Segoe UI', 10, 'bold')
tk.Label(add_tab, text="Student Name:", font=FONT_LABEL, bg='#f3f6fc').pack(pady=(40, 5))
name_entry = tk.Entry(add_tab, font=FONT_LABEL)
name_entry.pack(padx=40, fill='x')

# Remove Username label and entry
# Add Upload Image button and label
image_path_var = tk.StringVar()
def upload_image():
    from tkinter import filedialog
    import os
    file_path = filedialog.askopenfilename(
        title="Select Student Image",
        filetypes=[("Image Files", "*.jpg;*.jpeg;*.png")]
    )
    if file_path:
        image_path_var.set(file_path)
        image_label.config(text=f"Selected: {os.path.basename(file_path)}")
    else:
        image_label.config(text="No image selected.")

upload_btn = tk.Button(add_tab, text="Upload Image", font=FONT_BUTTON, bg='#6366f1', fg='white', relief='flat', padx=16, pady=6, command=upload_image)
upload_btn.pack(pady=(10, 0))
image_label = tk.Label(add_tab, text="No image selected.", font=('Segoe UI', 9), bg='#f3f6fc', fg='#6366f1')
image_label.pack(pady=(2, 10))

def add_student():
    name = name_entry.get().strip()
    image_path = image_path_var.get()
    if not name or not image_path:
        messagebox.showerror("Error", "Please enter the student's name and upload an image.")
        return
    # Save image to registered_faces folder
    import os, shutil
    from datetime import datetime
    faces_dir = os.path.join(os.path.dirname(__file__), 'registered_faces')
    if not os.path.exists(faces_dir):
        os.makedirs(faces_dir)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # Clean name for filename
    safe_name = name.replace(' ', '_')
    ext = os.path.splitext(image_path)[1]
    dest_filename = f"{safe_name}_{timestamp}{ext}"
    dest_path = os.path.join(faces_dir, dest_filename)
    shutil.copy(image_path, dest_path)
    # Add student to database (no username)
    students_ref.push({
        'name': name
    })
    messagebox.showinfo("Success", f"Student '{name}' added and image uploaded.")
    name_entry.delete(0, tk.END)
    image_path_var.set("")
    image_label.config(text="No image selected.")

add_btn = tk.Button(add_tab, text="Add Student", font=FONT_BUTTON, bg='#6366f1', fg='white', relief='flat', padx=16, pady=6, command=add_student)
add_btn.pack(pady=20)

# --- Dashboard Tab Content ---
dash_tab = tabs['Dashboard']
summary_frame = tk.Frame(dash_tab, bg='#f3f6fc')
summary_frame.pack(pady=20)
summary_labels = {}
summaries = [
    ("Present", 0, "#d4f5d2"),
    ("Absent", 0, "#fbd6d6"),
    ("Late", 0, "#fff4c2"),
    ("Total", 0, "#e3d9fb")
]
for title, count, color in summaries:
    card = tk.Frame(summary_frame, bg=color, width=120, height=70, padx=16, pady=10, relief='ridge', bd=2, highlightbackground='#e0e7ff', highlightthickness=1)
    card.pack(side='left', padx=15, pady=5)
    tk.Label(card, text=title, font=('Segoe UI', 12, 'bold'), bg=color).pack()
    value_label = tk.Label(card, text=str(count), font=('Segoe UI', 18, 'bold'), bg=color)
    value_label.pack()
    summary_labels[title] = value_label
pie_frame = tk.Frame(dash_tab, bg='#f3f6fc')
pie_frame.pack(pady=10)
pie_canvas = None
def fetch_students_today():
    try:
        url = f"{FIREBASE_URL}/students.json"
        response = requests.get(url)
        if response.status_code == 200 and response.json():
            data = response.json()
            students_dict = {}
            today = datetime.now().date()
            for key, value in data.items():
                name = value.get('name', 'Unknown')
                checkin_time = value.get('checkin_time', None)
                timestamp = value.get('timestamp', None)
                record_date = None
                if timestamp:
                    try:
                        record_date = datetime.fromisoformat(str(timestamp)[:19]).date()
                    except Exception:
                        record_date = None
                if record_date != today:
                    continue
                if name not in students_dict or (
                    timestamp and students_dict[name][4] and timestamp > students_dict[name][4]
                ):
                    if checkin_time:
                        hour, minute = map(int, checkin_time.split(":"))
                        if hour < 8:
                            status = "Present"
                        else:
                            status = "Late"
                    else:
                        status = value.get('status', 'Absent')
                    emotion = value.get('emotion', None)
                    emoji = value.get('emoji', None)
                    students_dict[name] = (name, status, emoji, None, timestamp)
            return list(students_dict.values())
        else:
            return []
    except Exception as e:
        print(f"Error fetching students: {e}")
        return []
def update_dashboard():
    global pie_canvas
    students = fetch_students_today()
    users_data = students_ref.get() or {}
    all_usernames = set()
    for key, val in users_data.items():
        uname = val.get('username')
        if uname:
            all_usernames.add(uname)
    attended_names = set(s[0] for s in students)
    for uname in all_usernames - attended_names:
        students.append((uname, 'Absent', '😐', None, None))
    present = sum(1 for s in students if s[1] == "Present")
    absent = sum(1 for s in students if s[1] == "Absent")
    late = sum(1 for s in students if s[1] == "Late")
    total = len(students)
    summary_labels["Present"].config(text=str(present))
    summary_labels["Absent"].config(text=str(absent))
    summary_labels["Late"].config(text=str(late))
    summary_labels["Total"].config(text=str(total))
    emotion_counts = {
        'Happy': sum(1 for s in students if s[2] == '😊'),
        'Sad': sum(1 for s in students if s[2] == '😢'),
        'Angry': sum(1 for s in students if s[2] == '😠'),
        'Neutral': sum(1 for s in students if s[2] == '😐' or not s[2]),
    }
    for widget in pie_frame.winfo_children():
        widget.destroy()
    labels = [f"😊 Happy", f"😢 Sad", f"😠 Angry", f"😐 Neutral"]
    sizes = [emotion_counts['Happy'], emotion_counts['Sad'], emotion_counts['Angry'], emotion_counts['Neutral']]
    colors = ['#fef08a', '#bae6fd', '#fecaca', '#e5e7eb']
    if sum(sizes) == 0:
        tk.Label(pie_frame, text="No emotion data for today.", font=FONT_LABEL, bg='#f3f6fc', fg='#6366f1').pack(pady=30)
    else:
        fig, ax = plt.subplots(figsize=(4, 2.2), dpi=100)
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct=lambda pct: f'{int(round(pct/100*sum(sizes)))}' if pct > 0 else '',
            colors=colors,
            startangle=90,
            textprops={'fontsize': 10}
        )
        ax.axis('equal')
        ax.set_title('Emotional Distribution', fontsize=12)
        fig.tight_layout()
        pie_canvas = FigureCanvasTkAgg(fig, master=pie_frame)
        pie_canvas.draw()
        pie_canvas.get_tk_widget().pack(fill='x', expand=True)
        plt.close(fig)
refresh_btn = tk.Button(dash_tab, text="Refresh Dashboard", font=FONT_BUTTON, bg='#6366f1', fg='white', relief='flat', padx=16, pady=6, command=update_dashboard)
refresh_btn.pack(pady=10)
update_dashboard()
show_tab('Add Student')


root.mainloop()
