import warnings
warnings.filterwarnings("ignore")

import sys
import os

import subprocess
import ctypes

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)

def exe_dir():
    if hasattr(sys, '_MEIPASS'):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))

import pytesseract
pytesseract.pytesseract.tesseract_cmd = resource_path("tesseract/tesseract.exe")
os.environ["TESSDATA_PREFIX"] = resource_path("tesseract/tessdata")

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
import fitz
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
import re
import json
import qrcode
from datetime import datetime
import threading
import tempfile
import urllib.request
import unicodedata
import concurrent.futures
import hashlib
import hmac
import uuid
import platform
import traceback



# ============================================================
#  LICENSE
# ============================================================
_SECRET       = b"abha-studio-secret-v52-2024"
_DEMO_KEY = "DEMO"
program_data  = os.environ.get('PROGRAMDATA', os.path.expanduser("~"))
app_folder    = os.path.join(program_data, "ABHA_Studio")
_LICENSE_FILE = os.path.join(app_folder, "license.key")
_RUNTIME_DEMO_MODE = False


def _get_machine_code() -> str:
    parts = []
    try: parts.append(str(uuid.getnode()))
    except Exception: pass
    try: parts.append(platform.node())
    except Exception: pass
    try: parts.append(platform.processor())
    except Exception: pass
    raw    = "|".join(parts) or "fallback"
    digest = hashlib.sha256(raw.encode()).hexdigest().upper()
    h      = digest[:16]
    return f"{h[0:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"


def _expected_key(machine_code: str) -> str:
    digest = hmac.new(_SECRET, machine_code.strip().upper().encode(),
                      hashlib.sha256).hexdigest().upper()
    h = digest[:16]
    return f"{h[0:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"


