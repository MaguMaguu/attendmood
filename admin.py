import tkinter as tk
from tkinter import messagebox, ttk, Scrollbar
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, timedelta
import requests
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import calendar

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
root.geometry("1350x750")
root.configure(bg='#f3f6fc')

# --- Welcome Message at the Top ---
WELCOME_BG = '#6366f1'  # purple
WELCOME_FG = 'white'
WELCOME_FONT = ('Segoe UI', 16, 'bold')
welcome_frame = tk.Frame(root, bg=WELCOME_BG, height=50)
welcome_frame.pack(side='top', fill='x')
welcome_label = tk.Label(
    welcome_frame,
    text="Welcome!",
    bg=WELCOME_BG,
    fg=WELCOME_FG,
    font=WELCOME_FONT,
    pady=10
)
welcome_label.pack(fill='both', expand=True)

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
# Change the order: Dashboard first, then Add Student, then Remove Student
for tab_name in ['Dashboard', 'Add Student', 'Remove Student', 'Emotion History', 'Attendance History', 'Attendance & Emotion']:
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

# Change the sidebar button order to match the new tab order
for i, tab_name in enumerate(['Dashboard', 'Add Student', 'Remove Student', 'Emotion History', 'Attendance History', 'Attendance & Emotion']):
    btn = tk.Button(
        sidebar, text=tab_name, font=SIDEBAR_BTN_FONT, bg=SIDEBAR_BG, fg=SIDEBAR_FG,
        relief='flat', bd=0, activebackground=SIDEBAR_ACTIVE_BG, activeforeground=SIDEBAR_FG,
        command=lambda name=tab_name: show_tab(name)
    )
    btn.pack(fill='x', pady=(0, 2), padx=8)
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

# --- Remove Student Tab Content ---
remove_tab = tabs['Remove Student']
tk.Label(remove_tab, text="Remove Student", font=('Segoe UI', 14, 'bold'), bg='#f3f6fc').pack(pady=(40, 20))

# Student selection for removal
tk.Label(remove_tab, text="Select Student to Remove:", font=FONT_LABEL, bg='#f3f6fc').pack(pady=(0, 5))
remove_student_var = tk.StringVar()
remove_student_combo = ttk.Combobox(remove_tab, textvariable=remove_student_var, state='readonly', width=30)
remove_student_combo.pack(padx=40, pady=(0, 20))

# Refresh student list button
def refresh_remove_student_list():
    """Refresh the student dropdown list for removal"""
    try:
        students_data = students_ref.get() or {}
        student_options = []
        for key, val in students_data.items():
            name = val.get('name', 'Unknown')
            student_options.append(f"{name} (ID: {key})")
        
        student_options.sort()
        remove_student_combo['values'] = student_options
        if student_options:
            remove_student_combo.current(0)
        else:
            remove_student_combo.set("")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load students: {str(e)}")

refresh_students_btn = tk.Button(remove_tab, text="Refresh Student List", font=FONT_BUTTON, bg='#64748b', fg='white', relief='flat', padx=16, pady=6, command=refresh_remove_student_list)
refresh_students_btn.pack(pady=(0, 20))

# Warning message
warning_label = tk.Label(remove_tab, text="⚠️ Warning: This action cannot be undone!\nRemoving a student will delete all their attendance and emotion records.", 
                        font=('Segoe UI', 10), bg='#f3f6fc', fg='#ef4444', justify='center')
warning_label.pack(pady=(0, 20))

def remove_student():
    """Remove selected student from Firebase"""
    selected = remove_student_var.get()
    if not selected:
        messagebox.showerror("Error", "Please select a student to remove.")
        return
    
    # Extract student ID from the selection (format: "Name (ID: key)")
    try:
        student_id = selected.split("(ID: ")[1].rstrip(")")
        student_name = selected.split(" (ID: ")[0]
    except IndexError:
        messagebox.showerror("Error", "Invalid student selection.")
        return
    
    # Confirmation dialog
    result = messagebox.askyesno(
        "Confirm Removal", 
        f"Are you sure you want to remove '{student_name}'?\n\nThis will permanently delete:\n• Student profile\n• All attendance records\n• All emotion records\n\nThis action cannot be undone!",
        icon='warning'
    )
    
    if result:
        try:
            # Remove student from Firebase
            student_ref = db.reference(f'/students/{student_id}')
            student_ref.delete()
            
            messagebox.showinfo("Success", f"Student '{student_name}' has been successfully removed.")
            
            # Refresh the dropdown list
            refresh_remove_student_list()
            
            # Refresh other dropdowns that might be affected
            refresh_student_dropdowns()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove student: {str(e)}")

remove_btn = tk.Button(remove_tab, text="Remove Student", font=FONT_BUTTON, bg='#ef4444', fg='white', relief='flat', padx=16, pady=8, command=remove_student)
remove_btn.pack(pady=10)

# Instructions
instructions_label = tk.Label(remove_tab, text="Instructions:\n1. Click 'Refresh Student List' to load current students\n2. Select the student you want to remove\n3. Click 'Remove Student' and confirm the action", 
                             font=('Segoe UI', 9), bg='#f3f6fc', fg='#6b7280', justify='left')
