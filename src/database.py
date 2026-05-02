"""
database.py  –  PDF to Audiobook · Data Layer
Handles all SQLite persistence:  users, audio_files, settings
"""

import sqlite3
import hashlib
import os
from pathlib import Path

DB_PATH = Path.home() / ".pdf_audiobook.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist yet."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                username  TEXT    NOT NULL UNIQUE,
                password  TEXT    NOT NULL,          -- SHA-256 hex digest
                email     TEXT,
                created   TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS audio_files (
                file_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(user_id),
                name       TEXT    NOT NULL,
                path       TEXT    NOT NULL,
                source_pdf TEXT,
                voice      TEXT,
                speed      INTEGER,
                size_kb    INTEGER,
                duration   TEXT,
                created    TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS settings (
                setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL UNIQUE REFERENCES users(user_id),
                default_voice TEXT DEFAULT '',
                default_speed INTEGER DEFAULT 150,
                theme         TEXT DEFAULT 'dark'
            );
        """)


# ── Auth ───────────────────────────────────────────────────────────────────

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username: str, password: str, email: str = "") -> dict | None:
    """
    Create a new user.  Returns the user row dict or None if username taken.
    """
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                (username.strip(), _hash(password), email.strip())
            )
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username.strip(),)
            ).fetchone()
            _init_settings(conn, row["user_id"])
            return dict(row)
    except sqlite3.IntegrityError:
        return None


def login_user(username: str, password: str) -> dict | None:
    """Returns user row dict on success, None on failure."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username.strip(), _hash(password))
        ).fetchone()
        return dict(row) if row else None


# ── Settings ───────────────────────────────────────────────────────────────

def _init_settings(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO settings (user_id) VALUES (?)", (user_id,)
    )


def get_settings(user_id: int) -> dict:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM settings WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row:
            return dict(row)
        # auto-create if missing
        conn.execute("INSERT INTO settings (user_id) VALUES (?)", (user_id,))
        return {"user_id": user_id, "default_voice": "",
                "default_speed": 150, "theme": "dark"}


def save_settings(user_id: int, voice: str, speed: int, theme: str = "dark") -> None:
    with _connect() as conn:
        conn.execute("""
            INSERT INTO settings (user_id, default_voice, default_speed, theme)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                default_voice = excluded.default_voice,
                default_speed = excluded.default_speed,
                theme         = excluded.theme
        """, (user_id, voice, speed, theme))


# ── Library ────────────────────────────────────────────────────────────────

def add_audio_file(user_id: int, name: str, path: str, source_pdf: str,
                   voice: str, speed: int, size_kb: int) -> dict:
    with _connect() as conn:
        conn.execute("""
            INSERT INTO audio_files
                (user_id, name, path, source_pdf, voice, speed, size_kb)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, path, source_pdf, voice, speed, size_kb))
        row = conn.execute(
            "SELECT * FROM audio_files WHERE path = ?", (path,)
        ).fetchone()
        return dict(row)


def get_library(user_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM audio_files WHERE user_id = ? ORDER BY created DESC",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def delete_audio_entry(file_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM audio_files WHERE file_id = ?", (file_id,))


def update_user_email(user_id: int, email: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE users SET email = ? WHERE user_id = ?",
                     (email.strip(), user_id))


def change_password(user_id: int, old_pw: str, new_pw: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE user_id = ? AND password = ?",
            (user_id, _hash(old_pw))
        ).fetchone()
        if not row:
            return False
        conn.execute("UPDATE users SET password = ? WHERE user_id = ?",
                     (_hash(new_pw), user_id))
        return True