def _is_demo_mode() -> bool:
    if _RUNTIME_DEMO_MODE:
        return True
    if not os.path.isfile(_LICENSE_FILE):
        return False
    try:
        with open(_LICENSE_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        try:
            data = json.loads(content)
            saved_key = data.get("key", "").strip().upper()
        except (json.JSONDecodeError, AttributeError):
            saved_key = content.upper()
        return saved_key == _DEMO_KEY
    except Exception:
        return False


def _is_activated() -> bool:
    if _RUNTIME_DEMO_MODE:
        return True

    if not os.path.isfile(_LICENSE_FILE):
        return False
    try:
        with open(_LICENSE_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
        try:
            data = json.loads(content)
            saved_key = data.get("key", "").strip().upper()
        except (json.JSONDecodeError, AttributeError):
            saved_key = content.upper()
        if saved_key == _DEMO_KEY:
            return True
        return saved_key == _expected_key(_get_machine_code())
    except Exception:
        return False


def _save_license(key: str):
    normalized = key.strip().upper()
    if normalized == _DEMO_KEY:
        return
    os.makedirs(os.path.dirname(_LICENSE_FILE), exist_ok=True)
    data = {"key": normalized}
    with open(_LICENSE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
#  TAMIL NAME EXTRACTOR
# ============================================================
class TamilNameExtractor:
    """Uses robust existing extraction functions for better accuracy."""
    
    @staticmethod
    def extract_from_text(text: str) -> str:
        if not text or not text.strip():
            return ""
        
        # Use the robust _extract_best_tamil_name_from_text function
        result = _extract_best_tamil_name_from_text(text, "")
        if result:
            return result
        
        # Fallback to _find_best_tamil_candidate
        fallback = _find_best_tamil_candidate(text)
        if fallback:
            return fallback
        
        # Final fallback: extract longest Tamil sequence
        return _extract_longest_tamil_sequence(text, min_chars=3)


# ============================================================
#  FONT SETUP
# ============================================================
TAMIL_FONT_FILENAME    = "NotoSansTamil-Bold.ttf"
MALAYALAM_FONT_FILENAME = "NotoSansMalayalam-Bold.ttf"
ENGLISH_FONT_FILENAME  = "Arial-Bold.ttf"
TAMIL_FONT_URL = (
    "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/"
    "NotoSansTamil/NotoSansTamil-Bold.ttf"
)
MALAYALAM_FONT_URL = (
    "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/"
    "NotoSansMalayalam/NotoSansMalayalam-Bold.ttf"
)

HINDI_FONT_FILENAME = "NotoSansDevanagari-Bold.ttf"
HINDI_FONT_URL = (
    "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/"
    "NotoSansDevanagari/NotoSansDevanagari-Bold.ttf"
)

def _font_candidates(filename):
    candidates = [resource_path(filename), os.path.join(exe_dir(), filename)]
    if filename == TAMIL_FONT_FILENAME:
        candidates += [
            r"C:\Windows\Fonts\NotoSansTamil-Bold.ttf",
            r"C:\Windows\Fonts\Nirmala.ttf",
            r"C:\Windows\Fonts\NirmalaB.ttf",
            r"C:\Windows\Fonts\latha.ttf",
            r"C:\Windows\Fonts\vijaya.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansTamil-Bold.ttf",
            "/usr/share/fonts/truetype/lohit-tamil/Lohit-Tamil.ttf",
        ]
    elif filename == MALAYALAM_FONT_FILENAME:
        candidates += [
            r"C:\Windows\Fonts\NotoSansMalayalam-Bold.ttf",
            r"C:\Windows\Fonts\Nirmala.ttf",
            r"C:\Windows\Fonts\NirmalaB.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansMalayalam-Bold.ttf",
            "/usr/share/fonts/truetype/lohit-malayalam/Lohit-Malayalam.ttf",
        ]
    
    elif filename == HINDI_FONT_FILENAME:
        candidates += [
            r"C:\Windows\Fonts\NotoSansDevanagari-Bold.ttf",
            r"C:\Windows\Fonts\Nirmala.ttf",
            r"C:\Windows\Fonts\NirmalaB.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
        ]
        
    elif filename == ENGLISH_FONT_FILENAME:
        candidates += [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
            r"C:\Windows\Fonts\Georgia.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    return candidates

def _find_font(filename):
    for path in _font_candidates(filename):
        try:
            if path and os.path.isfile(path):
                return path
        except Exception:
            pass
    return None

def ensure_tamil_font():
    path = _find_font(TAMIL_FONT_FILENAME)
    if path: return path
    save_path = os.path.join(exe_dir(), TAMIL_FONT_FILENAME)
    try:
        urllib.request.urlretrieve(TAMIL_FONT_URL, save_path)
        if os.path.isfile(save_path): return save_path
    except Exception as e:
        print(f"[WARN] Could not download Tamil font: {e}")
    return None

def ensure_malayalam_font():
    path = _find_font(MALAYALAM_FONT_FILENAME)
    if path: return path
    save_path = os.path.join(exe_dir(), MALAYALAM_FONT_FILENAME)
    try:
        urllib.request.urlretrieve(MALAYALAM_FONT_URL, save_path)
        if os.path.isfile(save_path): return save_path
    except Exception as e:
        print(f"[WARN] Could not download Malayalam font: {e}")
    return None
def ensure_hindi_font():
    path = _find_font(HINDI_FONT_FILENAME)
    if path: return path
    save_path = os.path.join(exe_dir(), HINDI_FONT_FILENAME)
    try:
        urllib.request.urlretrieve(HINDI_FONT_URL, save_path)
        if os.path.isfile(save_path): return save_path
    except Exception as e:
        print(f"[WARN] Could not download Hindi font: {e}")
    return None

_TAMIL_FONT_PATH    = ensure_tamil_font()
_MALAYALAM_FONT_PATH = ensure_malayalam_font()
_HINDI_FONT_PATH    = ensure_hindi_font()
_ENGLISH_FONT_PATH  = _find_font(ENGLISH_FONT_FILENAME)
_font_cache         = {}

def load_tamil_font(size):
    key = ("tamil", size)
    if key in _font_cache: return _font_cache[key]
    for path in ([_TAMIL_FONT_PATH] if _TAMIL_FONT_PATH else []) + _font_candidates(TAMIL_FONT_FILENAME):
        if not path or not os.path.isfile(path): continue
        try:
            f = ImageFont.truetype(path, size)
            _font_cache[key] = f
            return f
        except Exception: pass
    f = ImageFont.load_default()
    _font_cache[key] = f
    return f
def load_malayalam_font(size):
    key = ("malayalam", size)
    if key in _font_cache: return _font_cache[key]
    for path in ([_MALAYALAM_FONT_PATH] if _MALAYALAM_FONT_PATH else []) + _font_candidates(MALAYALAM_FONT_FILENAME):
        if not path or not os.path.isfile(path): continue
        try:
            f = ImageFont.truetype(path, size)
            _font_cache[key] = f
            return f
        except Exception: pass
    f = ImageFont.load_default()
    _font_cache[key] = f
    return f

def load_english_font(size):
    key = ("english", size)
    if key in _font_cache: return _font_cache[key]
    for path in ([_ENGLISH_FONT_PATH] if _ENGLISH_FONT_PATH else []) + _font_candidates(ENGLISH_FONT_FILENAME):
        if not path or not os.path.isfile(path): continue
        try:
            f = ImageFont.truetype(path, size)
            _font_cache[key] = f
            return f
        except Exception: pass
    f = ImageFont.load_default()
    _font_cache[key] = f
    return f

def load_hindi_font(size):
    key = ("hindi", size)
    if key in _font_cache: return _font_cache[key]
    for path in ([_HINDI_FONT_PATH] if _HINDI_FONT_PATH else []) + _font_candidates(HINDI_FONT_FILENAME):
        if not path or not os.path.isfile(path): continue
        try:
            f = ImageFont.truetype(path, size)
            _font_cache[key] = f
            return f
        except Exception: pass
    f = ImageFont.load_default()
    _font_cache[key] = f
    return f

# ============================================================
#  RAQM CHECK
# ============================================================
def _check_raqm():
    try:
        import PIL.features
        if PIL.features.check_feature("raqm"):
            if _TAMIL_FONT_PATH:
                ImageFont.truetype(_TAMIL_FONT_PATH, 20,
                    layout_engine=ImageFont.Layout.RAQM)
            return True
    except Exception: pass
    return False

_RAQM_AVAILABLE = _check_raqm() if _TAMIL_FONT_PATH else False


# ============================================================
#  TAMIL RENDERER
# ============================================================
def _render_tamil_to_image(text, font_path, font_size, fill=(0, 0, 0)):
    text = unicodedata.normalize("NFC", text)
    loaded_font = None
    if font_path:
        try:
            loaded_font = ImageFont.truetype(font_path, font_size,
                                             layout_engine=ImageFont.Layout.RAQM)
        except Exception:
            try:
                loaded_font = ImageFont.truetype(font_path, font_size)
            except Exception:
                pass
    if loaded_font is None:
        loaded_font = ImageFont.load_default()
    tmp_img  = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    tmp_draw = ImageDraw.Draw(tmp_img)
    try:
        bbox = tmp_draw.textbbox((0, 0), text, font=loaded_font)
        w  = bbox[2] - bbox[0] + 4
        h  = bbox[3] - bbox[1] + 4
        ox = -bbox[0] + 2
        oy = -bbox[1] + 2
    except AttributeError:
        tw, th = tmp_draw.textsize(text, font=loaded_font)
        w, h   = tw + 4, th + 4
        ox, oy = 2, 2
    w, h = max(w, 1), max(h, 1)
    img  = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((ox, oy), text, font=loaded_font,
              fill=fill + (255,) if len(fill) == 3 else fill)
    return img

def draw_tamil(draw, xy, text, font, fill=(0, 0, 0), card_image=None, font_path=None):
    if not text: return
    text = unicodedata.normalize("NFC", text)
    # Use the explicitly passed font_path, fall back to Tamil font
    _path = font_path if font_path else _TAMIL_FONT_PATH
    if card_image is not None and _path:
        font_size = 28
        try: font_size = font.size
        except Exception: pass
        glyph_img = _render_tamil_to_image(text, _path, font_size, fill)
        card_image.paste(glyph_img, (int(xy[0]), int(xy[1])), glyph_img)
        return
    if _RAQM_AVAILABLE:
        draw.text(xy, text, font=font, fill=fill)
    else:
        draw.text(xy, text, font=font, fill=fill)

# ============================================================
#  THEME
# ============================================================
class Theme:
    DARK = dict(
        MODE="dark",
        BG_ROOT="#020D1F",
        BG_PANEL="#020D1F",
        BG_CARD="#031225",
        BG_INPUT="#031225",
        BG_HOVER="#0A2040",
        BORDER="#1565C0",
        BORDER2="#1976D2",
        BORDER_GOLD="#1565C0",
        ACCENT="#1976D2",
        ACCENT2="#1565C0",
        ACCENT_LIGHT="#42A5F5",
        ACCENT_DIM="#031225",
        SUCCESS="#1976D2",
        WARNING="#F59E0B",
        ERROR_COL="#F87171",
        INFO="#1976D2",
        TEXT_1="#E3F2FD",
        TEXT_2="#90CAF9",
        TEXT_3="#4A7FA5",
        TAG_BG="#031225",
        SCROLLBAR="#1976D2",
        NAV_BG="#020D1F",
        NAV_ACTIVE="#031225",
        DIVIDER="#1565C0",
        SHADOW="#00000066",
    )
    LIGHT = dict(DARK)
    _current = DARK

    @classmethod
    def get(cls, key):
        return cls._current.get(key, "#FF00FF")

    @classmethod
    def apply_dark(cls):
        cls._current = dict(cls.DARK)
        ctk.set_appearance_mode("dark")

def T(key):
    return Theme.get(key)

Theme.apply_dark()
ctk.set_default_color_theme("blue")

# ============================================================
#  USER MANAGEMENT
# ============================================================
_USERS_FILE = os.path.join(app_folder, "users.json")

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def _load_users() -> dict:
    if not os.path.isfile(_USERS_FILE):
        default = {"admin": _hash_password("admin")}
        _save_users(default)
        return default
    try:
        with open(_USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}
    except Exception as e:
        print(f"[WARN] Could not load users: {e}")
        return {"admin": _hash_password("admin")}

def _save_users(users: dict):
    os.makedirs(app_folder, exist_ok=True)
    with open(_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def _add_user(username: str, password: str):
    username = username.strip().lower()
    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters."
    if not re.match(r"^[a-z0-9_.\-]+$", username):
        return False, "Username may only contain letters, digits, _ . -"
    if not password or len(password) < 4:
        return False, "Password must be at least 4 characters."
    users = _load_users()
    if username in users:
        return False, f"User '{username}' already exists."
    users[username] = _hash_password(password)
    _save_users(users)
    return True, f"User '{username}' created successfully."

def _delete_user(username: str):
    username = username.strip().lower()
    users = _load_users()
    if username not in users:
        return False, f"User '{username}' not found."
    if len(users) == 1:
        return False, "Cannot delete the last user account."
    del users[username]
    _save_users(users)
    return True, f"User '{username}' deleted."

def _change_password(username: str, new_password: str):
    username = username.strip().lower()
    if not new_password or len(new_password) < 4:
        return False, "Password must be at least 4 characters."
    users = _load_users()
    if username not in users:
        return False, f"User '{username}' not found."
    users[username] = _hash_password(new_password)
    _save_users(users)
    return True, f"Password updated for '{username}'."


# ── Globals ──────────────────────────────────────────────────
pdf_doc       = None
last_result   = None
last_fields   = None
preview_label = None
_back_preview_label = None
app           = None
status_var    = None
progress_bar  = None
_field_vars   = {}
_tab_frames   = {}
_tab_buttons  = {}
_active_tab   = None
_executor     = concurrent.futures.ThreadPoolExecutor(max_workers=2)
_native_name_font_size = [30]

num_map = str.maketrans("OolIi|ZzSsgqB", "0011112255998")
_ABHA_LETTER_MAP = str.maketrans("OolIi|", "001111")

_bg_enabled_state = True   # OFF by default


# ============================================================
#  CARD BACKGROUND HELPER
# ============================================================
def _find_bg_path():
    for name in ["Pm1.png", "Pm1.jpg", "Pm1.jpeg", "Pm 1.png", "Pm 1.jpg", "Pm 1.jpeg",
                 "background.png", "background.jpg", "background.jpeg",
                 "bg.png", "bg.jpg", "card_bg.png", "card_bg.jpg"]:
        for base in [exe_dir(), resource_path("")]:
            p = os.path.join(base, name)
            if p and os.path.isfile(p):
                return p
    return None

def _find_bg2_path():
    for name in ["Pm2.png", "Pm2.jpg", "Pm2.jpeg", "Pm 2.png", "Pm 2.jpg", "Pm 2.jpeg",
                 "background2.png", "background2.jpg", "background2.jpeg",
                 "bg2.png", "bg2.jpg", "card_bg2.png", "card_bg2.jpg"]:
        for base in [exe_dir(), resource_path("")]:
            p = os.path.join(base, name)
            if p and os.path.isfile(p):
                return p
    return None

def _make_builtin_background(card_w, card_h):
    bg = Image.new("RGB", (card_w, card_h), (255, 255, 255))
    draw_bg = ImageDraw.Draw(bg)
    for y in range(int(card_h * 0.18)):
        ratio = y / (card_h * 0.18)
        r = int(16  + (255 - 16)  * ratio)
        g = int(185 + (255 - 185) * ratio)
        b = int(129 + (255 - 129) * ratio)
        draw_bg.line([(0, y), (card_w, y)], fill=(r, g, b))
    stripe_col = (230, 248, 240)
    for x in range(-card_h, card_w + card_h, 80):
        draw_bg.line([(x, 0), (x + card_h, card_h)], fill=stripe_col, width=30)
    bar_h = int(card_h * 0.06)
    for y in range(card_h - bar_h, card_h):
        ratio = (y - (card_h - bar_h)) / bar_h
        r = int(16  * (1 - ratio) + 10  * ratio)
        g = int(185 * (1 - ratio) + 120 * ratio)
        b = int(129 * (1 - ratio) + 80  * ratio)
        draw_bg.line([(0, y), (card_w, y)], fill=(r, g, b))
    draw_bg.rectangle([0, 0, card_w, int(card_h * 0.012)], fill=(16, 185, 129))
    return bg

_bg_image_cache = {}

def _get_background_image(card_w, card_h, bg_index=1):
    bg_path = _find_bg_path() if bg_index == 1 else _find_bg2_path()
    cache_key = (card_w, card_h, bg_path or "builtin", bg_index)
    if cache_key in _bg_image_cache:
        return _bg_image_cache[cache_key]
    if bg_path:
        try:
            bg = Image.open(bg_path).convert("RGB").resize(
                (card_w, card_h), Image.LANCZOS)
            _bg_image_cache[cache_key] = bg
            return bg
        except Exception as e:
            print(f"[BG WARN] Could not load {bg_path}: {e}")
    bg = _make_builtin_background(card_w, card_h)
    _bg_image_cache[cache_key] = bg
    return bg


# ============================================================
#  LOGO HELPER
# ============================================================
def _find_logo_path():
    for candidate in [
        resource_path("logo.png"),
        os.path.join(exe_dir(), "logo.png"),
    ]:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


# ============================================================
#  APP ICON
# ============================================================
def _set_app_icon(window):
    logo_path = _find_logo_path()
    if logo_path:
        try:
            tmp_ico = os.path.join(tempfile.gettempdir(), "abha_studio_icon.ico")
            img = Image.open(logo_path).convert("RGBA")
            img.save(tmp_ico, format="ICO",
                     sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])
            window.iconbitmap(tmp_ico)
            return
        except Exception as e:
            print(f"[WARN] logo.png → ico failed: {e}")
    try:
        size = 64
        img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([0, 0, size-1, size-1], radius=14, fill=(16, 185, 129))
        fnt = None
        for candidate in [_ENGLISH_FONT_PATH,
                           r"C:\Windows\Fonts\arial.ttf",
                           r"C:\Windows\Fonts\segoeui.ttf"]:
            if candidate and os.path.isfile(candidate):
                try: fnt = ImageFont.truetype(candidate, 28); break
                except Exception: pass
        if fnt is None: fnt = ImageFont.load_default()
        try:
            bbox = draw.textbbox((0, 0), "AB", font=fnt)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            tw, th = draw.textsize("AB", font=fnt)
        draw.text(((size - tw) // 2, (size - th) // 2), "AB",
                  font=fnt, fill=(255, 255, 255))
        tmp_ico = os.path.join(tempfile.gettempdir(), "abha_studio_icon.ico")
        img.save(tmp_ico, format="ICO", sizes=[(120, 120), (64, 64), (32, 32)])
        window.iconbitmap(tmp_ico)
    except Exception as e:
        print(f"[WARN] Could not set window icon: {e}")


# ============================================================
#  NAVBAR LOGO HELPER
# ============================================================
def _make_navbar_logo(parent):
    logo_path = _find_logo_path()
    if logo_path:
        try:
            pil_logo = Image.open(logo_path).convert("RGBA").resize(
                (30, 30), Image.LANCZOS)
            ctk_logo = ctk.CTkImage(
                light_image=pil_logo, dark_image=pil_logo, size=(30, 30))
            lbl = ctk.CTkLabel(parent, image=ctk_logo, text="")
            lbl.image = ctk_logo
            lbl.pack(side="left", padx=(0, 10), pady=12)
            return lbl
        except Exception as e:
            print(f"[WARN] navbar logo load failed: {e}")
    logo_c = tk.Canvas(parent, width=32, height=32,
                        bg=T("NAV_BG"), highlightthickness=0)
    logo_c.pack(side="left", padx=(0, 10), pady=12)
    logo_c.create_oval(1, 1, 31, 31, fill=T("ACCENT"), outline="")
    logo_c.create_text(16, 16, text="AB", fill="#FFFFFF",
                       font=("Arial", 9, "bold"))
    return logo_c


# ============================================================
#  HELPER: rounded pill badge
# ============================================================
def _pill_label(parent, text, color, bg=None):
    bg = bg or T("ACCENT_DIM")
    return ctk.CTkLabel(parent, text=text,
                        font=ctk.CTkFont("Arial", 8, weight="bold"),
                        fg_color=bg, text_color=color,
                        corner_radius=20, padx=10, pady=3)


# ============================================================
#  MACHINE CODE SCREEN  (shown after registration)
# ============================================================
class MachineCodeScreen(ctk.CTkToplevel):
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.on_success    = on_success
        self._machine_code = _get_machine_code()
        self.overrideredirect(True)
        self.configure(fg_color=T("BG_ROOT"))
        self.resizable(False, False)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h   = 520, 580
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.lift()
        self.attributes("-topmost", True)
        self.grab_set()
        self._drag_x = self._drag_y = 0
        self._build()

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.winfo_x()
        self._drag_y = e.y_root - self.winfo_y()

    def _drag_move(self, e):
        self.geometry(f"+{e.x_root-self._drag_x}+{e.y_root-self._drag_y}")

    def _build(self):
        ctk.CTkFrame(self, fg_color=T("ACCENT"), height=4,
                     corner_radius=0).pack(fill="x", side="top")
        tbar = ctk.CTkFrame(self, fg_color=T("BG_PANEL"),
                            height=38, corner_radius=0)
        tbar.pack(fill="x"); tbar.pack_propagate(False)
        ctk.CTkLabel(tbar, text="  ABHA Card Studio — Machine Code",
                     font=ctk.CTkFont("Arial", 9),
                     text_color=T("TEXT_3")).pack(side="left", padx=10)
        ctk.CTkButton(tbar, text="✕", width=38, height=34,
                      font=ctk.CTkFont("Arial", 11),
                      fg_color="transparent", hover_color="#8B0000",
                      text_color=T("TEXT_3"), corner_radius=0,
                      command=self.destroy).pack(side="right")
        tbar.bind("<ButtonPress-1>", self._drag_start)
        tbar.bind("<B1-Motion>",     self._drag_move)

        outer = ctk.CTkFrame(self, fg_color=T("BG_ROOT"), corner_radius=0)
        outer.pack(fill="both", expand=True, padx=24, pady=20)
        card = ctk.CTkFrame(outer, fg_color=T("BG_PANEL"), corner_radius=16,
                             border_width=1, border_color=T("BORDER"))
        card.pack(fill="both", expand=True)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=32, pady=24)

        # Icon
        ic = tk.Canvas(inner, width=56, height=56,
                        bg=T("BG_PANEL"), highlightthickness=0)
        ic.pack(pady=(0, 12))
        ic.create_oval(2, 2, 54, 54,
                       fill=T("ACCENT_DIM"), outline=T("ACCENT_LIGHT"), width=2)
        ic.create_text(28, 28, text="🖥", font=("Arial", 20))

        ctk.CTkLabel(inner, text="Your Machine Code",
                     font=ctk.CTkFont("Arial", 16, weight="bold"),
                     text_color=T("TEXT_1")).pack()
        ctk.CTkLabel(inner,
                     text="Share this code with the developer to receive your License Key.",
                     font=ctk.CTkFont("Arial", 9),
                     text_color=T("TEXT_2"), wraplength=400).pack(pady=(6, 16))

        # Machine code box
        mc_box = ctk.CTkFrame(inner, fg_color=T("ACCENT_DIM"), corner_radius=10,
                               border_width=1, border_color=T("ACCENT_LIGHT"))
        mc_box.pack(fill="x", pady=(0, 12))
        mc_row = ctk.CTkFrame(mc_box, fg_color="transparent")
        mc_row.pack(fill="x", padx=14, pady=14)
        ctk.CTkLabel(mc_row, text=self._machine_code,
                     font=ctk.CTkFont("Arial", 16, weight="bold"),
                     text_color=T("ACCENT2")).pack(side="left")
        ctk.CTkButton(mc_row, text="Copy", width=60, height=30,
                      corner_radius=8,
                      font=ctk.CTkFont("Arial", 9, weight="bold"),
                      fg_color=T("ACCENT"), hover_color=T("ACCENT2"),
                      text_color="#FFFFFF",
                      command=self._copy_mc).pack(side="right")

        self._msg_var = tk.StringVar(value="")
        ctk.CTkLabel(inner, textvariable=self._msg_var,
                     font=ctk.CTkFont("Arial", 9),
                     text_color=T("SUCCESS")).pack(pady=(0, 12))

        # Enter license key
        ctk.CTkLabel(inner, text="Enter License Key",
                     font=ctk.CTkFont("Arial", 9, weight="bold"),
                     text_color=T("TEXT_1")).pack(anchor="w", pady=(0, 6))

        self._key_var = tk.StringVar()
        self._key_entry = ctk.CTkEntry(
            inner, textvariable=self._key_var,
            placeholder_text="XXXX-XXXX-XXXX-XXXX",
            font=ctk.CTkFont("Arial", 13),
            fg_color=T("BG_INPUT"), border_color=T("BORDER2"),
            text_color=T("TEXT_1"), height=42, corner_radius=10)
        self._key_entry.pack(fill="x")
        self._key_entry.bind("<Return>", lambda e: self._activate())

        self._err_var = tk.StringVar(value="")
        ctk.CTkLabel(inner, textvariable=self._err_var,
                     font=ctk.CTkFont("Arial", 9),
                     text_color=T("ERROR_COL"),
                     wraplength=420).pack(pady=(6, 0))

        ctk.CTkButton(inner, text="Activate License",
                      font=ctk.CTkFont("Arial", 12, weight="bold"),
                      fg_color=T("ACCENT"), hover_color=T("ACCENT2"),
                      text_color="#FFFFFF", height=42, corner_radius=10,
                      command=self._activate).pack(fill="x", pady=(10, 0))

        self._key_entry.focus()

    def _copy_mc(self):
        self.clipboard_clear()
        self.clipboard_append(self._machine_code)
        self._msg_var.set("✓  Machine Code copied!")

    def _activate(self):
        entered  = self._key_var.get().strip().upper()
        if entered == _DEMO_KEY:
            global _RUNTIME_DEMO_MODE
            _RUNTIME_DEMO_MODE = True
            self._err_var.set("✓  Trial mode activated!")
            self.after(1, self._close_and_success)
            return
        expected = _expected_key(self._machine_code)
        if entered == expected:
            _save_license(entered)
            self.after(1, self._close_and_success)
        else:
            self._err_var.set("❌  Invalid license key. Please try again.")
            self._key_var.set("")
            self._key_entry.focus()
            
# ============================================================
#  ACTIVATION SCREEN
# ============================================================
class ActivationScreen(ctk.CTkToplevel):
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.on_success    = on_success
        self._machine_code = _get_machine_code()
        self.overrideredirect(True)
        self.configure(fg_color=T("BG_ROOT"))
        self.resizable(False, False)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h   = 520, 560
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.lift(); self.attributes("-topmost", True); self.grab_set()
        self._drag_x = self._drag_y = 0
        self._build()

    def _drag_start(self, e): self._drag_x = e.x_root - self.winfo_x(); self._drag_y = e.y_root - self.winfo_y()
    def _drag_move(self, e): self.geometry(f"+{e.x_root-self._drag_x}+{e.y_root-self._drag_y}")

    def _minimize(self):
        self.overrideredirect(False); self.iconify()
        self.bind("<Map>", lambda e: (self.overrideredirect(True), self.lift(), self.attributes("-topmost", True)))

    def _build(self):
        ctk.CTkFrame(self, fg_color=T("ACCENT"), height=4, corner_radius=0).pack(fill="x", side="top")
        tbar = ctk.CTkFrame(self, fg_color=T("BG_PANEL"), height=38, corner_radius=0)
        tbar.pack(fill="x"); tbar.pack_propagate(False)
        ctk.CTkLabel(tbar, text="  ABHA Card Studio — Activation",
                     font=ctk.CTkFont("Arial", 9), text_color=T("TEXT_3")).pack(side="left", padx=10)
        for txt, cmd, hov in [("✕", self.destroy, "#DBEAFE"), ("—", self._minimize, T("BG_HOVER"))]:
            ctk.CTkButton(tbar, text=txt, width=38, height=34, font=ctk.CTkFont("Arial", 11),
                          fg_color="transparent", hover_color=hov,
                          text_color=T("TEXT_3"), corner_radius=0, command=cmd).pack(side="right")
        tbar.bind("<ButtonPress-1>", self._drag_start)
        tbar.bind("<B1-Motion>", self._drag_move)
        outer = ctk.CTkFrame(self, fg_color=T("BG_ROOT"), corner_radius=0)
        outer.pack(fill="both", expand=True, padx=24, pady=20)
        card = ctk.CTkFrame(outer, fg_color=T("BG_PANEL"), corner_radius=16,
                             border_width=1, border_color=T("BORDER"))
        card.pack(fill="both", expand=True)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=32, pady=24)
        ic = tk.Canvas(inner, width=56, height=56, bg=T("BG_PANEL"), highlightthickness=0)
        ic.pack(pady=(0, 12))
        ic.create_oval(2, 2, 54, 54, fill=T("ACCENT_DIM"), outline=T("ACCENT_LIGHT"), width=2)
        ic.create_text(28, 28, text="🔐", font=("Arial", 20))
        ctk.CTkLabel(inner, text="Product Activation",
                     font=ctk.CTkFont("Arial", 18, weight="bold"),
                     text_color=T("TEXT_1")).pack()
        ctk.CTkLabel(inner, text="ABHA Card Studio  ·  v5.2",
                     font=ctk.CTkFont("Arial", 9),
                     text_color="#FFFFFF").pack(pady=(2, 16))
        s1 = ctk.CTkFrame(inner, fg_color=T("ACCENT_DIM"), corner_radius=10,
                           border_width=1, border_color=T("ACCENT_LIGHT"))
        s1.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(s1, text="STEP 1 — Your Machine Code",
                     font=ctk.CTkFont("Arial", 8, weight="bold"),
                     text_color="#FFFFFF").pack(anchor="w", padx=14, pady=(10, 4))
        mc_row = ctk.CTkFrame(s1, fg_color="transparent")
        mc_row.pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkLabel(mc_row, text=self._machine_code,
                     font=ctk.CTkFont("Arial", 14, weight="bold"),
                     text_color="#FFFFFF").pack(side="left")
        ctk.CTkButton(mc_row, text="Copy", width=56, height=28, corner_radius=8,
                      font=ctk.CTkFont("Arial", 9, weight="bold"),
                      fg_color=T("ACCENT"), hover_color=T("ACCENT2"),
                      text_color="#FFFFFF", command=self._copy_mc).pack(side="right")
        ctk.CTkLabel(inner, text="Send this code to the developer to receive your License Key.",
                     font=ctk.CTkFont("Arial", 9), text_color="#FFFFFF",
                     wraplength=420).pack(anchor="w", pady=(0, 12))
        ctk.CTkLabel(inner, text="STEP 3 — Enter License Key",
                     font=ctk.CTkFont("Arial", 8, weight="bold"),
                     text_color="#FFFFFF").pack(anchor="w", pady=(0, 6))
        self._key_var = tk.StringVar()
        self._key_entry = ctk.CTkEntry(inner, textvariable=self._key_var,
                                        placeholder_text="XXXX-XXXX-XXXX-XXXX",
                                        font=ctk.CTkFont("Arial", 13),
                                        fg_color=T("BG_INPUT"), border_color=T("BORDER2"),
                                        text_color=T("TEXT_1"), height=42, corner_radius=10)
        self._key_entry.pack(fill="x")
        self._key_entry.bind("<Return>", lambda e: self._activate())
        self._err_var = tk.StringVar(value="")
        self._err_lbl = ctk.CTkLabel(inner, textvariable=self._err_var,
                                      font=ctk.CTkFont("Arial", 9),
                                      text_color=T("ERROR_COL"), wraplength=420)
        self._err_lbl.pack(pady=(6, 0))
        ctk.CTkButton(inner, text="Activate License",
                      font=ctk.CTkFont("Arial", 12, weight="bold"),
                      fg_color=T("ACCENT"), hover_color=T("ACCENT2"),
                      text_color="#FFFFFF", height=42, corner_radius=10,
                      command=self._activate).pack(fill="x", pady=(12, 0))
        self._key_entry.focus()

    def _copy_mc(self):
        self.clipboard_clear(); self.clipboard_append(self._machine_code)
        self._err_var.set("✓  Machine Code copied!")
        self._err_lbl.configure(text_color=T("SUCCESS"))

    def _close_and_success(self):
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        try:
            self.master.after(100, self.on_success)
        except Exception:
            pass

    def _activate(self):
        entered  = self._key_var.get().strip().upper()
        if entered == _DEMO_KEY:
            global _RUNTIME_DEMO_MODE
            _RUNTIME_DEMO_MODE = True
            self._err_var.set("✓  Trial mode activated! Card will show TRIAL watermark.")
            self._err_lbl.configure(text_color="#F59E0B")
            self.after(1, self._close_and_success)
            return
            
        expected = _expected_key(self._machine_code)
        if entered == expected:
            _save_license(entered)
            self.after(1, self._close_and_success)
        else:
            self._err_var.set("❌  Invalid license key. Please try again.")
            self._err_lbl.configure(text_color=T("ERROR_COL"))
            self._key_var.set(""); self._key_entry.focus()


# ============================================================
#  LOADING SCREEN
# ============================================================
class LoadingScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(fg_color=T("BG_ROOT"))
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h   = 460, 320
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.lift(); self.attributes("-topmost", True)
        ctk.CTkFrame(self, fg_color=T("ACCENT"), height=4, corner_radius=0).pack(fill="x", side="top")
        outer = ctk.CTkFrame(self, fg_color=T("BG_ROOT"), corner_radius=0)
        outer.pack(fill="both", expand=True, padx=20, pady=16)
        card = ctk.CTkFrame(outer, fg_color=T("BG_PANEL"), corner_radius=20,
                             border_width=1, border_color=T("BORDER"))
        card.pack(fill="both", expand=True)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")
        logo_path = _find_logo_path()
        if logo_path:
            try:
                pil_logo = Image.open(logo_path).convert("RGBA").resize((90, 90), Image.LANCZOS)
                ctk_logo = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(90, 90))
                lbl = ctk.CTkLabel(inner, image=ctk_logo, text="")
                lbl.image = ctk_logo
                lbl.pack(pady=(0, 10))
            except Exception:
                self._draw_icon(inner)
        else:
            self._draw_icon(inner)
        ctk.CTkLabel(inner, text="ABHA Card Studio",
                     font=ctk.CTkFont("Arial", 20, weight="bold"),
                     text_color=T("TEXT_1")).pack()
        ctk.CTkLabel(inner, text="v5.2",
                     font=ctk.CTkFont("Arial", 9),
                     text_color=T("TEXT_3")).pack(pady=(2, 20))
        if _is_demo_mode():
            ctk.CTkLabel(inner, text="⚠  TRIAL VERSION  —  For evaluation only",
                         font=ctk.CTkFont("Arial", 9, weight="bold"),
                         text_color="#F59E0B").pack(pady=(0, 8))
        self.prog_bar = ctk.CTkProgressBar(inner, height=6, width=320,
                                            fg_color="#FFFFFF",
                                            progress_color=T("ACCENT"),
                                            corner_radius=10)
        self.prog_bar.pack(); self.prog_bar.set(0)
        self.status_lbl = ctk.CTkLabel(inner, text="Starting up…",
                                        font=ctk.CTkFont("Arial", 9),
                                        text_color=T("TEXT_3"))
        self.status_lbl.pack(pady=(10, 0))
        self._steps = [
            (0.25, "Loading OCR engine…"),
            (0.50, "Preparing Tamil fonts…"),
            (0.70, "Setting up QR pipeline…"),
            (1.00, "All systems ready ✓"),
        ]
        self._animate(0)

    def _draw_icon(self, parent):
        c = tk.Canvas(parent, width=90, height=90, bg=T("BG_PANEL"), highlightthickness=0)
        c.pack(pady=(0, 20))
        c.create_oval(1, 1, 89, 89, fill=T("ACCENT"), outline="")
        c.create_text(26, 26, text="AB", fill="#FFFFFF", font=("Arial", 30, "bold"))

    def _animate(self, idx):
        if idx >= len(self._steps): return
        ratio, msg = self._steps[idx]
        self._smooth(ratio, msg, idx, 20, 300)

    def _smooth(self, target, msg, nxt, steps, ms):
        try: current = float(self.prog_bar.get() or 0)
        except: current = 0.0
        delta = (target - current) / steps
        iv    = ms // steps
        def tick(i, cur):
            if not self.winfo_exists(): return
            nv = min(cur + delta, target)
            self.prog_bar.set(nv)
            if i < steps: self.after(iv, tick, i + 1, nv)
            else:
                self.status_lbl.configure(text=msg)
                if nxt + 1 < len(self._steps):
                    self.after(200, self._animate, nxt + 1)
        tick(0, current)


# ============================================================
#  LOGIN SCREEN
# ============================================================
class LoginScreen(ctk.CTkToplevel):
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.on_success = on_success
        self._attempts  = 0
        self._locked    = False
        self.overrideredirect(True)
        self.configure(fg_color=T("BG_ROOT"))
        self.resizable(False, False)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h   = 420, 580
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.lift(); self.attributes("-topmost", True); self.grab_set()
        self._drag_x = self._drag_y = 0
        self._build()

    def _drag_start(self, e): self._drag_x = e.x_root - self.winfo_x(); self._drag_y = e.y_root - self.winfo_y()
    def _drag_move(self, e): self.geometry(f"+{e.x_root-self._drag_x}+{e.y_root-self._drag_y}")
    def _minimize(self):
        self.overrideredirect(False); self.iconify()
        self.bind("<Map>", lambda e: (self.overrideredirect(True), self.lift(), self.attributes("-topmost", True)))

    def _build(self):
        ctk.CTkFrame(self, fg_color=T("ACCENT"), height=4, corner_radius=0).pack(fill="x", side="top")
        tbar = ctk.CTkFrame(self, fg_color=T("BG_PANEL"), height=36, corner_radius=0)
        tbar.pack(fill="x"); tbar.pack_propagate(False)
        ctk.CTkLabel(tbar, text="  ABHA Card Studio",
                     font=ctk.CTkFont("Arial", 9), text_color=T("TEXT_3")).pack(side="left", padx=10)
        for txt, cmd, hov in [("✕", self.destroy, "#DBEAFE"), ("—", self._minimize, T("BG_HOVER"))]:
            ctk.CTkButton(tbar, text=txt, width=38, height=32,
                          font=ctk.CTkFont("Arial", 11),
                          fg_color="transparent", hover_color=hov,
                          text_color=T("TEXT_3"), corner_radius=0, command=cmd).pack(side="right")
        tbar.bind("<ButtonPress-1>", self._drag_start)
        tbar.bind("<B1-Motion>", self._drag_move)
        outer = ctk.CTkFrame(self, fg_color=T("BG_ROOT"), corner_radius=0)
        outer.pack(fill="both", expand=True, padx=28, pady=20)
        card = ctk.CTkFrame(outer, fg_color=T("BG_PANEL"), corner_radius=20,
                             border_width=1, border_color=T("BORDER"))
        card.pack(fill="both", expand=True)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=36, pady=28)
        logo_path = _find_logo_path()
        if logo_path:
            try:
                pil_logo = Image.open(logo_path).convert("RGBA").resize((60, 60), Image.LANCZOS)
                ctk_logo = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(60, 60))
                lbl = ctk.CTkLabel(inner, image=ctk_logo, text="")
                lbl.image = ctk_logo
                lbl.pack(pady=(0, 14))
            except Exception:
                self._draw_icon(inner)
        else:
            self._draw_icon(inner)
        ctk.CTkLabel(inner, text="Welcome back",
                     font=ctk.CTkFont("Arial", 20, weight="bold"),
                     text_color=T("TEXT_1")).pack()
        ctk.CTkLabel(inner, text="Sign in to your account",
                     font=ctk.CTkFont("Arial", 10),
                     text_color="#FFFFFF").pack(pady=(4, 20))
        for label, var_name, show, placeholder in [
            ("Username", "_user_var", "", "Enter your username"),
            ("Password", "_pass_var", "●", "Enter your password"),
        ]:
            ctk.CTkLabel(inner, text=label,
                         font=ctk.CTkFont("Arial", 10, weight="bold"),
                         text_color="#FFFFFF").pack(anchor="w", pady=(0, 4))
            setattr(self, var_name, tk.StringVar())
            entry = ctk.CTkEntry(inner, textvariable=getattr(self, var_name),
                                  placeholder_text=placeholder, show=show,
                                  font=ctk.CTkFont("Arial", 11),
                                  fg_color=T("BG_INPUT"), border_color=T("BORDER2"),
                                  text_color=T("TEXT_1"), height=42, corner_radius=10)
            entry.pack(fill="x", pady=(0, 14))
            if var_name == "_user_var":
                self._user_entry = entry
                entry.bind("<Return>", lambda e: self._pass_entry.focus())
            else:
                self._pass_entry = entry
                entry.bind("<Return>", lambda e: self._attempt_login())
        show_row = ctk.CTkFrame(inner, fg_color="transparent")
        show_row.pack(fill="x", pady=(0, 8))
        self._show_pw = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(show_row, text="Show password", variable=self._show_pw,
                        font=ctk.CTkFont("Arial", 9), text_color="#FFFFFF",
                        fg_color=T("ACCENT"), hover_color=T("ACCENT2"),
                        border_color=T("BORDER2"), checkmark_color="#FFFFFF",
                        height=16, width=16, command=self._toggle_pw).pack(side="left")
        self._err_var = tk.StringVar(value="")
        self._err_lbl = ctk.CTkLabel(inner, textvariable=self._err_var,
                                      font=ctk.CTkFont("Arial", 9),
                                      text_color=T("ERROR_COL"), wraplength=320)
        self._err_lbl.pack(pady=(0, 8))
        self._login_btn = ctk.CTkButton(inner, text="Sign In →",
                                         font=ctk.CTkFont("Arial", 13, weight="bold"),
                                         fg_color=T("ACCENT"), hover_color=T("ACCENT2"),
                                         text_color="#FFFFFF", height=44, corner_radius=12,
                                         command=self._attempt_login)
        self._login_btn.pack(fill="x")
        ctk.CTkLabel(inner, text="Authorised personnel only",
                     font=ctk.CTkFont("Arial", 8),
                     text_color=T("TEXT_3")).pack(pady=(14, 0))
        self._user_entry.focus()

    def _draw_icon(self, parent):
        c = tk.Canvas(parent, width=60, height=60, bg=T("BG_PANEL"), highlightthickness=0)
        c.pack(pady=(0, 14))
        c.create_oval(1, 1, 59, 59, fill=T("ACCENT"), outline="")
        c.create_text(30, 30, text="AB", fill="#FFFFFF", font=("Arial", 16, "bold"))

    def _toggle_pw(self):
        self._pass_entry.configure(show="" if self._show_pw.get() else "●")

    def _shake(self):
        ox, oy = self.winfo_x(), self.winfo_y()
        for dx, delay in zip([8, -8, 6, -6, 3, -3, 0], range(0, 280, 40)):
            self.after(delay, lambda d=dx: self.geometry(f"+{ox+d}+{oy}"))

    def _lock(self, seconds=30):
        self._locked = True
        self._login_btn.configure(state="disabled")
        def _countdown(s):
            if not self.winfo_exists(): return
            if s <= 0:
                self._locked = False; self._attempts = 0
                self._login_btn.configure(state="normal"); self._err_var.set("")
            else:
                self._err_var.set(f"Too many attempts. Please wait {s}s…")
                self._err_lbl.configure(text_color=T("WARNING"))
                self.after(1000, _countdown, s - 1)
        _countdown(seconds)

    def _close_and_success(self):
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        try:
            self.on_success()
        except Exception:
            pass

    def _attempt_login(self):
        if self._locked: return
        username = self._user_var.get().strip().lower()
        password = self._pass_var.get()
        users    = _load_users()
        if users.get(username) == _hash_password(password):
            self.after(1, self._close_and_success)
        else:
            self._attempts += 1
            self._shake()
            if self._attempts >= 5:
                self._lock(30)
            else:
                remaining = 5 - self._attempts
                self._err_var.set(f"Incorrect credentials.  ({remaining} attempt{'s' if remaining != 1 else ''} left)")
                self._err_lbl.configure(text_color=T("ERROR_COL"))
                self._pass_var.set(""); self._pass_entry.focus()