instructions_label.pack(pady=(30, 0))

# Initialize the remove student list
refresh_remove_student_list()

# --- Dashboard Tab Content ---
dash_tab = tabs['Dashboard']

# Date picker for dashboard
dashboard_date_frame = tk.Frame(dash_tab, bg='#f3f6fc')
dashboard_date_frame.pack(pady=(20, 10))

tk.Label(dashboard_date_frame, text="Select Date:", font=FONT_LABEL, bg='#f3f6fc').pack(side='left', padx=(0, 10))

# Dashboard date picker components
dashboard_selected_date_var = tk.StringVar()
dashboard_selected_date_var.set(datetime.now().strftime('%Y-%m-%d'))

# Year dropdown for dashboard
dashboard_current_year = datetime.now().year
dashboard_year_var = tk.StringVar()
dashboard_year_combo = ttk.Combobox(dashboard_date_frame, textvariable=dashboard_year_var, state='readonly', width=6)
dashboard_year_combo['values'] = [str(year) for year in range(dashboard_current_year - 2, dashboard_current_year + 1)]
dashboard_year_combo.set(str(dashboard_current_year))
dashboard_year_combo.pack(side='left', padx=(0, 5))

# Month dropdown for dashboard
dashboard_month_var = tk.StringVar()
dashboard_month_combo = ttk.Combobox(dashboard_date_frame, textvariable=dashboard_month_var, state='readonly', width=10)
dashboard_month_combo['values'] = [calendar.month_name[i] for i in range(1, 13)]
dashboard_month_combo.set(calendar.month_name[datetime.now().month])
dashboard_month_combo.pack(side='left', padx=(0, 5))

# Day dropdown for dashboard
dashboard_day_var = tk.StringVar()
dashboard_day_combo = ttk.Combobox(dashboard_date_frame, textvariable=dashboard_day_var, state='readonly', width=4)
dashboard_day_combo.set(str(datetime.now().day))
dashboard_day_combo.pack(side='left', padx=(0, 15))

def update_dashboard_days(*args):
    """Update day dropdown based on selected year and month for dashboard"""
    try:
        year = int(dashboard_year_var.get())
        month = list(calendar.month_name).index(dashboard_month_var.get())
        _, max_day = calendar.monthrange(year, month)
        dashboard_day_combo['values'] = [str(i) for i in range(1, max_day + 1)]
        
        # Reset day if current day is not valid for the selected month
        current_day = int(dashboard_day_var.get()) if dashboard_day_var.get().isdigit() else 1
        if current_day > max_day:
            dashboard_day_var.set('1')
    except (ValueError, IndexError):
        dashboard_day_combo['values'] = [str(i) for i in range(1, 32)]

def get_dashboard_selected_date():
    """Get the selected date as a datetime.date object for dashboard"""
    try:
        year = int(dashboard_year_var.get())
        month = list(calendar.month_name).index(dashboard_month_var.get())
        day = int(dashboard_day_var.get())
        return datetime(year, month, day).date()
    except (ValueError, IndexError):
        return datetime.now().date()

# Bind events to update days when year or month changes
dashboard_year_var.trace('w', update_dashboard_days)
dashboard_month_var.trace('w', update_dashboard_days)

# Initialize days for current month
update_dashboard_days()

# Update dashboard button
update_dashboard_btn = tk.Button(dashboard_date_frame, text="Update Dashboard", font=FONT_BUTTON, bg='#6366f1', fg='white', relief='flat', padx=16, pady=6, command=lambda: update_dashboard(get_dashboard_selected_date()))
update_dashboard_btn.pack(side='left')

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
    return fetch_students_for_date(datetime.now().date())

def fetch_students_for_date(target_date):
    """Fetch students data for a specific date"""
    try:
        url = f"{FIREBASE_URL}/students.json"
        response = requests.get(url)
        if response.status_code == 200 and response.json():
            data = response.json()
            students_dict = {}
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
                if record_date != target_date:
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

# At-Risk Students Section
at_risk_frame = tk.Frame(dash_tab, bg='#f3f6fc')
at_risk_frame.pack(pady=(10, 0))
at_risk_label = tk.Label(at_risk_frame, text="At-Risk Students (3+ Sad Days This Week):", font=('Segoe UI', 11, 'bold'), bg='#f3f6fc', fg='#ef4444')
at_risk_label.pack(anchor='w')
at_risk_list = tk.Label(at_risk_frame, text="", font=('Segoe UI', 10), bg='#f3f6fc', fg='#ef4444', justify='left')
at_risk_list.pack(anchor='w')

