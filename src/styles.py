"""
styles.py  –  PDF to Audiobook · UI Theme
Centralized colour palette, fonts, and helper factory functions.
"""

import tkinter as tk
from tkinter import ttk

# ── Colour palette ──────────────────────────────────────────────────────────
BG        = "#1a1a2e"
PANEL     = "#16213e"
ACCENT    = "#0f3460"
HIGHLIGHT = "#e94560"
TEXT      = "#eaeaea"
SUBTEXT   = "#9a9ab0"
SUCCESS   = "#4caf8a"
WARNING   = "#f0a500"
ERROR_CLR = "#e94560"

# ── Fonts ────────────────────────────────────────────────────────────────────
FONT_TITLE = ("Georgia",    20, "bold")
FONT_HEAD  = ("Georgia",    13, "bold")
FONT_BODY  = ("Courier New", 11)
FONT_SMALL = ("Courier New",  9)
FONT_BTN   = ("Courier New", 10, "bold")


def apply_notebook_style() -> None:
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Custom.TNotebook",
                    background=BG, borderwidth=0)
    style.configure("Custom.TNotebook.Tab",
                    background=PANEL, foreground=SUBTEXT,
                    padding=[14, 6], font=FONT_BTN)
    style.map("Custom.TNotebook.Tab",
              background=[("selected", ACCENT)],
              foreground=[("selected", TEXT)])
    style.configure("red.Horizontal.TProgressbar",
                    troughcolor=ACCENT, background=HIGHLIGHT)


def btn(parent: tk.Widget, text: str, command,
        color: str = HIGHLIGHT, **kw) -> tk.Button:
    """Factory: create a styled flat button with hover effect."""
    b = tk.Button(parent, text=text, command=command,
                  bg=color, fg=TEXT, activebackground=ACCENT,
                  activeforeground=TEXT, relief="flat", bd=0,
                  padx=14, pady=6, font=FONT_BTN, cursor="hand2", **kw)
    b.bind("<Enter>", lambda e, c=color: b.config(bg=ACCENT))
    b.bind("<Leave>", lambda e, c=color: b.config(bg=c))
    return b


def section_header(parent: tk.Widget, title: str) -> tk.Frame:
    """Labelled horizontal rule used as a section divider."""
    f = tk.Frame(parent, bg=BG)
    tk.Label(f, text=title, bg=BG, fg=HIGHLIGHT,
             font=FONT_HEAD).pack(side=tk.LEFT, padx=(8, 0))
    tk.Frame(f, bg=ACCENT, height=1).pack(
        side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=2)
    return f


def label(parent: tk.Widget, text: str, fg: str = TEXT,
          font=None, **kw) -> tk.Label:
    return tk.Label(parent, text=text, bg=BG, fg=fg,
                    font=font or FONT_BODY, **kw)


def entry(parent: tk.Widget, textvariable: tk.StringVar,
          show: str = "", width: int = 30) -> tk.Entry:
    return tk.Entry(parent, textvariable=textvariable,
                    bg=ACCENT, fg=TEXT, insertbackground=TEXT,
                    relief="flat", font=FONT_BODY,
                    show=show, width=width)


def panel_frame(parent: tk.Widget, **kw) -> tk.Frame:
    return tk.Frame(parent, bg=PANEL, **kw)


def error_label(parent: tk.Widget) -> tk.Label:
    """An initially-empty label used to show inline error messages."""
    return tk.Label(parent, text="", bg=BG, fg=ERROR_CLR,
                    font=FONT_SMALL, wraplength=340)