# ============================================================
#  TESSERACT CONFIG
# ============================================================
_LANG_EN       = "eng"
_LANG_TA       = "tam"
_LANG_ML       = "mal"
_LANG_HI       = "hin"
_LANG_EN_TA    = "eng+tam"
_LANG_EN_ML    = "eng+mal"
_LANG_EN_HI    = "eng+hin"
_LANG_EN_TA_ML = "eng+tam+mal"
_LANG_ALL      = "eng+tam+mal+hin"
_CFG_BEST      = "--oem 1 --psm 6 -c tessedit_do_invert=0"
_CFG_FAST      = "--oem 3 --psm 6 -c tessedit_do_invert=0"
_CFG_SPARSE    = "--oem 3 --psm 11"

# Malayalam Unicode range: \u0D00-\u0D7F
def _has_malayalam(text):
    return bool(re.search(r"[\u0D00-\u0D7F]", text or ""))

def _has_tamil(text):
    return bool(re.search(r"[\u0B80-\u0BFF]", text or ""))


# ============================================================
#  PREPROCESSING
# ============================================================
def _safe_ocr(image, lang, config=''):
    try:
        text = pytesseract.image_to_string(image, lang=lang, config=config)
        if text.strip(): return text
    except Exception as e:
        print(f"[OCR WARN] Tesseract failed for lang={lang}: {e}")
    if lang == 'tam':
        try:
            text_tameng = pytesseract.image_to_string(image, lang='tam+eng', config=config)
            if text_tameng.strip(): return text_tameng
        except Exception as e2:
            print(f"[OCR WARN] Tamil+English fallback failed: {e2}")
    if 'tam' in lang and lang != 'tam':
        try:
            text_tam = pytesseract.image_to_string(image, lang='tam', config=config)
            if text_tam.strip(): return text_tam
        except Exception as e2:
            print(f"[OCR WARN] Tamil fallback failed: {e2}")
    if 'eng' in lang and lang != 'eng':
        try:
            return pytesseract.image_to_string(image, lang='eng', config=config)
        except Exception as e2:
            print(f"[OCR ERROR] English fallback failed: {e2}")
    return ""

def _preprocess(img, scale=3):
    h, w  = img.shape[:2]
    big   = cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
    gray  = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY) if big.ndim == 3 else big
    gray  = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if np.mean(thresh) < 127: thresh = cv2.bitwise_not(thresh)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    return thresh


# ============================================================
#  TAMIL–ENGLISH PHONETIC CROSS-CHECK
# ============================================================
_TAM_ROMAN = [
    ("\u0B9A\u0BC1", "su"), ("\u0BA4\u0BB0\u0BCD", "thar"),
    ("\u0B9A\u0BA9\u0BCD", "san"), ("\u0BAE\u0BC1", "mu"),
    ("\u0BA4\u0BCD\u0BA4\u0BC1", "tthu"), ("\u0B95\u0BC1", "ku"),
    ("\u0BAE\u0BBE\u0BB0\u0BCD", "mar"), ("\u0BB0\u0BBE\u0B9C\u0BA9\u0BCD", "rajan"),
    ("\u0B86", "aa"), ("\u0B88", "ii"), ("\u0B8A", "uu"),
    ("\u0B8F", "ee"), ("\u0B90", "ai"), ("\u0B93", "oo"), ("\u0B94", "au"),
    ("\u0B85", "a"),  ("\u0B87", "i"),  ("\u0B89", "u"),
    ("\u0B8E", "e"),  ("\u0B92", "o"),
    ("\u0BB8", "s"), ("\u0BB7", "sh"), ("\u0B9C", "j"), ("\u0BB9", "h"),
    ("\u0B95", "k"), ("\u0B99", "ng"), ("\u0B9A", "ch"), ("\u0B9E", "ny"),
    ("\u0B9F", "t"),  ("\u0BA3", "n"),  ("\u0BA4", "th"), ("\u0BA8", "n"),
    ("\u0BAA", "p"),  ("\u0BAE", "m"),  ("\u0BAF", "y"),  ("\u0BB0", "r"),
    ("\u0BB2", "l"),  ("\u0BB5", "v"),  ("\u0BB4", "zh"), ("\u0BB3", "l"),
    ("\u0BB1", "r"),  ("\u0BA9", "n"),  ("\u0B83", "h"),  ("\u0B82", "m"),
    ("\u0BBE", "aa"), ("\u0BBF", "i"),  ("\u0BC0", "ii"), ("\u0BC1", "u"),
    ("\u0BC2", "uu"), ("\u0BC6", "e"),  ("\u0BC7", "ee"), ("\u0BC8", "ai"),
    ("\u0BCA", "o"),  ("\u0BCB", "oo"), ("\u0BCC", "au"),
    ("\u0BCD", ""), ("\u0B82", "m"), ("\u0B83", "h"),
]

def _tamil_to_roman(tamil_text: str) -> str:
    result = unicodedata.normalize("NFC", tamil_text)
    for tam, rom in _TAM_ROMAN:
        result = result.replace(tam, rom)
    result = re.sub(r"[^\x00-\x7F]", "", result)
    return result.lower().strip()

def _phonetic_match_score(tamil_name: str, english_name: str) -> float:
    if not tamil_name or not english_name: return 0.0
    rom = re.sub(r"[^a-z]", "", _tamil_to_roman(tamil_name))
    eng = re.sub(r"[^a-z]", "", english_name.lower())
    if not rom or not eng: return 0.0
    m, n = len(rom), len(eng)
    dp   = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if rom[i-1] == eng[j-1]: dp[i][j] = dp[i-1][j-1] + 1
            else: dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    lcs = dp[m][n]
    precision = lcs / m if m else 0
    recall    = lcs / n if n else 0
    if precision + recall == 0: return 0.0
    return 2 * precision * recall / (precision + recall)

def _select_best_tamil_name_with_english(candidates, english_name, phonetic_weight=0.6):
    if not candidates: return ""
    seen = {}
    for tam, score in candidates:
        if tam and tam not in seen: seen[tam] = score
    candidates = list(seen.items())
    if not english_name: return max(candidates, key=lambda x: x[1])[0]
    best_name = ""; best_blend = -1.0; best_chars = 0; best_words = 0
    for tam, ocr_score in candidates:
        if not tam: continue
        ph = _phonetic_match_score(tam, english_name)
        ocr_norm = min(ocr_score / 200.0, 1.0)
        tam_chars = len(re.sub(r"[^\u0B80-\u0BFF]", "", tam))
        tam_words = len(tam.split())
        length_bonus = min(tam_chars / 20.0, 0.25)
        word_bonus = min(max(tam_words - 1, 0) * 0.08, 0.35)
        multi_word_bonus = 0.15 if tam_words > 1 else 0.0
        quality_bonus = min(_tamil_name_quality(tam, tam) / 180.0, 0.3)
        blend = phonetic_weight * ph + (1.0 - phonetic_weight) * ocr_norm + length_bonus + word_bonus + multi_word_bonus + quality_bonus
        choose_current = False
        if blend > best_blend + 1e-6: choose_current = True
        elif abs(blend - best_blend) <= 0.08:
            if tam_words > best_words: choose_current = True
            elif tam_words == best_words and tam_chars > best_chars: choose_current = True
        elif abs(blend - best_blend) <= 0.15:
            if best_name and (tam in best_name or best_name in tam):
                choose_current = tam_chars > best_chars
            elif best_words == 1 and tam_words > 1 and blend >= best_blend - 0.05:
                choose_current = True
        if choose_current:
            best_blend = blend; best_name = tam; best_chars = tam_chars; best_words = tam_words
    if english_name and best_name:
        ph = _phonetic_match_score(best_name, english_name)
        if ph < 0.25: return ""
    return best_name

def _is_plausible_tamil_name(name: str, english_name: str = "") -> bool:
    if not name: return False
    words = name.split()
    has_enough_chars = any(len(re.sub(r"[^\u0B80-\u0BFF]", "", w)) >= 3 for w in words)
    if not has_enough_chars: return False
    if english_name:
        score = _phonetic_match_score(name, english_name)
        if score < 0.15: return False
    return True


# ============================================================
#  NAME EXTRACTION HELPERS
# ============================================================
_LABEL_SKIP = re.compile(
    r"^\s*(name|பெயர்|abha|health|id|card|number|address|mobile|dob|"
    r"date|birth|account|gender|ayushman|photo|image|"
    r"ஆயுஷ்மான்|பாரத்|ஆதார்|அரசு)\b",
    re.IGNORECASE | re.UNICODE,
)
_TAMIL_LABEL_WORDS = {
    'பெயர்', 'முகவரி', 'கைபேசி', 'பிறந்த', 'தேதி', 'பாலினம்',
    'எண்', 'அபா', 'ஆண்', 'பெண்', 'விலாசம்', 'பபயர்', 'பெயா்', 'பபயா்',
    'பெயா', 'பயா', 'பயர்', 'பபயமி', 'ிபபயமி', 'பபயமிபபப', 'ிபபயமிபபப',
    'பபப', 'பிப', 'பிபப', 'பபபய', 'பபயம','ிபபயமி'
}
_GARBAGE_WORDS = {
    "fiat","het","ap","el","lat","iet","les","kes","pt","et",
    "le","la","al","an","en","er","es","re","de","di","fi",
    "ht","hi","at","it","is","as","or","of","to","a","e","i",
}
_HEADER_WORDS = {
    "ayushman","bharat","health","account","abha","card",
    "number","address","mobile","dob","gender","photo","image",
    "pradhan","mantri","jan","arogya","yojana",
}
_NAME_NOISE_SUFFIX = {
    "mei","moi","nei","lei","wei","rei","sei","bei","dei","fei",
    "gei","hei","kei","tei","vei","yei","zei","oei","uei",
    "kel","mel","nel","rel","sel","tel","vel",
}
_NAME_STOP = re.compile(
    r"\b(abha|number|mobile|dob|gender|address|account|card|"
    r"health|ayushman|district|state|pincode|photo|image|"
    r"pradhan|mantri|arogya|yojana|hidn|hid)\b",
    re.IGNORECASE
)
_TAMIL_NAME_LABELS = ("\u0BAA\u0BC6\u0BAF\u0BB0\u0BCD",)
_TAMIL_SECTION_WORDS = (
    "\u0BAE\u0BC1\u0B95\u0BB5\u0BB0\u0BBF",
    "\u0B95\u0BC8\u0BAA\u0BC7\u0B9A\u0BBF",
    "\u0BAA\u0BBF\u0BB1\u0BA8\u0BCD\u0BA4",
    "\u0BAA\u0BBE\u0BB2\u0BBF\u0BA9\u0BAE\u0BCD",
)
_TAMIL_NAME_NOISE_WORDS = {
    'முகவரி', 'கைபேசி', 'பிறந்த', 'தேதி', 'பாலினம்', 'எண்', 'அபா', 'ஆண்', 'பெண்',
    'விலாசம்', 'மாவட்டம்', 'மாநிலம்', 'குடும்பம்', 'தொலைபேசி', 'பிரதான', 'அடையாள',
    'அறிக்கை', 'நீளம்', 'தாவல்', 'ஐடி', 'இடம்', 'மின்னஞ்சல்', 'படிப்படி',
    'யமி', 'யமிப', 'பயமி', 'பபயமி', 'ிபயமி', 'ிபபயமி',
    'பயம', 'யம', 'யமிபப', 'மிபப', 'மிப',
}
_TAMIL_LABEL_VARIANTS = {
    "nane", "mame", "nome", "nam", "naane",
    "name", "abha", "address", "mobile", "dob", "gender", "photo", "image", "id", "number",
    "பயர்", "பெயா", "பெயா்", "பபயர்", "பெய", "பய", "பிய"
}

def _contains_name_label(line):
    if not line: return False
    if re.search(r"\bname\b", line, re.IGNORECASE): return True
    return any(tok in line for tok in _TAMIL_NAME_LABELS)

def _strip_name_labels(line):
    if not line: return ""
    cleaned = re.sub(r"(?i)\bname\b|/|\\|:|-", " ", line)
    cleaned = re.sub(r"(?i)\babha\b", " ", cleaned)
    for tok in _TAMIL_NAME_LABELS:
        cleaned = cleaned.replace(tok, " ")
    return re.sub(r"\s{2,}", " ", cleaned).strip()

def _is_name_block_end(line):
    ll = (line or "").lower()
    if any(x in ll for x in ["address", "dob", "gender", "mobile", "abha number"]): return True
    return any(tok in (line or "") for tok in _TAMIL_SECTION_WORDS)

def _is_real_name_word(word):
    if not word: return False
    w = word.strip(".,")
    if not w: return False
    if len(w) < 1 or len(w) > 30: return False
    if not w.replace(".", "").replace("-", "").isalpha(): return False
    if w.lower() in _GARBAGE_WORDS: return False
    return True

def _is_english_name_line(line):
    line = line.strip()
    if not line: return False
    if _LABEL_SKIP.match(line): return False
    if re.search(r"[@#$%&*_|\\/<>:0-9]", line): return False
    words = line.split()
    if not (1 <= len(words) <= 10): return False
    if any(w.lower() in _HEADER_WORDS for w in words): return False
    real = [w for w in words if _is_real_name_word(w)]
    if not real: return False
    return True

def _strip_tamil_labels(line):
    if not line: return ""
    label_pattern = re.compile(
        r"^\s*(?:name|பெயர்|பெயா|பயர்|பெயா்|பபயர்|பெய|பய|பிய|பயா|nam|nom|نام)\s*[:\-–/\\]?\s*",
        re.IGNORECASE
    )
    cleaned = label_pattern.sub("", line)
    cleaned = re.sub(r"(?i)\b(abha|address|mobile|dob|gender|photo|image|id|number|state|district)\b", " ", cleaned)
    cleaned = re.sub(r"[:/\\\-]+", " ", cleaned)
    cleaned = re.sub(r"\s*نام\s*", " ", cleaned)
    cleaned = re.sub(r"[ி]?ப+ய+மி?ப*", " ", cleaned)
    cleaned = re.sub(r"^[\u0B80-\u0BFF]{1,4}\s+", " ", cleaned)
    for tok in _TAMIL_NAME_LABELS:
        cleaned = re.sub(rf"(?<![\u0B80-\u0BFF]){re.escape(tok)}(?![\u0B80-\u0BFF])", " ", cleaned)
    for tok in _TAMIL_LABEL_WORDS:
        cleaned = re.sub(rf"(?<![\u0B80-\u0BFF]){re.escape(tok)}(?![\u0B80-\u0BFF])", " ", cleaned)
    for tok in _TAMIL_LABEL_VARIANTS:
        cleaned = re.sub(rf"(?<![\u0B80-\u0BFF]){re.escape(tok)}(?![\u0B80-\u0BFF])", " ", cleaned)
    return re.sub(r"\s{2,}", " ", cleaned).strip()

def _is_tamil_name_line(line):
    line = (line or "").strip()
    if not line: return False
    tam = sum(1 for c in line if '\u0B80' <= c <= '\u0BFF')
    if tam < 2: return False
    alpha = sum(1 for c in line if c.isalpha())
    if alpha > 0 and tam / alpha < 0.5: return False
    if any(tok in line for tok in _TAMIL_SECTION_WORDS): return False
    if any(tok in line for tok in _TAMIL_NAME_NOISE_WORDS): return False
    words = [w for w in line.split() if re.search(r"[\u0B80-\u0BFF]", w)]
    if not words: return False
    valid_words = [w for w in words if len(re.sub(r"[^\u0B80-\u0BFF]", "", w)) >= 2]
    if not valid_words: return False
    if len(valid_words) > 6: return False
    return True