def get_at_risk_students():
    url = f"{FIREBASE_URL}/students.json"
    response = requests.get(url)
    if response.status_code != 200 or not response.json():
        return []
    data = response.json()
    # Map: name -> {date: emotion}
    from collections import defaultdict
    emotion_map = defaultdict(dict)
    today = datetime.now().date()
    week_start = today - timedelta(days=6)
    for v in data.values():
        name = v.get('name')
        ts = v.get('timestamp')
        emotion = v.get('emotion')
        if name and ts and emotion:
            try:
                dt = datetime.fromisoformat(str(ts)[:19])
                d = dt.date()
                if week_start <= d <= today:
                    emotion_map[name][d] = emotion
            except Exception:
                continue
    at_risk = []
    for name, days in emotion_map.items():
        sad_count = sum(1 for e in days.values() if e == '😢')
        if sad_count >= 3:
            at_risk.append(name)
    return at_risk

def update_dashboard(selected_date=None):
    global pie_canvas
    # Use today's date if no date is provided
    if selected_date is None:
        selected_date = datetime.now().date()
        students = fetch_students_today()
    else:
        students = fetch_students_for_date(selected_date)
    
    users_data = students_ref.get() or {}
    all_student_names = set()
    for key, val in users_data.items():
        name = val.get('name')
        if name:
            all_student_names.add(name)
    
    attended_names = set(s[0] for s in students)
    for name in all_student_names - attended_names:
        students.append((name, 'Absent', None, None, None))
    present = sum(1 for s in students if s[1] == "Present")
    absent = sum(1 for s in students if s[1] == "Absent")
    late = sum(1 for s in students if s[1] == "Late")
    total = len(students)
    summary_labels["Present"].config(text=str(present))
    summary_labels["Absent"].config(text=str(absent))
    summary_labels["Late"].config(text=str(late))
    summary_labels["Total"].config(text=str(total))
    emotion_counts = {
        'Happy': sum(1 for s in students if s[1] != 'Absent' and s[2] == '😊'),
        'Sad': sum(1 for s in students if s[1] != 'Absent' and s[2] == '😢'),
        'Angry': sum(1 for s in students if s[1] != 'Absent' and s[2] == '😠'),
        'Neutral': sum(1 for s in students if s[1] != 'Absent' and (s[2] == '😐' or not s[2])),
    }
    for widget in pie_frame.winfo_children():
        widget.destroy()
    labels = [f"😊 Happy", f"😢 Sad", f"😠 Angry", f"😐 Neutral"]
    sizes = [emotion_counts['Happy'], emotion_counts['Sad'], emotion_counts['Angry'], emotion_counts['Neutral']]
    colors = ['#fef08a', '#bae6fd', '#fecaca', '#e5e7eb']
    if sum(sizes) == 0:
        tk.Label(pie_frame, text="No emotion data for today.", font=FONT_LABEL, bg='#f3f6fc', fg='#6366f1').pack(pady=30)
    else:
        # --- Changed from pie chart to bar (column) chart ---
        fig, ax = plt.subplots(figsize=(4, 2.2), dpi=100)
        bars = ax.bar(labels, sizes, color=colors)
        ax.set_ylabel('Count')
        ax.set_title(f'Emotional Distribution ({selected_date.strftime("%Y-%m-%d")})')
        ax.set_ylim(0, max(sizes) + 1)
        for bar, size in zip(bars, sizes):
            ax.annotate(str(size), xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10)
        fig.tight_layout()
        pie_canvas = FigureCanvasTkAgg(fig, master=pie_frame)
        pie_canvas.draw()
        pie_canvas.get_tk_widget().pack(fill='x', expand=True)
        plt.close(fig)
    at_risk = get_at_risk_students()
    if at_risk:
        at_risk_list.config(text="\n".join(at_risk))
    else:
        at_risk_list.config(text="None")

update_dashboard()
# Set Dashboard as the initial tab
show_tab('Dashboard')

# --- Emotion History Tab Content ---
emotion_tab = tabs['Emotion History']
tk.Label(emotion_tab, text="Emotion History", font=('Segoe UI', 14, 'bold'), bg='#f3f6fc').pack(pady=(30, 10))

# Create a frame for the controls (dropdowns and button)
controls_frame = tk.Frame(emotion_tab, bg='#f3f6fc')
controls_frame.pack(pady=(0, 20))

# Student selection
tk.Label(controls_frame, text="Student:", font=FONT_LABEL, bg='#f3f6fc').pack(side='left', padx=(0, 5))
emotion_student_var = tk.StringVar()
emotion_student_combo = ttk.Combobox(controls_frame, textvariable=emotion_student_var, state='readonly', width=15)
emotion_student_combo.pack(side='left', padx=(0, 15))

