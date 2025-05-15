import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import os


students = [
    {"name": "Micoh Alon", "photo": "profile1.jpg"},
    {"name": "Joyce Insorio", "photo": "profile2.jpg"},
    {"name": "Mark Solero", "photo": "profile3.jpg"},
    {"name": "Warren Tuazon", "photo": "profile4.jpg"},
    {"name": "Sharina Silva", "photo": "profile5.jpg"},
    {"name": "Jurie Imperial", "photo": "profile6.jpg"},
    {"name": "Pascual Placios", "photo": "profile7.jpg"},
]

 
for s in students:
    if not os.path.exists(s["photo"]):
        s["photo"] = "default.png"  

root = tk.Tk()
root.title("Attendance System")
root.geometry("1000x600")
root.configure(bg="white")


sidebar = tk.Frame(root, bg="#2f3e9e", width=180)
sidebar.pack(side="left", fill="y")
menu_items = ["Dashboard", "Attendance", "Class Schedule", "Reports", "Calendar"]
for item in menu_items:
    tk.Button(sidebar, text=item, bg="#2f3e9e", fg="white", bd=0, font=("Arial", 12), anchor="w", padx=20).pack(fill="x", pady=5)

topbar = tk.Frame(root, bg="#f5f5f5", height=50)
topbar.pack(fill="x")
tk.Label(topbar, text="Attendance", bg="#f5f5f5", font=("Arial", 14, "bold")).pack(side="left", padx=20)


content = tk.Frame(root, bg="white")
content.pack(fill="both", expand=True)

canvas = tk.Canvas(content, bg="white")
scrollbar = tk.Scrollbar(content, orient="vertical", command=canvas.yview)
scrollable_frame = tk.Frame(canvas, bg="white")

scrollable_frame.bind(
    "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")


def load_image(path):
    img = Image.open(path).resize((80, 80))
    return ImageTk.PhotoImage(img)

images = {}
for student in students:
    images[student["name"]] = load_image(student["photo"])


def mark_attendance(name, status):
    print(f"{name} marked as {status}")

def change_image(name, label):
    filepath = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
    if filepath:
        students_dict[name] = filepath
        images[name] = load_image(filepath)
        label.config(image=images[name])

students_dict = {student["name"]: student["photo"] for student in students}

for i, student in enumerate(students):
    card = tk.Frame(scrollable_frame, bd=1, relief="solid", padx=10, pady=10, bg="white")
    card.grid(row=i // 4, column=i % 4, padx=10, pady=10)

    img_label = tk.Label(card, image=images[student["name"]], bg="white")
    img_label.pack()
    img_label.bind("<Button-1>", lambda e, n=student["name"], l=img_label: change_image(n, l))

    tk.Label(card, text=student["name"], bg="white", font=("Arial", 10, "bold")).pack(pady=5)

    btn_frame = tk.Frame(card, bg="white")
    btn_frame.pack()
    tk.Button(btn_frame, text="P", width=2, bg="#4caf50", fg="white", command=lambda n=student["name"]: mark_attendance(n, "Present")).pack(side="left", padx=2)
    tk.Button(btn_frame, text="A", width=2, bg="#f44336", fg="white", command=lambda n=student["name"]: mark_attendance(n, "Absent")).pack(side="left", padx=2)
    tk.Button(btn_frame, text="L", width=2, bg="#ff9800", fg="white", command=lambda n=student["name"]: mark_attendance(n, "Late")).pack(side="left", padx=2)

root.mainloop()
