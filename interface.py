import tkinter as tk
from tkinter import font as tkfont
import subprocess
import sys
import os

class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Fuzzu ML Hand Gesture Control")
        self.root.geometry("360x460")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a1a")

        title_font  = tkfont.Font(family="Segoe UI", size=16, weight="bold")
        sub_font    = tkfont.Font(family="Segoe UI", size=9)
        btn_font    = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        badge_font  = tkfont.Font(family="Segoe UI", size=8)

        header = tk.Frame(self.root, bg="#1a1a1a")
        header.pack(pady=(36, 4))

        tk.Label(header, text="☝", font=tkfont.Font(size=32),
                 bg="#1a1a1a", fg="#ffffff").pack()
        tk.Label(header, text="Hand Gesture Control",
                 font=title_font, bg="#1a1a1a", fg="#ffffff").pack(pady=(6, 2))
        tk.Label(header, text="Select a mode to get started",
                 font=sub_font, bg="#1a1a1a", fg="#888888").pack()

        tk.Frame(self.root, bg="#2e2e2e", height=1, width=280).pack(pady=24)

        self._make_button(
            label="🖱  Gesture Mouse Mode",
            badge=None,
            color="#f0a500",
            hover="#ffc230",
            command=self._launch_gesture_mouse,
            font=btn_font,
            badge_font=badge_font,
        )

        self._make_button(
            label="✏  Drawing Board Mode",
            badge="Coming Soon",
            color="#2e2e2e",
            hover="#3a3a3a",
            command=None,
            font=btn_font,
            badge_font=badge_font,
            text_color="#666666",
        )

        self._make_button(
            label="Exit",
            badge=None,
            color="#c0392b",
            hover="#e74c3c",
            command=self.root.destroy,
            font=btn_font,
            badge_font=badge_font,
        )

        tk.Label(self.root, text="Fuzzu ML · v1.0",
                 font=sub_font, bg="#1a1a1a", fg="#444444").pack(side="bottom", pady=14)

    def _make_button(self, label, badge, color, hover,
                     command, font, badge_font, text_color="#ffffff"):
        frame = tk.Frame(self.root, bg="#1a1a1a")
        frame.pack(pady=6)

        btn = tk.Button(
            frame,
            text=label,
            font=font,
            fg=text_color,
            bg=color,
            activebackground=hover,
            activeforeground=text_color,
            relief="flat",
            bd=0,
            padx=20,
            pady=14,
            width=22,
            cursor="hand2" if command else "arrow",
            command=command if command else lambda: None,
        )
        btn.pack()

        if badge:
            tk.Label(
                frame,
                text=badge,
                font=badge_font,
                bg="#3a3a3a",
                fg="#888888",
                padx=6, pady=2,
            ).pack(pady=(2, 0))

        if command:
            btn.bind("<Enter>", lambda e: btn.config(bg=hover))
            btn.bind("<Leave>", lambda e: btn.config(bg=color))

    def _launch_gesture_mouse(self):
        """Hide launcher, run main.py, restore launcher on exit."""
        self.root.withdraw()
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        proc = subprocess.Popen([sys.executable, script])
        proc.wait()
        self.root.deiconify()


def main():
    root = tk.Tk()
    LauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()