# Month picker
tk.Label(controls_frame, text="Month:", font=FONT_LABEL, bg='#f3f6fc').pack(side='left', padx=(0, 5))
def get_month_options():
    now = datetime.now()
    months = []
    for i in range(0, 12):
        month = (now.month - i - 1) % 12 + 1
        year = now.year - ((now.month - i - 1) // 12)
        months.append(f"{calendar.month_name[month]} {year}")
    return months

emotion_month_var = tk.StringVar()
emotion_month_combo = ttk.Combobox(
    controls_frame, textvariable=emotion_month_var, state='readonly', values=get_month_options(), width=15
)
emotion_month_combo.current(0)
emotion_month_combo.pack(side='left', padx=(0, 15))

# Show History button beside dropdowns
def fetch_emotion_history():
    for widget in emotion_chart_frame.winfo_children():
        widget.destroy()
    student_name = emotion_student_var.get()
    month_year = emotion_month_var.get()
    if not student_name or not month_year:
        tk.Label(emotion_chart_frame, text="Please select a student and month.", font=('Segoe UI', 11), bg='#f3f6fc', fg='#6366f1').pack(pady=30)
        return
    # Parse selected month and year
    try:
        month_name, year = month_year.split()
        month = list(calendar.month_name).index(month_name)
        year = int(year)
    except Exception:
        tk.Label(emotion_chart_frame, text="Invalid month selected.", font=('Segoe UI', 11), bg='#f3f6fc', fg='#6366f1').pack(pady=30)
        return
    # Fetch all records for this student from Firebase
    url = f"{FIREBASE_URL}/students.json"
    response = requests.get(url)
    if response.status_code != 200 or not response.json():
        tk.Label(emotion_chart_frame, text="No data found.", font=('Segoe UI', 11), bg='#f3f6fc', fg='#6366f1').pack(pady=30)
        return
    data = response.json()
    # Collect records for this student in the selected month
    records = []
    for v in data.values():
        if v.get('name') == student_name:
            ts = v.get('timestamp')
            emotion = v.get('emotion')
            if ts and emotion:
                try:
                    dt = datetime.fromisoformat(str(ts)[:19])
                    if dt.year == year and dt.month == month:
                        records.append((dt.date(), emotion))
                except Exception:
                    continue
    if not records:
        tk.Label(emotion_chart_frame, text="No emotion data for this student in the selected month.", font=('Segoe UI', 11), bg='#f3f6fc', fg='#6366f1').pack(pady=30)
        return
    # Count each emotion
    from collections import Counter
    emoji_map = {'😊': 'Happy', '😢': 'Sad', '😠': 'Angry', '😐': 'Neutral'}
    emotion_counts = Counter(emoji_map.get(e, 'Neutral') for _, e in records if e)
    labels = ['Happy', 'Sad', 'Angry', 'Neutral']
    sizes = [emotion_counts.get(label, 0) for label in labels]
    colors = ['#fef08a', '#bae6fd', '#fecaca', '#e5e7eb']
    # Show as bar chart
    fig, ax = plt.subplots(figsize=(5, 3), dpi=100)
    bars = ax.bar(labels, sizes, color=colors)
    ax.set_ylabel('Count')
    ax.set_title(f'{student_name} - Emotional Distribution ({month_name} {year})')
    ax.set_ylim(0, max(sizes) + 1 if sizes else 1)
    for bar, size in zip(bars, sizes):
        if size > 0:
            ax.annotate(str(size), xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10)
    fig.tight_layout()
    chart_canvas = FigureCanvasTkAgg(fig, master=emotion_chart_frame)
    chart_canvas.draw()
    chart_canvas.get_tk_widget().pack(fill='both', expand=True)
    plt.close(fig)

fetch_btn = tk.Button(controls_frame, text="Show History", font=FONT_BUTTON, bg='#6366f1', fg='white', relief='flat', padx=16, pady=6, command=fetch_emotion_history)
fetch_btn.pack(side='left')

# Placeholder for chart
emotion_chart_frame = tk.Frame(emotion_tab, bg='#f3f6fc')
emotion_chart_frame.pack(pady=20, fill='both', expand=True)

# --- Attendance History Tab Content ---
attendance_history_tab = tabs['Attendance History']
tk.Label(attendance_history_tab, text="Student Attendance History", font=('Segoe UI', 14, 'bold'), bg='#f3f6fc').pack(pady=(30, 10))

# Create a frame for the controls (dropdowns and button)
attendance_controls_frame = tk.Frame(attendance_history_tab, bg='#f3f6fc')
attendance_controls_frame.pack(pady=(0, 20))

# Student selection for attendance history
tk.Label(attendance_controls_frame, text="Student:", font=FONT_LABEL, bg='#f3f6fc').pack(side='left', padx=(0, 5))
attendance_student_var = tk.StringVar()
attendance_student_combo = ttk.Combobox(attendance_controls_frame, textvariable=attendance_student_var, state='readonly', width=15)
attendance_student_combo.pack(side='left', padx=(0, 15))

# Month picker for attendance history
tk.Label(attendance_controls_frame, text="Month:", font=FONT_LABEL, bg='#f3f6fc').pack(side='left', padx=(0, 5))
attendance_month_var = tk.StringVar()
attendance_month_combo = ttk.Combobox(
    attendance_controls_frame, textvariable=attendance_month_var, state='readonly', values=get_month_options(), width=15
)
attendance_month_combo.current(0)
attendance_month_combo.pack(side='left', padx=(0, 15))

# Function to fetch and display attendance history
def fetch_attendance_history():
    for widget in attendance_history_frame.winfo_children():
        widget.destroy()
    
    student_name = attendance_student_var.get()
    month_year = attendance_month_var.get()
    
    if not student_name or not month_year:
        tk.Label(attendance_history_frame, text="Please select a student and month.", font=('Segoe UI', 11), bg='#f3f6fc', fg='#6366f1').pack(pady=30)
        return
    
    # Parse selected month and year
    try:
        month_name, year = month_year.split()
        month = list(calendar.month_name).index(month_name)
        year = int(year)
    except Exception:
        tk.Label(attendance_history_frame, text="Invalid month selected.", font=('Segoe UI', 11), bg='#f3f6fc', fg='#6366f1').pack(pady=30)
        return
    
    # Fetch all records for this student from Firebase
    url = f"{FIREBASE_URL}/students.json"
    response = requests.get(url)
    if response.status_code != 200 or not response.json():
        tk.Label(attendance_history_frame, text="No data found.", font=('Segoe UI', 11), bg='#f3f6fc', fg='#6366f1').pack(pady=30)
        return
    
    data = response.json()
    
    # Collect attendance records for this student in the selected month
    records = []
    for v in data.values():
        if v.get('name') == student_name:
            ts = v.get('timestamp')
            status = v.get('status', 'Present')  # Default to Present if no status
            checkin_time = v.get('checkin_time')
            
            if ts:
                try:
                    dt = datetime.fromisoformat(str(ts)[:19])
                    if dt.year == year and dt.month == month:
                        # Determine status based on checkin time if not explicitly set
                        if not status or status == 'Present':
                            if checkin_time:
                                hour, minute = map(int, checkin_time.split(":"))
                                if hour >= 8:  # Late if after 8:00 AM
                                    status = "Late"
                                else:
                                    status = "Present"
                        records.append((dt.date(), status, checkin_time or 'N/A'))
                except Exception:
                    continue
    
    if not records:
        tk.Label(attendance_history_frame, text="No attendance data for this student in the selected month.", font=('Segoe UI', 11), bg='#f3f6fc', fg='#6366f1').pack(pady=30)
        return
    
    # Sort records by date
    records.sort(key=lambda x: x[0])
    
    # Create scrollable frame for records
    main_container = tk.Frame(attendance_history_frame, bg='#f3f6fc')
    main_container.pack(fill='both', expand=True, padx=20, pady=10)
    
    canvas = tk.Canvas(main_container, bg='#f3f6fc', highlightthickness=0)
    scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg='#f3f6fc')
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Create header
    header_frame = tk.Frame(scrollable_frame, bg='#6366f1', padx=10, pady=8)
    header_frame.pack(fill='x', pady=(0, 10))
    
    tk.Label(header_frame, text=f"Attendance History - {student_name} ({month_name} {year})", 
             font=('Segoe UI', 12, 'bold'), bg='#6366f1', fg='white').pack()
    
    # Summary statistics
    total_days = len(records)
    present_days = sum(1 for r in records if r[1] == 'Present')
    late_days = sum(1 for r in records if r[1] == 'Late')
    absent_days = total_days - present_days - late_days
    
    stats_frame = tk.Frame(scrollable_frame, bg='#f3f6fc')
    stats_frame.pack(fill='x', pady=(0, 15))
    
    # Create summary cards
    summary_data = [
        ("Total Days", total_days, "#e3d9fb"),
        ("Present", present_days, "#d4f5d2"),
        ("Late", late_days, "#fff4c2"),
        ("Absent", absent_days, "#fbd6d6")
    ]
    
    for title, count, color in summary_data:
        stat_card = tk.Frame(stats_frame, bg=color, padx=12, pady=8, relief='ridge', bd=1)
        stat_card.pack(side='left', padx=5)
        tk.Label(stat_card, text=title, font=('Segoe UI', 10, 'bold'), bg=color).pack()
        tk.Label(stat_card, text=str(count), font=('Segoe UI', 14, 'bold'), bg=color).pack()
    
    # Display individual records
    records_frame = tk.Frame(scrollable_frame, bg='#f3f6fc')
    records_frame.pack(fill='both', expand=True, pady=10)
    
    for i, (date, status, checkin_time) in enumerate(records):
        # Determine colors based on status
        if status == 'Present':
            bg_color = '#d4f5d2'
            status_color = '#22c55e'
        elif status == 'Late':
            bg_color = '#fff4c2'
            status_color = '#f59e0b'
        else:  # Absent
            bg_color = '#fbd6d6'
            status_color = '#ef4444'
        
        record_frame = tk.Frame(records_frame, bg=bg_color, padx=15, pady=10, relief='raised', bd=1)
        record_frame.pack(fill='x', pady=2)
        
        # Date
        date_label = tk.Label(record_frame, text=date.strftime('%Y-%m-%d (%A)'), 
                             font=('Segoe UI', 11, 'bold'), bg=bg_color, fg='#1f2937')
        date_label.pack(side='left')
        
        # Status badge
        status_badge = tk.Frame(record_frame, bg=status_color, padx=8, pady=2)
        status_badge.pack(side='right', padx=(10, 0))
        tk.Label(status_badge, text=status, font=('Segoe UI', 9, 'bold'), bg=status_color, fg='white').pack()
        
        # Check-in time
        if checkin_time != 'N/A':
            time_label = tk.Label(record_frame, text=f"Check-in: {checkin_time}", 
                                 font=('Segoe UI', 9), bg=bg_color, fg='#6b7280')
            time_label.pack(side='right', padx=(10, 10))
    
    # Bind mousewheel to canvas for scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