def _name_from_abha_address(address):
    if not address: return ""
    prefix = re.split(r"[@\d]", address)[0].strip()
    prefix = re.sub(r"\d", "", prefix).strip()
    if len(prefix) < 2: return ""
    words = prefix.split()
    return " ".join(w.title() for w in words if len(w) > 1)

def _is_valid_english_name_candidate(line):
    line = line.strip()
    if not line: return ""
    if re.search(r"[\u0B80-\u0BFF@#$%&*|\\/<>:\d]", line): return ""
    if _NAME_STOP.search(line): return ""
    tokens = line.split()
    cleaned_tokens = []
    for tok in tokens:
        ct = re.sub(r"[^A-Za-z.\-]", "", tok.strip(".,'-"))
        if not ct: continue
        if ct.lower() in _HEADER_WORDS or ct.lower() in _GARBAGE_WORDS: break
        if _NAME_STOP.search(ct): break
        if len(re.sub(r"[^A-Za-z]", "", ct)) < 1: continue
        cleaned_tokens.append(ct if ct[0].isupper() else ct.title())
    if not cleaned_tokens or len(cleaned_tokens) > 6: return ""
    cap_count = sum(1 for w in cleaned_tokens if w[0].isupper())
    if cap_count < max(1, len(cleaned_tokens) // 2): return ""
    result = " ".join(cleaned_tokens)
    if len(re.sub(r"[^A-Za-z]", "", result)) < 3: return ""
    return result

def _extract_abha_from_text(text):
    ocr_map = str.maketrans("OolIi|ZzSsgqBGDQ", "0011112255998600")
    cleaned = re.sub(r'[OolIi|]', lambda m: {'O':'0','o':'0','l':'1','I':'1','i':'1','|':'1'}[m.group()], text)
    condensed = re.sub(r'(?<=\d)\s+(?=\d)', '', cleaned)
    pattern1 = r"(?<![A-Za-z0-9])([A-Za-z0-9]{2})[\s\-./]+([A-Za-z0-9]{4})[\s\-./]+([A-Za-z0-9]{4})[\s\-./]+([A-Za-z0-9]{4})(?![A-Za-z0-9])"
    for src in [text, cleaned, condensed]:
        for m in re.finditer(pattern1, src):
            raw = "".join(m.groups())
            if len(raw) == 14:
                trans = raw.translate(ocr_map)
                if trans.isdigit() and trans[:2] != '00':
                    return f"{trans[0:2]}-{trans[2:6]}-{trans[6:10]}-{trans[10:14]}"
    pattern2 = r"(?<![A-Za-z0-9])([A-Za-z0-9]{14})(?![A-Za-z0-9])"
    for src in [condensed, cleaned, text]:
        for m in re.finditer(pattern2, src):
            raw = m.group(1)
            trans = raw.translate(ocr_map)
            if trans.isdigit() and trans[:2] != '00':
                return f"{trans[0:2]}-{trans[2:6]}-{trans[6:10]}-{trans[10:14]}"
    return ""

def _tamil_name_quality(cleaned, line):
    if not cleaned: return 0
    tam_chars = len(re.sub(r"[^\u0B80-\u0BFF]", "", cleaned))
    score = tam_chars * 2
    if any(tok in line for tok in _TAMIL_NAME_LABELS): score += 200
    if any(tok in line for tok in _TAMIL_NAME_NOISE_WORDS): score -= 20
    if any(tok in line for tok in _TAMIL_SECTION_WORDS): score -= 30
    tokens = cleaned.split()
    word_count = len(tokens)
    if 1 <= word_count <= 2: score += 20
    if word_count > 8: score -= 10
    if tam_chars < 2: score -= 10
    avg_len = tam_chars / word_count if word_count else 0
    if avg_len >= 3: score += 10
    if re.search(r"\d", line): score -= 30
    return score

def _clean_english_name(line):
    words = line.split()
    good  = []
    for w in words:
        cw = re.sub(r"[^A-Za-z.\-]", "", w)
        if not cw: continue
        if cw.lower() in _HEADER_WORDS: break
        if cw.lower() in _NAME_NOISE_SUFFIX and len(good) >= 1: break
        if _is_real_name_word(cw): good.append(cw if cw[0].isupper() else cw.title())
        else:
            if len(good) > 0: break
    return " ".join(good).strip()

def _collapse_broken_tamil_spacing(text):
    if not text: return text
    def collapse(match):
        tok = match.group(0)
        parts = re.split(r"[\s\-\.]+", tok)
        if len(parts) < 3: return tok
        lengths = [len(re.sub(r"[^\u0B80-\u0BFF]", "", p)) for p in parts]
        if not lengths or sum(lengths) == 0: return tok
        avg_len = sum(lengths) / len(lengths)
        if avg_len <= 4.5: return "".join(parts)
        return tok
    return re.sub(r"[\u0B80-\u0BFF]+(?:[\s\-\.]+[\u0B80-\u0BFF]+)+", collapse, text)

def _is_tamil_initial(token):
    tok = token.strip()
    base_chars = re.sub(r"[\u0BBE-\u0BCD\u0BD7]", "", tok)
    tamil_base_count = len(re.sub(r"[^\u0B80-\u0BFF]", "", base_chars))
    if tamil_base_count > 2: return False
    if tok.endswith('.') or tok.endswith('-'): return True
    if re.fullmatch(r"[\u0B80-\u0BFF]+", tok): return True
    return False

def _base_count(w):
    return len(re.sub(r"[^\u0B80-\u0BFF]", "", re.sub(r"[\u0BBE-\u0BCD\u0BD7]", "", w)))

def _clean_tamil_name(line):
    if not line: return ""
    cleaned = _strip_tamil_labels(line)
    cleaned = _collapse_broken_tamil_spacing(cleaned)
    best_score = 0; best_chunk = ""
    for match in re.findall(r"[\u0B80-\u0BFF]+(?:[\s\-\.]+[\u0B80-\u0BFF]+)+", cleaned):
        chunk = match.strip()
        if not chunk: continue
        words = [w for w in chunk.split() if w not in _TAMIL_LABEL_WORDS and w not in _TAMIL_SECTION_WORDS and w not in _TAMIL_NAME_NOISE_WORDS]
        words = [w for w in words if len(re.sub(r"[^\u0B80-\u0BFF]", "", w)) >= 1]
        if not words: continue
        if len(words) > 1:
            while len(words) > 1 and _base_count(words[0]) < 2:
                if _is_tamil_initial(words[0]): break
                words.pop(0)
            while len(words) > 1 and _base_count(words[-1]) < 2:
                if _is_tamil_initial(words[-1]): break
                words.pop()
        if not words: continue
        chunk = " ".join(words)
        chunk = re.sub(r"\s{2,}", " ", chunk).strip()
        score = len(re.sub(r"[^\u0B80-\u0BFF]", "", chunk))
        if score < 1: continue
        if score > best_score: best_score = score; best_chunk = chunk
    if best_chunk: return unicodedata.normalize("NFC", best_chunk)
    tokens = cleaned.split()
    valid = [tok for tok in tokens if re.search(r"[\u0B80-\u0BFF]", tok) and tok not in _TAMIL_LABEL_WORDS and tok not in _TAMIL_SECTION_WORDS]
    full_clean = " ".join(valid).strip()
    if full_clean: return unicodedata.normalize("NFC", full_clean)
    raw_text = " ".join(re.findall(r"[\u0B80-\u0BFF]+", cleaned)).strip()
    return unicodedata.normalize("NFC", raw_text)

def _is_valid_tamil_name_candidate(line):
    if not line: return ""
    cleaned = _clean_tamil_name(line)
    if not cleaned: return ""
    label_present = bool(re.search(r"\b(name|பெயர்|பெயா|பயர்|பெயா்|பபயர்)\b", line, re.IGNORECASE))
    min_chars = 2 if label_present else 2
    tam_count = len(re.sub(r"[^\u0B80-\u0BFF]", "", cleaned))
    if tam_count < min_chars: return ""
    # Only reject obvious address words, not common name parts
    address_words = {'முகவரி', 'விலாசம்', 'மாவட்டம்', 'மாநிலம்', 'தாலுகா', 'அஞ்சல்'}
    if any(tok in cleaned for tok in address_words): return ""
    all_tokens = cleaned.split()
    if len(all_tokens) > 1:
        filtered = [t for t in all_tokens if t not in _TAMIL_NAME_NOISE_WORDS]
        tokens = filtered if filtered else all_tokens
    else:
        tokens = all_tokens
    cleaned = " ".join(tokens).strip()
    tam_count = len(re.sub(r"[^\u0B80-\u0BFF]", "", cleaned))
    if tam_count < min_chars: return ""
    words = [w for w in cleaned.split() if re.search(r"[\u0B80-\u0BFF]", w)]
    if not words: return ""
    if len(words) > 10: return ""
    # Be more lenient - accept any word with at least 1 Tamil char
    return unicodedata.normalize("NFC", cleaned)

def _find_best_tamil_candidate(text):
    best = ""; best_score = 0
    for line in [l.strip() for l in text.split("\n") if l.strip()]:
        if not re.search(r"[\u0B80-\u0BFF]", line): continue
        candidate = _is_valid_tamil_name_candidate(line)
        if not candidate: continue
        score = _tamil_name_quality(candidate, line)
        if score > best_score: best_score = score; best = candidate
    return best

def _extract_longest_tamil_sequence(text, min_chars=2):
    if not text: return ""
    best = ""
    for seq in re.findall(r"[\u0B80-\u0BFF]+(?:[\s\-\.]+[\u0B80-\u0BFF]+)*", text):
        cleaned = _clean_tamil_name(seq)
        if not cleaned: continue
        count = len(re.sub(r"[^\u0B80-\u0BFF]", "", cleaned))
        if count < min_chars: continue
        # More lenient - don't reject based on section words in fallback
        if count > len(re.sub(r"[^\u0B80-\u0BFF]", "", best)): best = cleaned
    return unicodedata.normalize("NFC", best)

def _choose_best_tamil_name(region_name, field_name):
    if not region_name: return field_name
    if not field_name: return region_name
    region_count = len(re.sub(r"[^\u0B80-\u0BFF]", "", region_name))
    field_count = len(re.sub(r"[^\u0B80-\u0BFF]", "", field_name))
    region_score = _tamil_name_quality(region_name, region_name)
    field_score = _tamil_name_quality(field_name, field_name)
    if field_score > region_score + 15: return field_name
    if field_count > region_count + 2: return field_name
    if field_score >= region_score and field_count >= region_count: return field_name
    return region_name

def _find_tamil_name_near_label(lines):
    if not lines: return ""
    for i, line in enumerate(lines):
        if re.search(r"\b(பெயர்|பெயா|பயர்|பெயா்|பபயர்|name)\b", line, re.IGNORECASE):
            candidates = []
            if re.search(r"[\u0B80-\u0BFF]", line): candidates.append(line.strip())
            for j in range(i + 1, min(i + 5, len(lines))):
                next_line = lines[j].strip()
                if not next_line: continue
                if re.search(r"\b(address|dob|gender|mobile|முகவரி|பிறந்த|பாலினம்|abha|number)\b", next_line, re.IGNORECASE): break
                if re.search(r"[\u0B80-\u0BFF]", next_line): candidates.append(next_line); continue
                break
            if candidates:
                combined = " ".join(candidates)
                cleaned = _clean_tamil_name(combined)
                valid = _is_valid_tamil_name_candidate(cleaned)
                if valid: return valid
                fallback = _extract_longest_tamil_sequence(combined, min_chars=3)
                if fallback: return fallback
    return ""

def _extract_tamil_from_image(img):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if img.ndim == 3 else img
    thresh = _preprocess(gray, scale=2)
    texts = []
    for lang, cfg in [('tam+eng','--oem 3 --psm 6'),('tam','--oem 3 --psm 6'),('tam+eng','--oem 3 --psm 3'),('tam','--oem 3 --psm 3')]:
        text = _safe_ocr(Image.fromarray(thresh), lang=lang, config=cfg)
        if text.strip(): texts.append(text)
    combined = "\n".join(texts)
    if not combined.strip(): return ""
    candidate = _find_best_tamil_candidate(combined)
    if candidate: return candidate
    return _extract_longest_tamil_sequence(combined, min_chars=2)

def _extract_tamil_name_from_pdf_lines(pdf_lines):
    if not pdf_lines: return ""
    label_pattern = re.compile(r"(\bname\b|பெயர்|பெயா|பயர்|பெயா்|பபயர்)", re.IGNORECASE)
    stop_pattern = re.compile(r"\b(address|dob|gender|mobile|state|district|abha|name|nom|முகவரி|பிறந்த|பாலினம்)\b", re.IGNORECASE)
    for i, line in enumerate(pdf_lines):
        label_match = label_pattern.search(line)
        if not label_match: continue
        raw_tail = line[label_match.end():].strip()
        if raw_tail and re.search(r"[\u0B80-\u0BFF]", raw_tail):
            valid_tail = _is_valid_tamil_name_candidate(raw_tail)
            if valid_tail: return valid_tail
            cleaned = _clean_tamil_name(raw_tail)
            if cleaned and _is_valid_tamil_name_candidate(cleaned): return cleaned
        raw_tamil = " ".join(re.findall(r"[\u0B80-\u0BFF]+(?:[\s\-\.]+[\u0B80-\u0BFF]+)*", line))
        if raw_tamil and _is_valid_tamil_name_candidate(raw_tamil): return _is_valid_tamil_name_candidate(raw_tamil)
        tamil_lines = []
        for j in range(i + 1, min(i + 5, len(pdf_lines))):
            next_line = pdf_lines[j].strip()
            if not next_line: continue
            if stop_pattern.search(next_line): break
            if re.search(r"[\u0B80-\u0BFF]", next_line): tamil_lines.append(next_line); continue
            if tamil_lines: break
        if tamil_lines:
            combined = " ".join(tamil_lines)
            valid_combined = _is_valid_tamil_name_candidate(combined)
            if valid_combined: return valid_combined
            cleaned = _clean_tamil_name(combined)
            if cleaned and _is_valid_tamil_name_candidate(cleaned): return cleaned
    best = ""; best_score = 0
    for line in pdf_lines:
        if not re.search(r"[\u0B80-\u0BFF]", line): continue
        candidate = _is_valid_tamil_name_candidate(line)
        if not candidate: continue
        score = _tamil_name_quality(candidate, line)
        if score > best_score: best_score = score; best = candidate
    return best

def _extract_tamil_name_from_pdf_text(pdf_text, pdf_lines, eng_anchor=""):
    if not pdf_text or not pdf_text.strip(): return _extract_tamil_name_from_pdf_lines(pdf_lines)
    candidate = _extract_best_tamil_name_from_text(pdf_text, eng_anchor)
    if candidate: return candidate
    extractor_candidate = TamilNameExtractor().extract_from_text(pdf_text)
    if extractor_candidate: return extractor_candidate
    return _extract_tamil_name_from_pdf_lines(pdf_lines)


# ============================================================
#  EXTRACT NAME FROM REGION
# ============================================================
def extract_name_from_region(img):
    try:
        h, w = img.shape[:2]
        crop = img[int(h*0.01):int(h*0.55), int(w*0.05):int(w*1.0)]
        thresh = _preprocess(crop, scale=3)
        texts = []
        for lang in ['tam+eng', 'tam']:
            text = _safe_ocr(Image.fromarray(thresh), lang=lang)
            if text.strip(): texts.append(text)
        full_text = "\n".join(texts)
        lines = [l.strip() for l in full_text.split('\n') if l.strip()]
        eng_name = ""
        for line in lines:
            if re.search(r"(?i)name", line):
                parts = re.split(r"[:\-\s/\\$]+", line, 1)
                if len(parts) > 1:
                    candidate = re.sub(r"[^A-Za-z.\-\s]", "", parts[1]).strip()
                    candidate = _is_valid_english_name_candidate(candidate)
                    if candidate: eng_name = candidate; break
            elif _is_valid_english_name_candidate(line):
                eng_name = _is_valid_english_name_candidate(line); break
        tam_name = _extract_best_tamil_name_from_text(full_text, eng_name)
        if not tam_name:
            tam_name = TamilNameExtractor().extract_from_text(full_text)
        if not tam_name:
            best_candidate = _find_best_tamil_candidate(full_text)
            if best_candidate: tam_name = best_candidate
        # Direct fallback: extract any Tamil text with 2+ chars
        if not tam_name:
            tamil_matches = re.findall(r"[\u0B80-\u0BFF]{2,}", full_text)
            if tamil_matches:
                tam_name = max(tamil_matches, key=len)
        return eng_name, tam_name, []
    except Exception as e:
        print(f"[NAME ERROR] {e}")
        traceback.print_exc()
        return "", "", []
def extract_other_fields(img):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    text = pytesseract.image_to_string(thresh, lang='tam+eng', config='--psm 6')
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    full  = " ".join(lines)
    abha = mobile = dob = ""
    abha = _extract_abha_from_text(full)
    if not abha:
        condensed = re.sub(r'(\d)\s+(\d)', r'\1\2', full)
        abha = _extract_abha_from_text(condensed)
    if not abha: abha = _extract_abha_from_text(full.translate(_ABHA_LETTER_MAP))
    abha_digits = re.sub(r"\D", "", abha)
    dob = ""
    dob_digits = ""
    m = re.search(r"(\d{2})[-/\.]?(\d{2})[-/\.]?(\d{4})", full)
    if m:
        d, mo, y = m.groups()
        dob = f"{d}-{mo}-{fix_year_misread(y)}"
        dob_digits = re.sub(r"\D", "", dob)
    mobile = _extract_mobile_from_text(full, abha_digits, dob_digits)
    if not mobile:
        digit_config = '--psm 6 -c tessedit_char_whitelist=0123456789'
        mobile_text = pytesseract.image_to_string(thresh, lang='eng', config=digit_config)
        mobile = _extract_mobile_from_text(mobile_text, abha_digits, dob_digits)
    return abha, mobile, dob

# ============================================================
#  EXTRACT OTHER FIELDS
# ============================================================
def extract_other_fields(img):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    text = pytesseract.image_to_string(thresh, lang='tam+eng', config='--psm 6')
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    full  = " ".join(lines)
    abha = mobile = dob = ""
    abha = _extract_abha_from_text(full)
    if not abha:
        condensed = re.sub(r'(\d)\s+(\d)', r'\1\2', full)
        abha = _extract_abha_from_text(condensed)
    if not abha: abha = _extract_abha_from_text(full.translate(_ABHA_LETTER_MAP))
    abha_digits = re.sub(r"\D", "", abha)
    dob = ""
    dob_digits = ""
    m = re.search(r"(\d{2})[-/\.]?(\d{2})[-/\.]?(\d{4})", full)
    if m:
        d, mo, y = m.groups()
        dob = f"{d}-{mo}-{fix_year_misread(y)}"
        dob_digits = re.sub(r"\D", "", dob)
    mobile = _extract_mobile_from_text(full, abha_digits, dob_digits)
    if not mobile:
        digit_config = '--psm 6 -c tessedit_char_whitelist=0123456789'
        mobile_text = pytesseract.image_to_string(thresh, lang='eng', config=digit_config)
        mobile = _extract_mobile_from_text(mobile_text, abha_digits, dob_digits)
    return abha, mobile, dob

def fix_year_misread(year):
    try:
        yi = int(year)
        cy = datetime.now().year
        if 1950 <= yi <= cy: return str(yi)
        for i in range(len(year)):
            tmp = list(year)
            if tmp[i] == '0':
                tmp[i] = '9'
                cand = "".join(tmp)
                if cand.isdigit() and 1950 <= int(cand) <= cy: return cand
    except Exception: pass
    return year

def _simple_extract_tamil(text):
    """Old-code-style direct Tamil extraction — high reliability, no over-filtering."""
    if not text: return ""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    best = ""
    best_chars = 0
    for line in lines:
        if re.search(r"\d{5,}", line): continue
        if any(x in line.lower() for x in [
            "address","dob","gender","mobile","abha number",
            "pincode","district","state","pin code"
        ]): continue
        if any(tok in line for tok in {
            'முகவரி','விலாசம்','மாவட்டம்','மாநிலம்',
            'கைபேசி','பிறந்த','பாலினம்','தாலுகா','அஞ்சல்'
        }): continue
        # Pull out only Tamil characters + spaces
        tamil_only = re.sub(r"[^\u0B80-\u0BFF\s]", "", line).strip()
        count = len(re.sub(r"\s", "", tamil_only))
        if count >= 3 and count > best_chars:
            best = tamil_only
            best_chars = count
    return unicodedata.normalize("NFC", best) if best else ""

def extract_all_fields(img):
    h, w = img.shape[:2]
    img = img[:, :int(w * 0.72)]
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    pil  = Image.fromarray(gray)
    text = _safe_ocr(pil, lang=_LANG_ALL, config=_CFG_BEST)
    text_tam = _safe_ocr(pil, lang=_LANG_TA, config=_CFG_BEST)
    text_mal = _safe_ocr(pil, lang=_LANG_ML, config=_CFG_BEST)
    text_hin = _safe_ocr(pil, lang=_LANG_HI, config=_CFG_BEST)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if text_tam.strip():
        for line in [l.strip() for l in text_tam.split("\n") if l.strip()]:
            if line not in lines: lines.append(line)
    if text_mal.strip():
        for line in [l.strip() for l in text_mal.split("\n") if l.strip()]:
            if line not in lines: lines.append(line)
    if text_hin.strip():
        for line in [l.strip() for l in text_hin.split("\n") if l.strip()]:
            if line not in lines: lines.append(line)
    full = " ".join(lines)
    abha = _extract_abha_from_text(full)
    if not abha:
        condensed = re.sub(r'(\d)\s+(\d)', r'\1\2', full)
        abha = _extract_abha_from_text(condensed)
    if not abha: abha = _extract_abha_from_text(full.translate(_ABHA_LETTER_MAP))
    full_num_fixed = full.translate(num_map)
    abha_digits = re.sub(r"\D", "", abha)
    dob = ""
    for src in [full, full_num_fixed]:
        m = re.search(r"(\d{2})[-/\.](\d{2})[-/\.](\d{4})", src)
        if m:
            d, mo2, y = m.groups()
            dob = f"{d}-{mo2}-{fix_year_misread(y)}"; break
    dob_digits = re.sub(r"\D", "", dob)
    mobile = ""
    for src in [full, full_num_fixed]:
        pattern = r"(?:^|[^\d])((?:(?:91|\+91)[\s\-]*)?[6789](?:[\s\-]*\d){9})(?:[^\d]|$)"
        for cand_raw in re.findall(pattern, src):
            cand = re.sub(r"\D", "", cand_raw)
            if len(cand) == 12 and cand.startswith("91"): cand = cand[2:]
            if len(cand) == 10 and cand[0] in "6789":
                if cand not in abha_digits and cand not in dob_digits:
                    mobile = cand; break
        if mobile: break
    address = ""
    for i, line in enumerate(lines):
        if "abha address" in line.lower() or "முகவரி" in line:
            for j in range(i+1, min(i+4, len(lines))):
                if any(x in lines[j].lower() for x in ["mobile","dob","abha number","gender"]): break
                address = lines[j]; break
            break
    if not address:
        m = re.search(r"[\w.]+\s*@\s*abdm", full, re.IGNORECASE)
        if m: address = m.group()
    if address: address = re.sub(r"\s+@\s*", "@", address).strip()
    gender = ""
    tl = full.lower()
    if "female" in tl: gender = "Female"
    elif "male" in tl: gender = "Male"
    elif "\u0baa\u0bc6\u0ba3\u0bcd" in full: gender = "Female"
    elif "\u0b86\u0ba3\u0bcd" in full: gender = "Male"
    eng_ocr = ""
    best_tam = ""
    best_tam_score = 0
    best_raw_tam = ""
    best_raw_score = 0
    found_eng_label = False
    past_name_block = False
    all_tamil_candidates = []
    for line in lines:
        ll = line.lower().strip()
        if re.search(r"\b(name|பெயர்)\b", ll):
            found_eng_label = True
            parts = re.split(r"[:\-–/\\]", line, maxsplit=1)
            inline = parts[1].strip() if len(parts) > 1 else re.sub(r"\bname\b|பெயர்|/|\\", "", line, flags=re.IGNORECASE).strip()
            if inline:
                if re.search(r"[\u0B80-\u0BFF]", inline) and not past_name_block:
                    cleaned = _is_valid_tamil_name_candidate(inline)
                    if cleaned:
                        score = _tamil_name_quality(cleaned, inline) + 200
                        all_tamil_candidates.append((cleaned, score))
                        if score > best_tam_score: best_tam_score = score; best_tam = cleaned
                if not re.search(r"[\u0B80-\u0BFF]|\d", inline):
                    candidate = _is_valid_english_name_candidate(inline)
                    if candidate and not eng_ocr: eng_ocr = candidate
            continue
        if any(x in ll for x in ["address","dob","gender","mobile","முகவரி","பிறந்த","பாலினம்","கைபேசி"]):
            past_name_block = True
        if re.search(r"[\u0B80-\u0BFF]", line):
            raw_score = len(re.sub(r"[^\u0B80-\u0BFF]", "", line))
            if raw_score > best_raw_score: best_raw_score = raw_score; best_raw_tam = _clean_tamil_name(line)
            cleaned = _is_valid_tamil_name_candidate(line)
            if cleaned:
                score = _tamil_name_quality(cleaned, line)
                if past_name_block: score -= 40
                all_tamil_candidates.append((cleaned, score))
                if score > best_tam_score: best_tam_score = score; best_tam = cleaned
            elif not best_tam:
                raw_cleaned = _clean_tamil_name(line)
                if raw_cleaned and len(re.sub(r"[^\u0B80-\u0BFF]", "", raw_cleaned)) >= 3: best_tam = raw_cleaned
            continue
        if re.search(r"\d", line): continue
        if not eng_ocr:
            candidate = _is_valid_english_name_candidate(line)
            if candidate: eng_ocr = candidate; continue
        if found_eng_label and not eng_ocr and not past_name_block:
            if _NAME_STOP.search(ll): found_eng_label = False; continue
            candidate = _is_valid_english_name_candidate(line)
            if candidate: eng_ocr = candidate
    combined_text = "\n".join(lines)
    if text_tam.strip(): combined_text += "\n" + text_tam
    label_tam = _extract_best_tamil_name_from_text(combined_text, eng_ocr)
    if label_tam:
        score = _tamil_name_quality(label_tam, label_tam) + 220
        all_tamil_candidates.append((label_tam, score))
        if not best_tam or score >= best_tam_score: best_tam_score = score; best_tam = label_tam
    if not best_tam:
        tamil_extractor_candidate = TamilNameExtractor().extract_from_text(combined_text)
        if tamil_extractor_candidate:
            score = _tamil_name_quality(tamil_extractor_candidate, tamil_extractor_candidate) + 200
            all_tamil_candidates.append((tamil_extractor_candidate, score))
            if not best_tam or score >= best_tam_score: best_tam_score = score; best_tam = tamil_extractor_candidate
    label_near = _find_tamil_name_near_label(lines)
    if label_near:
        score = _tamil_name_quality(label_near, label_near) + 200
        all_tamil_candidates.append((label_near, score))
        if not best_tam or score >= best_tam_score: best_tam_score = score; best_tam = label_near
    elif not best_tam and best_raw_tam: best_tam = best_raw_tam
    if not best_tam:
        fallback_longest = _extract_longest_tamil_sequence(text + "\n" + text_tam + "\n" + full, min_chars=4)
        if fallback_longest:
            best_tam = fallback_longest
            all_tamil_candidates.append((fallback_longest, _tamil_name_quality(fallback_longest, fallback_longest)))
    if not best_tam:
        image_fallback = _extract_tamil_from_image(img)
        if image_fallback:
            best_tam = image_fallback
            all_tamil_candidates.append((image_fallback, _tamil_name_quality(image_fallback, image_fallback)))
    # PRIMARY: simple direct extraction (old-code reliability)
    simple_tam = _simple_extract_tamil(combined_text)

    if simple_tam:
        # Simple extraction found something — trust it
        tam_ocr = simple_tam
    elif best_tam:
        # Fall back to complex pipeline result
        if all_tamil_candidates and eng_ocr:
            phonetic_best = _select_best_tamil_name_with_english(
                all_tamil_candidates, eng_ocr, phonetic_weight=0.65)
            if phonetic_best:
                tam_ocr = phonetic_best
            else:
                tam_ocr = best_tam
        else:
            tam_ocr = best_tam
    else:
        tam_ocr = ""
    return abha, mobile, dob, address, gender, eng_ocr, tam_ocr


def detect_photo(img):
    h, w   = img.shape[:2]
    region = img[int(h*0.15):int(h*0.30), int(w*0.05):int(w*0.20)]
    return region if region is not None and region.size > 0 else None


# ============================================================
#  STATE & DISTRICT EXTRACTION
# ============================================================
_KNOWN_STATES = {
    "andhra pradesh","arunachal pradesh","assam","bihar","chhattisgarh",
    "goa","gujarat","haryana","himachal pradesh","jharkhand","karnataka",
    "kerala","madhya pradesh","maharashtra","manipur","meghalaya","mizoram",
    "nagaland","odisha","punjab","rajasthan","sikkim","tamil nadu",
    "telangana","tripura","uttar pradesh","uttarakhand","west bengal",
    "andaman and nicobar","chandigarh","dadra and nagar haveli",
    "daman and diu","delhi","jammu and kashmir","ladakh","lakshadweep",
    "puducherry",
}
_STATE_LGD = {
    "ANDHRA PRADESH":"28","ARUNACHAL PRADESH":"12","ASSAM":"18","BIHAR":"10",
    "CHHATTISGARH":"22","GOA":"30","GUJARAT":"24","HARYANA":"06",
    "HIMACHAL PRADESH":"02","JHARKHAND":"20","KARNATAKA":"29","KERALA":"32",
    "MADHYA PRADESH":"23","MAHARASHTRA":"27","MANIPUR":"14","MEGHALAYA":"17",
    "MIZORAM":"15","NAGALAND":"13","ODISHA":"21","PUNJAB":"03","RAJASTHAN":"08",
    "SIKKIM":"11","TAMIL NADU":"33","TELANGANA":"36","TRIPURA":"16",
    "UTTAR PRADESH":"09","UTTARAKHAND":"05","WEST BENGAL":"19",
    "ANDAMAN AND NICOBAR":"35","CHANDIGARH":"04","DADRA AND NAGAR HAVELI":"26",
    "DAMAN AND DIU":"25","DELHI":"07","JAMMU AND KASHMIR":"01","LADAKH":"37",
    "LAKSHADWEEP":"31","PUDUCHERRY":"34",
}
_DISTRICT_LGD = {
    "ARIYALUR":"572","CHENGALPATTU":"770","CHENNAI":"571","COIMBATORE":"573",
    "CUDDALORE":"574","DHARMAPURI":"575","DINDIGUL":"576","ERODE":"577",
    "KALLAKURICHI":"771","KANCHEEPURAM":"578","KANYAKUMARI":"579","KARUR":"580",
    "KRISHNAGIRI":"581","MADURAI":"582","MAYILADUTHURAI":"772","NAGAPATTINAM":"583",
    "NAMAKKAL":"584","NILGIRIS":"585","THE NILGIRIS":"587","PERAMBALUR":"586",
    "PUDUKKOTTAI":"588","RAMANATHAPURAM":"589","RANIPET":"773","SALEM":"590",
    "SIVAGANGA":"591","TENKASI":"774","THANJAVUR":"592","THENI":"593",
    "THOOTHUKUDI":"594","TIRUCHIRAPPALLI":"595","TIRUNELVELI":"596",
    "TIRUPATHUR":"775","TIRUPPUR":"776","TIRUVALLUR":"597","TIRUVANNAMALAI":"598",
    "TIRUVARUR":"599","VELLORE":"600","VILUPPURAM":"601","VIRUDHUNAGAR":"602",
}

def _get_state_lgd(state_name): return _STATE_LGD.get(state_name.strip().upper(), "")
def _get_district_lgd(district_name): return _DISTRICT_LGD.get(district_name.strip().upper(), "")

def _clean_location_value(val):
    if not val: return ""
    val = re.sub(r"[\d@#$%&*|\\/<>]", "", val)
    val = val.strip(" .,:-/")
    if len(val) < 3 or len(val) > 50: return ""
    return val.title().strip()

def extract_state_district(img, page=None):
    state = district = ""
    if page is not None:
        try:
            pdf_text = page.get_text("text")
            lines    = [l.strip() for l in pdf_text.split("\n") if l.strip()]
            for i, line in enumerate(lines):
                ll = line.lower()
                if not state and ("state" in ll or "மாநிலம்" in line or "மாநில" in line):
                    parts = re.split(r"[:\-–]", line, maxsplit=1)
                    val = parts[1].strip() if len(parts) > 1 else ""
                    if not val and i + 1 < len(lines): val = lines[i + 1]
                    val = _clean_location_value(val)
                    skip_words = {"district","mobile","dob","abha","address","number","gender","name"}
                    if val and not any(x in val.lower() for x in skip_words): state = val
                if not district and ("district" in ll or "மாவட்டம்" in line or "மாவட்ட" in line):
                    parts = re.split(r"[:\-–]", line, maxsplit=1)
                    val = parts[1].strip() if len(parts) > 1 else ""
                    if not val and i + 1 < len(lines): val = lines[i + 1]
                    val = _clean_location_value(val)
                    skip_words = {"state","mobile","dob","abha","address","number","gender","name"}
                    if val and not any(x in val.lower() for x in skip_words): district = val
                if state and district: break
            if not state:
                m = re.search(r"state\s*[:\-]\s*([A-Za-z ]{3,30})", pdf_text, re.IGNORECASE)
                if m: state = _clean_location_value(m.group(1))
            if not district:
                m = re.search(r"district\s*[:\-]\s*([A-Za-z ]{3,30})", pdf_text, re.IGNORECASE)
                if m: district = _clean_location_value(m.group(1))
            if state and district: return state, district
        except Exception as e:
            print(f"[WARN] Native state/district extract: {e}")
    try:
        gray  = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        text  = pytesseract.image_to_string(Image.fromarray(gray), lang=_LANG_EN_TA, config=_CFG_FAST)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for i, line in enumerate(lines):
            ll = line.lower()
            if not state and ("state" in ll or "மாநிலம்" in line or "மாநில" in line):
                parts = re.split(r"[:\-–]", line, maxsplit=1)
                val = parts[1].strip() if len(parts) > 1 else ""
                if not val and i + 1 < len(lines): val = lines[i + 1]
                val = _clean_location_value(val)
                if val and len(val) > 3:
                    skip_words = {"district","mobile","dob","abha","address","gender"}
                    if not any(x in val.lower() for x in skip_words): state = val
            if not district and ("district" in ll or "மாவட்டம்" in line or "மாவட்ட" in line):
                parts = re.split(r"[:\-–]", line, maxsplit=1)
                val = parts[1].strip() if len(parts) > 1 else ""
                if not val and i + 1 < len(lines): val = lines[i + 1]
                val = _clean_location_value(val)
                if val and len(val) > 3:
                    skip_words = {"state","mobile","dob","abha","address","gender"}
                    if not any(x in val.lower() for x in skip_words): district = val
            if state and district: break
        full_ocr = " ".join(lines)
        if not state:
            m = re.search(r"state\s*[:\-]\s*([A-Za-z ]{3,30})", full_ocr, re.IGNORECASE)
            if m: state = _clean_location_value(m.group(1))
        if not district:
            m = re.search(r"district\s*[:\-]\s*([A-Za-z ]{3,30})", full_ocr, re.IGNORECASE)
            if m: district = _clean_location_value(m.group(1))
    except Exception as e:
        print(f"[WARN] OCR state/district: {e}")
    return state, district


# ============================================================
#  PHYSICAL ADDRESS EXTRACTION
# ============================================================
def _extract_phys_addr_from_lines(lines):
    ADDR_LABEL = re.compile(
        r"(address|முகவரி|வசிப்பிட|permanent|residential|present|"
        r"house|village|town|pincode|pin\s*code|taluk|mandal|block|ward)",
        re.IGNORECASE)
    STOP = re.compile(
        r"(mobile|dob|abha\s*number|gender|date\s*of\s*birth|"
        r"abha\s*address|@abdm|hidn|\bhid\b)", re.IGNORECASE)
    for i, line in enumerate(lines):
        if "@abdm" in line.lower() or "abha address" in line.lower(): continue
        m = ADDR_LABEL.search(line)
        if not m: continue
        inline_val = line[m.end():].strip(" :,-–")
        parts = []
        if inline_val and len(inline_val) > 2 and "@abdm" not in inline_val.lower():
            parts.append(inline_val)
        for j in range(i + 1, min(i + 7, len(lines))):
            nxt = lines[j].strip()
            if not nxt: continue
            if STOP.search(nxt) or "@abdm" in nxt.lower(): break
            if re.match(r"^[A-Z\s]{2,20}:\s*$", nxt): break
            if len(nxt) > 2: parts.append(nxt)
        if parts: return ", ".join(parts).strip(", ")
    return ""

def _extract_phys_addr_pincode_fallback(lines):
    STOP = re.compile(r"(mobile|dob|abha|gender|date\s*of\s*birth|@abdm|name|பெயர்)", re.IGNORECASE)
    for i, line in enumerate(lines):
        if re.search(r"\b[1-9]\d{5}\b", line) and "@abdm" not in line.lower():
            start = max(0, i - 4)
            chunk = []
            for ln in lines[start: i + 2]:
                if STOP.search(ln) or "@abdm" in ln.lower(): continue
                if len(ln) > 2 and not re.match(r"^\d{2}[-/.]\d{2}[-/.]\d{4}$", ln):
                    chunk.append(ln)
            if chunk: return ", ".join(chunk).strip(", ")
    return ""

def extract_physical_address(img, page=None):
    if page is not None:
        try:
            pdf_text = page.get_text("text")
            lines    = [l.strip() for l in pdf_text.split("\n") if l.strip()]
            addr     = _extract_phys_addr_from_lines(lines)
            if addr: return addr
        except Exception as e:
            print(f"[WARN] Physical address PDF extract: {e}")
    try:
        gray  = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        text  = pytesseract.image_to_string(Image.fromarray(gray), lang=_LANG_EN_TA, config=_CFG_FAST)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        addr  = _extract_phys_addr_from_lines(lines)
        if addr: return addr
    except Exception as e:
        print(f"[WARN] Physical address OCR: {e}")
    try:
        if page is not None:
            all_text = page.get_text("text")
        else:
            gray     = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            all_text = pytesseract.image_to_string(Image.fromarray(gray), lang=_LANG_EN_TA, config=_CFG_FAST)
        all_lines = [l.strip() for l in all_text.split("\n") if l.strip()]
        addr      = _extract_phys_addr_pincode_fallback(all_lines)
        if addr: return addr
    except Exception as e:
        print(f"[WARN] Pincode heuristic: {e}")
    return ""


# ============================================================
#  QR PIPELINE
# ============================================================
def _decode_qr_from_array(img_rgb):
    d = cv2.QRCodeDetector()
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    data, pts, _ = d.detectAndDecode(img_bgr)
    if data: return data
    h, w = img_bgr.shape[:2]
    scale = 1000.0 / max(w, h)
    if scale < 1.0:
        small = cv2.resize(img_bgr, (0, 0), fx=scale, fy=scale)
        data, pts, _ = d.detectAndDecode(small)
        if data: return data
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    data, pts, _ = d.detectAndDecode(cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR))
    if data: return data
    return None

