"""
screens/login.py  –  PDF to Audiobook · Login & Registration Screen
"""

import tkinter as tk
from tkinter import messagebox

from styles import (BG, PANEL, ACCENT, HIGHLIGHT, TEXT, SUBTEXT, SUCCESS,
                    FONT_TITLE, FONT_HEAD, FONT_BODY, FONT_SMALL, FONT_BTN,
                    btn, entry, error_label, panel_frame)
import database as db


class LoginScreen(tk.Frame):
    """
    Shown before the main app.
    Calls on_login(user_dict) when authentication succeeds.
    """

    def __init__(self, parent: tk.Tk, on_login):
        super().__init__(parent, bg=BG)
        self.on_login = on_login
        self._mode = "login"     # "login" | "register"
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self):
        # ── App logo / title ──
        tk.Label(self, text="📖", bg=BG, fg=HIGHLIGHT,
                 font=("Georgia", 48)).pack(pady=(40, 4))
        tk.Label(self, text="PDF → Audiobook",
                 bg=BG, fg=TEXT, font=FONT_TITLE).pack()
        tk.Label(self, text="Sign in to save your library across sessions",
                 bg=BG, fg=SUBTEXT, font=FONT_SMALL).pack(pady=(2, 20))

        # ── Card ──
        card = panel_frame(self, padx=32, pady=28)
        card.pack(ipadx=10, ipady=10)

        # Title (changes between Login / Register)
        self._card_title_var = tk.StringVar(value="Login")
        tk.Label(card, textvariable=self._card_title_var,
                 bg=PANEL, fg=HIGHLIGHT, font=FONT_HEAD).grid(
            row=0, column=0, columnspan=2, pady=(0, 16), sticky="w")

        # ── Fields ──
        lbl_w = 14

        # Full name (only shown in register mode)
        self._name_row = tk.Frame(card, bg=PANEL)
        self._name_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=2)
        tk.Label(self._name_row, text="Full Name", bg=PANEL, fg=SUBTEXT,
                 font=FONT_SMALL, width=lbl_w, anchor="w").pack(side=tk.LEFT)
        self._name_var = tk.StringVar()
        entry(self._name_row, self._name_var, width=26).pack(side=tk.LEFT)

        # Username
        row2 = tk.Frame(card, bg=PANEL)
        row2.grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)
        tk.Label(row2, text="Username", bg=PANEL, fg=SUBTEXT,
                 font=FONT_SMALL, width=lbl_w, anchor="w").pack(side=tk.LEFT)
        self._user_var = tk.StringVar()
        entry(row2, self._user_var, width=26).pack(side=tk.LEFT)

        # Email (only register)
        self._email_row = tk.Frame(card, bg=PANEL)
        self._email_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=2)
        tk.Label(self._email_row, text="Email (opt.)", bg=PANEL, fg=SUBTEXT,
                 font=FONT_SMALL, width=lbl_w, anchor="w").pack(side=tk.LEFT)
        self._email_var = tk.StringVar()
        entry(self._email_row, self._email_var, width=26).pack(side=tk.LEFT)

        # Password
        row4 = tk.Frame(card, bg=PANEL)
        row4.grid(row=4, column=0, columnspan=2, sticky="ew", pady=2)
        tk.Label(row4, text="Password", bg=PANEL, fg=SUBTEXT,
                 font=FONT_SMALL, width=lbl_w, anchor="w").pack(side=tk.LEFT)
        self._pw_var = tk.StringVar()
        entry(row4, self._pw_var, show="•", width=26).pack(side=tk.LEFT)

        # Confirm password (only register)
        self._confirm_row = tk.Frame(card, bg=PANEL)
        self._confirm_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=2)
        tk.Label(self._confirm_row, text="Confirm PW", bg=PANEL, fg=SUBTEXT,
                 font=FONT_SMALL, width=lbl_w, anchor="w").pack(side=tk.LEFT)
        self._confirm_var = tk.StringVar()
        entry(self._confirm_row, self._confirm_var, show="•", width=26).pack(side=tk.LEFT)

        # Error label
        self._err = error_label(card)
        self._err.grid(row=6, column=0, columnspan=2, pady=(6, 0))

        # Primary action button
        self._action_btn = btn(card, "  Login  ", self._on_action,
                               color=HIGHLIGHT)
        self._action_btn.grid(row=7, column=0, columnspan=2, pady=(16, 4))

        # Toggle mode link
        self._toggle_var = tk.StringVar(value="Don't have an account?  Register →")
        toggle_lbl = tk.Label(card, textvariable=self._toggle_var,
                               bg=PANEL, fg=SUBTEXT, font=FONT_SMALL,
                               cursor="hand2")
        toggle_lbl.grid(row=8, column=0, columnspan=2)
        toggle_lbl.bind("<Button-1>", lambda e: self._toggle_mode())

        # Guest button
        btn(self, "  Continue as Guest  ", self._guest,
            color=ACCENT).pack(pady=(12, 0))
        tk.Label(self, text="(Guest sessions are not saved to the database)",
                 bg=BG, fg=SUBTEXT, font=FONT_SMALL).pack()

        self._set_mode("login")

        # Enter-key shortcut
        self._user_var.trace_add("write", lambda *_: self._clear_err())
        self._pw_var.trace_add("write",   lambda *_: self._clear_err())

    # ── Mode toggling ──────────────────────────────────────────────────────

    def _set_mode(self, mode: str):
        self._mode = mode
        if mode == "login":
            self._card_title_var.set("Login")
            self._action_btn.config(text="  Login  ")
            self._toggle_var.set("Don't have an account?  Register →")
            # hide register-only rows
            self._name_row.grid_remove()
            self._email_row.grid_remove()
            self._confirm_row.grid_remove()
        else:
            self._card_title_var.set("Create Account")
            self._action_btn.config(text="  Register  ")
            self._toggle_var.set("Already have an account?  Login →")
            self._name_row.grid()
            self._email_row.grid()
            self._confirm_row.grid()
        self._clear_err()

    def _toggle_mode(self):
        self._set_mode("register" if self._mode == "login" else "login")

    # ── Actions ────────────────────────────────────────────────────────────

    def _on_action(self):
        if self._mode == "login":
            self._do_login()
        else:
            self._do_register()

    def _do_login(self):
        username = self._user_var.get().strip()
        password = self._pw_var.get()
        if not username or not password:
            self._show_err("Please enter username and password.")
            return
        user = db.login_user(username, password)
        if user:
            self.on_login(user)
        else:
            self._show_err("Invalid username or password.")

    def _do_register(self):
        username = self._user_var.get().strip()
        password = self._pw_var.get()
        confirm  = self._confirm_var.get()
        email    = self._email_var.get().strip()

        if not username or not password:
            self._show_err("Username and password are required.")
            return
        if len(username) < 3:
            self._show_err("Username must be at least 3 characters.")
            return
        if len(password) < 4:
            self._show_err("Password must be at least 4 characters.")
            return
        if password != confirm:
            self._show_err("Passwords do not match.")
            return

        user = db.register_user(username, password, email)
        if user:
            messagebox.showinfo("Registered!",
                                f"Account created.\nWelcome, {username}!")
            self.on_login(user)
        else:
            self._show_err("Username already taken. Please choose another.")

    def _guest(self):
        guest_user = {
            "user_id":  None,
            "username": "Guest",
            "email":    "",
        }
        self.on_login(guest_user)

    # ── Helpers ────────────────────────────────────────────────────────────

    def _show_err(self, msg: str):
        self._err.config(text=msg)

    def _clear_err(self):
        self._err.config(text="")