# Show History button
fetch_attendance_btn = tk.Button(attendance_controls_frame, text="Show History", font=FONT_BUTTON, bg='#6366f1', fg='white', relief='flat', padx=16, pady=6, command=fetch_attendance_history)
fetch_attendance_btn.pack(side='left')

# Placeholder for attendance history display
attendance_history_frame = tk.Frame(attendance_history_tab, bg='#f3f6fc')
attendance_history_frame.pack(pady=20, fill='both', expand=True)

# --- Attendance & Emotion Tab Content ---
attend_emotion_tab = tabs['Attendance & Emotion']
tk.Label(attend_emotion_tab, text="Attendance & Emotional Profile", font=('Segoe UI', 14, 'bold'), bg='#f3f6fc').pack(pady=(30, 10))

# Create a main container frame for date controls and status counter
main_controls_frame = tk.Frame(attend_emotion_tab, bg='#f3f6fc')
main_controls_frame.pack(fill='x', padx=20, pady=(0, 10))

# Create a frame for date picker and refresh button
date_controls_frame = tk.Frame(main_controls_frame, bg='#f3f6fc')
date_controls_frame.pack(side='top')

# Date picker
tk.Label(date_controls_frame, text="Select Date:", font=FONT_LABEL, bg='#f3f6fc').pack(side='left', padx=(0, 5))

