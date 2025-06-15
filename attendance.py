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
from tkcalendar import DateEntry  
import tempfile
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import hashlib
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import calendar

# --- Firebase Initialization (moved to top) ---
cred_path = r'C:\Users\pc\Downloads\database.json'
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://moodattend-default-rtdb.asia-southeast1.firebasedatabase.app/'
})
ref = db.reference('/')

# --- Login/Register Window ---
def show_login_window():
    login_win = tk.Tk()
    login_win.title("Mood Attend - Login/Register")
    login_win.geometry("500x400")
    login_win.configure(bg='#f3f6fc')

    FONT_HEADER = ('Segoe UI', 16, 'bold')
    FONT_NORMAL = ('Segoe UI', 11)
    FONT_BUTTON = ('Segoe UI', 10, 'bold')

    tk.Label(login_win, text="Mood Attend", font=FONT_HEADER, bg='#f3f6fc', fg='#6366f1').pack(pady=(24, 8))
    tk.Label(login_win, text="Login or Register to continue", font=FONT_NORMAL, bg='#f3f6fc').pack(pady=(0, 16))

    tk.Label(login_win, text="Username:", font=FONT_NORMAL, bg='#f3f6fc').pack(anchor='w', padx=40)
    username_entry = tk.Entry(login_win, font=FONT_NORMAL)
    username_entry.pack(padx=40, fill='x')

    tk.Label(login_win, text="Password:", font=FONT_NORMAL, bg='#f3f6fc').pack(anchor='w', padx=40, pady=(8,0))
    password_entry = tk.Entry(login_win, font=FONT_NORMAL, show='*')
    password_entry.pack(padx=40, fill='x')

    msg_label = tk.Label(login_win, text="", font=FONT_NORMAL, bg='#f3f6fc', fg='red')
    msg_label.pack(pady=(8,0))

    def hash_pw(pw):
        return pw  # For demo, store as plain text. For real use: hashlib.sha256(pw.encode()).hexdigest()

    def login():
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        if not username or not password:
            msg_label.config(text="Please enter both fields.")
            return
        try:
            users_ref = db.reference('/users')
            users = users_ref.get() or {}
            for key, val in users.items():
                if val.get('username') == username and val.get('password') == hash_pw(password):
                    login_win.destroy()
                    show_attendance_window()
                    return
            msg_label.config(text="Invalid username or password.")
        except Exception as e:
            if msg_label.winfo_exists():
                msg_label.config(text=f"Error: {e}")

    def show_register_window():
        reg_win = tk.Toplevel(login_win)
        reg_win.title("Register")
        reg_win.geometry("500x400")
        reg_win.configure(bg='#f3f6fc')

        tk.Label(reg_win, text="Register", font=FONT_HEADER, bg='#f3f6fc', fg='#6366f1').pack(pady=(24, 8))
        tk.Label(reg_win, text="Create a new account", font=FONT_NORMAL, bg='#f3f6fc').pack(pady=(0, 16))

        tk.Label(reg_win, text="Username:", font=FONT_NORMAL, bg='#f3f6fc').pack(anchor='w', padx=40)
        reg_username_entry = tk.Entry(reg_win, font=FONT_NORMAL)
        reg_username_entry.pack(padx=40, fill='x')

        tk.Label(reg_win, text="Password:", font=FONT_NORMAL, bg='#f3f6fc').pack(anchor='w', padx=40, pady=(8,0))
        reg_password_entry = tk.Entry(reg_win, font=FONT_NORMAL, show='*')
        reg_password_entry.pack(padx=40, fill='x')

        tk.Label(reg_win, text="Confirm Password:", font=FONT_NORMAL, bg='#f3f6fc').pack(anchor='w', padx=40, pady=(8,0))
        reg_confirm_entry = tk.Entry(reg_win, font=FONT_NORMAL, show='*')
        reg_confirm_entry.pack(padx=40, fill='x')

        reg_msg_label = tk.Label(reg_win, text="", font=FONT_NORMAL, bg='#f3f6fc', fg='red')
        reg_msg_label.pack(pady=(8,0))

        def do_register():
            username = reg_username_entry.get().strip()
            password = reg_password_entry.get().strip()
            confirm = reg_confirm_entry.get().strip()
            if not username or not password or not confirm:
                reg_msg_label.config(text="Please fill all fields.", fg='red')
                return
            if password != confirm:
                reg_msg_label.config(text="Passwords do not match.", fg='red')
                return
            try:
                users_ref = db.reference('/users')
                users = users_ref.get() or {}
                for key, val in users.items():
                    if val.get('username') == username:
                        reg_msg_label.config(text="Username already exists.", fg='red')
                        return
                users_ref.push({
                    'username': username,
                    'password': hash_pw(password)
                })
                reg_msg_label.config(text="Registered! You can now login.", fg='green')
                reg_win.after(1500, reg_win.destroy)
            except Exception as e:
                reg_msg_label.config(text=f"Error: {e}", fg='red')

        tk.Button(reg_win, text="Register", font=FONT_BUTTON, bg='#6366f1', fg='white', relief='flat', padx=16, pady=6, command=do_register).pack(pady=16)

    btn_frame = tk.Frame(login_win, bg='#f3f6fc')
    btn_frame.pack(pady=16)
    tk.Button(btn_frame, text="Login", font=FONT_BUTTON, bg='#6366f1', fg='white', relief='flat', padx=16, pady=6, command=login).pack(side='left', padx=8)
    tk.Button(btn_frame, text="Register", font=FONT_BUTTON, bg='#e0e7ff', fg='#6366f1', relief='flat', padx=16, pady=6, command=show_register_window).pack(side='left', padx=8)

    login_win.mainloop()

