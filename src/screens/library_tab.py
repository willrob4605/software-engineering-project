"""
screens/library_tab.py  –  PDF to Audiobook · Library Tab
Displays all converted audiobooks for the logged-in user.
Supports play, save-as, and delete.
"""

from __future__ import annotations
import os
from pathlib import Path

import tkinter as tk
from tkinter import messagebox

import styles as S
import database as db


class LibraryTab(tk.Frame):
    """
    The 📚 Library tab.
    Parent calls .refresh(user) whenever the library may have changed.
    """

    def __init__(self, parent, output_dir: Path, on_play, on_save_as, **kw):
        """
        Parameters
        ----------
        on_play    : callable(path: str)  – play an audio file (handled by ConverterTab)
        on_save_as : callable(path: str)  – save-as dialog (handled by ConverterTab)
        """
        super().__init__(parent, bg=S.BG, **kw)
        self.output_dir = output_dir
        self._on_play    = on_play
        self._on_save_as = on_save_as
        self._user: dict | None = None
        self._entries: list[dict] = []   # current rows shown in listbox

        self._build()

    # ── Public API ──────────────────────────────────────────────────────────

    def refresh(self, user: dict | None = None):
        """Reload library from DB (or disk fallback for guest)."""
        if user is not None:
            self._user = user
        self._load_entries()
        self._populate()

    # ── UI Build ────────────────────────────────────────────────────────────

    def _build(self):
        # Header
        tk.Label(self, text="Your Converted Audiobooks",
                 bg=S.BG, fg=S.TEXT, font=S.FONT_HEAD).pack(pady=(14, 2))
        self._dir_label = tk.Label(
            self, text=f"Saved to: {self.output_dir}",
            bg=S.BG, fg=S.SUBTEXT, font=S.FONT_SMALL)
        self._dir_label.pack()

        # ── Search bar ──
        search_row = tk.Frame(self, bg=S.BG)
        search_row.pack(fill=tk.X, padx=16, pady=(8, 2))
        tk.Label(search_row, text="🔍", bg=S.BG, fg=S.SUBTEXT,
                 font=S.FONT_BODY).pack(side=tk.LEFT)
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._populate())
        tk.Entry(search_row, textvariable=self._search_var,
                 bg=S.ACCENT, fg=S.TEXT, insertbackground=S.TEXT,
                 relief="flat", font=S.FONT_BODY, width=40).pack(
            side=tk.LEFT, padx=(6, 0))

        # ── Listbox ──
        list_frame = tk.Frame(self, bg=S.BG)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)

        scrollbar = tk.Scrollbar(list_frame, bg=S.PANEL, troughcolor=S.BG)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._listbox = tk.Listbox(
            list_frame, yscrollcommand=scrollbar.set,
            bg=S.PANEL, fg=S.TEXT,
            selectbackground=S.ACCENT, selectforeground=S.TEXT,
            font=S.FONT_BODY, relief="flat", bd=0,
            activestyle="none", highlightthickness=0)
        self._listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self._listbox.yview)

        # Double-click to play
        self._listbox.bind("<Double-Button-1>", lambda e: self._play())

        # ── Detail panel ──
        self._detail = tk.Label(
            self, text="", bg=S.PANEL, fg=S.SUBTEXT,
            font=S.FONT_SMALL, anchor="w", padx=12, pady=4)
        self._detail.pack(fill=tk.X, padx=16)
        self._listbox.bind("<<ListboxSelect>>", self._on_select)

        # ── Buttons ──
        btn_row = tk.Frame(self, bg=S.BG)
        btn_row.pack(pady=(6, 10))

        S.btn(btn_row, "▶  Play",       self._play,    S.SUCCESS).pack(side=tk.LEFT, padx=4)
        S.btn(btn_row, "💾  Save As…",  self._save_as, S.ACCENT ).pack(side=tk.LEFT, padx=4)
        S.btn(btn_row, "🗑  Delete",     self._delete,  S.ACCENT ).pack(side=tk.LEFT, padx=4)
        S.btn(btn_row, "🔄  Refresh",   lambda: self.refresh(), S.PANEL).pack(side=tk.LEFT, padx=4)

        # ── Empty-state label ──
        self._empty_label = tk.Label(
            self,
            text="No audiobooks yet.\nConvert a PDF on the ⚙ Converter tab!",
            bg=S.BG, fg=S.SUBTEXT, font=S.FONT_BODY)

    # ── Data loading ────────────────────────────────────────────────────────

    def _load_entries(self):
        if self._user and self._user.get("user_id"):
            self._entries = db.get_library(self._user["user_id"])
        else:
            # Guest: scan output_dir for .wav files
            self._entries = []
            for wav in sorted(self.output_dir.glob("*.wav"),
                              key=lambda p: p.stat().st_mtime, reverse=True):
                self._entries.append({
                    "file_id": None,
                    "name":    wav.stem,
                    "path":    str(wav),
                    "created": "",
                    "size_kb": wav.stat().st_size // 1024,
                    "voice":   "",
                    "speed":   "",
                })

    # ── Populate listbox ────────────────────────────────────────────────────

    def _populate(self):
        query = self._search_var.get().lower()
        self._listbox.delete(0, tk.END)

        visible = [e for e in self._entries
                   if query in e["name"].lower()] if query else self._entries

        if not visible:
            self._empty_label.pack(pady=20)
        else:
            self._empty_label.pack_forget()

        for entry in visible:
            exists  = "✓" if os.path.exists(entry["path"]) else "✗"
            size    = entry.get("size_kb", "?")
            created = entry.get("created", "")[:16]   # trim seconds
            line = f"  {exists}  {entry['name']:<35}  {created:<16}  {size} KB"
            self._listbox.insert(tk.END, line)

        # colour missing files red
        for i, entry in enumerate(visible):
            if not os.path.exists(entry["path"]):
                self._listbox.itemconfig(i, fg=S.HIGHLIGHT)

        self._visible = visible   # keep reference for index lookups

    # ── Selection detail ────────────────────────────────────────────────────

    def _on_select(self, _event=None):
        entry = self._selected_entry()
        if not entry:
            return
        voice = entry.get("voice") or "—"
        speed = entry.get("speed") or "—"
        path  = entry.get("path", "")
        self._detail.config(
            text=f"  Voice: {voice}   Speed: {speed} wpm   Path: {path}")

    # ── Actions ─────────────────────────────────────────────────────────────

    def _play(self):
        entry = self._selected_entry()
        if entry is None:
            return
        if not os.path.exists(entry["path"]):
            messagebox.showerror("Missing File",
                                 f"File not found:\n{entry['path']}")
            return
        self._on_play(entry["path"])

    def _save_as(self):
        entry = self._selected_entry()
        if entry is None:
            return
        self._on_save_as(entry["path"])

    def _delete(self):
        entry = self._selected_entry()
        if entry is None:
            return
        name = entry["name"]
        delete_file = messagebox.askyesno(
            "Delete",
            f"Remove '{name}' from your library?\n\n"
            "Also delete the .wav file from disk?",
            icon="warning")

        if not delete_file:
            return

        # Remove DB record
        if entry.get("file_id") and self._user and self._user.get("user_id"):
            db.delete_audio_entry(entry["file_id"])

        # Optionally delete the file
        path = Path(entry["path"])
        if path.exists():
            try:
                path.unlink()
            except Exception as exc:
                messagebox.showwarning("Delete Error",
                                       f"Could not delete file:\n{exc}")

        self.refresh()

    # ── Helper ──────────────────────────────────────────────────────────────

    def _selected_entry(self) -> dict | None:
        sel = self._listbox.curselection()
        if not sel:
            messagebox.showinfo("Select Item",
                                "Please select an item in the library first.")
            return None
        idx = sel[0]
        try:
            return self._visible[idx]
        except (AttributeError, IndexError):
            return None