# Create date picker components
selected_date_var = tk.StringVar()
selected_date_var.set(datetime.now().strftime('%Y-%m-%d'))

# Year dropdown
current_year = datetime.now().year
year_var = tk.StringVar()
year_combo = ttk.Combobox(date_controls_frame, textvariable=year_var, state='readonly', width=6)
year_combo['values'] = [str(year) for year in range(current_year - 2, current_year + 1)]
year_combo.set(str(current_year))
year_combo.pack(side='left', padx=(0, 5))

# Month dropdown
month_var = tk.StringVar()
month_combo = ttk.Combobox(date_controls_frame, textvariable=month_var, state='readonly', width=10)
month_combo['values'] = [calendar.month_name[i] for i in range(1, 13)]
month_combo.set(calendar.month_name[datetime.now().month])
month_combo.pack(side='left', padx=(0, 5))

# Day dropdown
day_var = tk.StringVar()
day_combo = ttk.Combobox(date_controls_frame, textvariable=day_var, state='readonly', width=4)
day_combo.set(str(datetime.now().day))
day_combo.pack(side='left', padx=(0, 15))

def update_days(*args):
    """Update day dropdown based on selected year and month"""
    try:
        year = int(year_var.get())
        month = list(calendar.month_name).index(month_var.get())
        _, max_day = calendar.monthrange(year, month)
        day_combo['values'] = [str(i) for i in range(1, max_day + 1)]
        
        # Reset day if current day is not valid for the selected month
        current_day = int(day_var.get()) if day_var.get().isdigit() else 1
        if current_day > max_day:
            day_var.set('1')
    except (ValueError, IndexError):
        day_combo['values'] = [str(i) for i in range(1, 32)]

def get_selected_date():
    """Get the selected date as a datetime.date object"""
    try:
        year = int(year_var.get())
        month = list(calendar.month_name).index(month_var.get())
        day = int(day_var.get())
        return datetime(year, month, day).date()
    except (ValueError, IndexError):
        return datetime.now().date()

# Bind events to update days when year or month changes
year_var.trace('w', update_days)
month_var.trace('w', update_days)

# Initialize days for current month
update_days()

# Add refresh button
refresh_cards_btn = tk.Button(date_controls_frame, text="Show Attendance", font=FONT_BUTTON, bg='#6366f1', fg='white', relief='flat', padx=16, pady=6, command=lambda: show_attendance_emotion_cards(get_selected_date(), current_filter.get()))
refresh_cards_btn.pack(side='left')

# Status counter frame aligned with date controls
status_counter_frame = tk.Frame(main_controls_frame, bg='#f3f6fc')
status_counter_frame.pack(side='left')

# Create status counter cards
attendance_status_labels = {}
attendance_summaries = [
    ("Present", 0, "#d4f5d2"),
    ("Late", 0, "#fff4c2"),
    ("Absent", 0, "#fbd6d6"),
    ("Total", 0, "#e3d9fb")
]