def read_qr_from_rendered_image(img_rgb):
    raw = _decode_qr_from_array(img_rgb)
    if not raw: return None
    try: return json.loads(raw)
    except: return {"raw": raw}

def read_qr_from_pdf_page(page):
    d = cv2.QRCodeDetector()
    try: images = page.get_images(full=True)
    except: return None
    for img_info in images:
        xref = img_info[0]
        try: base = page.parent.extract_image(xref)
        except: continue
        if not base or "image" not in base: continue
        img_bytes = base["image"]
        q_img = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
        if q_img is None: continue
        h_q, w_q = q_img.shape[:2]
        if not (0.7 <= w_q / h_q <= 1.3) or w_q < 50: continue
        data, pts, _ = d.detectAndDecode(q_img)
        if not data:
            gray = cv2.cvtColor(q_img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            data, pts, _ = d.detectAndDecode(cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR))
        if data:
            try: return json.loads(data)
            except: return {"raw": data}
    return None

def _qr_physical_address(qr_data_dict):
    for key in ("address", "phr", "careContext", "care_context", "permanentAddress"):
        val = (qr_data_dict.get(key) or "").strip()
        if val and "@abdm" not in val.lower() and len(val) > 5: return val
    return ""

def build_qr_data_from_fields(name, abha, mobile, dob, address, gender,
                               state_name="", district_name="", physical_address=""):
    eng = name[0] if name and len(name) > 0 else ""
    hid = re.sub(r"\s+@\s*", "@", address).strip() if address else ""
    return {
        "hidn": abha, "hid": hid, "name": eng,
        "gender": gender[0].upper() if gender else "",
        "statelgd": _get_state_lgd(state_name),
        "distlgd": _get_district_lgd(district_name),
        "dob": dob, "district_name": district_name, "mobile": mobile,
        "address": physical_address if physical_address else "",
        "state_name": state_name if state_name else "TAMIL NADU",
    }

