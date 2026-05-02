"""
tests/test_app.py  –  PDF to Audiobook · Unit Tests
Covers TC-UNIT-01 through TC-UNIT-04 as defined in the SRS assignment.

Run with:
    python -m pytest tests/ -v
    -- or --
    python tests/test_app.py
"""

import os
import sys
import pathlib
import tempfile
import unittest

# ── Make sure project root is importable ────────────────────────────────────
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pdf_reader import extract_text, PDFReadError


# ── Helpers to create minimal test PDFs ─────────────────────────────────────

def _make_text_pdf(path: pathlib.Path, text: str = "Hello, this is test text."):
    """
    Write a minimal valid PDF with one text page.
    Uses only the standard library (no reportlab / fpdf dependency).
    This is a hand-crafted minimal PDF structure.
    """
    import struct, zlib

    # Very small hand-built PDF
    content_stream = (
        f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
    ).encode()

    pdf = b"%PDF-1.4\n"

    # object 1: catalog
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    # object 2: pages
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    # object 3: page
    obj3 = (b"3 0 obj\n<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] /Contents 4 0 R "
            b"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 "
            b"/BaseFont /Helvetica >> >> >> >>\nendobj\n")
    # object 4: content stream
    cs = content_stream
    obj4 = (f"4 0 obj\n<< /Length {len(cs)} >>\nstream\n").encode() \
           + cs + b"\nendstream\nendobj\n"

    offsets = []
    buf = pdf
    for obj in (obj1, obj2, obj3, obj4):
        offsets.append(len(buf))
        buf += obj

    xref_offset = len(buf)
    xref = f"xref\n0 5\n0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n"
    buf += xref.encode()

    trailer = (f"trailer\n<< /Size 5 /Root 1 0 R >>\n"
               f"startxref\n{xref_offset}\n%%EOF\n")
    buf += trailer.encode()

    path.write_bytes(buf)


def _make_image_only_pdf(path: pathlib.Path):
    """
    Write a minimal valid PDF with NO text (just an empty page).
    extract_text() should return an empty string for this.
    """
    pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
190
%%EOF
"""
    path.write_bytes(pdf)


# ── Test cases ───────────────────────────────────────────────────────────────

class TestExtractText(unittest.TestCase):
    """TC-UNIT-01 & TC-UNIT-02  –  pdf_reader.extract_text()"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp  = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_TC_UNIT_01_valid_pdf_returns_non_empty_string(self):
        """TC-UNIT-01: A readable PDF should produce non-empty text."""
        pdf = self.tmp / "readable.pdf"
        _make_text_pdf(pdf, "This is readable text for unit testing.")

        result = extract_text(str(pdf))

        self.assertIsInstance(result, str,
                              "extract_text() must return a string")
        self.assertGreater(len(result.strip()), 0,
                           "Should return non-empty text for a text PDF")

    def test_TC_UNIT_02_image_only_pdf_raises_PDFReadError(self):
        """TC-UNIT-02: A scanned/image-only PDF should raise PDFReadError."""
        pdf = self.tmp / "scanned.pdf"
        _make_image_only_pdf(pdf)

        with self.assertRaises(PDFReadError,
                               msg="Image-only PDF should raise PDFReadError"):
            extract_text(str(pdf))

    def test_missing_file_raises_PDFReadError(self):
        """Requesting a non-existent file should raise PDFReadError."""
        with self.assertRaises(PDFReadError):
            extract_text("/tmp/does_not_exist_xyz.pdf")

    def test_page_range_respected(self):
        """Only the requested pages should be extracted."""
        pdf = self.tmp / "multipage.pdf"
        _make_text_pdf(pdf, "Page one content here")
        # single-page PDF; end_page=0 should still return content
        result = extract_text(str(pdf), start_page=0, end_page=0)
        self.assertGreater(len(result.strip()), 0)