for title, count, color in attendance_summaries:
    status_card = tk.Frame(status_counter_frame, bg=color, width=80, height=65, padx=10, pady=8, relief='ridge', bd=2)
    status_card.pack(side='left', padx=5)
    status_card.pack_propagate(False)  # Maintain fixed size
    
    tk.Label(status_card, text=title, font=('Segoe UI', 10, 'bold'), bg=color, fg='#1f2937').pack()
    value_label = tk.Label(status_card, text=str(count), font=('Segoe UI', 16, 'bold'), bg=color, fg='#1f2937')
    value_label.pack()
    attendance_status_labels[title] = value_label

# Filter status frame beside the counter
filter_frame = tk.Frame(main_controls_frame, bg='#f3f6fc')
filter_frame.pack(side='left', padx=(20, 0))

tk.Label(filter_frame, text="Filter:", font=FONT_LABEL, bg='#f3f6fc').pack(anchor='w')

# Filter buttons
current_filter = tk.StringVar()
current_filter.set("All")

filter_buttons = {}
filter_options = [
    ("All", "#e3d9fb"),
    ("Present", "#d4f5d2"), 
    ("Late", "#fff4c2"),
    ("Absent", "#fbd6d6")
]

filter_buttons_frame = tk.Frame(filter_frame, bg='#f3f6fc')
filter_buttons_frame.pack()

def apply_filter(filter_status):
    """Apply status filter and refresh the display"""
    current_filter.set(filter_status)
    # Update button styles
    for status, btn in filter_buttons.items():
        if status == filter_status:
            btn.configure(relief='sunken', bd=2)
        else:
            btn.configure(relief='raised', bd=1)
    # Refresh the display with filter
    show_attendance_emotion_cards(get_selected_date(), filter_status)

for status, color in filter_options:
    btn = tk.Button(
        filter_buttons_frame, 
        text=status, 
        font=('Segoe UI', 9, 'bold'), 
        bg=color, 
        fg='#1f2937',
        relief='raised' if status != 'All' else 'sunken',
        bd=2 if status == 'All' else 1,
        padx=12, 
        pady=4,
        command=lambda s=status: apply_filter(s)
    )
    btn.pack(side='left', padx=2)
    filter_buttons[status] = btn

# Placeholder for cards
attend_emotion_table_frame = tk.Frame(attend_emotion_tab, bg='#f3f6fc')
attend_emotion_table_frame.pack(pady=10, fill='both', expand=True)

def refresh_student_dropdowns():
    students_data = students_ref.get() or {}
    names = [v.get('name', 'Unknown') for v in students_data.values() if v.get('name')]
    names = list(set(names))  # Remove duplicates
    names.sort()  # Sort alphabetically
    
    # Update emotion history dropdown
    emotion_student_combo['values'] = names
    if names:
        emotion_student_combo.current(0)
    
    # Update attendance history dropdown
    attendance_student_combo['values'] = names
    if names:
        attendance_student_combo.current(0)

refresh_student_dropdowns()

# Initialize attendance cards with today's data
def initialize_attendance_cards():
    show_attendance_emotion_cards(datetime.now().date())