def generate_qr_image(data_dict):
    payload = json.dumps(data_dict, ensure_ascii=False, separators=(',', ':'))
    qr_obj = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=10, border=2)
    qr_obj.add_data(payload)
    qr_obj.make(fit=True)
    pil_img = qr_obj.make_image(fill_color="black", back_color="white").convert("RGB")
    return np.array(pil_img)


# ============================================================
#  BUILD CARD
# ============================================================
def build_card(name, abha, mobile, dob, address, gender, photo, qr,
               use_background=None, bg_index=1, card_lang=""):
    card_w = 2700; card_h = 1700; ZM = card_w / 1011

    if use_background is None:
        use_background = _bg_enabled_state

    if use_background:
        bg_pil = _get_background_image(card_w, card_h, bg_index=bg_index)
        pil = bg_pil.copy()
    else:
        pil = Image.fromarray(np.ones((card_h, card_w, 3), dtype=np.uint8) * 255)

    if photo is not None and photo.size > 0:
        try:
            ph, pw = photo.shape[:2]
            scale = min((250 * ZM) / pw, (250 * ZM) / ph)
            nw, nh = int(pw * scale), int(ph * scale)
            pil.paste(Image.fromarray(cv2.resize(photo, (nw, nh))), (int(10 * ZM), int(180 * ZM)))
        except Exception as e:
            print(f"[WARN] photo paste: {e}")
    if qr is not None:
        try:
            qr_pil = Image.fromarray(qr)
            qr_size = int(280 * ZM)
            qr_pil = qr_pil.resize((qr_size, qr_size), Image.NEAREST)
            qr_x = card_w - qr_size - int(20 * ZM)
            qr_y = int(175 * ZM)
            pil.paste(qr_pil, (qr_x, qr_y))
        except Exception as e:
            print(f"[QR ERROR] {e}")
    draw = ImageDraw.Draw(pil)
    FS = int(30 * ZM); FSL = int(26 * ZM)
    _native_fs     = int(_native_name_font_size[0] * ZM)
    font_tam       = load_tamil_font(FS);       font_taml  = load_tamil_font(FSL)
    font_mal       = load_malayalam_font(FS);   font_mall  = load_malayalam_font(FSL)
    font_tam_name  = load_tamil_font(_native_fs)
    font_mal_name  = load_malayalam_font(_native_fs)
    font_eng       = load_english_font(FS);     font_engs  = load_english_font(int(28 * ZM))
    eng, tam  = name
    is_hindi = card_lang == "Hindi"
    if card_lang == "Malayalam":
        is_malayalam = True
    elif card_lang == "Tamil":
        is_malayalam = False
    else:
        is_malayalam = _has_malayalam(tam)
    if is_hindi:
        is_malayalam = False
    if is_hindi:
        font_hi       = load_hindi_font(FS)
        font_hil      = load_hindi_font(FSL)
        font_hi_name  = load_hindi_font(_native_fs)
        font_native   = font_hi
        font_nativel  = font_hil
    elif is_malayalam:
        font_native  = font_mal
        font_nativel = font_mall
    else:
        font_native  = font_tam
        font_nativel = font_taml

    # ── Pick correct font FILE PATH for image-level rendering ──
    _native_font_path = _MALAYALAM_FONT_PATH if is_malayalam else _TAMIL_FONT_PATH

    # All text black
    TEXT_COL  = (20, 20, 20)
    LABEL_COL = (20, 20, 20)

    if is_hindi:
        _GENDER_NATIVE = {"Male": "पुरुष", "Female": "महिला", "Other": "अन्य"}
        label_name    = "Name / नाम"
        label_abha    = "ABHA Number / आभा संख्या"
        label_address = "Abha Address / आभा पता"
        label_mobile  = "Mobile / मोबाइल"
        label_dob     = "DOB / जन्म तिथि"
        label_gender  = "Gender / लिंग"
        _native_font_path = _HINDI_FONT_PATH
    elif is_malayalam:
        _GENDER_NATIVE = {"Male": "പുരുഷൻ", "Female": "സ്ത്രീ", "Other": "മറ്റുള്ളവ"}
        label_name    = "Name / പേര്"
        label_abha    = "ABHA Number / അഭ നമ്പർ"
        label_address = "Abha Address / അഭ വിലാസം"
        label_mobile  = "Mobile / മൊബൈൽ"
        label_dob     = "DOB / ജനന തീയതി"
        label_gender  = "Gender / ലിംഗം"
    else:
        _GENDER_NATIVE = {"Male": "ஆண்", "Female": "பெண்", "Other": "மற்றவை"}
        label_name    = "Name / பெயர்"
        label_abha    = "ABHA Number / அபா எண்"
        label_address = "Abha Address / அபா முகவரி"
        label_mobile  = "Mobile / கைபேசி"
        label_dob     = "DOB / பிறந்த தேதி"
        label_gender  = "Gender / பாலினம்"

    draw_tamil(draw, (int(250*ZM), int(200*ZM)), label_name,
               font=font_nativel, fill=LABEL_COL,
               card_image=pil, font_path=_native_font_path)

    draw.text((int(250*ZM), int(224*ZM)), eng or "-", font=font_eng, fill=TEXT_COL)

    if is_hindi:
        font_native_name = load_hindi_font(_native_fs)
    elif is_malayalam:
        font_native_name = font_mal_name
    else:
        font_native_name = font_tam_name
    draw_tamil(draw, (int(250*ZM), int(255*ZM)), tam or "",
           font=font_native_name, fill=TEXT_COL,
           card_image=pil, font_path=_native_font_path)

    draw_tamil(draw, (int(250*ZM), int(305*ZM)), label_abha,
               font=font_nativel, fill=LABEL_COL,
               card_image=pil, font_path=_native_font_path)

    draw.text((int(250*ZM), int(333*ZM)), abha or "-", font=font_eng, fill=TEXT_COL)

    draw_tamil(draw, (int(250*ZM), int(378*ZM)), label_address,
               font=font_nativel, fill=LABEL_COL,
               card_image=pil, font_path=_native_font_path)

    draw.text((int(250*ZM), int(406*ZM)), address or "-", font=font_engs, fill=TEXT_COL)

    draw_tamil(draw, (int(720*ZM), int(530*ZM)), label_mobile,
               font=font_nativel, fill=LABEL_COL,
               card_image=pil, font_path=_native_font_path)

    draw.text((int(720*ZM), int(558*ZM)), mobile or "-", font=font_eng, fill=TEXT_COL)

    draw_tamil(draw, (int(360*ZM), int(530*ZM)), label_dob,
               font=font_nativel, fill=LABEL_COL,
               card_image=pil, font_path=_native_font_path)

    draw.text((int(360*ZM), int(558*ZM)), dob or "-", font=font_eng, fill=TEXT_COL)

    draw_tamil(draw, (int(20*ZM), int(530*ZM)), label_gender,
               font=font_nativel, fill=LABEL_COL,
               card_image=pil, font_path=_native_font_path)

    gender_native = _GENDER_NATIVE.get(gender, "")
    gender_display = f"{gender} / " if gender else "- "
    draw.text((int(20*ZM), int(558*ZM)), gender_display, font=font_eng, fill=TEXT_COL)
    try:
        eng_bbox = draw.textbbox((int(20*ZM), int(558*ZM)), gender_display, font=font_eng)
        tam_x = eng_bbox[2]
    except Exception:
        tam_x = int(800*ZM)

    draw_tamil(draw, (tam_x, int(558*ZM)), gender_native,
               font=font_native, fill=TEXT_COL,
               card_image=pil, font_path=_native_font_path)

    # ── TRIAL watermark ───────────────────────────────────
    if _is_demo_mode():
        import math
        wm_font = load_english_font(int(110 * ZM))
        wm_text = "TRIAL"
        wm_layer = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        wm_draw  = ImageDraw.Draw(wm_layer)
        try:
            bbox = wm_draw.textbbox((0, 0), wm_text, font=wm_font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except AttributeError:
            tw, th = wm_draw.textsize(wm_text, font=wm_font)
        wm_draw.text(
            ((card_w - tw) // 2, (card_h - th) // 2),
            wm_text, font=wm_font, fill=(0, 0, 0, 80)
        )
        angle = math.degrees(math.atan2(card_h, card_w))
        wm_layer = wm_layer.rotate(angle, expand=False)
        pil = pil.convert("RGBA")
        pil = Image.alpha_composite(pil, wm_layer)
        pil = pil.convert("RGB")
    return np.array(pil)


def _rebuild_card_from_fields(fields, photo, qr, use_background=None, bg_index=1):
    name = (fields.get("name_eng", ""), fields.get("name_tam", ""))
    return build_card(
        name, fields.get("abha", ""), fields.get("mobile", ""),
        fields.get("dob", ""), fields.get("address", ""),
        fields.get("gender", ""), photo, qr,
        use_background=use_background, bg_index=bg_index,
        card_lang=fields.get("_card_lang", "")
    )



# ============================================================
#  CORE PROCESSOR
# ============================================================
def _process_image(img, page=None):
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        f_name      = ex.submit(extract_name_from_region, img)
        f_fields    = ex.submit(extract_all_fields, img)
        f_loc       = ex.submit(extract_state_district, img, page)
        f_phys_addr = ex.submit(extract_physical_address, img, page)
        name_result                                            = f_name.result()
        abha, mobile, dob, address, gender, eng_ocr, tam_ocr  = f_fields.result()
        state_name, district_name                              = f_loc.result()
        physical_address                                       = f_phys_addr.result()
    if len(name_result) == 3: eng_name, tam_name, region_candidates = name_result
    else: eng_name, tam_name = name_result; region_candidates = []
    if not eng_name and eng_ocr: eng_name = eng_ocr
    all_candidates = list(region_candidates)
    if tam_ocr: all_candidates.append((tam_ocr, _tamil_name_quality(tam_ocr, tam_ocr)))
    if tam_name and tam_name != tam_ocr: all_candidates.append((tam_name, _tamil_name_quality(tam_name, tam_name)))
    if all_candidates and eng_name:
        tam_candidate = _select_best_tamil_name_with_english(
            all_candidates, eng_name, phonetic_weight=0.7)
        if tam_candidate:
            tam_name = tam_candidate
        # Do NOT blank out tam_name if phonetic fails — keep what we found
    elif tam_ocr:
        tam_name = _choose_best_tamil_name(tam_name, tam_ocr)
    if not tam_name:
        image_fallback = _extract_tamil_from_image(img)
        if image_fallback:
            tam_name = image_fallback  # removed _is_plausible_tamil_name gate
    if not eng_name and address:
        derived = _name_from_abha_address(address)
        if derived: eng_name = derived
    name = (eng_name, tam_name)
    photo = detect_photo(img)
    qr_data_dict = None
    if page is not None:
        qr_data_dict = read_qr_from_pdf_page(page)
    if qr_data_dict is None:
        qr_data_dict = read_qr_from_rendered_image(img)
    if qr_data_dict and "raw" not in qr_data_dict:
        if not abha and qr_data_dict.get("hidn"):
            raw = re.sub(r"\D", "", qr_data_dict["hidn"])
            if len(raw) == 14 and raw.isdigit() and raw[:2] != "00":
                abha = f"{raw[0:2]}-{raw[2:6]}-{raw[6:10]}-{raw[10:14]}"
        if qr_data_dict.get("mobile"): mobile = re.sub(r"\D", "", qr_data_dict["mobile"])[-10:]
        if qr_data_dict.get("dob"): dob = qr_data_dict["dob"]
        if qr_data_dict.get("gender"):
            g = qr_data_dict["gender"].upper()
            gender = "Male" if g == "M" else "Female" if g == "F" else qr_data_dict["gender"]
        if qr_data_dict.get("name"):
            eng_name = qr_data_dict["name"]
            if all_candidates:
                tam_candidate = _select_best_tamil_name_with_english(all_candidates, eng_name, phonetic_weight=0.6)
                if tam_candidate:
                                tam_name = tam_candidate
                            # keep existing tam_name if no better candidate found
            name = (eng_name, tam_name)
        if not state_name and qr_data_dict.get("state_name"): state_name = qr_data_dict["state_name"]
        if not district_name and qr_data_dict.get("district_name"): district_name = qr_data_dict["district_name"]
        if not address and qr_data_dict.get("hid"): address = re.sub(r"\s+@\s*", "@", qr_data_dict["hid"]).strip()
        qr_phys = _qr_physical_address(qr_data_dict)
        if qr_phys: physical_address = qr_phys
    if not state_name: state_name = "TAMIL NADU"
    qr_data_dict = build_qr_data_from_fields(name, abha, mobile, dob, address, gender,
                                              state_name=state_name, district_name=district_name,
                                              physical_address=physical_address)
    qr_image = generate_qr_image(qr_data_dict)
    fields = {
        "name_eng": name[0], "name_tam": name[1], "abha": abha,
        "mobile": mobile, "dob": dob, "address": address,
        "physical_address": physical_address, "gender": gender,
        "state_name": state_name, "district_name": district_name,
        "_photo": photo, "_qr": qr_image, "_qr_data": qr_data_dict,
    }
    card = build_card(name, abha, mobile, dob, address, gender, photo, qr_image, card_lang="")
    return card, fields


# ============================================================
#  PDF PROCESSING
# ============================================================
def process_pdf():
    global last_result, last_fields
    set_status("Processing PDF…", T("INFO"))
    progress_bar.configure(mode="indeterminate")
    progress_bar.start()

    def run():
        global last_result, last_fields
        try:
            page = pdf_doc[0]
            pix  = page.get_pixmap(dpi=800, alpha=False)
            img  = cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR)
            img  = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            card, fields = _process_image(img, page=page)
            try:
                pdf_text = page.get_text("text")
                changed  = False
                if len(pdf_text.strip()) > 20:
                    pdf_lines = [l.strip() for l in pdf_text.split('\n') if l.strip()]
                    if not fields.get("mobile"):
                        m = re.search(r"(?:^|[^\d])((?:(?:91|\+91)[\s\-]*)?[6789](?:[\s\-]*\d){9})(?:[^\d]|$)", pdf_text)
                        if m:
                            cand = re.sub(r"\D", "", m.group(1))
                            if len(cand) == 12 and cand.startswith("91"): cand = cand[2:]
                            if len(cand) == 10: fields["mobile"] = cand; changed = True
                    pdf_abha = _extract_abha_from_text(pdf_text)
                    if not pdf_abha:
                        condensed_pdf = re.sub(r'(\d)\s+(\d)', r'\1\2', pdf_text)
                        pdf_abha = _extract_abha_from_text(condensed_pdf)
                    if pdf_abha and pdf_abha != fields.get("abha"):
                        fields["abha"] = pdf_abha; changed = True
                    pdf_eng_name = ""
                    found_label = False
                    name_labels = [r"\bname\b", "பெயர்", "nom", "نام"]
                    for i, line in enumerate(pdf_lines):
                        is_label_line = any(re.search(label, line, re.IGNORECASE) for label in name_labels)
                        if is_label_line:
                            found_label = True
                            parts = re.split(r"[:\-–/]", line, maxsplit=1)
                            inline = parts[1].strip() if len(parts) > 1 else re.sub(r"name|பெயர்|nom|نام|/|\\", "", line, flags=re.IGNORECASE).strip()
                            if inline and not re.search(r"[\u0B80-\u0BFF]", inline) and not re.search(r"\d", inline):
                                candidate = _is_valid_english_name_candidate(inline)
                                if candidate: pdf_eng_name = candidate; break
                        elif found_label:
                            if not re.search(r"[\u0B80-\u0BFF]", line) and not re.search(r"\d", line) and len(line.strip()) > 2:
                                if not any(re.search(lbl, line, re.IGNORECASE) for lbl in name_labels):
                                    pdf_eng_name = line.strip(); break
                            else: break
                    if pdf_eng_name and not fields.get("name_eng"):
                        fields["name_eng"] = pdf_eng_name; changed = True
                    pdf_tam_name = _extract_tamil_name_from_pdf_text(pdf_text, pdf_lines, eng_anchor=fields.get("name_eng") or pdf_eng_name)
                    if not fields.get("name_tam"):
                        direct_tam = _extract_best_tamil_name_from_text(
                            pdf_text, eng_anchor=fields.get("name_eng", ""))
                        if direct_tam and _is_valid_tamil_name_candidate(direct_tam):
                            fields["name_tam"] = direct_tam; changed = True
                        else: pdf_tam_name = ""
                    if pdf_tam_name:
                        eng_anchor = fields.get("name_eng") or pdf_eng_name
                        if eng_anchor:
                            current = fields.get("name_tam", "")
                            candidates = []
                            if current: candidates.append((current, _tamil_name_quality(current, current)))
                            candidates.append((pdf_tam_name, _tamil_name_quality(pdf_tam_name, pdf_tam_name) + 50))
                            best = _select_best_tamil_name_with_english(candidates, eng_anchor, phonetic_weight=0.55)
                            if best: 
                                if best != fields.get("name_tam"): fields["name_tam"] = best; changed = True
                        elif not fields.get("name_tam"):
                            fields["name_tam"] = pdf_tam_name; changed = True
                        else:
                            current_score = _tamil_name_quality(fields["name_tam"], fields["name_tam"])
                            pdf_score = _tamil_name_quality(pdf_tam_name, pdf_tam_name)
                            if pdf_score > current_score + 15: fields["name_tam"] = pdf_tam_name; changed = True
                    for i, line in enumerate(pdf_lines):
                        ll = line.lower()
                        if "state" in ll and not fields.get("state_name"):
                            parts = re.split(r"[:\-–]", line, maxsplit=1)
                            val = parts[1].strip() if len(parts) > 1 else (pdf_lines[i+1] if i+1 < len(pdf_lines) else "")
                            val = _clean_location_value(val)
                            if val and len(val) > 3: fields["state_name"] = val; changed = True
                        if "district" in ll and not fields.get("district_name"):
                            parts = re.split(r"[:\-–]", line, maxsplit=1)
                            val = parts[1].strip() if len(parts) > 1 else (pdf_lines[i+1] if i+1 < len(pdf_lines) else "")
                            val = _clean_location_value(val)
                            if val and len(val) > 3: fields["district_name"] = val; changed = True
                    pdf_addr = _extract_phys_addr_from_lines(pdf_lines)
                    if not pdf_addr: pdf_addr = _extract_phys_addr_pincode_fallback(pdf_lines)
                    if pdf_addr and len(pdf_addr) > len(fields.get("physical_address", "")):
                        fields["physical_address"] = pdf_addr; changed = True
                if changed:
                    name    = (fields.get("name_eng", ""), fields.get("name_tam", ""))
                    qr_data = build_qr_data_from_fields(
                        name, fields.get("abha", ""), fields.get("mobile", ""),
                        fields.get("dob", ""), fields.get("address", ""),
                        fields.get("gender", ""), state_name=fields.get("state_name", "TAMIL NADU"),
                        district_name=fields.get("district_name", ""),
                        physical_address=fields.get("physical_address", ""))
                    fields["_qr"]      = generate_qr_image(qr_data)
                    fields["_qr_data"] = qr_data
                    card = _rebuild_card_from_fields(fields, fields.get("_photo"), fields.get("_qr"))
            except Exception as e:
                print(f"[WARN] Native PDF fallback:\n{traceback.format_exc()}")
            last_result = card
            last_fields = fields
            app.after(0, lambda: show_preview(card))
            app.after(0, lambda f=fields: _populate_inline_fields(f))
            app.after(0, lambda: set_status("Done — review and correct fields if needed.", T("SUCCESS")))
        except Exception as e:
            err = traceback.format_exc()
            err_msg = str(e)
            print(f"[ERROR] Full traceback:\n{err}")
            log = os.path.join(os.path.expanduser("~"), "Desktop", "abha_error.txt")
            try:
                with open(log, "w") as lf: lf.write(err)
            except Exception: pass
            app.after(0, lambda m=err_msg: set_status(f"Error: {m}", T("ERROR_COL")))
        finally:
            app.after(0, progress_bar.stop)
            app.after(0, lambda: progress_bar.configure(mode="determinate", progress_color=T("ACCENT")))

    threading.Thread(target=run, daemon=True).start()

def _populate_inline_fields(fields):
    for key, var in _field_vars.items():
        var.set(fields.get(key, ""))
    

def apply_inline_fields():
    global last_result, last_fields
    if last_fields is None:
        set_status("Upload a PDF first.", T("WARNING")); return
    for key, var in _field_vars.items():
        last_fields[key] = var.get().strip()
    if _card_lang_var is not None:
        last_fields["_card_lang"] = _card_lang_var.get()
    name = (last_fields.get("name_eng", ""), last_fields.get("name_tam", ""))
    qr_data = build_qr_data_from_fields(
        name, last_fields.get("abha", ""), last_fields.get("mobile", ""),
        last_fields.get("dob", ""), last_fields.get("address", ""),
        last_fields.get("gender", ""), state_name=last_fields.get("state_name", "TAMIL NADU"),
        district_name=last_fields.get("district_name", ""),
        physical_address=last_fields.get("physical_address", ""))
    last_fields["_qr"]      = generate_qr_image(qr_data)
    last_fields["_qr_data"] = qr_data
    result = _rebuild_card_from_fields(last_fields, last_fields.get("_photo"), last_fields.get("_qr"),
                                       use_background=_bg_enabled_state)
    last_result = result
    show_preview(result)
    set_status("Card updated with regenerated QR.", T("SUCCESS"))


# ============================================================
#  PRINT / SAVE — 2 PAGES
# ============================================================
def generate_print(side="both", dpi=300):
    if last_result is None:
        messagebox.showwarning("No Data", "Upload a PDF first."); return

    set_status("Generating print PDF…", T("INFO"))

    try:
        CR80_W_PT = 3.375 * 72
        CR80_H_PT = 2.125 * 72
        doc = fitz.open()

        # ── Front page ────────────────────────────────────
        if side in ("front", "both"):
            card1 = _rebuild_card_from_fields(
                last_fields, last_fields.get("_photo"), last_fields.get("_qr"),
                use_background=_bg_enabled_state, bg_index=1)
            
            pil1 = Image.fromarray(card1)
            pil1 = pil1.transpose(Image.FLIP_LEFT_RIGHT)
            tmp1 = tempfile.NamedTemporaryFile(suffix=".png", delete=False,
                                               dir=tempfile.gettempdir())
            tmp1.close()
            pil1.save(tmp1.name, "PNG")
            page1 = doc.new_page(width=CR80_W_PT, height=CR80_H_PT)
            page1.insert_image(fitz.Rect(0, 0, CR80_W_PT, CR80_H_PT), filename=tmp1.name)
            try: os.remove(tmp1.name)
            except Exception: pass

        # ── Back page ─────────────────────────────────────
        if side in ("back", "both"):
            bg2_path = _find_bg2_path()
            if bg2_path and _bg_enabled_state:
                pil2 = Image.open(bg2_path).convert("RGB").resize(
                    (int(CR80_W_PT * 10), int(CR80_H_PT * 10)), Image.LANCZOS)
            else:
                pil2 = Image.new("RGB", (int(CR80_W_PT * 10), int(CR80_H_PT * 10)), (255, 255, 255))
            # ── TRIAL watermark on back side ──────────────────
            if _is_demo_mode():
                import math
                bw, bh = pil2.size
                try:
                    wm_font = load_english_font(int(bh * 0.25))
                except Exception:
                    wm_font = ImageFont.load_default()
                wm_text = "TRIAL"
                wm_layer = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
                wm_draw  = ImageDraw.Draw(wm_layer)
                try:
                    bbox = wm_draw.textbbox((0, 0), wm_text, font=wm_font)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]
                except AttributeError:
                    tw, th = wm_draw.textsize(wm_text, font=wm_font)
                wm_draw.text(
                    ((bw - tw) // 2, (bh - th) // 2),
                    wm_text, font=wm_font, fill=(0, 0, 0, 80)
                )
                angle = math.degrees(math.atan2(bh, bw))
                wm_layer = wm_layer.rotate(angle, expand=False)
                pil2 = pil2.convert("RGBA")
                pil2 = Image.alpha_composite(pil2, wm_layer)
                pil2 = pil2.convert("RGB")
            back_pil = pil2.convert("RGB")
            tmp2 = tempfile.NamedTemporaryFile(suffix=".png", delete=False,
                                               dir=tempfile.gettempdir())
            tmp2.close()
            pil2.save(tmp2.name, "PNG")
            page2 = doc.new_page(width=CR80_W_PT, height=CR80_H_PT)
            page2.insert_image(fitz.Rect(0, 0, CR80_W_PT, CR80_H_PT), filename=tmp2.name)
            try: os.remove(tmp2.name)
            except Exception: pass

        # ── Save & open ───────────────────────────────────
        tmp_final = tempfile.NamedTemporaryFile(prefix="abha_card_", suffix=".pdf",
                                                dir=tempfile.gettempdir(), delete=False)
        tmp_final.close()
        doc.save(tmp_final.name, deflate=True)
        doc.close()
        os.startfile(tmp_final.name)

        side_label = {"front": "Front only", "back": "Back only", "both": "Both sides"}[side]
        set_status(f"PDF opened — {side_label} · CR80 (3.375 × 2.125 in). Print at Actual Size.", T("SUCCESS"))

    except PermissionError:
        set_status("Close the previously opened PDF and try again.", T("ERROR_COL"))
    except Exception as e:
        set_status(f"Error: {e}", T("ERROR_COL"))
        print(traceback.format_exc())
        




# ============================================================
#  UI HELPERS
# ============================================================

# These will be initialized after root window is created in main()
_doc_type_var = None
_card_lang_var = None  # ADD THIS

def open_pdf():
    global pdf_doc
    f = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
    if f:
        pdf_doc = fitz.open(f)
        set_status(f"Loaded: {os.path.basename(f)}", T("INFO"))
        if _doc_type_var is not None and _doc_type_var.get() == "PMJAY":
            process_pmjay_pdf()
        else:
            process_pdf()

def show_preview(img):
    try:
        pw = max(preview_label.winfo_width() - 10, 100)
        ph = max(preview_label.winfo_height() - 10, 60)
        card_w = pw
        card_h = int(card_w * 638 / 1011)
        if card_h > ph:
            card_h = ph
            card_w = int(card_h * 1011 / 638)
    except Exception:
        card_w, card_h = 600, 378

    try:
        scale = ctk.ScalingTracker.get_widget_scaling(preview_label)
        card_w = int(card_w / scale)
        card_h = int(card_h / scale)
    except Exception:
        pass

    pil = Image.fromarray(img)
    cimg = ctk.CTkImage(light_image=pil, size=(max(card_w, 100), max(card_h, 63)))
    preview_label.configure(image=cimg, text="")
    preview_label.image = cimg

def set_status(msg, color=None):
    if status_var: status_var.set(msg)
    if hasattr(set_status, "_lbl") and set_status._lbl:
        set_status._lbl.configure(text_color=color or T("TEXT_2"))


def _switch_tab(name):
    global _active_tab
    for n, f in _tab_frames.items(): f.pack_forget()
    _tab_frames[name].pack(fill="both", expand=True)
    _active_tab = name
    for n, b in _tab_buttons.items():
        is_active = (n == name)
        b.configure(
            fg_color="transparent",
            text_color=T("ACCENT") if is_active else T("TEXT_2"),
            border_width=0)
        
        
        
# ============================================================
#  GOOGLE TRANSLATE HELPER
# ============================================================
def _translate_to_tamil(text: str) -> str:
    """Translate English text to Tamil — kept for backward compatibility."""
    return _translate_to_language(text, target_lang="ta")


def _translate_to_language(text: str, target_lang: str = "ta") -> str:
    """
    Translate English text to any language using Google Translate free endpoint.
    target_lang: 'ta' = Tamil, 'ml' = Malayalam
    """
    if not text or not text.strip():
        return ""
    try:
        import urllib.parse
        import urllib.request
        import json

        text_encoded = urllib.parse.quote(text.strip())
        url = (
            f"https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=en&tl={target_lang}&dt=t&q={text_encoded}"
        )
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0"
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        translated = ""
        for block in data[0]:
            if block[0]:
                translated += block[0]
        return unicodedata.normalize("NFC", translated.strip())
    except Exception as e:
        print(f"[TRANSLATE WARN] {e}")
        return ""


# ============================================================
# ============================================================
#  MAIN UI
# ============================================================
def build_ui():
    global preview_label, status_var, progress_bar
    global _tab_frames, _tab_buttons, _active_tab, _field_vars, _doc_type_var
    _tab_frames = {}; _tab_buttons = {}; _active_tab = None; _field_vars.clear()

    app.configure(fg_color=T("BG_ROOT"))

    navbar = ctk.CTkFrame(app, fg_color="#020D1F", height=64, corner_radius=0,
                           border_width=0)
    navbar.pack(fill="x", side="top")
    navbar.pack_propagate(False)

    ctk.CTkFrame(navbar, width=4, fg_color=T("ACCENT"),
                 corner_radius=0).pack(side="left", fill="y")

    brand = ctk.CTkFrame(navbar, fg_color="transparent")
    brand.pack(side="left", fill="y", padx=(16, 0))
    _make_navbar_logo(brand)
    ctk.CTkLabel(brand, text="ABHA Card Studio",
                 font=ctk.CTkFont("Arial", 14, weight="bold"),
                 text_color="#FFFFFF").pack(side="left", pady=18)

    _pill_label(navbar, "v5.2", "#FFFFFF", T("ACCENT")).pack(
        side="left", padx=(10, 0), pady=20)

    ctk.CTkFrame(navbar, width=1, fg_color=T("BORDER"),
                 corner_radius=0).pack(side="left", fill="y", padx=20, pady=12)

    tabs_f = ctk.CTkFrame(navbar, fg_color="transparent")
    tabs_f.pack(side="left", fill="y")
    for label, tab_name in [("📄  Single File", "single")]:
        btn = ctk.CTkButton(
            tabs_f, text=label,
            font=ctk.CTkFont("Arial", 10, weight="bold"),
            fg_color="transparent", hover_color=T("NAV_ACTIVE"),
            text_color=T("TEXT_1"), height=60, width=120,
            corner_radius=0, border_width=0,
            command=lambda n=tab_name: _switch_tab(n))
        btn.pack(side="left")
        _tab_buttons[tab_name] = btn

    right = ctk.CTkFrame(navbar, fg_color="transparent")
    right.pack(side="right", padx=16, fill="y")

    global _card_lang_var
    _card_lang_var = tk.StringVar(value="Tamil")
    ctk.CTkOptionMenu(
        right,
        variable=_card_lang_var,
        values=["Tamil", "Malayalam", "Hindi"],
        fg_color=T("BG_CARD"),
        button_color=T("ACCENT"),
        button_hover_color=T("ACCENT2"),
        dropdown_fg_color=T("BG_CARD"),
        text_color=T("TEXT_1"),
        font=ctk.CTkFont("Arial", 10),
        height=34,
        width=140,
        corner_radius=8,
        command=lambda v: _on_lang_change(v)
    ).pack(side="right", padx=(0, 8), pady=14)
    


    font_ok = _TAMIL_FONT_PATH is not None

    def _logout():
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            app.destroy()

    ctk.CTkButton(right, text="Logout",
                   font=ctk.CTkFont("Arial", 10, weight="bold"),
                   fg_color="transparent", hover_color="#FEF2F2",
                   border_width=1, border_color=T("ERROR_COL"),
                   text_color=T("ERROR_COL"), height=32, width=76,
                   corner_radius=8, command=_logout
                   ).pack(side="right", pady=14, padx=(0, 6))

    ctk.CTkFrame(app, height=1, fg_color=T("BORDER"), corner_radius=0).pack(fill="x")

    content = ctk.CTkFrame(app, fg_color=T("BG_ROOT"), corner_radius=0)
    content.pack(fill="both", expand=True)

    # ── Single File Tab ─────────────────────────────────────
    single_tab = ctk.CTkFrame(content, fg_color=T("BG_ROOT"), corner_radius=0)
    _tab_frames["single"] = single_tab
    single_tab.columnconfigure(0, weight=0, minsize=220)
    single_tab.columnconfigure(1, weight=1)
    single_tab.columnconfigure(2, weight=0, minsize=290)
    single_tab.rowconfigure(0, weight=1)

    left_panel = ctk.CTkFrame(single_tab, fg_color="#020D1F",
                               corner_radius=0, width=225, border_width=0)
    left_panel.grid(row=0, column=0, sticky="nsew")
    left_panel.grid_propagate(False)
    ctk.CTkFrame(single_tab, width=1, fg_color=T("BORDER"),
                 corner_radius=0).grid(row=0, column=0, sticky="nse")

    panel_inner = ctk.CTkFrame(left_panel, fg_color="transparent")
    panel_inner.pack(fill="both", expand=True, padx=18, pady=22)

    upload_btn = ctk.CTkButton(
        panel_inner, text="⬆  Upload PDF",
        font=ctk.CTkFont("Arial", 11, weight="bold"),
        fg_color=T("ACCENT"), hover_color=T("ACCENT2"),
        text_color="#FFFFFF", height=42, corner_radius=10,
        border_width=0, command=open_pdf)
    upload_btn.pack(fill="x", pady=(0, 6))

    ctk.CTkFrame(panel_inner, height=1, fg_color=T("BORDER"), corner_radius=0).pack(fill="x", pady=(0, 8))

# ── Print side selector ──────────────────────────────
    ctk.CTkLabel(panel_inner, text="Print Side",
                 font=ctk.CTkFont("Arial", 9, weight="bold"),
                 text_color=T("TEXT_2")).pack(anchor="center", pady=(0, 4))

    _print_side_var = tk.StringVar(value="Both Sides")
    app.bind("<Control-p>", lambda e: _do_print())

    ctk.CTkOptionMenu(
        panel_inner,
        variable=_print_side_var,
        values=["Both Sides", "Front Only"],
        fg_color=T("BG_CARD"),
        button_color=T("ACCENT"),
        button_hover_color=T("ACCENT2"),
        dropdown_fg_color=T("BG_CARD"),
        text_color=T("TEXT_1"),
        font=ctk.CTkFont("Arial", 10),
        height=36,
        corner_radius=8
    ).pack(fill="x", pady=(0, 6))

    ctk.CTkLabel(panel_inner, text="Print DPI",
                 font=ctk.CTkFont("Arial", 9, weight="bold"),
                 text_color=T("TEXT_2")).pack(anchor="center", pady=(0, 4))

    _print_dpi_var = tk.StringVar(value="650 DPI")
    ctk.CTkOptionMenu(
        panel_inner,
        variable=_print_dpi_var,
        values=["150 DPI", "300 DPI", "600 DPI", "650 DPI", "800 DPI"],
        fg_color=T("BG_CARD"),
        button_color=T("ACCENT"),
        button_hover_color=T("ACCENT2"),
        dropdown_fg_color=T("BG_CARD"),
        text_color=T("TEXT_1"),
        font=ctk.CTkFont("Arial", 10),
        height=36,
        corner_radius=8
    ).pack(fill="x", pady=(0, 10))

    def _do_print():
        side_map = {"Both Sides": "both", "Front Only": "front"}
        dpi = int(_print_dpi_var.get().replace(" DPI", ""))
        generate_print(side_map.get(_print_side_var.get(), "both"), dpi=dpi)


    ctk.CTkButton(panel_inner, text="🖨  Print",
                  font=ctk.CTkFont("Arial", 11, weight="bold"),
                  fg_color=T("ACCENT"), hover_color=T("ACCENT2"),
                  text_color="#FFFFFF", height=42, corner_radius=10,
                  command=_do_print).pack(fill="x")

    

    # ── BACKGROUND TOGGLE ────────────────────────────────────
    ctk.CTkFrame(panel_inner, height=1, fg_color=T("BORDER"), corner_radius=0).pack(fill="x", pady=(2, 5))
    ctk.CTkLabel(panel_inner, text="CARD BACKGROUND",
                 font=ctk.CTkFont("Arial", 8, weight="bold"),
                 text_color=T("TEXT_1")).pack(anchor="center", pady=(10, 2))

    bg_card = ctk.CTkFrame(panel_inner, fg_color=T("BG_CARD"),
                            corner_radius=10, border_width=1,
                            border_color=T("BORDER"))
    bg_card.pack(fill="x")

    bg_top = ctk.CTkFrame(bg_card, fg_color="transparent")
    bg_top.pack(fill="x", padx=12, pady=(6, 2))
    ctk.CTkLabel(bg_top, text="🖼 Background",
                 font=ctk.CTkFont("Arial", 10, weight="bold"),
                 text_color=T("TEXT_1")).pack(expand=True)

    _bg_bg_var = tk.BooleanVar(value=True)   # OFF by default

    bg_status_lbl = ctk.CTkLabel(bg_card, text="",
                                  font=ctk.CTkFont("Arial", 9, weight="bold"),
                                  text_color=T("TEXT_3"))
    bg_status_lbl.pack_forget()



    def _on_bg_toggle():
        global _bg_enabled_state, last_result, last_fields
        _bg_enabled_state = _bg_var.get()
        if _bg_enabled_state:
            bg_toggle_btn.configure(text="ON ✓",
                                    fg_color=T("ACCENT"),
                                    text_color="#FFFFFF")
        else:
            bg_toggle_btn.configure(text="OFF",
                                    fg_color=T("BG_INPUT"),
                                    hover_color=T("BG_HOVER"),
                                    border_color=T("BORDER2"),
                                    text_color=T("TEXT_2"))
        if last_fields is not None:
            refreshed = _rebuild_card_from_fields(
                last_fields, last_fields.get("_photo"), last_fields.get("_qr"),
                use_background=_bg_enabled_state)
            last_result = refreshed
            if _showing_front[0]:
                _show_front_in_label()
            else:
                _show_back_in_label()
            set_status(
                f"Background {'enabled' if _bg_enabled_state else 'disabled'}.",
                T("SUCCESS") if _bg_enabled_state else T("INFO"))
            
    bg_toggle_btn = ctk.CTkButton(
        bg_card, text="OFF",
        font=ctk.CTkFont("Arial", 10, weight="bold"),
        fg_color=T("BG_INPUT"), hover_color=T("BG_HOVER"),
        border_color=T("BORDER2"),
        text_color=T("TEXT_2"),
        height=34, corner_radius=8,
        command=lambda: [_bg_var.set(not _bg_var.get()), _on_bg_toggle()])
    bg_toggle_btn.pack(fill="x", padx=12, pady=(0, 4))
    _on_bg_toggle()


    if not font_ok:
        warn = ctk.CTkFrame(panel_inner, fg_color="#FFF7ED",
                             corner_radius=10, border_width=1, border_color="#FED7AA")
        warn.pack(fill="x", pady=(20, 0))
        ctk.CTkLabel(warn,
                     text="⚠  Tamil font missing.\nPlace NotoSansTamil-Bold.ttf\nnext to this .exe",
                     font=ctk.CTkFont("Arial", 8), text_color="#C2410C",
                     justify="left", wraplength=170).pack(padx=12, pady=10, anchor="w")

    info_f = ctk.CTkFrame(left_panel, fg_color="transparent")
    info_f.pack(side="bottom", fill="x", padx=18, pady=14)
    ctk.CTkFrame(info_f, height=1, fg_color=T("BORDER"), corner_radius=0).pack(fill="x", pady=(0, 8))
    ctk.CTkLabel(info_f, text="ABHA Card Studio  v5.2",
                 font=ctk.CTkFont("Arial", 8), text_color=T("TEXT_3")).pack(anchor="w")

    preview_area = ctk.CTkFrame(single_tab, fg_color=T("BG_ROOT"), corner_radius=0)
    preview_area.grid(row=0, column=1, sticky="nsew")

    prev_hdr = ctk.CTkFrame(preview_area, fg_color=T("BG_PANEL"),
                             height=52, corner_radius=0, border_width=0)
    prev_hdr.pack(fill="x"); prev_hdr.pack_propagate(False)
    ctk.CTkFrame(prev_hdr, height=1, fg_color=T("BORDER"),
                 corner_radius=0).pack(side="bottom", fill="x")
    hdr_inner = ctk.CTkFrame(prev_hdr, fg_color="transparent")
    hdr_inner.pack(fill="both", expand=True, padx=18)
    ctk.CTkLabel(hdr_inner, text="Card Preview",
                 font=ctk.CTkFont("Arial", 12, weight="bold"),
                 text_color=T("TEXT_1")).pack(side="left", pady=14)
    _pill_label(hdr_inner, "Live Output", T("ACCENT"), T("ACCENT_DIM")).pack(side="left", padx=10, pady=16)

    preview_outer = ctk.CTkFrame(preview_area, fg_color=T("BG_ROOT"), corner_radius=0)
    preview_outer.pack(fill="both", expand=True, padx=0, pady=0)

    # ── Flip card layout (single card + flip button) ─────────
    _showing_front = [True]  # mutable flag
    
    def _on_lang_change(lang):
        global last_result, last_fields

        # ── Update the Name field label ──
        if _name_tam_label_var_ref[0] is not None:
            if lang == "Malayalam":
                _name_tam_label_var_ref[0].set("Name (Malayalam)")
            elif lang == "Hindi":
                _name_tam_label_var_ref[0].set("Name (Hindi)")
            else:
                _name_tam_label_var_ref[0].set("Name (Tamil)")

        if last_fields is None:
            return
        last_fields["_card_lang"] = lang

        # ── Auto-translate name when language changes ──
        eng = last_fields.get("name_eng", "").strip()
        if eng:
            def _auto_translate():
                target = "ml" if lang == "Malayalam" else "hi" if lang == "Hindi" else "ta"
                result = _translate_to_language(eng, target_lang=target)
                if result:
                    if "name_tam" in _field_vars:
                        app.after(0, lambda r=result: _field_vars["name_tam"].set(r))
                    last_fields["name_tam"] = result
                    app.after(0, apply_inline_fields)
                    app.after(0, lambda: set_status(
                        f"✓ Name auto-translated to {lang}.", T("SUCCESS")))
            threading.Thread(target=_auto_translate, daemon=True).start()
            return

        refreshed = _rebuild_card_from_fields(
            last_fields, last_fields.get("_photo"), last_fields.get("_qr"),
            use_background=_bg_enabled_state)
        last_result = refreshed
        if _showing_front[0]:
            _show_front_in_label()
        set_status(f"Card language set to {lang}.", T("SUCCESS"))

    flip_controls = ctk.CTkFrame(preview_outer, fg_color="transparent")
    flip_controls.pack(fill="x", pady=(0, 8))

    side_label = ctk.CTkLabel(flip_controls, text="◀  Front Side",
                              font=ctk.CTkFont("Arial", 10, weight="bold"),
                              text_color=T("ACCENT"))
    side_label.pack(side="left")

    flip_btn = ctk.CTkButton(
        flip_controls, text="🔄  Show Back",
        font=ctk.CTkFont("Arial", 10, weight="bold"),
        fg_color=T("BG_INPUT"), hover_color=T("BG_HOVER"),
        border_width=1, border_color=T("BORDER2"),
        text_color=T("TEXT_1"), height=32, width=130, corner_radius=8,
        command=lambda: _flip_card())
    flip_btn.pack(side="right")

    shadow_frame = ctk.CTkFrame(preview_outer, fg_color=T("BORDER"), corner_radius=14)
    shadow_frame.pack(fill="both", expand=True)
    preview_frame = ctk.CTkFrame(shadow_frame, fg_color=T("BG_CARD"), corner_radius=12)
    preview_frame.pack(fill="both", expand=True, padx=1, pady=1)

    preview_label = ctk.CTkLabel(
        preview_frame,
        text="Upload a PDF to generate the card.",
        font=ctk.CTkFont("Arial", 11),
        text_color=T("TEXT_3"))
    preview_label.pack(expand=True, fill="both")

    _back_preview_label = None  # not used as separate widget anymore

    def _get_card_size():
        try:
            pw = max(preview_frame.winfo_width() - 10, 100)
            ph = max(preview_frame.winfo_height() - 10, 60)
        except Exception:
            pw, ph = 600, 380
        card_w = pw
        card_h = int(card_w * 638 / 1011)
        if card_h > ph:
            card_h = ph
            card_w = int(card_h * 1011 / 638)
        try:
            scale = ctk.ScalingTracker.get_widget_scaling(preview_label)
            card_w = int(card_w / scale)
            card_h = int(card_h / scale)
        except Exception:
            pass
        return max(card_w, 100), max(card_h, 63)

    def _show_front_in_label():
        if last_result is None: return
        card_w, card_h = _get_card_size()
        pil = Image.fromarray(last_result)
        cimg = ctk.CTkImage(light_image=pil, size=(card_w, card_h))
        preview_label.configure(image=cimg, text="")
        preview_label.image = cimg

    def _show_back_in_label():
        card_w, card_h = _get_card_size()
        if _bg_enabled_state:
            bg2_path = _find_bg2_path()
            if bg2_path:
                try:
                    back_pil = Image.open(bg2_path).convert("RGB").resize(
                        (card_w * 2, card_h * 2), Image.LANCZOS)
                except Exception:
                    back_pil = Image.new("RGB", (card_w * 2, card_h * 2), (255, 255, 255))
            else:
                back_pil = Image.new("RGB", (card_w * 2, card_h * 2), (255, 255, 255))
        else:
            back_pil = Image.new("RGB", (card_w * 2, card_h * 2), (255, 255, 255))
        
        # ── TRIAL watermark on back side ──────────────────
        if _is_demo_mode():
            import math
            bw, bh = back_pil.size
            try:
                wm_font = load_english_font(int(bh * 0.25))
            except Exception:
                wm_font = ImageFont.load_default()
            wm_text = "TRIAL"
            wm_layer = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            wm_draw = ImageDraw.Draw(wm_layer)
            try:
                bbox = wm_draw.textbbox((0, 0), wm_text, font=wm_font)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
            except AttributeError:
                tw, th = wm_draw.textsize(wm_text, font=wm_font)
            wm_draw.text(
                ((bw - tw) // 2, (bh - th) // 2),
                wm_text, font=wm_font, fill=(0, 0, 0, 80)
            )
            angle = math.degrees(math.atan2(bh, bw))
            wm_layer = wm_layer.rotate(angle, expand=False)
            back_pil = back_pil.convert("RGBA")
            back_pil = Image.alpha_composite(back_pil, wm_layer)
            back_pil = back_pil.convert("RGB")
        
        back_pil = back_pil.convert("RGB")
        cimg = ctk.CTkImage(light_image=back_pil, size=(card_w, card_h))
        preview_label.configure(image=cimg, text="")
        preview_label.image = cimg

    def _flip_card():
        _showing_front[0] = not _showing_front[0]
        if _showing_front[0]:
            side_label.configure(text="◀  Front Side", text_color=T("ACCENT"))
            flip_btn.configure(text="🔄  Show Back")
            _show_front_in_label()
        else:
            side_label.configure(text="Back Side  ▶", text_color=T("TEXT_3"))
            flip_btn.configure(text="🔄  Show Front")
            _show_back_in_label()

    def _on_resize(event):
        if last_result is None: return
        if _showing_front[0]:
            _show_front_in_label()
        else:
            _show_back_in_label()

    preview_frame.bind("<Configure>", _on_resize)
    ctk.CTkFrame(single_tab, width=1, fg_color=T("BORDER"),
                 corner_radius=0).grid(row=0, column=1, sticky="nse")

    right_panel = ctk.CTkFrame(single_tab, fg_color="#020D1F",
                                corner_radius=0, width=290, border_width=0)
    right_panel.grid(row=0, column=2, sticky="nsew")
    right_panel.grid_propagate(False)

    fhdr = ctk.CTkFrame(right_panel, fg_color=T("BG_PANEL"), height=52, corner_radius=0)
    fhdr.pack(fill="x"); fhdr.pack_propagate(False)
    ctk.CTkFrame(fhdr, height=1, fg_color=T("BORDER"), corner_radius=0).pack(side="bottom", fill="x")
    fhdr_inner = ctk.CTkFrame(fhdr, fg_color="transparent")
    fhdr_inner.pack(fill="both", expand=True, padx=16)
    ctk.CTkLabel(fhdr_inner, text="Extracted Fields",
                 font=ctk.CTkFont("Arial", 12, weight="bold"),
                 text_color=T("TEXT_1")).pack(side="left", pady=14)
    _pill_label(fhdr_inner, "Edit & Apply", T("ACCENT"), T("ACCENT_DIM")).pack(side="right", pady=16)

    fields_scroll = ctk.CTkScrollableFrame(right_panel, fg_color="#020D1F",
                                            scrollbar_button_color=T("SCROLLBAR"),
                                            scrollbar_button_hover_color=T("ACCENT_LIGHT"))
    fields_scroll.pack(fill="both", expand=True, padx=14, pady=10)

    ABHA_FIELD_DEFS = [
        ("name_eng",         "Name (English)", "👤"),
        ("name_tam",         "Name (Tamil)", "👤"),
        ("abha",             "ABHA Number", "🪪"),
        ("mobile",           "Mobile", "📱"),
        ("dob",              "Date of Birth", "📅"),
        ("address",          "ABHA Address (@abdm)", "🔗"),
        ("physical_address", "Physical Address", "🏠"),
        ("gender",           "Gender", "⚧"),
        ("state_name",       "State", "📍"),
        ("district_name",    "District", "📍"),
    ]

    def _rebuild_fields(doc_type="ABHA"):
        for w in fields_scroll.winfo_children():
            w.destroy()
        _field_vars.clear()
        _name_eng_var_ref[0] = None
        _name_tam_var_ref[0] = None

        FIELD_DEFS = ABHA_FIELD_DEFS

        for key, label, icon in FIELD_DEFS:
            row_f = ctk.CTkFrame(fields_scroll, fg_color=T("BG_CARD"),
                                  corner_radius=8, border_width=1,
                                  border_color=T("BORDER"))
            row_f.pack(fill="x", pady=4)
            lbl_row = ctk.CTkFrame(row_f, fg_color="transparent")
            lbl_row.pack(fill="x", padx=12, pady=(8, 2))
            ctk.CTkLabel(lbl_row, text=icon,
                         font=ctk.CTkFont("Arial", 9),
                         text_color=T("ACCENT")).pack(side="left", padx=(0, 4))

            if key == "name_tam":
                _name_tam_label_var = tk.StringVar(value="Name (Tamil)")
                _name_tam_label_var_ref[0] = _name_tam_label_var
                ctk.CTkLabel(lbl_row, textvariable=_name_tam_label_var,
                             font=ctk.CTkFont("Arial", 8, weight="bold"),
                             text_color="#FFFFFF").pack(side="left")
            else:
                ctk.CTkLabel(lbl_row, text=label,
                             font=ctk.CTkFont("Arial", 8, weight="bold"),
                             text_color="#FFFFFF").pack(side="left")

            var = tk.StringVar(value="")

            if key == "name_tam":
                entry_row = ctk.CTkFrame(row_f, fg_color="transparent")
                entry_row.pack(fill="x", padx=12, pady=(2, 4))
                tam_entry = ctk.CTkEntry(
                    entry_row, textvariable=var,
                    font=ctk.CTkFont("Arial", 10),
                    fg_color=T("BG_INPUT"), border_color=T("BORDER2"),
                    text_color=T("TEXT_1"), height=34, corner_radius=6)
                tam_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

                translate_status = tk.StringVar(value="")

                def _do_translate(v=var, status=translate_status):
                    ref = _name_eng_var_ref[0]
                    eng_text = ref.get().strip() if ref else ""
                    if not eng_text:
                        status.set("⚠ No English name")
                        return
                    status.set("⏳ Translating…")
                    def _run():
                        lang = _card_lang_var.get()
                        if lang == "Malayalam":
                            result = _translate_to_language(eng_text, target_lang="ml")
                        elif lang == "Hindi":
                            result = _translate_to_language(eng_text, target_lang="hi")
                        else:
                            result = _translate_to_language(eng_text, target_lang="ta")
                        if result:
                            v.set(result)
                            status.set("✓ Done")
                        else:
                            status.set("✗ Failed / Offline")
                        app.after(3000, lambda: status.set(""))
                    threading.Thread(target=_run, daemon=True).start()

                ctk.CTkButton(
                    entry_row, text="🌐 Translate",
                    font=ctk.CTkFont("Arial", 8, weight="bold"),
                    fg_color=T("ACCENT"), hover_color=T("ACCENT2"),
                    text_color="#FFFFFF",
                    height=34, width=90, corner_radius=6,
                    command=_do_translate
                ).pack(side="right")

                ctk.CTkLabel(row_f, textvariable=translate_status,
                             font=ctk.CTkFont("Arial", 8),
                             text_color=T("SUCCESS")).pack(
                                 anchor="w", padx=12, pady=(0, 4))

                # ── Font size controls ──────────────────────────────
                fs_row = ctk.CTkFrame(row_f, fg_color="transparent")
                fs_row.pack(fill="x", padx=12, pady=(0, 8))

                ctk.CTkLabel(fs_row, text="Font Size",
                             font=ctk.CTkFont("Arial", 8, weight="bold"),
                             text_color=T("TEXT_2")).pack(side="left", padx=(0, 8))

                _fs_display = tk.StringVar(value=str(_native_name_font_size[0]))

                fs_spin = ctk.CTkFrame(fs_row, fg_color=T("BG_INPUT"),
                                       corner_radius=8, border_width=1,
                                       border_color=T("BORDER2"))
                fs_spin.pack(side="left")

                def _dec_fs(disp=_fs_display):
                    if _native_name_font_size[0] > 10:
                        _native_name_font_size[0] -= 1
                        disp.set(str(_native_name_font_size[0]))
                        _refresh_native_font()

                def _inc_fs(disp=_fs_display):
                    if _native_name_font_size[0] < 80:
                        _native_name_font_size[0] += 1
                        disp.set(str(_native_name_font_size[0]))
                        _refresh_native_font()

                def _refresh_native_font():
                    global last_result
                    if last_fields is None:
                        return
                    refreshed = _rebuild_card_from_fields(
                        last_fields,
                        last_fields.get("_photo"),
                        last_fields.get("_qr"),
                        use_background=_bg_enabled_state)
                    last_result = refreshed
                    _show_front_in_label()

                ctk.CTkButton(fs_spin, text="−", width=30, height=30,
                              font=ctk.CTkFont("Arial", 14, weight="bold"),
                              fg_color="transparent",
                              hover_color=T("BG_HOVER"),
                              text_color=T("TEXT_1"),
                              corner_radius=0,
                              command=_dec_fs).pack(side="left")

                ctk.CTkLabel(fs_spin, textvariable=_fs_display,
                             font=ctk.CTkFont("Arial", 11, weight="bold"),
                             text_color=T("TEXT_1"),
                             width=36).pack(side="left")

                ctk.CTkButton(fs_spin, text="+", width=30, height=30,
                              font=ctk.CTkFont("Arial", 14, weight="bold"),
                              fg_color="transparent",
                              hover_color=T("BG_HOVER"),
                              text_color=T("TEXT_1"),
                              corner_radius=0,
                              command=_inc_fs).pack(side="left")

                ctk.CTkLabel(fs_row, text="(10 – 80)",
                             font=ctk.CTkFont("Arial", 7),
                             text_color=T("TEXT_3")).pack(side="left", padx=(8, 0))
            else:
                ctk.CTkEntry(row_f, textvariable=var,
                             font=ctk.CTkFont("Arial", 10),
                             fg_color=T("BG_INPUT"), border_color=T("BORDER2"),
                             text_color=T("TEXT_1"), height=34, corner_radius=6
                             ).pack(fill="x", padx=12, pady=(2, 10))

            _field_vars[key] = var
            if key == "name_eng": _name_eng_var_ref[0] = var
            elif key == "name_tam": _name_tam_var_ref[0] = var
    _name_eng_var_ref = [None]
    _name_tam_var_ref = [None]
    _name_tam_label_var_ref = [None]
    _rebuild_fields("ABHA")
    

    ctk.CTkFrame(right_panel, height=1, fg_color=T("BORDER"), corner_radius=0).pack(fill="x")
    apply_footer = ctk.CTkFrame(right_panel, fg_color=T("BG_PANEL"), height=64, corner_radius=0)
    apply_footer.pack(fill="x", side="bottom"); apply_footer.pack_propagate(False)
    ctk.CTkButton(apply_footer,
                   text="✓  Apply & Regenerate QR",
                   font=ctk.CTkFont("Arial", 11, weight="bold"),
                   fg_color=T("ACCENT"), hover_color=T("ACCENT2"),
                   text_color="#FFFFFF", height=40, corner_radius=10,
                   command=apply_inline_fields
                   ).pack(fill="x", padx=14, pady=12)

    # ── Status Bar ──────────────────────────────────────────
    ctk.CTkFrame(app, height=1, fg_color=T("BORDER"), corner_radius=0).pack(fill="x", side="bottom")
    statusbar = ctk.CTkFrame(app, fg_color="#020D1F", height=32, corner_radius=0)
    statusbar.pack(fill="x", side="bottom")
    statusbar.pack_propagate(False)
    global status_var, progress_bar
    status_var = tk.StringVar(value="Ready  ·  Upload a PDF to begin")
    status_lbl = ctk.CTkLabel(statusbar, textvariable=status_var,
                               font=ctk.CTkFont("Arial", 9),
                               text_color="#FFFFFF")
    if _is_demo_mode():
        ctk.CTkLabel(statusbar, text="⚠  TRIAL VERSION",
                     font=ctk.CTkFont("Arial", 8, weight="bold"),
                     text_color="#F59E0B").pack(side="left", padx=(10, 0))
    status_lbl.pack(side="left", padx=(20, 0))
    set_status._lbl = status_lbl
    ctk.CTkLabel(statusbar, text="ABHA CARD STUDIO",
                 font=ctk.CTkFont("Arial", 7, weight="bold"),
                 text_color="#C7D2FE").pack(side="right", padx=14)
    progress_bar = ctk.CTkProgressBar(statusbar, width=140, height=4,
                                       fg_color="#FFFFFF",
                                       progress_color="#1565C0",
                                       corner_radius=10)
    progress_bar.pack(side="right", padx=(0, 10), pady=14)
    progress_bar.set(0)

    _switch_tab("single")


# ============================================================
#  EXTRACT BEST TAMIL NAME FROM TEXT
# ============================================================
def _extract_best_tamil_name_from_text(text: str, eng_anchor: str = "") -> str:
    if not text or not text.strip(): return ""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    candidates = []
    for line in lines:
        if not re.search(r"[\u0B80-\u0BFF]", line): continue
        candidate = _is_valid_tamil_name_candidate(line)
        if candidate:
            score = _tamil_name_quality(candidate, line)
            candidates.append((candidate, score))
    if not candidates:
        seq = _extract_longest_tamil_sequence(text, min_chars=3)
        return seq
    if eng_anchor:
        best = _select_best_tamil_name_with_english(candidates, eng_anchor)
        if best: return best
    return max(candidates, key=lambda x: x[1])[0]


# ============================================================
#  ENTRY POINT
# ============================================================
def main():

    global app, _doc_type_var, _card_lang_var
    app = ctk.CTk()
    # Initialize Tkinter variables after root is created
    _doc_type_var = tk.StringVar(value="ABHA")
    _card_lang_var = None  # Will be set in build_ui()

    app.geometry("1280x760")
    app.minsize(980, 600)
    app.title("ABHA Card Studio")
    _set_app_icon(app)
    app.withdraw()

    try:
        available_langs = pytesseract.get_languages(config='')
        print(f"[INIT] Available OCR languages: {available_langs}")
        if 'tam' not in available_langs:
            print("[WARN] 'tam' (Tamil) language data NOT found in tessdata folder!")
    except Exception as e:
        print(f"[WARN] Could not check OCR languages: {e}")

    def _launch_main():
        global _bg_var
        _bg_var = tk.BooleanVar(value=True)
        _bg_var.set(True)
        build_ui()
        loader = LoadingScreen(app)
        def after_load():
            if loader.winfo_exists():
                loader.destroy()
            app.deiconify()
            app.lift()
        app.after(2800, after_load)

    def _after_activation():
        _launch_main()

    def _on_close():
        """When user closes the window, if in trial/no license, prompt for key."""
        if _is_demo_mode() or not _is_activated():
            ans = messagebox.askyesno(
                "Activate License",
                "You are running in TRIAL mode.\n\n"
                "Would you like to enter your License Key now\nto unlock the full version?",
                icon="warning"
            )
            if ans:
                def _on_activate_done():
                    # After activating, just continue running normally
                    pass
                MachineCodeScreen(app, on_success=_on_activate_done)
                return  # Don't close the app yet
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", _on_close)

    # ── Startup flow ──────────────────────────────────────
    if not _is_activated():
        # Never activated at all
        ActivationScreen(app, on_success=_after_activation)
    else:
        _launch_main()

    app.mainloop()
if __name__ == "__main__":
    main()
