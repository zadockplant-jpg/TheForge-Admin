import customtkinter as ctk


def clear_frame(frame):
    for child in frame.winfo_children():
        child.destroy()


def row(parent, label, widget):
    wrapper = ctk.CTkFrame(parent, fg_color="transparent")
    wrapper.pack(fill="x", padx=8, pady=5)
    ctk.CTkLabel(wrapper, text=label, width=150, anchor="w").pack(side="left")
    widget.pack(side="left", fill="x", expand=True)
    return wrapper


def text_box(parent, text="", height=120):
    box = ctk.CTkTextbox(parent, height=height)
    box.insert("1.0", text)
    return box


def show_error(parent, message):
    dialog = ctk.CTkToplevel(parent)
    dialog.title("Error")
    dialog.geometry("440x180")
    dialog.grab_set()
    ctk.CTkLabel(dialog, text="Error", font=("Arial", 18, "bold")).pack(pady=(18, 6))
    ctk.CTkLabel(dialog, text=str(message), wraplength=380).pack(padx=18, pady=10)
    ctk.CTkButton(dialog, text="Close", command=dialog.destroy).pack(pady=10)


def show_info(parent, title, message):
    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.geometry("460x190")
    dialog.grab_set()
    ctk.CTkLabel(dialog, text=title, font=("Arial", 18, "bold")).pack(pady=(18, 6))
    ctk.CTkLabel(dialog, text=str(message), wraplength=400).pack(padx=18, pady=10)
    ctk.CTkButton(dialog, text="Close", command=dialog.destroy).pack(pady=10)
