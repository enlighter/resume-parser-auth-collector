from __future__ import annotations

import mimetypes
import re
from typing import Optional

try:
    import magic as _magic  # python-magic
except Exception:
    _magic = None

# --- PAN & Aadhaar validators ---

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
AADHAAR_RE = re.compile(r"^\d{12}$")

# Verhoeff checksum tables
_d = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,2,3,4,0,6,7,8,9,5],
    [2,3,4,0,1,7,8,9,5,6],
    [3,4,0,1,2,8,9,5,6,7],
    [4,0,1,2,3,9,5,6,7,8],
    [5,9,8,7,6,0,4,3,2,1],
    [6,5,9,8,7,1,0,4,3,2],
    [7,6,5,9,8,2,1,0,4,3],
    [8,7,6,5,9,3,2,1,0,4],
    [9,8,7,6,5,4,3,2,1,0],
]
_p = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,5,7,6,2,8,3,0,9,4],
    [5,8,0,3,7,9,6,1,4,2],
    [8,9,1,6,0,4,3,5,2,7],
    [9,4,5,3,1,2,6,8,7,0],
    [4,2,8,6,5,7,3,9,0,1],
    [2,7,9,3,8,0,6,4,1,5],
    [7,0,4,6,9,1,3,2,5,8],
]
_inv = [0,4,3,2,1,5,6,7,8,9]


def verhoeff_valid(number_str: str) -> bool:
    """Return True if string of digits passes Verhoeff check (used for Aadhaar)."""
    c = 0
    # process from right to left
    for i, ch in enumerate(reversed(number_str)):
        if not ch.isdigit():
            return False
        c = _d[c][_p[(i + 1) % 8][int(ch)]]
    return c == 0


def is_valid_pan(value: str) -> bool:
    return bool(PAN_RE.match(value or ""))


def is_valid_aadhaar(value: str) -> bool:
    s = (value or "").strip().replace(" ", "")
    return bool(AADHAAR_RE.match(s)) and verhoeff_valid(s)


# --- MIME sniffing ---

ALLOWED_DOC_MIMES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}

def sniff_mime(first_bytes: bytes, filename: Optional[str] = None) -> str:
    if _magic is not None:
        try:
            m = _magic.Magic(mime=True)
            return m.from_buffer(first_bytes) or ""
        except Exception:
            pass
    if filename:
        guess, _ = mimetypes.guess_type(filename)
        if guess:
            return guess
    return ""


def is_allowed_mime(mime: str) -> bool:
    return mime in ALLOWED_DOC_MIMES
