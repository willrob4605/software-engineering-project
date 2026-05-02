"""
app.py  –  PDF to Audiobook Converter
Entry point.  Wires together the login screen and main notebook.

Requirements:
    pip install pypdf pyttsx3 pygame
    Linux also needs:  sudo apt install espeak-ng
"""

import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database as db
import styles   as S
from screens.login         import LoginScreen
from screens.converter_tab import ConverterTab
from screens.library_tab   import LibraryTab
from screens.settings_tab  import SettingsTab

# Base folder — each user gets their own subdirectory inside
AUDIOBOOKS_ROOT = Path.home() / "Audiobooks"


class PDFAudiobookApp:
    """Root application controller."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("📖 PDF to Audiobook Converter")
        self.root.geometry("880x700")
        self.root.minsize(720, 560)
        self.root.configure(bg=S.BG)

        AUDIOBOOKS_ROOT.mkdir(exist_ok=True)
        db.init_db()

        self._user: dict | None = None
        self._login_frame: LoginScreen | None = None
        self._main_frame:  tk.Frame | None    = None

        self._show_login()

    # ── Login flow ─────────────────────────────────────────────────────────

    def _show_login(self):
        if self._main_frame:
            self._main_frame.pack_forget()
        self._login_frame = LoginScreen(self.root, on_login=self._on_login)
        self._login_frame.pack(fill=tk.BOTH, expand=True)

    def _on_login(self, user: dict):
        self._user = user
        self.root.title(f"📖 PDF to Audiobook  —  {user.get('username', 'Guest')}")
        if self._login_frame:
            self._login_frame.pack_forget()
        self._build_main()
        self._main_frame.pack(fill=tk.BOTH, expand=True)

    # ── Per-user output directory ──────────────────────────────────────────

    def _user_output_dir(self) -> Path:
        """
        Each user gets Audiobooks/<username>/ so libraries never mix.
        Guest files go into Audiobooks/Guest/.
        """
        username = (self._user or {}).get("username", "Guest")
        safe = "".join(c for c in username if c.isalnum() or c in "-_").strip() or "user"
        folder = AUDIOBOOKS_ROOT / safe
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    # ── Main notebook ──────────────────────────────────────────────────────

    def _build_main(self):
        if self._main_frame:
            self._main_frame.destroy()

        self._main_frame = tk.Frame(self.root, bg=S.BG)
        output_dir = self._user_output_dir()

        # Header bar
        hdr = tk.Frame(self._main_frame, bg=S.PANEL, pady=10)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="📖  PDF  →  Audiobook",
                 bg=S.PANEL, fg=S.TEXT, font=S.FONT_TITLE).pack(side=tk.LEFT, padx=16)
        uname = (self._user or {}).get("username", "Guest")
        tk.Label(hdr, text=f"👤 {uname}",
                 bg=S.PANEL, fg=S.SUBTEXT, font=S.FONT_SMALL).pack(side=tk.RIGHT, padx=16)

        # Notebook
        S.apply_notebook_style()
        nb_frame = tk.Frame(self._main_frame, bg=S.BG)
        nb_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(8, 0))
        self._nb = ttk.Notebook(nb_frame, style="Custom.TNotebook")
        self._nb.pack(fill=tk.BOTH, expand=True)

        tab_conv = tk.Frame(self._nb, bg=S.BG)
        tab_lib  = tk.Frame(self._nb, bg=S.BG)
        tab_set  = tk.Frame(self._nb, bg=S.BG)
        self._nb.add(tab_conv, text="  ⚙  Converter  ")
        self._nb.add(tab_lib,  text="  📚  Library   ")
        self._nb.add(tab_set,  text="  ⚙️  Settings  ")

        self._conv_tab = ConverterTab(
            tab_conv, output_dir=output_dir,
            on_library_change=self._refresh_library)
        self._conv_tab.pack(fill=tk.BOTH, expand=True)

        self._lib_tab = LibraryTab(
            tab_lib, output_dir=output_dir,
            on_play=self._play_from_library,
            on_save_as=self._conv_tab.save_audio_as)
        self._lib_tab.pack(fill=tk.BOTH, expand=True)

        self._set_tab = SettingsTab(
            tab_set, output_dir=output_dir,
            on_logout=self._logout,
            on_delete_account=self._delete_account)   # ← new callback
        self._set_tab.pack(fill=tk.BOTH, expand=True)

        # Status bar
        self._status_var = tk.StringVar(value="  Ready.")
        tk.Label(self._main_frame, textvariable=self._status_var,
                 bg=S.ACCENT, fg=S.SUBTEXT, font=S.FONT_SMALL,
                 anchor="w", padx=12, pady=4).pack(fill=tk.X, side=tk.BOTTOM)

        if self._user:
            self._conv_tab.set_user(self._user)
            self._lib_tab.refresh(self._user)
            self._set_tab.load(self._user)

        self._nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

    # ── Tab change ─────────────────────────────────────────────────────────

    def _on_tab_change(self, _event=None):
        if self._nb.index(self._nb.select()) == 1:
            self._lib_tab.refresh(self._user)

    # ── Cross-tab helpers ──────────────────────────────────────────────────

    def _play_from_library(self, path: str):
        self._nb.select(0)
        self._conv_tab.load_audio(path)
        self._conv_tab._play(path)

    def _refresh_library(self):
        self._lib_tab.refresh(self._user)

    # ── Logout ─────────────────────────────────────────────────────────────

    def _logout(self):
        self._user = None
        if self._main_frame:
            self._main_frame.destroy()
            self._main_frame = None
        self.root.title("📖 PDF to Audiobook Converter")
        self._show_login()

    # ── Delete account ─────────────────────────────────────────────────────

    def _delete_account(self):
        """SettingsTab confirms deletion then calls this to return to login."""
        self._user = None
        if self._main_frame:
            self._main_frame.destroy()
            self._main_frame = None
        self.root.title("📖 PDF to Audiobook Converter")
        self._show_login()


# ── Entry point ────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.25)
    except Exception:
        pass
    PDFAudiobookApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()