"""
screens/settings_tab.py  –  PDF to Audiobook · Settings Tab
Profile info, password change, default voice/speed, storage stats, delete account.
"""

from __future__ import annotations
import os
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox

import styles as S
import database as db
from converter import list_voices


class SettingsTab(tk.Frame):
    """
    The ⚙️ Settings tab.
    Call .load(user) when a user logs in.
    """

    def __init__(self, parent, output_dir: Path, on_logout,
                 on_delete_account=None, **kw):
        super().__init__(parent, bg=S.BG, **kw)
        self.output_dir       = output_dir
        self._on_logout       = on_logout
        self._on_delete_account = on_delete_account
        self._user: dict | None = None
        self._voices = list_voices()
        self._build()

    # ── Public API ──────────────────────────────────────────────────────────

    def load(self, user: dict):
        self._user = user
        self._username_var.set(user.get("username", ""))
        self._email_var.set(user.get("email", "") or "")

        if user.get("user_id"):
            s = db.get_settings(user["user_id"])
            saved_voice = s.get("default_voice", "")
            saved_speed = int(s.get("default_speed", 150))
            names = [v.name for v in self._voices]
            if saved_voice in names:
                self._def_voice_var.set(saved_voice)
            self._def_speed_var.set(saved_speed)

        self._refresh_storage()
        self._guest_notice.config(
            text="" if user.get("user_id")
            else "⚠  Logged in as Guest – settings won't be saved.")

    # ── UI Build ────────────────────────────────────────────────────────────

    def _build(self):
        canvas = tk.Canvas(self, bg=S.BG, highlightthickness=0)
        scroll = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=S.BG)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win_id, width=canvas.winfo_width())
        inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        self._build_inner(inner)

    def _build_inner(self, parent):
        pad = dict(padx=16, pady=(10, 4))

        # Guest notice
        self._guest_notice = tk.Label(parent, text="", bg=S.BG,
                                      fg=S.WARNING, font=S.FONT_SMALL)
        self._guest_notice.pack(pady=(8, 0))

        # ── Profile ──────────────────────────────────────────────────────
        S.section_header(parent, "👤  Profile").pack(fill=tk.X, **pad)
        pf = S.panel_frame(parent, padx=14, pady=10)
        pf.pack(fill=tk.X, padx=16, pady=4)

        self._username_var = tk.StringVar()
        self._email_var    = tk.StringVar()

        self._field_row(pf, 0, "Username", self._username_var, readonly=True)
        self._field_row(pf, 1, "Email",    self._email_var)
        S.btn(pf, "  Update Email  ", self._update_email,
              color=S.ACCENT).grid(row=2, column=1, sticky="w", pady=(8, 0))

        # ── Password ─────────────────────────────────────────────────────
        S.section_header(parent, "🔒  Change Password").pack(fill=tk.X, **pad)
        pwf = S.panel_frame(parent, padx=14, pady=10)
        pwf.pack(fill=tk.X, padx=16, pady=4)

        self._old_pw_var  = tk.StringVar()
        self._new_pw_var  = tk.StringVar()
        self._conf_pw_var = tk.StringVar()

        self._field_row(pwf, 0, "Current PW",  self._old_pw_var,  show="•")
        self._field_row(pwf, 1, "New PW",       self._new_pw_var,  show="•")
        self._field_row(pwf, 2, "Confirm PW",   self._conf_pw_var, show="•")

        self._pw_err = S.error_label(pwf)
        self._pw_err.grid(row=3, column=0, columnspan=2)
        S.btn(pwf, "  Change Password  ", self._change_password,
              color=S.ACCENT).grid(row=4, column=1, sticky="w", pady=(8, 0))

        # ── Default TTS Settings ─────────────────────────────────────────
        S.section_header(parent, "🎙  Default Voice Settings").pack(fill=tk.X, **pad)
        sf = S.panel_frame(parent, padx=14, pady=10)
        sf.pack(fill=tk.X, padx=16, pady=4)

        tk.Label(sf, text="Default Voice", bg=S.PANEL, fg=S.SUBTEXT,
                 font=S.FONT_SMALL, width=14, anchor="w").grid(row=0, column=0, sticky="w")
        self._def_voice_var = tk.StringVar()
        vnames = [v.name for v in self._voices] or ["(no voices found)"]
        vc = ttk.Combobox(sf, textvariable=self._def_voice_var,
                          values=vnames, width=40, state="readonly", font=S.FONT_BODY)
        vc.current(0)
        vc.grid(row=0, column=1, sticky="w", pady=4)

        tk.Label(sf, text="Default Speed", bg=S.PANEL, fg=S.SUBTEXT,
                 font=S.FONT_SMALL, width=14, anchor="w").grid(row=1, column=0, sticky="w")
        self._def_speed_var = tk.IntVar(value=150)
        sp_row = tk.Frame(sf, bg=S.PANEL)
        sp_row.grid(row=1, column=1, sticky="w", pady=4)
        tk.Scale(sp_row, from_=60, to=280, variable=self._def_speed_var,
                 orient=tk.HORIZONTAL, length=220,
                 bg=S.PANEL, fg=S.TEXT, troughcolor=S.ACCENT,
                 highlightthickness=0, bd=0, showvalue=True,
                 font=S.FONT_SMALL).pack(side=tk.LEFT)
        S.btn(sf, "  💾  Save Defaults  ", self._save_defaults,
              color=S.HIGHLIGHT).grid(row=2, column=1, sticky="w", pady=(8, 0))

        # ── Storage ──────────────────────────────────────────────────────
        S.section_header(parent, "💾  Storage").pack(fill=tk.X, **pad)
        stf = S.panel_frame(parent, padx=14, pady=10)
        stf.pack(fill=tk.X, padx=16, pady=4)

        self._storage_label = tk.Label(stf, text="", bg=S.PANEL, fg=S.TEXT,
                                       font=S.FONT_SMALL, anchor="w")
        self._storage_label.pack(fill=tk.X)

        btn_row = tk.Frame(stf, bg=S.PANEL)
        btn_row.pack(pady=(8, 0))
        S.btn(btn_row, "  Open Folder  ", self._open_folder,
              color=S.ACCENT).pack(side=tk.LEFT, padx=(0, 8))
        S.btn(btn_row, "  🔄 Refresh  ", self._refresh_storage,
              color=S.PANEL).pack(side=tk.LEFT)

        # ── Account ──────────────────────────────────────────────────────
        S.section_header(parent, "🚪  Account").pack(fill=tk.X, **pad)
        af = S.panel_frame(parent, padx=14, pady=10)
        af.pack(fill=tk.X, padx=16, pady=(4, 4))

        S.btn(af, "  Logout  ", self._logout,
              color=S.ACCENT).pack(side=tk.LEFT, padx=(0, 12))

        # ── Delete Account ────────────────────────────────────────────────
        S.section_header(parent, "⚠️  Danger Zone").pack(fill=tk.X, **pad)
        df = S.panel_frame(parent, padx=14, pady=10)
        df.pack(fill=tk.X, padx=16, pady=(4, 20))

        tk.Label(df, text="Permanently deletes your account and all library records.\n"
                           "Your audio files on disk are NOT deleted.",
                 bg=S.PANEL, fg=S.SUBTEXT, font=S.FONT_SMALL,
                 justify="left").pack(anchor="w", pady=(0, 8))

        self._del_pw_var = tk.StringVar()
        pw_row = tk.Frame(df, bg=S.PANEL)
        pw_row.pack(anchor="w", pady=(0, 6))
        tk.Label(pw_row, text="Confirm password:", bg=S.PANEL, fg=S.SUBTEXT,
                 font=S.FONT_SMALL).pack(side=tk.LEFT, padx=(0, 8))
        tk.Entry(pw_row, textvariable=self._del_pw_var, show="•",
                 bg=S.ACCENT, fg=S.TEXT, insertbackground=S.TEXT,
                 relief="flat", font=S.FONT_BODY, width=22).pack(side=tk.LEFT)

        self._del_err = S.error_label(df)
        self._del_err.pack(anchor="w")

        S.btn(df, "  🗑  Delete My Account  ", self._delete_account,
              color=S.HIGHLIGHT).pack(anchor="w", pady=(4, 0))

    # ── Field helper ────────────────────────────────────────────────────────

    def _field_row(self, parent, row, label_text, var, readonly=False, show=""):
        tk.Label(parent, text=label_text, bg=S.PANEL, fg=S.SUBTEXT,
                 font=S.FONT_SMALL, width=14, anchor="w").grid(
            row=row, column=0, sticky="w", pady=2)
        state = "readonly" if readonly else "normal"
        e = tk.Entry(parent, textvariable=var, font=S.FONT_BODY,
                     bg=S.ACCENT, fg=S.TEXT, insertbackground=S.TEXT,
                     relief="flat", width=30, show=show, state=state,
                     disabledbackground=S.BG, disabledforeground=S.SUBTEXT)
        e.grid(row=row, column=1, sticky="w", pady=2, padx=(8, 0))

    # ── Actions ─────────────────────────────────────────────────────────────

    def _update_email(self):
        if not self._user or not self._user.get("user_id"):
            messagebox.showinfo("Guest", "Log in to update your profile.")
            return
        db.update_user_email(self._user["user_id"], self._email_var.get().strip())
        messagebox.showinfo("Updated", "Email updated successfully.")

    def _change_password(self):
        self._pw_err.config(text="")
        if not self._user or not self._user.get("user_id"):
            messagebox.showinfo("Guest", "Log in to change your password.")
            return
        old, new, conf = (self._old_pw_var.get(), self._new_pw_var.get(),
                          self._conf_pw_var.get())
        if not old or not new:
            self._pw_err.config(text="All fields are required.")
            return
        if new != conf:
            self._pw_err.config(text="New passwords do not match.")
            return
        if len(new) < 4:
            self._pw_err.config(text="Password must be at least 4 characters.")
            return
        if db.change_password(self._user["user_id"], old, new):
            messagebox.showinfo("Success", "Password changed successfully.")
            self._old_pw_var.set("")
            self._new_pw_var.set("")
            self._conf_pw_var.set("")
        else:
            self._pw_err.config(text="Current password is incorrect.")

    def _save_defaults(self):
        if not self._user or not self._user.get("user_id"):
            messagebox.showinfo("Guest", "Log in to save default settings.")
            return
        db.save_settings(user_id=self._user["user_id"],
                         voice=self._def_voice_var.get(),
                         speed=self._def_speed_var.get())
        messagebox.showinfo("Saved", "Default voice and speed saved to your profile.")

    def _refresh_storage(self):
        wavs = list(self.output_dir.glob("*.wav"))
        total_mb = sum(f.stat().st_size for f in wavs) / (1024 * 1024)
        self._storage_label.config(
            text=(f"Folder:  {self.output_dir}\n"
                  f"Files: {len(wavs)}   Total size: {total_mb:.1f} MB"))

    def _open_folder(self):
        import subprocess, sys as _sys
        folder = str(self.output_dir)
        try:
            if _sys.platform == "win32":
                os.startfile(folder)
            elif _sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as exc:
            messagebox.showwarning("Open Folder", str(exc))

    def _logout(self):
        if messagebox.askyesno("Logout", "Log out of your account?"):
            self._on_logout()

    def _delete_account(self):
        self._del_err.config(text="")
        if not self._user or not self._user.get("user_id"):
            messagebox.showinfo("Guest", "No account to delete in guest mode.")
            return

        password = self._del_pw_var.get()
        if not password:
            self._del_err.config(text="Enter your password to confirm.")
            return

        # Verify password before deleting
        check = db.login_user(self._user["username"], password)
        if not check:
            self._del_err.config(text="Incorrect password.")
            return

        confirmed = messagebox.askyesno(
            "Delete Account",
            f"This will permanently delete the account '{self._user['username']}' "
            f"and all its library records.\n\n"
            f"Your audio files on disk will NOT be deleted.\n\n"
            f"Are you sure?",
            icon="warning"
        )
        if not confirmed:
            return

        db.delete_user(self._user["user_id"])
        messagebox.showinfo("Deleted", "Your account has been deleted.")
        self._del_pw_var.set("")
        if self._on_delete_account:
            self._on_delete_account()