class TestLoadLibrary(unittest.TestCase):
    """TC-UNIT-03 & TC-UNIT-04  –  database.get_library() edge cases"""

    def setUp(self):
        import database
        # Redirect the DB to a temp file so we don't pollute the real DB
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_db = database.DB_PATH
        database.DB_PATH = pathlib.Path(self._tmp.name) / "test.db"
        database.init_db()

    def tearDown(self):
        import database
        database.DB_PATH = self._orig_db
        self._tmp.cleanup()

    def test_TC_UNIT_03_missing_user_returns_empty_list(self):
        """TC-UNIT-03: get_library() for a user with no files → empty list."""
        import database
        user = database.register_user("testuser_03", "pass1234")
        self.assertIsNotNone(user)
        result = database.get_library(user["user_id"])
        self.assertEqual(result, [],
                         "New user should have an empty library")

    def test_TC_UNIT_04_add_and_retrieve_entry(self):
        """TC-UNIT-04: add_audio_file() then get_library() returns that entry."""
        import database
        user = database.register_user("testuser_04", "pass5678")
        database.add_audio_file(
            user_id   = user["user_id"],
            name      = "test_book",
            path      = "/tmp/test_book.wav",
            source_pdf= "/tmp/test.pdf",
            voice     = "English (US)",
            speed     = 150,
            size_kb   = 1024,
        )
        lib = database.get_library(user["user_id"])
        self.assertEqual(len(lib), 1)
        self.assertEqual(lib[0]["name"], "test_book")

    def test_delete_removes_entry(self):
        """delete_audio_entry() should remove the record from the DB."""
        import database
        user = database.register_user("testuser_del", "pass9999")
        entry = database.add_audio_file(
            user_id=user["user_id"], name="del_test",
            path="/tmp/del.wav", source_pdf="",
            voice="", speed=150, size_kb=0)
        database.delete_audio_entry(entry["file_id"])
        lib = database.get_library(user["user_id"])
        self.assertEqual(lib, [])


class TestAuthFlow(unittest.TestCase):
    """Auth: register, login, duplicate username, wrong password."""

    def setUp(self):
        import database
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_db = database.DB_PATH
        database.DB_PATH = pathlib.Path(self._tmp.name) / "auth_test.db"
        database.init_db()

    def tearDown(self):
        import database
        database.DB_PATH = self._orig_db
        self._tmp.cleanup()

    def test_register_and_login(self):
        import database
        user = database.register_user("alice", "secret123")
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "alice")

        logged = database.login_user("alice", "secret123")
        self.assertIsNotNone(logged)
        self.assertEqual(logged["user_id"], user["user_id"])

    def test_duplicate_username_returns_none(self):
        import database
        database.register_user("bob", "pw1")
        result = database.register_user("bob", "pw2")
        self.assertIsNone(result, "Duplicate username should return None")

    def test_wrong_password_returns_none(self):
        import database
        database.register_user("carol", "correct")
        result = database.login_user("carol", "wrong")
        self.assertIsNone(result)

    def test_change_password(self):
        import database
        user = database.register_user("dave", "oldpw")
        ok = database.change_password(user["user_id"], "oldpw", "newpw")
        self.assertTrue(ok)
        self.assertIsNotNone(database.login_user("dave", "newpw"))
        self.assertIsNone(database.login_user("dave", "oldpw"))

    def test_change_password_wrong_old_fails(self):
        import database
        user = database.register_user("eve", "mypw")
        ok = database.change_password(user["user_id"], "wrongold", "newpw")
        self.assertFalse(ok)


class TestConverterModule(unittest.TestCase):
    """converter.py: list_voices() and argument validation."""

    def test_list_voices_returns_list(self):
        from converter import list_voices
        voices = list_voices()
        self.assertIsInstance(voices, list)

    def test_convert_empty_text_raises_TTSError(self):
        from converter import convert_to_audio, TTSError
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td) / "out.wav"
            with self.assertRaises(TTSError):
                convert_to_audio("   ", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
