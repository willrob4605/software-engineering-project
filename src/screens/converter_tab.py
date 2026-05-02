"""
screens/converter_tab.py  –  PDF to Audiobook · Converter Tab
Handles file selection, TTS settings, conversion progress, and playback.
"""

from __future__ import annotations
import os
import shutil
import threading
import time
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import styles as S
import database as db
from pdf_reader import extract_text, page_count, PDFReadError
from converter  import convert_to_audio, list_voices, TTSError


class ConverterTab(tk.Frame):
    """
    The ⚙ Converter tab.  All state that belongs here lives here;
    the parent app just calls .set_user() when login changes.
    """

    def __init__(self, parent, output_dir: Path, on_library_change, **kw):
        super().__init__(parent, bg=S.BG, **kw)
        self.output_dir        = output_dir
        self.on_library_change = on_library_change   # callback → refresh library tab

        self._user: dict | None = None
        self._pdf_path: str | None = None
        self._current_audio: str | None = None
        self._is_playing     = False
        self._pygame_ok      = False

        self._voices = list_voices()

        self._init_pygame()
        self._build()

    # ── Pygame ─────────────────────────────────────────────────────────────

    def _init_pygame(self):
        try:
            import pygame
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._pygame = pygame
            self._pygame_ok = True
        except Exception:
            self._pygame_ok = False

    # ── Public API ─────────────────────────────────────────────────────────

    def set_user(self, user: dict):
        self._user = user
        # load saved settings for this user
        if user.get("user_id"):
            s = db.get_settings(user["user_id"])
            saved_voice = s.get("default_voice", "")
            saved_speed = s.get("default_speed", 150)
            if saved_voice:
                names = [v.name for v in self._voices]
                if saved_voice in names:
                    self._voice_var.set(saved_voice)
            self._speed_var.set(saved_speed)

    def load_audio(self, path: str):
        """Called from library tab – load & ready an audio file for playback."""
        self._current_audio = path
        self._play_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.NORMAL)
        self._save_btn.config(state=tk.NORMAL)
        self._np_label.config(text=f"Ready: {Path(path).name}")

    # ── UI Build ───────────────────────────────────────────────────────────

    def _build(self):
        # ── 1 · Upload ──
        S.section_header(self, "1 · Upload PDF").pack(
            fill=tk.X, padx=8, pady=(10, 4))

        row = tk.Frame(self, bg=S.BG)
        row.pack(fill=tk.X, padx=16, pady=4)
        self._file_label = tk.Label(
            row, text="No file selected",
            bg=S.PANEL, fg=S.SUBTEXT, font=S.FONT_BODY,
            anchor="w", padx=10, pady=8, relief="flat")
        self._file_label.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)
        S.btn(row, "  Browse…  ", self._browse, color=S.ACCENT).pack(
            side=tk.RIGHT, padx=(8, 0))

        self._page_info = tk.Label(self, text="", bg=S.BG, fg=S.SUBTEXT,
                                   font=S.FONT_SMALL)
        self._page_info.pack(anchor="w", padx=20)

        # ── 2 · Voice Settings ──
        S.section_header(self, "2 · Voice Settings").pack(
            fill=tk.X, padx=8, pady=(10, 4))

        sf = S.panel_frame(self, padx=14, pady=10)
        sf.pack(fill=tk.X, padx=16, pady=4)

        # Voice picker
        tk.Label(sf, text="Voice", bg=S.PANEL, fg=S.SUBTEXT,
                 font=S.FONT_SMALL, width=12, anchor="w").grid(
            row=0, column=0, sticky="w")
        self._voice_var = tk.StringVar()
        vnames = [v.name for v in self._voices]
        if not vnames:
            vnames = ["(no TTS voices found – install espeak-ng)"]
        vc = ttk.Combobox(sf, textvariable=self._voice_var,
                          values=vnames, width=46, state="readonly",
                          font=S.FONT_BODY)
        default_idx = next(
            (i for i, n in enumerate(vnames)
             if any(k in n for k in ("America)", "Zira", "David", "United States"))),
            0)
        vc.current(default_idx)
        vc.grid(row=0, column=1, sticky="w", pady=4)

        # Speed
        tk.Label(sf, text="Speed (wpm)", bg=S.PANEL, fg=S.SUBTEXT,
                 font=S.FONT_SMALL, width=12, anchor="w").grid(
            row=1, column=0, sticky="w")
        sp_row = tk.Frame(sf, bg=S.PANEL)
        sp_row.grid(row=1, column=1, sticky="w", pady=4)
        self._speed_var = tk.IntVar(value=150)
        tk.Scale(sp_row, from_=60, to=280, variable=self._speed_var,
                 orient=tk.HORIZONTAL, length=240,
                 bg=S.PANEL, fg=S.TEXT, troughcolor=S.ACCENT,
                 highlightthickness=0, bd=0, showvalue=True,
                 font=S.FONT_SMALL).pack(side=tk.LEFT)
        tk.Label(sp_row, text="◀ slow    fast ▶",
                 bg=S.PANEL, fg=S.SUBTEXT, font=S.FONT_SMALL).pack(
            side=tk.LEFT, padx=8)

        # Output name
        tk.Label(sf, text="Output name", bg=S.PANEL, fg=S.SUBTEXT,
                 font=S.FONT_SMALL, width=12, anchor="w").grid(
            row=2, column=0, sticky="w")
        self._outname_var = tk.StringVar(value="my_audiobook")
        tk.Entry(sf, textvariable=self._outname_var, font=S.FONT_BODY,
                 bg=S.ACCENT, fg=S.TEXT, insertbackground=S.TEXT,
                 relief="flat", width=32).grid(
            row=2, column=1, sticky="w", pady=4)

        # Save-settings button
        S.btn(sf, "  💾  Save as defaults  ", self._save_settings,
              color=S.ACCENT).grid(row=3, column=1, sticky="w", pady=(8, 0))

        # ── 3 · Convert ──
        S.section_header(self, "3 · Convert").pack(
            fill=tk.X, padx=8, pady=(10, 4))
        cf = S.panel_frame(self, padx=14, pady=10)
        cf.pack(fill=tk.X, padx=16, pady=4)

        btn_row = tk.Frame(cf, bg=S.PANEL)
        btn_row.pack(fill=tk.X)
        self._convert_btn = S.btn(
            btn_row, "  🎙  Convert to Audiobook  ",
            self._start_conversion, color=S.HIGHLIGHT)
        self._convert_btn.pack(side=tk.LEFT)
        self._conv_status = tk.Label(btn_row, text="", bg=S.PANEL,
                                     fg=S.SUBTEXT, font=S.FONT_SMALL)
        self._conv_status.pack(side=tk.LEFT, padx=14)

        self._prog_var = tk.DoubleVar()
        self._progress = ttk.Progressbar(
            cf, variable=self._prog_var, maximum=100, length=400,
            style="red.Horizontal.TProgressbar")
        self._progress.pack(fill=tk.X, pady=(8, 0))

        # ── 4 · Playback ──
        S.section_header(self, "4 · Playback & Download").pack(
            fill=tk.X, padx=8, pady=(10, 4))
        pf = S.panel_frame(self, padx=14, pady=10)
        pf.pack(fill=tk.X, padx=16, pady=4)

        ctrl = tk.Frame(pf, bg=S.PANEL)
        ctrl.pack()

        self._play_btn = S.btn(ctrl, "▶  Play",  self._play,  color=S.SUCCESS)
        self._play_btn.pack(side=tk.LEFT, padx=4)
        self._play_btn.config(state=tk.DISABLED)

        self._stop_btn = S.btn(ctrl, "■  Stop",  self._stop,  color=S.ACCENT)
        self._stop_btn.pack(side=tk.LEFT, padx=4)
        self._stop_btn.config(state=tk.DISABLED)

        self._save_btn = S.btn(ctrl, "💾  Save As…", self._save_as, color=S.ACCENT)
        self._save_btn.pack(side=tk.LEFT, padx=4)
        self._save_btn.config(state=tk.DISABLED)

        self._np_label = tk.Label(pf, text="", bg=S.PANEL,
                                  fg=S.SUBTEXT, font=S.FONT_SMALL)
        self._np_label.pack(pady=(6, 0))

        if not self._pygame_ok:
            tk.Label(pf, text="⚠  pygame not installed – playback unavailable",
                     bg=S.PANEL, fg=S.WARNING, font=S.FONT_SMALL).pack()

        self._tick()

    # ── Browse ─────────────────────────────────────────────────────────────

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select a PDF file",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if not path:
            return
        self._pdf_path = path
        name = Path(path).name
        stem = Path(path).stem
        self._file_label.config(text=f"  {name}", fg=S.TEXT)
        self._outname_var.set(stem[:40].replace(" ", "_"))
        pages = page_count(path)
        self._page_info.config(
            text=f"  Pages: {pages}" if pages else "  (page count unavailable)")

    # ── Conversion ─────────────────────────────────────────────────────────

    def _start_conversion(self):
        if not self._pdf_path:
            messagebox.showwarning("No File", "Please select a PDF file first.")
            return
        if not Path(self._pdf_path).is_file():
            messagebox.showerror("Not Found", "Selected PDF no longer exists.")
            return

        self._convert_btn.config(state=tk.DISABLED)
        self._play_btn.config(state=tk.DISABLED)
        self._stop_btn.config(state=tk.DISABLED)
        self._save_btn.config(state=tk.DISABLED)
        self._prog_var.set(0)
        threading.Thread(target=self._run_conversion, daemon=True).start()

    def _run_conversion(self):
        def ui(fn): self.after(0, fn)

        try:
            ui(lambda: self._conv_status.config(text="Extracting PDF text…"))
            ui(lambda: self._prog_var.set(15))
            text = extract_text(self._pdf_path)

            ui(lambda: self._conv_status.config(text="Initialising TTS engine…"))
            ui(lambda: self._prog_var.set(35))

            # grab current settings from main thread vars
            vname = self._voice_var.get()
            speed = self._speed_var.get()
            voice_id = next(
                (v.id for v in self._voices if v.name == vname), None)

            ui(lambda: self._conv_status.config(
                text="Generating audio… (may take a moment)"))
            ui(lambda: self._prog_var.set(55))

            out_name = (self._outname_var.get().strip() or "audiobook"
                        ).replace(" ", "_")
            out_path = self.output_dir / f"{out_name}.wav"

            convert_to_audio(text, out_path, voice_id=voice_id, speed_wpm=speed)

            size_kb = out_path.stat().st_size // 1024

            # Save to DB if logged in
            if self._user and self._user.get("user_id"):
                db.add_audio_file(
                    user_id   = self._user["user_id"],
                    name      = out_name,
                    path      = str(out_path),
                    source_pdf= self._pdf_path or "",
                    voice     = vname,
                    speed     = speed,
                    size_kb   = size_kb,
                )

            self._current_audio = str(out_path)

            ui(lambda: self._prog_var.set(100))
            ui(lambda: self._conv_status.config(text="✓ Done!"))
            ui(self._on_done)

        except (PDFReadError, TTSError) as exc:
            err = str(exc)
            ui(lambda: messagebox.showerror("Conversion Error", err))
            ui(lambda: self._conv_status.config(text="Failed."))
            ui(lambda: self._prog_var.set(0))
            ui(lambda: self._convert_btn.config(state=tk.NORMAL))
        except Exception as exc:
            err = str(exc)
            ui(lambda: messagebox.showerror("Unexpected Error", err))
            ui(lambda: self._conv_status.config(text="Failed."))
            ui(lambda: self._prog_var.set(0))
            ui(lambda: self._convert_btn.config(state=tk.NORMAL))

    def _on_done(self):
        self._convert_btn.config(state=tk.NORMAL)
        self._play_btn.config(state=tk.NORMAL)
        self._stop_btn.config(state=tk.NORMAL)
        self._save_btn.config(state=tk.NORMAL)
        self._np_label.config(
            text=f"Ready: {Path(self._current_audio).name}")
        self.on_library_change()
        messagebox.showinfo("Success",
                            f"Audiobook created!\n\n{self._current_audio}")

    # ── Playback ───────────────────────────────────────────────────────────

    def _play(self, path: str | None = None):
        target = path or self._current_audio
        if not target or not os.path.exists(target):
            messagebox.showerror("Not Found", "Audio file not found.")
            return
        if not self._pygame_ok:
            messagebox.showwarning("Playback",
                                   "pygame is not installed.\n"
                                   "Run: pip install pygame")
            return
        try:
            self._pygame.mixer.music.load(target)
            self._pygame.mixer.music.play()
            self._is_playing = True
            self._np_label.config(
                text=f"▶  {Path(target).stem}", fg=S.SUCCESS)
            self._play_btn.config(text="⏸  Pause",
                                  command=self._pause, bg=S.WARNING)
        except Exception as e:
            messagebox.showerror("Playback Error", str(e))

    def _pause(self):
        if self._pygame_ok:
            self._pygame.mixer.music.pause()
        self._is_playing = False
        self._play_btn.config(text="▶  Resume",
                              command=self._resume, bg=S.SUCCESS)
        self._np_label.config(fg=S.SUBTEXT)

    def _resume(self):
        if self._pygame_ok:
            self._pygame.mixer.music.unpause()
        self._is_playing = True
        self._play_btn.config(text="⏸  Pause",
                              command=self._pause, bg=S.WARNING)
        self._np_label.config(fg=S.SUCCESS)

    def _stop(self):
        if self._pygame_ok:
            self._pygame.mixer.music.stop()
        self._is_playing = False
        self._play_btn.config(text="▶  Play",
                              command=self._play, bg=S.SUCCESS)
        self._np_label.config(text="", fg=S.SUBTEXT)

    def _tick(self):
        """Poll pygame every 500 ms so we detect when a track finishes."""
        if self._pygame_ok and self._is_playing:
            if not self._pygame.mixer.music.get_busy():
                self._is_playing = False
                self._play_btn.config(text="▶  Play",
                                      command=self._play, bg=S.SUCCESS)
                self._np_label.config(text="", fg=S.SUBTEXT)
        self.after(500, self._tick)

    # ── Save As ────────────────────────────────────────────────────────────

    def save_audio_as(self, src: str | None = None):
        path = src or self._current_audio
        if not path:
            return
        dest = filedialog.asksaveasfilename(
            title="Save audiobook",
            defaultextension=".wav",
            filetypes=[("WAV audio", "*.wav"), ("All files", "*.*")],
            initialfile=Path(path).name)
        if dest:
            shutil.copy2(path, dest)
            messagebox.showinfo("Saved", f"Audiobook saved to:\n{dest}")

    def _save_as(self):
        self.save_audio_as()

    # ── Persist Settings ───────────────────────────────────────────────────

    def _save_settings(self):
        if not self._user or not self._user.get("user_id"):
            messagebox.showinfo("Not logged in",
                                "Log in to save settings to your profile.")
            return
        db.save_settings(
            user_id=self._user["user_id"],
            voice=self._voice_var.get(),
            speed=self._speed_var.get())
        messagebox.showinfo("Saved", "Default voice and speed saved!")