# --- Attendance UI moved to a function ---
def show_attendance_window():
    global root
    root = tk.Tk()
    root.title("Mood Attend - Attendance")
    root.geometry("1350x800")
    root.configure(bg='#f3f6fc')

    FONT_HEADER = ('Segoe UI', 18, 'bold')
    FONT_SUBHEADER = ('Segoe UI', 12, 'bold')
    FONT_NORMAL = ('Segoe UI', 11)
    FONT_BUTTON = ('Segoe UI', 10, 'bold')
    FONT_CARD = ('Segoe UI', 10)

    header_frame = tk.Frame(root, bg='#6366f1', height=40)
    header_frame.pack(fill='x')
    try:
        logo_img = Image.open("logo.png")
        logo_img = logo_img.resize((24, 24), Image.LANCZOS)
        logo_photo = ImageTk.PhotoImage(logo_img)
        logo_label = tk.Label(header_frame, image=logo_photo, bg='#6366f1')
        logo_label.image = logo_photo  # Keep reference
        logo_label.pack(side='left', padx=(15, 6), pady=4)
    except Exception:
        logo_label = tk.Label(header_frame, text="📝", font=('Segoe UI', 14, 'bold'), bg='#6366f1', fg='white')
        logo_label.pack(side='left', padx=(15, 6), pady=4)
    header_label = tk.Label(header_frame, text="Mood Attend - Attendance System", font=('Segoe UI', 14, 'bold'), fg='white', bg='#6366f1', pady=6)
    header_label.pack(side='left')

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

    # Emoji color mapping for easy emotion identification
    EMOJI_COLORS = {
        '😊': "#d4f8d4",  # Light green for happy
        '😢': "#bfdbfe",  # Light blue for sad
        '😠': "#fecaca",  # Light red for angry
        '😐': "#e5e7eb",  # Light gray for neutral
    }

    # --- Main Content Frames ---
    attendance_frame = tk.Frame(root, bg='#f3f6fc')
    attendance_frame.pack(fill='both', expand=True)

    # --- Attendance Tab Content (moved to attendance_frame) ---
    top_frame = tk.Frame(attendance_frame, bg=COLORS['navbar'], height=35)
    top_frame.pack(fill='x', pady=(0, 5))

    # Replace date label with DateEntry (datepicker)
    from tkcalendar import DateEntry  # Already imported at the top

    def on_date_change(event=None):
        selected_date = date_picker.get_date()
        populate_student_cards(selected_date)

    date_picker = DateEntry(top_frame, width=12, background=COLORS['purple'], foreground='white', borderwidth=2, font=FONT_NORMAL, date_pattern='yyyy-mm-dd')
    date_picker.set_date(datetime.now())
    date_picker.pack(side='left', padx=15, pady=6)
    date_picker.bind("<<DateEntrySelected>>", on_date_change)

    def export_attendance():
        selected_date = date_picker.get_date()
        students = fetch_students(selected_date)
        if not students:
            msg.showwarning("Export Attendance", "No attendance data to export for the selected date.")
            return
        filetypes = [("Excel files", "*.xlsx")]
        file = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=filetypes)
        if not file:
            return
        # Prepare data for DataFrame
        data = []
        emoji_to_emotion = {
            '😠': 'angry',
            '😊': 'happy',
            '😢': 'sad',
            '😐': 'neutral',
        }
        for row in students:
            name, status, emoji, _, timestamp = row
            emotion = emoji_to_emotion.get(emoji, 'neutral')
            formatted_time = timestamp
            if timestamp:
                try:
                    dt = datetime.fromisoformat(str(timestamp)[:19])
                    formatted_time = dt.strftime('%Y-%m-%d %H:%M')
                except Exception:
                    formatted_time = str(timestamp)
            data.append([name, status, emoji, emotion, formatted_time])
        df = pd.DataFrame(data, columns=["Name", "Status", "Emoji", "Emotion", "Date & Time"])
        try:
            # Create Excel writer with header information
            with pd.ExcelWriter(file, engine='openpyxl') as writer:
                # Create header information
                header_data = [
                    ["Daily Attendance Report"],
                    [""],
                    [f"Date: {selected_date.strftime('%A, %B %d, %Y')}"],
                    [f"Total Students: {len(data)}"],
                    [f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
                    [""],
                    [""]
                ]
                
                # Create header DataFrame
                header_df = pd.DataFrame(header_data)
                header_df.to_excel(writer, sheet_name='Daily Attendance', index=False, header=False, startrow=0)
                
                # Write main data starting after header
                df.to_excel(writer, sheet_name='Daily Attendance', index=False, startrow=len(header_data))
                
            msg.showinfo("Export Attendance", f"Attendance for {selected_date.strftime('%Y-%m-%d')} exported to {file}")
        except Exception as e:
            msg.showerror("Export Attendance", f"Error exporting to Excel: {e}")

    def send_attendance_email():
        selected_date = date_picker.get_date()
        students = fetch_students(selected_date)
        if not students:
            msg.showwarning("Send Attendance", "No attendance data to send for the selected date.")
            return
        # Prompt for recipient email
        import tkinter.simpledialog as simpledialog
        recipient = simpledialog.askstring("Send Attendance", "Enter recipient email:")
        if not recipient:
            return
        # Export to a temporary Excel file
        data = []
        emoji_to_emotion = {
            '😠': 'angry',
            '😊': 'happy',
            '😢': 'sad',
            '😐': 'neutral',
        }
        for row in students:
            name, status, emoji, emotion, timestamp = row
            formatted_time = timestamp
            if timestamp:
                try:
                    dt = datetime.fromisoformat(str(timestamp)[:19])
                    formatted_time = dt.strftime('%Y-%m-%d %H:%M')
                except Exception:
                    formatted_time = str(timestamp)
            data.append([name, status, emoji, emotion, formatted_time])
        df = pd.DataFrame(data, columns=["Name", "Status", "Emoji", "Emotion", "Date & Time"])
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            temp_filename = tmp.name
        try:
            df.to_excel(temp_filename, index=False)
        except Exception as e:
            msg.showerror("Send Attendance", f"Failed to export Excel file: {e}")
            return
        sender_email = "alonmicoh@gmail.com"
        app_password = "xsyq ewzj yley qmwj"
        subject = f"Attendance for {selected_date.strftime('%Y-%m-%d')}"
        body = f"Please find attached the attendance for {selected_date.strftime('%Y-%m-%d')}."
        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = recipient
        message['Subject'] = subject
        message.attach(MIMEText(body, 'plain'))
        with open(temp_filename, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename=Attendance_{selected_date.strftime('%Y-%m-%d')}.xlsx")
        message.attach(part)
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(sender_email, app_password)
                server.sendmail(sender_email, recipient, message.as_string())
            msg.showinfo("Send Attendance", f"Attendance sent to {recipient}!")
        except Exception as e:
            msg.showerror("Send Attendance", f"Failed to send email: {e}")
        finally:
            try:
                os.remove(temp_filename)
            except Exception:
                pass

    # --- Save Button with Hover Effect ---
    def on_enter(e):
        save_btn['bg'] = '#4f46e5'
    def on_leave(e):
        save_btn['bg'] = COLORS['purple']

    def on_send_enter(e):
        send_btn['bg'] = '#4f46e5'
    def on_send_leave(e):
        send_btn['bg'] = COLORS['purple']

    save_btn = tk.Button(top_frame, text="💾 Save", bg=COLORS['purple'], fg="white", font=FONT_BUTTON, command=export_attendance, relief='flat', padx=12, pady=4, bd=0, activebackground='#4f46e5')
    save_btn.pack(side='right', padx=(8, 4), pady=6)
    save_btn.bind("<Enter>", on_enter)
    save_btn.bind("<Leave>", on_leave)

    send_btn = tk.Button(top_frame, text="📧 Send", bg=COLORS['purple'], fg="white", font=FONT_BUTTON, command=send_attendance_email, relief='flat', padx=12, pady=4, bd=0, activebackground='#4f46e5')
    send_btn.pack(side='right', padx=(8, 4), pady=6)
    send_btn.bind("<Enter>", on_send_enter)
    send_btn.bind("<Leave>", on_send_leave)

    export_weekly_btn = tk.Button(top_frame, text="📊 Weekly", bg=COLORS['purple'], fg="white", font=FONT_BUTTON, command=lambda: export_weekly_summary(), relief='flat', padx=12, pady=4, bd=0, activebackground='#4f46e5')
    export_weekly_btn.pack(side='right', padx=(8, 4), pady=6)
    def on_weekly_enter(e):
        export_weekly_btn['bg'] = '#4f46e5'
    def on_weekly_leave(e):
        export_weekly_btn['bg'] = COLORS['purple']
    export_weekly_btn.bind("<Enter>", on_weekly_enter)
    export_weekly_btn.bind("<Leave>", on_weekly_leave)

    export_monthly_btn = tk.Button(top_frame, text="📅 Monthly", bg=COLORS['purple'], fg="white", font=FONT_BUTTON, command=lambda: export_monthly_summary(), relief='flat', padx=12, pady=4, bd=0, activebackground='#4f46e5')
    export_monthly_btn.pack(side='right', padx=(8, 4), pady=6)
    def on_monthly_enter(e):
        export_monthly_btn['bg'] = '#4f46e5'
    def on_monthly_leave(e):
        export_monthly_btn['bg'] = COLORS['purple']
    export_monthly_btn.bind("<Enter>", on_monthly_enter)
    export_monthly_btn.bind("<Leave>", on_monthly_leave)

    # --- Summary and Pie Chart Side by Side (Attendance Tab) ---
    summary_pie_frame = tk.Frame(attendance_frame, bg='#f3f6fc')
    summary_pie_frame.pack(fill='x', padx=15, pady=5)

    summary_frame = tk.Frame(summary_pie_frame, bg='#f3f6fc')
    summary_frame.pack(side='left', fill='x')

    summary_labels = {}
    summaries = [
        ("Present", 0, COLORS['present']),
        ("Late", 0, COLORS['late']),
        ("Absent", 0, COLORS['absent']),  # Added Absent summary card
        ("Total", 0, COLORS['total'])
    ]

    for title, count, color in summaries:
        card = tk.Frame(summary_frame, bg=color, width=110, height=60, padx=10, pady=6, relief='ridge', bd=1, highlightbackground='#e0e7ff', highlightthickness=1)
        card.pack(side='left', padx=10, pady=4)
        tk.Label(card, text=title, font=('Segoe UI', 10, 'bold'), bg=color).pack()
        value_label = tk.Label(card, text=str(count), font=('Segoe UI', 16, 'bold'), bg=color)
        value_label.pack()
        summary_labels[title] = value_label

    # --- Emotion Color Legend (below summary cards) ---
    legend_frame = tk.Frame(summary_frame, bg='#f3f6fc')
    legend_frame.pack(side='left', padx=(25, 0))
    
    # Legend title and items in vertical layout
    tk.Label(legend_frame, text="Emotion Colors:", font=('Segoe UI', 9, 'bold'), bg='#f3f6fc', fg='#6366f1').pack(anchor='w')
    
    # Create legend items in a grid
    legend_items_frame = tk.Frame(legend_frame, bg='#f3f6fc')
    legend_items_frame.pack()
    
    emotions = [('😊', 'Happy', EMOJI_COLORS['😊']), ('😢', 'Sad', EMOJI_COLORS['😢']), 
                ('😠', 'Angry', EMOJI_COLORS['😠']), ('😐', 'Neutral', EMOJI_COLORS['😐'])]
    
    for i, (emoji, emotion_name, color) in enumerate(emotions):
        legend_item = tk.Frame(legend_items_frame, bg=color, relief='ridge', bd=1)
        legend_item.grid(row=i//2, column=i%2, padx=3, pady=2, sticky='w')
        tk.Label(legend_item, text=f"{emoji} {emotion_name}", font=('Segoe UI', 8), bg=color, padx=5, pady=2).pack()

    # --- Emotion Dashboard as Scale (Attendance Tab) ---
    pie_frame = tk.Frame(summary_pie_frame, bg='#f3f6fc')
    pie_frame.pack(side='left', fill='y', expand=True, padx=(30,0))
    pie_canvas = None  # Will hold the matplotlib canvas

    def draw_emotion_scale(emotion_counts):
        # Remove previous widgets
        for widget in pie_frame.winfo_children():
            widget.destroy()
        # Draw a vertical bar chart for emotion counts
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        fig, ax = plt.subplots(figsize=(3.5, 1.8), dpi=100)
        emojis = list(emotion_counts.keys())
        counts = [emotion_counts[e] for e in emojis]
        ax.bar(emojis, counts, color=['#fef08a', '#bae6fd', '#fecaca', '#e5e7eb'])
        ax.set_ylabel('Count')
        ax.set_title('Emotion Distribution', fontsize=11)
        ax.set_xticks(range(len(emojis)), emojis, fontsize=14)
        for i, v in enumerate(counts):
            ax.text(i, v + 0.05, str(v), ha='center', va='bottom', fontsize=10)
        ax.set_ylim(0, max(counts) + 1 if counts else 1)
        fig.tight_layout(pad=1.0)
        chart_canvas = FigureCanvasTkAgg(fig, master=pie_frame)
        chart_canvas.draw()
        chart_canvas.get_tk_widget().pack(fill='both', expand=True)
        plt.close(fig)



    # --- Filter (Attendance Tab) ---
    filter_frame = tk.Frame(attendance_frame, bg='#f3f6fc')
    filter_frame.pack(fill='x', padx=15, pady=(3, 5))
    tk.Label(filter_frame, text="Filter:", font=('Segoe UI', 9), bg='#f3f6fc').pack(side='left')
    filter_dropdown = ttk.Combobox(filter_frame, values=["All Students", "Present","Absent", "Late"], state='readonly', font=('Segoe UI', 9), width=12)
    filter_dropdown.set("All Students")
    filter_dropdown.pack(side='left', padx=6)

    def on_filter_change(event=None):
        selected_date = date_picker.get_date()
        populate_student_cards(selected_date)

    filter_dropdown.bind("<<ComboboxSelected>>", on_filter_change)

    # --- Student Cards Grid (Attendance Tab) ---
    # Create an outer frame to hold the canvas and scrollbar
    cards_outer_frame = tk.Frame(attendance_frame, bg='#f3f6fc')
    cards_outer_frame.pack(padx=15, pady=5, fill='both', expand=True)

    # Create a canvas and a vertical scrollbar
    cards_canvas = tk.Canvas(cards_outer_frame, bg='#f3f6fc', highlightthickness=0)
    cards_scrollbar = tk.Scrollbar(cards_outer_frame, orient='vertical', command=cards_canvas.yview)
    cards_canvas.configure(yscrollcommand=cards_scrollbar.set)
    cards_canvas.pack(side='left', fill='both', expand=True)
    cards_scrollbar.pack(side='right', fill='y')

    # Create the frame inside the canvas
    cards_frame = tk.Frame(cards_canvas, bg='#f3f6fc')
    cards_window = cards_canvas.create_window((0, 0), window=cards_frame, anchor='nw')

    def on_cards_frame_configure(event):
        cards_canvas.configure(scrollregion=cards_canvas.bbox('all'))
    cards_frame.bind('<Configure>', on_cards_frame_configure)

    def on_canvas_configure(event):
        # Make the inner frame width match the canvas width
        canvas_width = event.width
        cards_canvas.itemconfig(cards_window, width=canvas_width)
    cards_canvas.bind('<Configure>', on_canvas_configure)

    # Enable mousewheel scrolling for the canvas

    def _on_mousewheel(event):
        cards_canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
    cards_canvas.bind_all('<MouseWheel>', _on_mousewheel)

    FIREBASE_URL = "https://moodattend-default-rtdb.asia-southeast1.firebasedatabase.app"

    # --- Emotion to Emoji Mapping ---
    EMOTION_EMOJI = {
        'angry': '😠',
        'happy': '😊',
        'sad': '😢',
        'neutral': '😐',
        'detecting...': '😐',
    }

    def fetch_students(selected_date=None):
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
                    # Parse the date from timestamp
                    record_date = None
                    if timestamp:
                        try:
                            record_date = datetime.fromisoformat(str(timestamp)[:19]).date()
                        except Exception:
                            record_date = None
                    # If selected_date is given, only consider records for that date
                    if selected_date is not None and record_date is not None and record_date != selected_date:
                        continue
                    # Only keep the latest record for each student
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
                        if not emoji and emotion:
                            mapped_emotion = str(emotion).lower()
                            emoji = EMOTION_EMOJI.get(mapped_emotion, EMOTION_EMOJI['neutral'])
                        face_image = value.get('face_image', None)
                        students_dict[name] = (name, status, emoji, face_image, timestamp)
                return list(students_dict.values())
            else:
                return []
        except Exception as e:
            print(f"Error fetching students: {e}")
            return []

    def populate_student_cards(selected_date=None):
        nonlocal pie_canvas
        for widget in cards_frame.winfo_children():
            widget.destroy()
        for widget in pie_frame.winfo_children():
            widget.destroy()
        if selected_date is None:
            selected_date = datetime.now().date()
        students = fetch_students(selected_date)

        # --- Fetch all registered student names from /students node ---
        try:
            registered_ref = db.reference('/students')
            registered_data = registered_ref.get() or {}
            all_names = set()
            for key, val in registered_data.items():
                if 'name' in val:
                    all_names.add(val['name'])
                elif 'username' in val:
                    all_names.add(val['username'])
        except Exception as e:
            all_names = set()

        attended_names = set(s[0] for s in students)
        for name in all_names - attended_names:
            students.append((name, 'Absent', None, None, None))

        filter_value = filter_dropdown.get()
        if filter_value != "All Students":
            students = [s for s in students if s[1] == filter_value]
        all_students = students
        present = sum(1 for s in all_students if s[1] == "Present")
        late = sum(1 for s in all_students if s[1] == "Late")
        absent = sum(1 for s in all_students if s[1] == "Absent")  # Absent counter
        total = len(all_students)
        summary_labels["Present"].config(text=str(present))
        summary_labels["Late"].config(text=str(late))
        summary_labels["Absent"].config(text=str(absent))  # Update Absent label
        summary_labels["Total"].config(text=str(total))
        # Count emotions for scale
        # Only count emotions for students who are not absent
        emotion_counts = {
            '😊': sum(1 for s in all_students if s[2] == '😊' and s[1] != 'Absent'),
            '😢': sum(1 for s in all_students if s[2] == '😢' and s[1] != 'Absent'),
            '😠': sum(1 for s in all_students if s[2] == '😠' and s[1] != 'Absent'),
            '😐': sum(1 for s in all_students if s[2] == '😐' and s[1] != 'Absent'),
            # 'No Emotion': sum(1 for s in all_students if s[1] == 'Absent'),  # Exclude from chart
        }
        draw_emotion_scale(emotion_counts)
        cols = 5
        for i, student in enumerate(students):
            card = create_card(cards_frame, *student, attendance_tab=True)
            card.grid(row=i//cols, column=i%cols, padx=10, pady=10, sticky='n')
        if not students:
            tk.Label(cards_frame, text="No students present for this date.", font=('Segoe UI', 12), bg='#f3f6fc').pack(pady=20)

    def fetch_attendance_history(student_name):
        try:
            url = f"{FIREBASE_URL}/students.json"
            response = requests.get(url)
            if response.status_code == 200 and response.json():
                data = response.json()
                # Collect all records for this student (by name)
                history = []
                for key, value in data.items():
                    name = value.get('name', 'Unknown')
                    if name == student_name:
                        status = value.get('status', '-')
                        emotion = value.get('emotion', '-')
                        emoji = value.get('emoji', '-')
                        timestamp = value.get('timestamp', '-')
                        history.append((timestamp, status, emoji, emotion))
                # Sort by timestamp descending (latest first)
                history.sort(reverse=True, key=lambda x: x[0] if x[0] else '')
                return history
            else:
                return []
        except Exception as e:
            print(f"Error fetching attendance history: {e}")
            return []

    def show_attendance_history(student_name, selected_date=None):
        # Fetch all records for this student
        history = fetch_attendance_history(student_name)
        # Always show all records, ignore selected_date
        win = tk.Toplevel()
        win.title(f"Previous Attendance for {student_name}")
        win.geometry("540x200")
        win.configure(bg='#f3f6fc')
        tk.Label(win, text=f"Previous Attendance for {student_name}", font=FONT_SUBHEADER, bg='#f3f6fc', anchor='center', justify='center').pack(pady=(12, 6), fill='x')
        if not history:
            tk.Label(win, text="No previous attendance found.", font=FONT_NORMAL, bg='#f3f6fc').pack(pady=20)
            return
        # Table headers
        header_frame = tk.Frame(win, bg='#f3f6fc')
        header_frame.pack(fill='x', padx=10)
        headers = ["Date & Time", "Status", "Emoji", "Emotion"]
        for i, h in enumerate(headers):
            lbl = tk.Label(header_frame, text=h, font=FONT_NORMAL, bg='#f3f6fc', fg='#6366f1', width=15, anchor='center', borderwidth=1, relief='solid')
            lbl.grid(row=0, column=i, padx=0, pady=0, sticky='nsew')
            header_frame.grid_columnconfigure(i, weight=1)
        # Table rows
        table_frame = tk.Frame(win, bg='#f3f6fc')
        table_frame.pack(fill='both', expand=True, padx=10, pady=5)
        for r, row in enumerate(history):
            for c, val in enumerate(row):
                display_val = val
                if c == 0:  # Timestamp column
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(val[:19])
                        display_val = dt.strftime('%Y-%m-%d %H:%M')
                    except Exception:
                        display_val = val
                lbl = tk.Label(table_frame, text=display_val, font=FONT_CARD, bg='#f3f6fc', width=15, anchor='center', borderwidth=1, relief='solid')
                lbl.grid(row=r, column=c, padx=0, pady=0, sticky='nsew')
                table_frame.grid_columnconfigure(c, weight=1)
        for c in range(len(headers)):
            table_frame.grid_columnconfigure(c, weight=1)

    def create_card(parent, name, status, emoji, photo_path=None, timestamp=None, attendance_tab=False):
        frame = tk.Frame(
            parent,
            bg=COLORS['card_bg'],
            relief='groove',
            bd=2,
            padx=0,  # Reduce padding
            pady=0,  # Reduce padding
            highlightbackground='#e0e7ff',
            highlightthickness=1,
            width=230,  # Set a fixed width
            height=310  # Set a fixed height
        )
        frame.pack_propagate(False)  # Prevent frame from resizing to fit content

        # --- Add student name at the top ---
        tk.Label(frame, text=name, font=('Segoe UI', 12, 'bold'), bg=COLORS['card_bg'], fg='black').pack(anchor='center', padx=0, pady=(8, 2))

        img_loaded = False
        if photo_path:
            try:
                img = Image.open(photo_path)
                img = img.resize((80, 80))
                photo = ImageTk.PhotoImage(img)
                img_label = tk.Label(frame, image=photo, bg=COLORS['card_bg'])
                img_label.image = photo  # Keep a reference!
                img_label.pack(anchor='center', padx=0, pady=4)
                img_loaded = True
            except Exception as e:
                pass  # Will try to load from registered_faces below
        if not img_loaded:
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
                    img_label.pack(anchor='center', padx=0, pady=4)
                    img_loaded = True
                except Exception as e:
                    pass
        if not img_loaded:
            tk.Label(frame, text=f"👤 {name}", font=FONT_CARD, bg=COLORS['card_bg']).pack(anchor='center', padx=0, pady=4)

        # --- Status/Absent Button ---
        if attendance_tab:
            # Attendance tab: show status bar
            status_frame = tk.Frame(frame, bg=COLORS['card_bg'])
            status_frame.pack(anchor='center', padx=0, pady=(0, 4))
            for s in ["Present", "Absent", "Late"]:
                if s == status:
                    if s == "Absent":
                        bg = "#ef4444"
                        fg = "white"
                    elif s == "Present":
                        bg = "#10b981"
                        fg = "white"
                    elif s == "Late":
                        bg = "#f59e42"
                        fg = "white"
                    else:
                        bg = "#e5e7eb"
                        fg = "#6b7280"
                else:
                    bg = "#e5e7eb"
                    fg = "#6b7280"
                lbl = tk.Label(status_frame, text=s, bg=bg, fg=fg, padx=6, pady=2, font=FONT_CARD, relief='ridge', bd=1)
                lbl.pack(side='left', padx=2)
            # Add date and time display
            if timestamp:
                from datetime import datetime
                dt_str = None
                if isinstance(timestamp, datetime):
                    dt_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(timestamp, str):
                    try:
                        dt = datetime.fromisoformat(timestamp[:19])
                        dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        try:
                            dt = datetime.strptime(timestamp[:10], '%Y-%m-%d')
                            dt_str = dt.strftime('%Y-%m-%d')
                        except Exception:
                            dt_str = timestamp  # fallback to raw string
                else:
                    dt_str = str(timestamp)
                tk.Label(frame, text=f"Date & Time: {dt_str}", font=FONT_CARD, bg=COLORS['card_bg'], fg='#6366f1').pack(anchor='center', padx=0, pady=(0, 4))
            else:
                tk.Label(frame, text="Date & Time: -", font=FONT_CARD, bg=COLORS['card_bg'], fg='#6366f1').pack(anchor='center', padx=0, pady=(0, 4))
            # Show emotion/emoji only if not absent in attendance tab
            if not (attendance_tab and status == 'Absent'):
                tk.Label(frame, text="Emotional Status:", font=FONT_CARD, bg=COLORS['card_bg']).pack(anchor='center', padx=0, pady=(2, 0))
                # Apply color coding to emoji based on emotion
                emoji_bg_color = EMOJI_COLORS.get(emoji, COLORS['card_bg'])
                emoji_label = tk.Label(frame, text=emoji if emoji else '', font=('Segoe UI', 24), 
                                     bg=emoji_bg_color, relief='ridge', bd=1, padx=8, pady=4)
                emoji_label.pack(anchor='center', padx=0)
            else:
                tk.Label(frame, text="Emotional Status:", font=FONT_CARD, bg=COLORS['card_bg']).pack(anchor='center', padx=0, pady=(2, 0))
                tk.Label(frame, text='', font=('Segoe UI', 24), bg=COLORS['card_bg']).pack(anchor='center', padx=0)
            # --- See Previous Attendance Button ---
            # Pass the selected date to show_attendance_history
            btn = tk.Button(frame, text="See Previous Attendance", font=FONT_CARD, bg=COLORS['button'], fg='#6366f1', relief='ridge', bd=1,
                            command=lambda: show_attendance_history(name, date_picker.get_date()))
            btn.pack(anchor='center', pady=(8, 4))
        else:
            # Students tab: show Mark as Absent button if not absent
            if status != 'Absent':
                btn = tk.Button(frame, text="Mark as Absent", font=FONT_CARD, bg="#ef4444", fg='white', relief='ridge', bd=1,
                                command=lambda: [mark_as_absent(name), populate_student_cards(date_picker.get_date())])
                btn.pack(anchor='center', pady=(4, 8))
            else:
                # If already absent, show nothing (or you could show a label if desired)
                tk.Label(frame, text="", bg=COLORS['card_bg']).pack(anchor='center', pady=(4, 8))
            # --- Emotion summary chart for this student ---
            # Fetch all attendance records for this student
            try:
                url = f"{FIREBASE_URL}/students.json"
                import requests
                response = requests.get(url)
                emotion_counts = {'😊': 0, '😢': 0, '😠': 0, '😐': 0}
                if response.status_code == 200 and response.json():
                    data = response.json()
                    for key, value in data.items():
                        if value.get('name') == name:
                            emoji_val = value.get('emoji', '😐')
                            if emoji_val in emotion_counts:
                                emotion_counts[emoji_val] += 1
                            else:
                                emotion_counts['😐'] += 1
            except Exception as e:
                emotion_counts = {'😊': 0, '😢': 0, '😠': 0, '😐': 0}
            # Draw bar chart using matplotlib
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            fig, ax = plt.subplots(figsize=(2.2, 1.1), dpi=100)
            emojis = list(emotion_counts.keys())
            counts = [emotion_counts[e] for e in emojis]
            ax.bar(emojis, counts, color=['#fef08a', '#bae6fd', '#fecaca', '#e5e7eb'])
            ax.set_ylabel('')
            ax.set_title('Emotions', fontsize=9)
            ax.set_xticks(range(len(emojis)), emojis, fontsize=10)
            for i, v in enumerate(counts):
                ax.text(i, v + 0.05, str(v), ha='center', va='bottom', fontsize=8)
            ax.set_ylim(0, max(counts) + 1)
            ax.set_yticks([])
            fig.tight_layout(pad=0.5)
            chart_canvas = FigureCanvasTkAgg(fig, master=frame)
            chart_canvas.draw()
            chart_canvas.get_tk_widget().pack(anchor='center', pady=(2, 4))
            plt.close(fig)
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

    # Add this function to handle marking as absent

    def mark_as_absent(student_name):
        try:
            url = f"{FIREBASE_URL}/students.json"
            response = requests.get(url)
            if response.status_code == 200 and response.json():
                data = response.json()
                for key, value in data.items():
                    if value.get('name') == student_name:
                        update_url = f"{FIREBASE_URL}/students/{key}.json"
                        requests.patch(update_url, json={"status": "Absent"})
                        break
            # Refresh both tabs
            populate_student_cards(date_picker.get_date())
            populate_student_cards(date_picker.get_date())
        except Exception as e:
            msg.showerror("Error", f"Failed to mark as absent: {e}")

    def export_weekly_summary():
        # Dialog for week selection
        def ask_week_date():
            win = tk.Toplevel(root)
            win.title("Select Week")
            win.geometry("300x180")
            win.configure(bg='#f3f6fc')
            tk.Label(win, text="Select any date in the week:", font=FONT_NORMAL, bg='#f3f6fc').pack(pady=(16, 4))
            tk.Label(win, text="(Monday to Friday will be included)", font=('Segoe UI', 9), bg='#f3f6fc', fg='gray').pack(pady=(0, 8))
            # Use DateEntry for week selection
            date_picker = DateEntry(win, width=12, background=COLORS['purple'], foreground='white', borderwidth=2, font=FONT_NORMAL, date_pattern='yyyy-mm-dd')
            date_picker.set_date(datetime.now())
            date_picker.pack(pady=4)
            result = {'date': None}
            def on_ok():
                result['date'] = date_picker.get_date()
                win.destroy()
            tk.Button(win, text="OK", font=FONT_BUTTON, bg=COLORS['purple'], fg='white', relief='flat', command=on_ok).pack(pady=12)
            win.grab_set()
            win.wait_window()
            return result['date']
        selected_date = ask_week_date()
        if not selected_date:
            return
        # Calculate the week range (Monday to Friday)
        weekday = selected_date.weekday()  # Monday is 0, Sunday is 6
        week_start = selected_date - timedelta(days=weekday)
        week_end = week_start + timedelta(days=4)  # Friday is 4 days after Monday
        # Fetch all attendance records for the week
        try:
            url = f"{FIREBASE_URL}/students.json"
            response = requests.get(url)
            if response.status_code != 200 or not response.json():
                msg.showerror("Export Weekly Summary", "No attendance data found.")
                return
            data = response.json()
        except Exception as e:
            msg.showerror("Export Weekly Summary", f"Error fetching data: {e}")
            return
        # Get all registered students
        try:
            registered_ref = db.reference('/students')
            registered_data = registered_ref.get() or {}
            all_students = set()
            for key, val in registered_data.items():
                if 'name' in val:
                    all_students.add(val['name'])
                elif 'username' in val:
                    all_students.add(val['username'])
        except Exception as e:
            all_students = set()

        # Filter records for the selected week
        records = []
        for key, value in data.items():
            timestamp = value.get('timestamp')
            name = value.get('name', 'Unknown')
            status = value.get('status', 'Absent')
            emotion = value.get('emotion', 'neutral')
            emoji = value.get('emoji', '😐')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(str(timestamp)[:19])
                    record_date = dt.date()
                    if week_start <= record_date <= week_end:
                        records.append((name, status, emoji, emotion, dt))
                except Exception:
                    continue

        # Calculate total weekdays in the period
        total_weekdays = 5  # Monday to Friday

        # Summarize attendance and emotion per student
        summary = {}
        
        # Initialize all registered students
        for student_name in all_students:
            summary[student_name] = {'Present': 0, 'Absent': 0, 'Late': 0, '😊': 0, '😢': 0, '😠': 0, '😐': 0}
        
        # Count actual attendance records
        for name, status, emoji, emotion, dt in records:
            if name not in summary:
                summary[name] = {'Present': 0, 'Absent': 0, 'Late': 0, '😊': 0, '😢': 0, '😠': 0, '😐': 0}
            if status in summary[name]:
                summary[name][status] += 1
            else:
                summary[name][status] = 1
            if emoji in summary[name]:
                summary[name][emoji] += 1
            else:
                summary[name][emoji] = 1

        # Calculate absences for each student
        for student_name in summary:
            attended_days = summary[student_name]['Present'] + summary[student_name]['Late']
            summary[student_name]['Absent'] = max(0, total_weekdays - attended_days)
        # Prepare data for DataFrame
        data = []
        for name, counts in summary.items():
            row = [name, counts.get('Present', 0), counts.get('Absent', 0), counts.get('Late', 0),
                   counts.get('😊', 0), counts.get('😢', 0), counts.get('😠', 0), counts.get('😐', 0)]
            data.append(row)
        columns = ["Name", "Present", "Absent", "Late", "Happy (😊)", "Sad (😢)", "Angry (😠)", "Neutral (😐)"]
        df = pd.DataFrame(data, columns=columns)
        
        # Ask for file location
        filetypes = [("Excel files", "*.xlsx")]
        file = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=filetypes, title=f"Save Weekly Summary ({week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}) As")
        if not file:
            return
        try:
            # Create Excel writer with multiple sheets/formatting
            with pd.ExcelWriter(file, engine='openpyxl') as writer:
                # Create header information
                header_data = [
                    ["Weekly Attendance Summary"],
                    [""],
                    [f"Week Range: {week_start.strftime('%A, %B %d, %Y')} to {week_end.strftime('%A, %B %d, %Y')}"],
                    [f"Total Weekdays: {total_weekdays}"],
                    [f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
                    [""],
                    [""]
                ]
                
                # Create header DataFrame
                header_df = pd.DataFrame(header_data)
                header_df.to_excel(writer, sheet_name='Weekly Summary', index=False, header=False, startrow=0)
                
                # Write main data starting after header
                df.to_excel(writer, sheet_name='Weekly Summary', index=False, startrow=len(header_data))
                
            msg.showinfo("Export Weekly Summary", f"Weekly summary for {week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')} exported to {file}")
        except Exception as e:
            msg.showerror("Export Weekly Summary", f"Error exporting to Excel: {e}")

    def export_monthly_summary():
        # Dialog for month/year selection
        def ask_month_year():
            win = tk.Toplevel(root)
            win.title("Select Month and Year")
            win.geometry("300x160")
            win.configure(bg='#f3f6fc')
            tk.Label(win, text="Select Month:", font=FONT_NORMAL, bg='#f3f6fc').pack(pady=(16, 4))
            # Use DateEntry for month/year selection
            date_picker = DateEntry(win, width=12, background=COLORS['purple'], foreground='white', borderwidth=2, font=FONT_NORMAL, date_pattern='yyyy-mm-dd')
            date_picker.set_date(datetime.now())
            date_picker.pack(pady=4)
            result = {'date': None}
            def on_ok():
                result['date'] = date_picker.get_date()
                win.destroy()
            tk.Button(win, text="OK", font=FONT_BUTTON, bg=COLORS['purple'], fg='white', relief='flat', command=on_ok).pack(pady=12)
            win.grab_set()
            win.wait_window()
            return result['date']
        selected_date = ask_month_year()
        if not selected_date:
            return
        year = selected_date.year
        month = selected_date.month
        # Fetch all attendance records for the month
        try:
            url = f"{FIREBASE_URL}/students.json"
            response = requests.get(url)
            if response.status_code != 200 or not response.json():
                msg.showerror("Export Monthly Summary", "No attendance data found.")
                return
            data = response.json()
        except Exception as e:
            msg.showerror("Export Monthly Summary", f"Error fetching data: {e}")
            return
        # Get all registered students
        try:
            registered_ref = db.reference('/students')
            registered_data = registered_ref.get() or {}
            all_students = set()
            for key, val in registered_data.items():
                if 'name' in val:
                    all_students.add(val['name'])
                elif 'username' in val:
                    all_students.add(val['username'])
        except Exception as e:
            all_students = set()

        # Filter records for the selected month/year
        records = []
        for key, value in data.items():
            timestamp = value.get('timestamp')
            name = value.get('name', 'Unknown')
            status = value.get('status', 'Absent')
            emotion = value.get('emotion', 'neutral')
            emoji = value.get('emoji', '😐')
            if timestamp:
                try:
                    dt = datetime.fromisoformat(str(timestamp)[:19])
                    if dt.year == year and dt.month == month:
                        records.append((name, status, emoji, emotion, dt))
                except Exception:
                    continue

        # Calculate total weekdays in the month
        import calendar
        total_days = calendar.monthrange(year, month)[1]
        first_day = datetime(year, month, 1).weekday()  # Monday is 0
        total_weekdays = 0
        for day in range(1, total_days + 1):
            weekday = (first_day + day - 1) % 7
            if weekday < 5:  # Monday to Friday (0-4)
                total_weekdays += 1

        # Summarize attendance and emotion per student
        summary = {}
        
        # Initialize all registered students
        for student_name in all_students:
            summary[student_name] = {'Present': 0, 'Absent': 0, 'Late': 0, '😊': 0, '😢': 0, '😠': 0, '😐': 0}
        
        # Count actual attendance records
        for name, status, emoji, emotion, dt in records:
            if name not in summary:
                summary[name] = {'Present': 0, 'Absent': 0, 'Late': 0, '😊': 0, '😢': 0, '😠': 0, '😐': 0}
            if status in summary[name]:
                summary[name][status] += 1
            else:
                summary[name][status] = 1
            if emoji in summary[name]:
                summary[name][emoji] += 1
            else:
                summary[name][emoji] = 1

        # Calculate absences for each student
        for student_name in summary:
            attended_days = summary[student_name]['Present'] + summary[student_name]['Late']
            summary[student_name]['Absent'] = max(0, total_weekdays - attended_days)
        # Prepare data for DataFrame
        data = []
        for name, counts in summary.items():
            row = [name, counts.get('Present', 0), counts.get('Absent', 0), counts.get('Late', 0),
                   counts.get('😊', 0), counts.get('😢', 0), counts.get('😠', 0), counts.get('😐', 0)]
            data.append(row)
        columns = ["Name", "Present", "Absent", "Late", "Happy (😊)", "Sad (😢)", "Angry (😠)", "Neutral (😐)"]
        df = pd.DataFrame(data, columns=columns)
        
        # Ask for file location
        filetypes = [("Excel files", "*.xlsx")]
        file = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=filetypes, title="Save Monthly Summary As")
        if not file:
            return
        try:
            # Create Excel writer with multiple sheets/formatting
            with pd.ExcelWriter(file, engine='openpyxl') as writer:
                # Create header information
                month_name = calendar.month_name[month]
                month_start = datetime(year, month, 1)
                month_end = datetime(year, month, calendar.monthrange(year, month)[1])
                
                header_data = [
                    ["Monthly Attendance Summary"],
                    [""],
                    [f"Month: {month_name} {year}"],
                    [f"Date Range: {month_start.strftime('%B %d, %Y')} to {month_end.strftime('%B %d, %Y')}"],
                    [f"Total Weekdays: {total_weekdays}"],
                    [f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
                    [""],
                    [""]
                ]
                
                # Create header DataFrame
                header_df = pd.DataFrame(header_data)
                header_df.to_excel(writer, sheet_name='Monthly Summary', index=False, header=False, startrow=0)
                
                # Write main data starting after header
                df.to_excel(writer, sheet_name='Monthly Summary', index=False, startrow=len(header_data))
                
            msg.showinfo("Export Monthly Summary", f"Monthly summary for {month_name} {year} exported to {file}")
        except Exception as e:
            msg.showerror("Export Monthly Summary", f"Error exporting to Excel: {e}")

    # Call with today's date by default
    populate_student_cards(date_picker.get_date())
    root.mainloop()

# --- Start the app with login window ---
if __name__ == "__main__":
    show_login_window()

