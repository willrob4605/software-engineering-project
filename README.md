# PDF to Audiobook Converter
**Group Members:** Will Roberts

A desktop application that converts PDF files into spoken-word audiobooks,
with voice selection, speed control, a personal library, and user accounts.

---

## Project Structure

```
pdf_audiobook/
├── app.py                   ← Entry point (run this)
├── database.py              ← SQLite layer  (users, library, settings)
├── pdf_reader.py            ← PDF text extraction (pypdf)
├── converter.py             ← Text-to-speech engine (pyttsx3)
├── styles.py                ← Colours, fonts, widget factories
├── requirements.txt
├── screens/
│   ├── login.py             ← Login / Register screen
│   ├── converter_tab.py     ← ⚙ Converter tab
│   ├── library_tab.py       ← 📚 Library tab
│   └── settings_tab.py      ← ⚙️ Settings tab
└── tests/
    └── test_app.py          ← Unit tests (pytest or unittest)
```

---

## Setup

### 1 · Python
Requires Python 3.10 or later.

### 2 · Install dependencies

```bash
pip install -r requirements.txt
```

### 3 · Linux only – install the TTS voice engine

```bash
sudo apt install espeak-ng
```

macOS and Windows include a TTS engine by default, so this step is not needed
on those platforms.

---

## Running the app

```bash
python app.py
```

The first time you launch you will be asked to log in or register.
You can also choose **Continue as Guest** to skip account creation
(guest sessions are not saved to the database).

---

## Running the tests

```bash
# From the project root:
python -m pytest tests/ -v

# Or without pytest:
python tests/test_app.py
```

---

## Features

| Feature | Status |
|---|---|
| PDF text extraction | ✅ |
| Text-to-speech conversion (WAV) | ✅ |
| Voice selection | ✅ |
| Adjustable speech speed (60–280 wpm) | ✅ |
| Playback (play / pause / resume / stop) | ✅ |
| Save audio as WAV | ✅ |
| Personal library (per-user, SQLite) | ✅ |
| User login & registration | ✅ |
| Password change | ✅ |
| Guest mode (no account needed) | ✅ |
| Settings saved per user | ✅ |
| Library search | ✅ |

---

## Architecture

The application uses a **Layered Architecture**:

```
┌──────────────────────────────────┐
│         UI Layer (tkinter)       │  screens/ + styles.py
├──────────────────────────────────┤
│       Application Layer          │  app.py, converter.py, pdf_reader.py
├──────────────────────────────────┤
│       Data Layer                 │  database.py  (SQLite)
└──────────────────────────────────┘
```

Each layer communicates only with the layer directly below it, keeping
modules independent and easy to modify without breaking other parts.

---

## Known Limitations

- Scanned / image-only PDFs cannot be converted (OCR not included).
- Playback requires `pygame`; if unavailable the audio file is still
  generated and can be opened in any media player.
- Voice availability depends on the operating system's installed TTS voices.