def show_attendance_emotion_cards(selected_date=None, status_filter="All"):
    # Use today's date if no date is provided
    if selected_date is None:
        selected_date = datetime.now().date()
    
    # Clear existing widgets
    for widget in attend_emotion_table_frame.winfo_children():
        widget.destroy()

    # Create main container with scrollbar
    main_container = tk.Frame(attend_emotion_table_frame, bg='#f3f6fc')
    main_container.pack(fill='both', expand=True, padx=20, pady=10)

    # Create canvas and scrollbar for scrolling
    canvas = tk.Canvas(main_container, bg='#f3f6fc', highlightthickness=0)
    scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg='#f3f6fc')

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Pack canvas and scrollbar
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Add date header
    date_header = tk.Frame(scrollable_frame, bg='#6366f1', padx=15, pady=8)
    date_header.pack(fill='x', pady=(0, 15))
    tk.Label(date_header, text=f"Attendance for {selected_date.strftime('%A, %B %d, %Y')}", 
             font=('Segoe UI', 12, 'bold'), bg='#6366f1', fg='white').pack()

    # Fetch and display data as cards
    try:
        url = f"{FIREBASE_URL}/students.json"
        response = requests.get(url)
        if response.status_code == 200 and response.json():
            data = response.json()
            
            # Get students data for the selected date
            students = fetch_students_for_date(selected_date)
            
            # Also get all registered students to show even if not present today
            students_data = students_ref.get() or {}
            all_student_names = set()
            for val in students_data.values():
                name = val.get('name')
                if name:
                    all_student_names.add(name)
            
            # Create a dictionary for quick lookup of selected date's data
            selected_date_data = {}
            for student in students:
                selected_date_data[student[0]] = {
                    'status': student[1],
                    'emotion': student[2],
                    'emoji': student[2] if student[2] else '😐'
                }
            
            # Calculate status counts for all registered students
            present_count = 0
            late_count = 0
            absent_count = 0
            
            for name in all_student_names:
                student_info = selected_date_data.get(name, {'status': 'Absent'})
                if student_info['status'] == 'Present':
                    present_count += 1
                elif student_info['status'] == 'Late':
                    late_count += 1
                else:
                    absent_count += 1
            
            total_count = len(all_student_names)
            
            # Update status counter labels (always show total counts)
            attendance_status_labels["Present"].config(text=str(present_count))
            attendance_status_labels["Late"].config(text=str(late_count))
            attendance_status_labels["Absent"].config(text=str(absent_count))
            attendance_status_labels["Total"].config(text=str(total_count))
            
            # Filter students based on status_filter
            filtered_students = []
            for name in sorted(all_student_names):
                student_info = selected_date_data.get(name, {'status': 'Absent'})
                if status_filter == "All" or student_info['status'] == status_filter:
                    filtered_students.append(name)
            
            # Create cards frame with grid layout
            cards_frame = tk.Frame(scrollable_frame, bg='#f3f6fc')
            cards_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Show filter info
            if status_filter != "All":
                filter_info = tk.Label(scrollable_frame, text=f"Showing {status_filter} students only ({len(filtered_students)} of {total_count})", 
                                     font=('Segoe UI', 10, 'italic'), bg='#f3f6fc', fg='#6366f1')
                filter_info.pack(pady=(0, 10))
            
            row = 0
            col = 0
            max_cols = 4  
            
            for name in filtered_students:
                # Get student data for selected date or default values
                student_info = selected_date_data.get(name, {
                    'status': 'Absent',
                    'emotion': '😐',
                    'emoji': '😐'
                })
                
                # Determine card colors based on status
                if student_info['status'] == 'Present':
                    card_bg = '#d4f5d2'  # Light green
                    status_color = '#22c55e'
                elif student_info['status'] == 'Late':
                    card_bg = '#fff4c2'  # Light yellow
                    status_color = '#f59e0b'
                else:  # Absent
                    card_bg = '#fbd6d6'  
                    status_color = '#ef4444'
                
                # Create student card
                card = tk.Frame(cards_frame, bg=card_bg, relief='raised', bd=2, padx=15, pady=12)
                card.grid(row=row, column=col, padx=10, pady=8, sticky='ew', ipadx=10, ipady=5)
                
                # Student name (larger, bold)
                name_label = tk.Label(card, text=name, font=('Segoe UI', 13, 'bold'), 
                                    bg=card_bg, fg='#1f2937')
                name_label.pack(anchor='w')
                
                # Status with colored background
                status_frame = tk.Frame(card, bg=status_color, padx=8, pady=2)
                status_frame.pack(anchor='w', pady=(5, 0))
                status_label = tk.Label(status_frame, text=student_info['status'], 
                                      font=('Segoe UI', 10, 'bold'), bg=status_color, fg='white')
                status_label.pack()
                
                # Emotion with emoji (only show if not absent)
                if student_info['status'] != 'Absent':
                    emotion_frame = tk.Frame(card, bg=card_bg)
                    emotion_frame.pack(anchor='w', pady=(8, 0))
                    emotion_label = tk.Label(emotion_frame, text=f"Mood: {student_info['emoji']}", 
                                           font=('Segoe UI', 11), bg=card_bg, fg='#374151')
                    emotion_label.pack(side='left')
                
                # Date
                date_label = tk.Label(card, text=f"Date: {selected_date.strftime('%Y-%m-%d')}", 
                                    font=('Segoe UI', 9), bg=card_bg, fg='#6b7280')
                date_label.pack(anchor='w', pady=(5, 0))
                
                # Move to next position
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
            
            # Configure grid weights for responsive layout
            for i in range(max_cols):
                cards_frame.grid_columnconfigure(i, weight=1, uniform="card")
            
            # Show message if no students found for the selected date or filter
            if not all_student_names:
                # Reset counters when no students found
                attendance_status_labels["Present"].config(text="0")
                attendance_status_labels["Late"].config(text="0")
                attendance_status_labels["Absent"].config(text="0")
                attendance_status_labels["Total"].config(text="0")
                
                no_data_label = tk.Label(scrollable_frame, text=f"No student data found for {selected_date.strftime('%B %d, %Y')}", 
                                       font=('Segoe UI', 12), bg='#f3f6fc', fg='#6b7280')
                no_data_label.pack(pady=50)
            elif not filtered_students:
                # Show message when filter results in no students
                no_filter_data_label = tk.Label(scrollable_frame, text=f"No {status_filter.lower()} students found for {selected_date.strftime('%B %d, %Y')}", 
                                              font=('Segoe UI', 12), bg='#f3f6fc', fg='#6b7280')
                no_filter_data_label.pack(pady=50)

    except Exception as e:
        # Reset counters on error
        attendance_status_labels["Present"].config(text="0")
        attendance_status_labels["Late"].config(text="0")
        attendance_status_labels["Absent"].config(text="0")
        attendance_status_labels["Total"].config(text="0")
        
        error_label = tk.Label(scrollable_frame, text=f"Failed to fetch data: {str(e)}", 
                             font=('Segoe UI', 11), bg='#f3f6fc', fg='#ef4444')
        error_label.pack(pady=30)

    # Bind mousewheel to canvas for scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)


root.mainloop()
