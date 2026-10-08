# from __future__ import annotations

# import os
# import sqlite3
# import uuid

# from datetime import datetime, timedelta

# from flask import Flask, redirect, render_template, request, url_for
# from werkzeug.utils import secure_filename

# from reportlab.lib.units import mm
# from reportlab.pdfgen import canvas

# from reportlab.lib.units import mm # type: ignore
# from reportlab.pdfgen import canvas # type: ignore
# from reportlab.lib.styles import ParagraphStyle # type: ignore

# from reportlab.platypus import SimpleDocTemplate, Preformatted # type: ignore
# from reportlab.lib.styles import getSampleStyleSheet # type: ignore

# import io
# import zipfile
# import csv
# from flask import send_file, Response

# APP_DIR = os.path.dirname(os.path.abspath(__file__))
# # DB_PATH = os.path.join(APP_DIR, "tailor.db")
# THERMAL_WIDTH = 80 * mm   # 80mm paper width

# APP_DIR = os.path.dirname(os.path.abspath(__file__))

# REPORT_DIR = os.path.join(APP_DIR, "static", "reports")
# os.makedirs(REPORT_DIR, exist_ok=True)

# app = Flask(__name__)
# _db_ready = False

# GALLERY_FOLDER = os.path.join(APP_DIR, "static", "uploads", "gallery")
# os.makedirs(GALLERY_FOLDER, exist_ok=True)
# app.config["GALLERY_FOLDER"] = GALLERY_FOLDER

# UPLOAD_FOLDER = os.path.join(APP_DIR, "static", "uploads")
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# REQ_ICON_FOLDER = os.path.join(APP_DIR, "static", "req_icons")
# os.makedirs(REQ_ICON_FOLDER, exist_ok=True)
# app.config["REQ_ICON_FOLDER"] = REQ_ICON_FOLDER


# # def get_db() -> sqlite3.Connection:
# #     conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
# #     conn.row_factory = sqlite3.Row
# #     conn.execute("PRAGMA foreign_keys = ON")
# #     conn.execute("PRAGMA journal_mode = WAL")
# #     conn.execute("PRAGMA synchronous = NORMAL")
# #     conn.execute("PRAGMA busy_timeout = 30000")
# #     return conn

# import os
# import pyodbc
# from dotenv import load_dotenv

# load_dotenv()

from __future__ import annotations
import os
import sys
import sqlite3
from datetime import datetime
from cryptography.fernet import Fernet
from machine_id import get_machine_id
from flask import Flask, render_template

from dotenv import load_dotenv
import os
import re
import unicodedata

load_dotenv(override=True)
import pyodbc

import os
import sqlite3
import uuid
from datetime import datetime, timedelta

from flask import Flask, redirect, render_template, request, url_for, send_from_directory, jsonify, session
from werkzeug.utils import secure_filename

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from reportlab.lib.units import mm # type: ignore
from reportlab.pdfgen import canvas # type: ignore
from reportlab.lib.styles import ParagraphStyle # type: ignore
from reportlab.lib.pagesizes import A4 # type: ignore
from reportlab.pdfbase import pdfmetrics # type: ignore
from reportlab.pdfbase.ttfonts import TTFont # type: ignore

from reportlab.platypus import SimpleDocTemplate, Preformatted, Table, TableStyle, Paragraph, Spacer # type: ignore
from reportlab.lib.styles import getSampleStyleSheet # type: ignore
from reportlab.lib import colors # type: ignore

import io
import zipfile
import csv
import math
import shutil
import subprocess
import tempfile
from functools import lru_cache
from flask import send_file, Response
from PIL import Image, ImageDraw, ImageFont, features

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "tailor.db")
THERMAL_WIDTH = 80 * mm   # 80mm paper width

APP_DIR = os.path.dirname(os.path.abspath(__file__))

REPORT_DIR = os.path.join(APP_DIR, "static", "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "ilogictech-admin-session-key")
_db_ready = False

GALLERY_FOLDER = os.path.join(APP_DIR, "static", "uploads", "gallery")
os.makedirs(GALLERY_FOLDER, exist_ok=True)
app.config["GALLERY_FOLDER"] = GALLERY_FOLDER

UPLOAD_FOLDER = os.path.join(APP_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

REQ_ICON_FOLDER = os.path.join(APP_DIR, "static", "req_icons")
os.makedirs(REQ_ICON_FOLDER, exist_ok=True)
app.config["REQ_ICON_FOLDER"] = REQ_ICON_FOLDER

FONTS_FOLDER = os.path.join(APP_DIR, "fonts")

_REPORTLAB_FONT_CACHE: tuple[str, str] | None = None


def has_tamil_chars(text: str | None) -> bool:
    return any(0x0B80 <= ord(ch) <= 0x0BFF for ch in str(text or ""))


def get_reportlab_tamil_fonts() -> tuple[str, str]:
    global _REPORTLAB_FONT_CACHE
    if _REPORTLAB_FONT_CACHE is not None:
        return _REPORTLAB_FONT_CACHE

    regular_font = "Helvetica"
    bold_font = "Helvetica-Bold"
    regular_candidates = [
        # Match browser Tamil fallback look (Windows UI stack) as closely as possible.
        r"C:\Windows\Fonts\Nirmala.ttf",
        r"C:\Windows\Fonts\Latha.ttf",
        r"C:\Windows\Fonts\Vijaya.ttf",
        os.path.join(FONTS_FOLDER, "Nirmala.ttf"),
        os.path.join(FONTS_FOLDER, "Latha.ttf"),
        os.path.join(FONTS_FOLDER, "Vijaya.ttf"),
        os.path.join(FONTS_FOLDER, "NotoSansTamil-Regular.ttf"),
    ]
    bold_candidates = [
        os.path.join(FONTS_FOLDER, "NotoSansTamil-Bold.ttf"),
        r"C:\Windows\Fonts\NirmalaB.ttf",
    ]

    for font_path in regular_candidates:
        if not os.path.exists(font_path):
            continue
        try:
            pdfmetrics.registerFont(TTFont("TamilFont", font_path))
            regular_font = "TamilFont"
            break
        except Exception:
            continue

    for font_path in bold_candidates:
        if not os.path.exists(font_path):
            continue
        try:
            pdfmetrics.registerFont(TTFont("TamilFont-Bold", font_path))
            bold_font = "TamilFont-Bold"
            break
        except Exception:
            continue

    if bold_font == "Helvetica-Bold" and regular_font != "Helvetica":
        bold_font = regular_font

    _REPORTLAB_FONT_CACHE = (regular_font, bold_font)
    return _REPORTLAB_FONT_CACHE

# ---------------- APP PATH ----------------

def init_license_db():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_code TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    con.commit()
    con.close()

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = get_app_dir()

DB_FILE = os.path.join(APP_DIR, "license_db.sqlite")
print("APP DB PATH:", DB_FILE)
init_license_db()

def get_secret_key():
    secret = os.getenv("FERNET_SECRET")
    if not secret:
        raise Exception("FERNET_SECRET not found in .env")
    return secret.encode()

def get_license_from_db():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("SELECT license_code FROM licenses ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    con.close()
    return row[0] if row else None

def validate_license():
    license_code = get_license_from_db()

    if not license_code:
        return False, "License not found. Please contact the administrator.", None

    try:
        secret = get_secret_key()
        fernet = Fernet(secret)

        decrypted = fernet.decrypt(license_code.encode()).decode()

        machine_id, expiry_date = decrypted.split("|")

        if machine_id != get_machine_id():
            return False, "Invalid machine ID", None

        expiry_dt = datetime.fromisoformat(expiry_date)
        now = datetime.now()

        if expiry_dt < now:
            return False, "License expired", None

        # ðŸ”” Calculate remaining days
        remaining_days = (expiry_dt - now).days

        if remaining_days <= 30:
            warning = f"Your license will expire in {remaining_days} days. Please contact administrator."
            return True, "Valid license", warning

        return True, "Valid license", None

    except Exception as e:
        return False, f"Invalid license: {str(e)}", None

from flask import render_template

@app.before_request
def check_license():
    # valid, message = validate_license()
    valid, message, warning = validate_license()

    if not valid:
        return render_template("license_error.html", message=message)


class SqlRow(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def _sqlserverize(sql: str) -> str:
    q = sql
    q = q.replace(" NULLS LAST", "")
    q = q.replace("||", "+")
    q = re.sub(r"\bdate\(([^)]+)\)", r"CAST(\1 AS DATE)", q, flags=re.IGNORECASE)
    q = re.sub(
        r"GROUP_CONCAT\s*\(\s*DISTINCT\s+([^)]+)\)",
        r"STRING_AGG(\1, ',')",
        q,
        flags=re.IGNORECASE,
    )
    q = re.sub(
        r"GROUP_CONCAT\s*\(\s*([^)]+)\)",
        r"STRING_AGG(\1, ',')",
        q,
        flags=re.IGNORECASE,
    )
    q = re.sub(
        r"strftime\('%H',\s*([^)]+)\)",
        r"FORMAT(\1, 'HH')",
        q,
        flags=re.IGNORECASE,
    )
    q = re.sub(
        r"strftime\('%Y-%m',\s*([^)]+)\)",
        r"FORMAT(\1, 'yyyy-MM')",
        q,
        flags=re.IGNORECASE,
    )
    q = re.sub(
        r"strftime\('%Y-%m-%d',\s*([^)]+)\)",
        r"CONVERT(VARCHAR(10), \1, 23)",
        q,
        flags=re.IGNORECASE,
    )
    m = re.search(r"\bLIMIT\s+(\d+)\s*$", q, flags=re.IGNORECASE)
    if m and re.match(r"^\s*SELECT\b", q, flags=re.IGNORECASE):
        limit_n = m.group(1)
        q = re.sub(r"\bLIMIT\s+\d+\s*$", "", q, flags=re.IGNORECASE)
        q = re.sub(r"^\s*SELECT\s+", f"SELECT TOP {limit_n} ", q, count=1, flags=re.IGNORECASE)
    return q


class CompatCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None

    def execute(self, sql, params=()):
        query = _sqlserverize(sql)
        self.lastrowid = None
        if sql.lstrip().upper().startswith("INSERT"):
            # Keep identity lookup in the same batch as INSERT.
            self._cursor.execute(f"{query}; SELECT CAST(SCOPE_IDENTITY() AS INT)", params)
            row = None
            # Advance to first result set that actually returns rows.
            while True:
                if self._cursor.description:
                    row = self._cursor.fetchone()
                    break
                if not self._cursor.nextset():
                    break
            self.lastrowid = int(row[0]) if row and row[0] is not None else None
            return self
        self._cursor.execute(query, params)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        columns = [c[0] for c in self._cursor.description]
        return SqlRow({columns[i]: row[i] for i in range(len(columns))})

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        columns = [c[0] for c in self._cursor.description]
        return [SqlRow({columns[i]: row[i] for i in range(len(columns))}) for row in rows]


class CompatConnection:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return CompatCursor(self._conn.cursor())

    def execute(self, sql, params=()):
        cur = CompatCursor(self._conn.cursor())
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

def get_db():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_DATABASE")

    if os.getenv("DB_TRUSTED_CONNECTION") == "yes":
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
        )
    else:
        user = os.getenv("DB_USERNAME")
        password = os.getenv("DB_PASSWORD")
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={user};PWD={password};"
        )

    return CompatConnection(pyodbc.connect(conn_str))


def reseed_identity_if_empty(conn, table_name: str, seed: int = 0) -> None:
    allowed_tables = {"customers"}
    if table_name not in allowed_tables:
        return
    row = conn.execute(f"SELECT COUNT(*) AS c FROM {table_name}").fetchone()
    total = int(row["c"] or 0) if row else 0
    if total != 0:
        return
    ident_row = conn.execute(f"SELECT IDENT_CURRENT('{table_name}') AS current_ident").fetchone()
    current_ident = ident_row["current_ident"] if ident_row else None
    if current_ident is None:
        return
    try:
        ident_num = int(float(current_ident))
    except (TypeError, ValueError):
        return
    if ident_num <= seed:
        return
    conn.execute(f"DBCC CHECKIDENT ('{table_name}', RESEED, {int(seed)})")
    conn.commit()


def extract_requirements(notes: str | None) -> list[str]:
    if not notes:
        return []
    for line in notes.splitlines():
        cleaned = str(line or "").strip()
        if not cleaned or not cleaned.lower().startswith("requirement"):
            continue
        raw = re.sub(r"^\s*requirements?\s*[:\-]?\s*", "", cleaned, flags=re.IGNORECASE).strip()
        parts = re.split(r"[,;|]", raw)
        values = [item.strip() for item in parts if item.strip()]
        if values:
            return values
    return []


def extract_payment_mode(notes: str | None) -> str:
    if not notes:
        return "-"
    for line in str(notes).splitlines():
        clean = line.strip()
        if not clean.lower().startswith("payment method:"):
            continue
        raw = clean.split(":", 1)[1].strip()
        if not raw:
            return "-"
        low = raw.lower()
        if low == "cash":
            return "Cash"
        if low == "gpay":
            return "GPay"
        if low == "card":
            return "Card"
        return raw
    return "-"


def fetch_order_measurements(
    conn,
    customer_id: int,
    order_id: int,
    order_created_at: str | None,
):
    direct_rows = conn.execute(
        "SELECT * FROM measurements WHERE order_id = ? ORDER BY id DESC",
        (order_id,),
    ).fetchall()
    if direct_rows:
        return direct_rows

    if not order_created_at:
        return conn.execute(
            "SELECT * FROM measurements WHERE customer_id = ? ORDER BY created_at DESC",
            (customer_id,),
        ).fetchall()

    orders = conn.execute(
        """
        SELECT id, created_at
        FROM orders
        WHERE customer_id = ?
        ORDER BY created_at DESC
        """,
        (customer_id,),
    ).fetchall()

    selected_index = None
    for idx, row in enumerate(orders):
        if int(row["id"]) == int(order_id):
            selected_index = idx
            break

    next_older_created_at = None
    if selected_index is not None and (selected_index + 1) < len(orders):
        next_older_created_at = orders[selected_index + 1]["created_at"]

    if next_older_created_at:
        rows = conn.execute(
            """
            SELECT * FROM measurements
            WHERE customer_id = ?
              AND created_at <= ?
              AND created_at > ?
            ORDER BY created_at DESC
            """,
            (customer_id, order_created_at, next_older_created_at),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM measurements
            WHERE customer_id = ?
              AND created_at <= ?
            ORDER BY created_at DESC
            """,
            (customer_id, order_created_at),
        ).fetchall()

    if rows:
        return rows
    return conn.execute(
        "SELECT * FROM measurements WHERE customer_id = ? ORDER BY created_at DESC",
        (customer_id,),
    ).fetchall()


def is_valid_phone(phone: str | None) -> bool:
    text = str(phone or "").strip()
    return bool(re.fullmatch(r"\+?[0-9]+", text))


def parse_measure_value(raw_value: str | None) -> float | None:
    text = str(raw_value or "").strip()
    if not text:
        return None
    normalized = text.replace(",", ".")
    if re.fullmatch(r"-?\d+(?:\.\d+)?", normalized):
        return float(normalized)
    if re.fullmatch(r"-?\d+\s+\d+/\d+|-?\d+/\d+", normalized):
        sign = -1 if normalized.startswith("-") else 1
        body = normalized[1:] if sign < 0 else normalized
        if " " in body:
            whole_text, frac_text = body.split(" ", 1)
            whole = int(whole_text)
        else:
            whole = 0
            frac_text = body
        num_text, den_text = frac_text.split("/", 1)
        den = int(den_text)
        if den == 0:
            return None
        frac = int(num_text) / den
        return sign * (whole + frac)
    return None


def norm_phone_digits(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def find_customer_by_phone(conn, raw_phone: str | None):
    phone_text = str(raw_phone or "").strip()
    if not phone_text:
        return None

    exact = conn.execute(
        "SELECT id, name, phone FROM customers WHERE phone = ?",
        (phone_text,),
    ).fetchone()
    if exact:
        return exact

    target_norm = norm_phone_digits(phone_text)
    if not target_norm:
        return None

    rows = conn.execute("SELECT id, name, phone FROM customers").fetchall()
    full_matches = [row for row in rows if norm_phone_digits(row["phone"]) == target_norm]
    if full_matches:
        return full_matches[0]

    if len(target_norm) >= 10:
        target_last10 = target_norm[-10:]
        last10_matches = [
            row
            for row in rows
            if len(norm_phone_digits(row["phone"])) >= 10
            and norm_phone_digits(row["phone"])[-10:] == target_last10
        ]
        if len(last10_matches) == 1:
            return last10_matches[0]
    return None


def fmt_measure(raw_value) -> str:
    text = str(raw_value or "").strip()
    if not text:
        return ""

    # Keep already-entered fraction styles untouched (e.g. "7 1/2", "1/3").
    if re.fullmatch(r"-?\d+\s+\d+/\d+|-?\d+/\d+", text):
        return text

    value: float
    if isinstance(raw_value, (int, float)):
        value = float(raw_value)
    elif re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        value = float(text)
    else:
        return text

    sign = "-" if value < 0 else ""
    absolute = abs(value)
    whole = int(absolute)
    frac = absolute - whole

    # Allowed fraction styles only.
    allowed = [
        (0, 1),
        (1, 4),
        (1, 3),
        (1, 2),
        (2, 3),
        (3, 4),
        (1, 1),
    ]
    num, den = min(allowed, key=lambda pair: abs(frac - (pair[0] / pair[1])))

    if num == den:
        whole += 1
        num = 0

    if num == 0:
        return f"{sign}{whole}"

    frac_text = f"{num}/{den}"
    if whole == 0:
        return f"{sign}{frac_text}"
    return f"{sign}{whole} {frac_text}"


@app.template_filter("fmt_measure")
def jinja_fmt_measure(raw_value) -> str:
    return fmt_measure(raw_value)


def date_only(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.date().isoformat()
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        try:
            return f"{int(value.year):04d}-{int(value.month):02d}-{int(value.day):02d}"
        except Exception:
            pass
    text = str(value).strip()
    if not text:
        return "-"
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", text)
    if m:
        return m.group(1)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        pass
    return text.split(" ", 1)[0]


@app.template_filter("date_only")
def jinja_date_only(value) -> str:
    return date_only(value)


def datetime_display(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    text = str(value).strip()
    if not text:
        return "-"
    m = re.match(r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})", text)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        pass
    d = date_only(text)
    return d if d != "-" else text


@app.template_filter("datetime_display")
def jinja_datetime_display(value) -> str:
    return datetime_display(value)


def normalize_payment_mode(mode: str | None, default: str = "Cash") -> str:
    allowed = {"Cash", "GPay", "Card"}
    text = str(mode or "").strip()
    return text if text in allowed else default


def customer_display_id(raw_id: int | None) -> int:
    if not raw_id or raw_id <= 0:
        return 0
    return raw_id


@app.route("/customers/lookup")
def customers_lookup():
    phone = request.args.get("phone", "").strip()
    if not phone or not is_valid_phone(phone):
        return jsonify({"found": False})

    conn = get_db()
    row = find_customer_by_phone(conn, phone)
    conn.close()
    if not row:
        return jsonify({"found": False})

    return jsonify(
        {
            "found": True,
            "id": int(row["id"]),
            "name": row["name"] or "",
            "phone": row["phone"] or "",
        }
    )


def fmt_id(raw_id: int | str | None, width: int = 4) -> str:
    try:
        value = int(raw_id or 0)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        return "-"
    return f"{value:0{width}d}"


@app.template_filter("fmt_id")
def jinja_fmt_id(raw_id: int | str | None, width: int = 4) -> str:
    return fmt_id(raw_id, width)


def fmt_order_id(raw_id: int | str | None, order_type: str | None = None) -> str:
    order_key = str(order_type or "").strip().lower()
    if order_key in {"material", "alteration"}:
        return fmt_id(raw_id, 4)
    return fmt_id(raw_id, 6)


@app.template_filter("fmt_order_id")
def jinja_fmt_order_id(raw_id: int | str | None, order_type: str | None = None) -> str:
    return fmt_order_id(raw_id, order_type)



# def init_db() -> None:
#     conn = get_db()
#     cur = conn.cursor()

#     # ---------- Gallery ----------
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS gallery_categories (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT NOT NULL UNIQUE
#         )
#     """)

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS gallery_items (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             category_id INTEGER NOT NULL,
#             item_name TEXT NOT NULL,
#             image_filename TEXT NOT NULL,
#             created_at TEXT NOT NULL,
#             FOREIGN KEY (category_id) REFERENCES gallery_categories (id)
#         )
#     """)

#     # ---------- Expenses / Salary ----------
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS expenses (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             expense_no TEXT UNIQUE,
#             expense_name TEXT NOT NULL,
#             amount REAL NOT NULL,
#             created_at TEXT NOT NULL
#         )
#     """)

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS salaries (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             expense_id INTEGER NOT NULL,
#             staff_no TEXT NOT NULL,
#             shift_no TEXT NOT NULL,
#             salary_amount REAL NOT NULL,
#             created_at TEXT NOT NULL,
#             FOREIGN KEY (expense_id) REFERENCES expenses (id)
#         )
#     """)

#     # ---------- Customers ----------
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS customers (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT NOT NULL,
#             phone TEXT NOT NULL UNIQUE,
#             address TEXT,
#             notes TEXT,
#             created_at TEXT NOT NULL
#         )
#     """)

#     cur.execute("PRAGMA table_info(customers)")
#     if "address" not in [r[1] for r in cur.fetchall()]:
#         cur.execute("ALTER TABLE customers ADD COLUMN address TEXT")

#     # ---------- Orders ----------
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS orders (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             customer_id INTEGER NOT NULL,
#             due_date TEXT,
#             status TEXT NOT NULL,
#             priority TEXT NOT NULL,
#             assigned_team TEXT,
#             assigned_tailor TEXT,
#             notes TEXT,
#             advance_amount REAL,
#             total_amount REAL,
#             paid_amount REAL,
#             order_type TEXT,
#             order_material_source TEXT,
#             inventory_applied INTEGER,
#             paid_at TEXT,
#             delivered_at TEXT,
#             completed_at TEXT,
#             picked_up_at TEXT,
#             cancelled_at TEXT,
#             created_at TEXT NOT NULL,
#             FOREIGN KEY (customer_id) REFERENCES customers (id)
#         )
#     """)

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS order_items (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             order_id INTEGER NOT NULL,
#             item_type TEXT NOT NULL,
#             qty INTEGER NOT NULL,
#             notes TEXT,
#             FOREIGN KEY (order_id) REFERENCES orders (id)
#         )
#     """)

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS order_images (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             order_id INTEGER NOT NULL,
#             filename TEXT NOT NULL,
#             label TEXT,
#             item_type TEXT,
#             FOREIGN KEY (order_id) REFERENCES orders (id)
#         )
#     """)

#     # ---------- Measurements ----------
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS measurements (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             customer_id INTEGER NOT NULL,
#             kind TEXT NOT NULL,
#             neck REAL,
#             chest REAL,
#             waist REAL,
#             hip REAL,
#             shoulder REAL,
#             sleeve REAL,
#             length REAL,
#             cuff REAL,
#             inseam REAL,
#             outseam REAL,
#             thigh REAL,
#             knee REAL,
#             bottom REAL,
#             assigned_tailor TEXT,
#             notes TEXT,
#             created_at TEXT NOT NULL,
#             FOREIGN KEY (customer_id) REFERENCES customers (id)
#         )
#     """)

#     # ---------- Tailors ----------
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS tailors (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             tailor_code TEXT UNIQUE,
#             name TEXT NOT NULL,
#             role TEXT NOT NULL,
#             phone TEXT NOT NULL,
#             status TEXT NOT NULL,
#             team TEXT
#         )
#     """)

#     # ---------- Inventory ----------
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS inventory (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             inventory_code TEXT UNIQUE,
#             name TEXT NOT NULL,
#             supplier TEXT,
#             qty INTEGER NOT NULL DEFAULT 0,
#             updated_at TEXT,
#             uom_id INTEGER
#         )
#     """)
#     cur.execute("PRAGMA table_info(inventory)")
#     inv_cols = [r[1] for r in cur.fetchall()]
#     if "cost_price" not in inv_cols:
#         cur.execute("ALTER TABLE inventory ADD COLUMN cost_price REAL")
#     if "selling_price" not in inv_cols:
#         cur.execute("ALTER TABLE inventory ADD COLUMN selling_price REAL")

#     # ---------- Categories ----------
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS categories (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT NOT NULL UNIQUE,
#             measurement_type TEXT NOT NULL
#         )
#     """)

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS subcategories (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             category_id INTEGER NOT NULL,
#             name TEXT NOT NULL,
#             UNIQUE(category_id, name),
#             FOREIGN KEY (category_id) REFERENCES categories (id)
#         )
#     """)

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS measurement_labels (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             category_id INTEGER NOT NULL,
#             subcategory_id INTEGER NOT NULL,
#             label TEXT NOT NULL
#         )
#     """)

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS measurement_fields (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             subcategory_id INTEGER NOT NULL,
#             field_key TEXT NOT NULL,
#             field_label TEXT NOT NULL,
#             sort_order INTEGER NOT NULL DEFAULT 0,
#             UNIQUE(subcategory_id, field_key)
#         )
#     """)

#     # ---------- Vendors ----------
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS vendors (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             vendor_code TEXT UNIQUE,
#             name TEXT NOT NULL,
#             phone TEXT,
#             email TEXT,
#             address TEXT,
#             created_at TEXT NOT NULL
#         )
#     """)

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS vendor_purchase_orders (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             vendor_id INTEGER NOT NULL,
#             total_amount REAL NOT NULL,
#             paid_amount REAL NOT NULL DEFAULT 0,
#             status TEXT NOT NULL,
#             notes TEXT,
#             purchased_at TEXT NOT NULL,
#             created_at TEXT NOT NULL
#         )
#     """)

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS vendor_purchase_items (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             purchase_id INTEGER NOT NULL,
#             inventory_id INTEGER NOT NULL,
#             uom_id INTEGER,
#             qty REAL NOT NULL,
#             unit_price REAL NOT NULL,
#             line_total REAL NOT NULL
#         )
#     """)
#     cur.execute("PRAGMA table_info(vendor_purchase_items)")
#     vpi_cols = [r[1] for r in cur.fetchall()]
#     if "selling_price" not in vpi_cols:
#         cur.execute("ALTER TABLE vendor_purchase_items ADD COLUMN selling_price REAL")

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS vendor_purchase_images (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             purchase_id INTEGER NOT NULL,
#             filename TEXT NOT NULL
#         )
#     """)

#     # ---------- UOM ----------
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS uoms (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT NOT NULL UNIQUE
#         )
#     """)

#     # ---------- Requirement Icons ----------
#     # cur.execute("""
#     #     CREATE TABLE IF NOT EXISTS requirement_icons (
#     #         id INTEGER PRIMARY KEY AUTOINCREMENT,
#     #         name TEXT NOT NULL,
#     #         icon TEXT NOT NULL
#     #     )
#     # """)

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS requirement_icons (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             name TEXT NOT NULL,
#             filename TEXT NOT NULL
#         )
#     """)

#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS app_settings (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             key TEXT NOT NULL UNIQUE,
#             value TEXT
#         )
#     """)
    
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS order_material_items (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             order_id INTEGER NOT NULL,
#             inventory_id INTEGER NOT NULL,
#             uom_id INTEGER,
#             qty REAL NOT NULL,
#             unit_price REAL,
#             notes TEXT,
#             FOREIGN KEY (order_id) REFERENCES orders (id),
#             FOREIGN KEY (inventory_id) REFERENCES inventory (id),
#             FOREIGN KEY (uom_id) REFERENCES uoms (id)
#         )
#     """)


#     cur.execute("PRAGMA table_info(requirement_icons)")
#     cols = [r[1] for r in cur.fetchall()]
#     if "icon" in cols and "filename" not in cols:
#         cur.execute("ALTER TABLE requirement_icons ADD COLUMN filename TEXT")

#     cur.execute("PRAGMA table_info(order_material_items)")
#     cols = [r[1] for r in cur.fetchall()]
#     if "uom_id" not in cols:
#         cur.execute("ALTER TABLE order_material_items ADD COLUMN uom_id INTEGER")
#     if "unit_price" not in cols:
#         cur.execute("ALTER TABLE order_material_items ADD COLUMN unit_price REAL")
#     if "line_total" not in cols:
#         cur.execute("ALTER TABLE order_material_items ADD COLUMN line_total REAL")

#     cur.execute("PRAGMA table_info(orders)")
#     cols = [r[1] for r in cur.fetchall()]
#     if "customer_display_id" not in cols:
#         cur.execute("ALTER TABLE orders ADD COLUMN customer_display_id INTEGER")

#     def seed_category_with_fields(
#         name: str,
#         measurement_type: str,
#         subcategories: list[str],
#         fields: list[tuple[str, str]],
#     ) -> None:
#         cur.execute(
#             "INSERT OR IGNORE INTO categories (name, measurement_type) VALUES (?, ?)",
#             (name, measurement_type),
#         )
#         row = cur.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
#         if not row:
#             return
#         category_id = row["id"]
#         for sub_name in subcategories:
#             cur.execute(
#                 "INSERT OR IGNORE INTO subcategories (category_id, name) VALUES (?, ?)",
#                 (category_id, sub_name),
#             )
#             sub_row = cur.execute(
#                 "SELECT id FROM subcategories WHERE category_id = ? AND name = ?",
#                 (category_id, sub_name),
#             ).fetchone()
#             if not sub_row:
#                 continue
#             sub_id = sub_row["id"]
#             for idx, (field_key, field_label) in enumerate(fields):
#                 cur.execute(
#                     """
#                     INSERT OR IGNORE INTO measurement_fields
#                         (subcategory_id, field_key, field_label, sort_order)
#                     VALUES (?, ?, ?, ?)
#                     """,
#                     (sub_id, field_key, field_label, idx),
#                 )

#     coat_subcategories = [
#         "Single Breasted Coat",
#         "Double Breasted Coat",
#         "Blazer",
#         "Long Coat",
#         "Short Coat",
#         "Formal Coat",
#         "Party Wear Coat",
#         "Winter Coat",
#         "Designer Coat",
#     ]
#     safari_subcategories = [
#         "Safari Suit",
#         "Safari Shirt",
#         "Safari Pant",
#         "Full Safari Set",
#         "Half Sleeve Safari",
#         "Full Sleeve Safari",
#         "Formal Safari",
#         "Cotton Safari",
#         "Khaki Safari",
#     ]
#     default_fields = [
#         ("height", "Height"),
#         ("body", "Body"),
#         ("shoulder", "Shoulder"),
#         ("chest", "Chest"),
#         ("waist", "Waist"),
#         ("hip", "Hip"),
#         ("sleeve_length", "Sleeve Length"),
#         ("length", "Length"),
#         ("neck", "Neck"),
#         ("collar", "Collar"),
#     ]

#     seed_category_with_fields("Coat", "Coat", coat_subcategories, default_fields)
#     seed_category_with_fields("Safari", "Safari", safari_subcategories, default_fields)

#     conn.commit()
#     conn.close()
#     conn = get_db()
#     tailor_rows = conn.execute("SELECT id, name FROM tailors").fetchall()
#     conn.close()
#     tailor_map = {row["name"]: row["id"] for row in tailor_rows}

def init_db():
    conn = get_db()
    cur = conn.cursor()

    def create(sql):
        cur.execute(sql)

    # ---------- Helper ----------
    def table_not_exists(name):
        return f"""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '{name}')
        BEGIN
        """

    def end():
        return "END"

    # ---------- Gallery ----------
    create(f"""
    {table_not_exists('gallery_categories')}
        CREATE TABLE gallery_categories (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255) NOT NULL UNIQUE
        )
    {end()}
    """)

    create(f"""
    {table_not_exists('gallery_items')}
        CREATE TABLE gallery_items (
            id INT IDENTITY(1,1) PRIMARY KEY,
            category_id INT NOT NULL,
            item_name NVARCHAR(255) NOT NULL,
            image_filename NVARCHAR(255) NOT NULL,
            created_at DATETIME2 NOT NULL,
            FOREIGN KEY (category_id) REFERENCES gallery_categories(id)
        )
    {end()}
    """)

    # ---------- Expenses ----------
    create(f"""
    {table_not_exists('expenses')}
        CREATE TABLE expenses (
            id INT IDENTITY(1,1) PRIMARY KEY,
            expense_no NVARCHAR(100) UNIQUE,
            expense_name NVARCHAR(255) NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            created_at DATETIME2 NOT NULL
        )
    {end()}
    """)

    create(f"""
    {table_not_exists('salaries')}
        CREATE TABLE salaries (
            id INT IDENTITY(1,1) PRIMARY KEY,
            expense_id INT NOT NULL,
            staff_no NVARCHAR(100) NOT NULL,
            shift_no NVARCHAR(100) NOT NULL,
            salary_amount DECIMAL(10,2) NOT NULL,
            created_at DATETIME2 NOT NULL,
            FOREIGN KEY (expense_id) REFERENCES expenses(id)
        )
    {end()}
    """)

    # ---------- Customers ----------
    create(f"""
    {table_not_exists('customers')}
        CREATE TABLE customers (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255) NOT NULL,
            phone NVARCHAR(50) NOT NULL UNIQUE,
            address NVARCHAR(MAX),
            notes NVARCHAR(MAX),
            created_at DATETIME2 NOT NULL
        )
    {end()}
    """)

    # ---------- Orders ----------
    create(f"""
    {table_not_exists('orders')}
        CREATE TABLE orders (
            id INT IDENTITY(1,1) PRIMARY KEY,
            customer_id INT NOT NULL,
            due_date DATETIME2,
            status NVARCHAR(50) NOT NULL,
            priority NVARCHAR(50) NOT NULL,
            assigned_team NVARCHAR(100),
            assigned_tailor NVARCHAR(100),
            notes NVARCHAR(MAX),
            advance_amount DECIMAL(10,2),
            discount_amount DECIMAL(10,2),
            total_amount DECIMAL(10,2),
            taxable_amount DECIMAL(10,2),
            gst_percent DECIMAL(10,2),
            gst_amount DECIMAL(10,2),
            cgst_percent DECIMAL(10,2),
            cgst_amount DECIMAL(10,2),
            sgst_percent DECIMAL(10,2),
            sgst_amount DECIMAL(10,2),
            paid_amount DECIMAL(10,2),
            order_type NVARCHAR(50),
            order_material_source NVARCHAR(50),
            inventory_applied BIT,
            paid_at DATETIME2,
            delivered_at DATETIME2,
            completed_at DATETIME2,
            picked_up_at DATETIME2,
            cancelled_at DATETIME2,
            created_at DATETIME2 NOT NULL,
            customer_display_id INT,
            invoice_id NVARCHAR(20),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    {end()}
    """)

    # ---------- Order Items ----------
    create(f"""
    {table_not_exists('order_items')}
        CREATE TABLE order_items (
            id INT IDENTITY(1,1) PRIMARY KEY,
            order_id INT NOT NULL,
            item_type NVARCHAR(100) NOT NULL,
            qty INT NOT NULL,
            notes NVARCHAR(MAX),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    {end()}
    """)

    create(f"""
    {table_not_exists('order_images')}
        CREATE TABLE order_images (
            id INT IDENTITY(1,1) PRIMARY KEY,
            order_id INT NOT NULL,
            filename NVARCHAR(255) NOT NULL,
            label NVARCHAR(255),
            item_type NVARCHAR(100),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    {end()}
    """)

    # ---------- Measurements ----------
    create(f"""
    {table_not_exists('measurements')}
        CREATE TABLE measurements (
            id INT IDENTITY(1,1) PRIMARY KEY,
            customer_id INT NOT NULL,
            order_id INT NULL,
            measure_status NVARCHAR(50),
            kind NVARCHAR(100) NOT NULL,
            neck FLOAT,
            chest FLOAT,
            waist FLOAT,
            hip FLOAT,
            shoulder FLOAT,
            sleeve FLOAT,
            length FLOAT,
            cuff FLOAT,
            inseam FLOAT,
            outseam FLOAT,
            thigh FLOAT,
            knee FLOAT,
            bottom FLOAT,
            assigned_tailor NVARCHAR(100),
            notes NVARCHAR(MAX),
            created_at DATETIME2 NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    {end()}
    """)

    # ---------- Tailors ----------
    create(f"""
    {table_not_exists('tailors')}
        CREATE TABLE tailors (
            id INT IDENTITY(1,1) PRIMARY KEY,
            tailor_code NVARCHAR(50) UNIQUE,
            name NVARCHAR(255) NOT NULL,
            role NVARCHAR(100) NOT NULL,
            phone NVARCHAR(50) NOT NULL,
            status NVARCHAR(50) NOT NULL,
            team NVARCHAR(100)
        )
    {end()}
    """)

    # ---------- Inventory ----------
    create(f"""
    {table_not_exists('inventory')}
        CREATE TABLE inventory (
            id INT IDENTITY(1,1) PRIMARY KEY,
            inventory_code NVARCHAR(50) UNIQUE,
            name NVARCHAR(255) NOT NULL,
            supplier NVARCHAR(255),
            qty INT NOT NULL DEFAULT 0,
            updated_at DATETIME2,
            uom_id INT,
            cost_price DECIMAL(10,2),
            selling_price DECIMAL(10,2)
        )
    {end()}
    """)

    # ---------- Categories ----------
    create(f"""
    {table_not_exists('categories')}
        CREATE TABLE categories (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255) NOT NULL UNIQUE,
            measurement_type NVARCHAR(100) NOT NULL,
            sort_order INT NOT NULL DEFAULT 0
        )
    {end()}
    """)

    create(f"""
    {table_not_exists('subcategories')}
        CREATE TABLE subcategories (
            id INT IDENTITY(1,1) PRIMARY KEY,
            category_id INT NOT NULL,
            name NVARCHAR(255) NOT NULL,
            CONSTRAINT uq_sub UNIQUE(category_id, name),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    {end()}
    """)

    create(f"""
    {table_not_exists('measurement_fields')}
        CREATE TABLE measurement_fields (
            id INT IDENTITY(1,1) PRIMARY KEY,
            subcategory_id INT NOT NULL,
            field_key NVARCHAR(100) NOT NULL,
            field_label NVARCHAR(255) NOT NULL,
            sort_order INT NOT NULL DEFAULT 0,
            CONSTRAINT uq_fields UNIQUE(subcategory_id, field_key)
        )
    {end()}
    """)

    create(f"""
    {table_not_exists('requirement_icons')}
        CREATE TABLE requirement_icons (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(255) NOT NULL UNIQUE,
            filename NVARCHAR(255) NOT NULL,
            sort_order INT NOT NULL DEFAULT 0
        )
    {end()}
    """)

    # ---------- Vendors ----------
    create(f"""
    {table_not_exists('vendors')}
        CREATE TABLE vendors (
            id INT IDENTITY(1,1) PRIMARY KEY,
            vendor_code NVARCHAR(50) UNIQUE,
            name NVARCHAR(255) NOT NULL,
            phone NVARCHAR(50),
            email NVARCHAR(255),
            address NVARCHAR(MAX),
            created_at DATETIME2 NOT NULL
        )
    {end()}
    """)

    # ---------- UOM ----------
    create(f"""
    {table_not_exists('uoms')}
        CREATE TABLE uoms (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(100) NOT NULL UNIQUE
        )
    {end()}
    """)

    # ---------- App Settings ----------
    create(f"""
    {table_not_exists('app_settings')}
        CREATE TABLE app_settings (
            id INT IDENTITY(1,1) PRIMARY KEY,
            [key] NVARCHAR(100) NOT NULL UNIQUE,
            value NVARCHAR(MAX)
        )
    {end()}
    """)

    create(f"""
    {table_not_exists('order_notifications')}
        CREATE TABLE order_notifications (
            id INT IDENTITY(1,1) PRIMARY KEY,
            order_id INT NOT NULL,
            event_type NVARCHAR(50) NOT NULL,
            message NVARCHAR(255),
            event_time DATETIME2 NOT NULL,
            is_read BIT NOT NULL DEFAULT 0,
            created_at DATETIME2 NOT NULL,
            CONSTRAINT uq_order_notifications UNIQUE(order_id, event_type),
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    {end()}
    """)

    # ---------- Category name normalization ----------
    # Keep user-defined names (e.g. Shirt, Pant) instead of numeric IDs.
    create("""
    UPDATE categories
    SET name = 'Shirt'
    WHERE UPPER(LTRIM(RTRIM(name))) = 'S001'
    """)

    create("""
    UPDATE categories
    SET name = 'Pant'
    WHERE UPPER(LTRIM(RTRIM(name))) = 'P001'
    """)

    create("""
    UPDATE order_items
    SET item_type = REPLACE(
        REPLACE(
            REPLACE(
                REPLACE(item_type, 'S001 -', 'Shirt -'),
                'P001 -', 'Pant -'
            ),
            'S001', 'Shirt'
        ),
        'P001', 'Pant'
    )
    WHERE item_type LIKE '%S001%' OR item_type LIKE '%P001%'
    """)

    create("""
    UPDATE measurements
    SET kind = REPLACE(
        REPLACE(
            REPLACE(
                REPLACE(kind, 'S001 -', 'Shirt -'),
                'P001 -', 'Pant -'
            ),
            'S001', 'Shirt'
        ),
        'P001', 'Pant'
    )
    WHERE kind LIKE '%S001%' OR kind LIKE '%P001%'
    """)

    create("""
    UPDATE order_images
    SET item_type = REPLACE(
        REPLACE(
            REPLACE(
                REPLACE(item_type, 'S001 -', 'Shirt -'),
                'P001 -', 'Pant -'
            ),
            'S001', 'Shirt'
        ),
        'P001', 'Pant'
    )
    WHERE item_type LIKE '%S001%' OR item_type LIKE '%P001%'
    """)

    # ---------- Schema updates ----------
    create("""
    IF COL_LENGTH('orders', 'order_no') IS NULL
    BEGIN
        ALTER TABLE orders ADD order_no NVARCHAR(20) NULL
    END
    """)

    create("""
    IF COL_LENGTH('orders', 'invoice_id') IS NULL
    BEGIN
        ALTER TABLE orders ADD invoice_id NVARCHAR(20) NULL
    END
    """)

    create("""
    IF COL_LENGTH('orders', 'customer_display_id') IS NULL
    BEGIN
        ALTER TABLE orders ADD customer_display_id INT NULL
    END
    """)

    create("""
    IF COL_LENGTH('orders', 'discount_amount') IS NULL
    BEGIN
        ALTER TABLE orders ADD discount_amount DECIMAL(10,2) NULL
    END
    """)

    create("""
    IF COL_LENGTH('orders', 'taxable_amount') IS NULL
    BEGIN
        ALTER TABLE orders ADD taxable_amount DECIMAL(10,2) NULL
    END
    """)

    create("""
    IF COL_LENGTH('orders', 'gst_percent') IS NULL
    BEGIN
        ALTER TABLE orders ADD gst_percent DECIMAL(10,2) NULL
    END
    """)

    create("""
    IF COL_LENGTH('orders', 'gst_amount') IS NULL
    BEGIN
        ALTER TABLE orders ADD gst_amount DECIMAL(10,2) NULL
    END
    """)

    create("""
    IF COL_LENGTH('orders', 'cgst_percent') IS NULL
    BEGIN
        ALTER TABLE orders ADD cgst_percent DECIMAL(10,2) NULL
    END
    """)

    create("""
    IF COL_LENGTH('orders', 'cgst_amount') IS NULL
    BEGIN
        ALTER TABLE orders ADD cgst_amount DECIMAL(10,2) NULL
    END
    """)

    create("""
    IF COL_LENGTH('orders', 'sgst_percent') IS NULL
    BEGIN
        ALTER TABLE orders ADD sgst_percent DECIMAL(10,2) NULL
    END
    """)

    create("""
    IF COL_LENGTH('orders', 'sgst_amount') IS NULL
    BEGIN
        ALTER TABLE orders ADD sgst_amount DECIMAL(10,2) NULL
    END
    """)

    create("""
    UPDATE orders
    SET customer_display_id = customer_id
    WHERE customer_display_id IS NULL
    """)

    create("""
    IF COL_LENGTH('measurements', 'order_id') IS NULL
    BEGIN
        ALTER TABLE measurements ADD order_id INT NULL
    END
    """)

    create("""
    IF COL_LENGTH('measurements', 'measure_status') IS NULL
    BEGIN
        ALTER TABLE measurements ADD measure_status NVARCHAR(50) NULL
    END
    """)

    create("""
    UPDATE m
    SET m.measure_status = ISNULL(NULLIF(LTRIM(RTRIM(o.status)), ''), 'In-Progress')
    FROM measurements m
    JOIN orders o ON o.id = m.order_id
    WHERE m.measure_status IS NULL
    """)

    create("""
    IF COL_LENGTH('categories', 'sort_order') IS NULL
    BEGIN
        ALTER TABLE categories ADD sort_order INT NOT NULL DEFAULT 0
    END
    """)

    create("""
    IF OBJECT_ID('requirement_icons', 'U') IS NOT NULL
       AND COL_LENGTH('requirement_icons', 'sort_order') IS NULL
    BEGIN
        ALTER TABLE requirement_icons ADD sort_order INT NOT NULL DEFAULT 0
    END
    """)

    create("""
    IF COL_LENGTH('categories', 'sort_order') IS NOT NULL
    BEGIN
        ;WITH ordered AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY ISNULL(sort_order, 0), id) - 1 AS rn
            FROM categories
        )
        UPDATE c
        SET sort_order = o.rn
        FROM categories c
        JOIN ordered o ON o.id = c.id
    END
    """)

    create("""
    IF OBJECT_ID('requirement_icons', 'U') IS NOT NULL
       AND COL_LENGTH('requirement_icons', 'sort_order') IS NOT NULL
    BEGIN
        ;WITH ordered AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY ISNULL(sort_order, 0), id) - 1 AS rn
            FROM requirement_icons
        )
        UPDATE r
        SET sort_order = o.rn
        FROM requirement_icons r
        JOIN ordered o ON o.id = r.id
    END
    """)

    create("""
    ;WITH base AS (
        SELECT 'T' AS pfx,
               ISNULL(MAX(
                   CASE
                       WHEN order_no LIKE 'T%' THEN TRY_CAST(SUBSTRING(order_no, 2, 20) AS INT)
                       ELSE TRY_CAST(order_no AS INT)
                   END
               ), 0) AS max_num
        FROM orders
        WHERE LOWER(ISNULL(order_type, '')) = 'tailoring'
          AND (
              order_no LIKE 'T%'
              OR TRY_CAST(order_no AS INT) IS NOT NULL
          )
        UNION ALL
        SELECT 'A' AS pfx, ISNULL(MAX(TRY_CAST(SUBSTRING(order_no, 2, 20) AS INT)), 0) AS max_num
        FROM orders WHERE order_no LIKE 'A%'
        UNION ALL
        SELECT 'M' AS pfx, ISNULL(MAX(TRY_CAST(SUBSTRING(order_no, 2, 20) AS INT)), 0) AS max_num
        FROM orders WHERE order_no LIKE 'M%'
    ),
    pending AS (
        SELECT
            o.id,
            CASE
                WHEN LOWER(ISNULL(o.order_type, '')) = 'tailoring' THEN 'T'
                WHEN LOWER(ISNULL(o.order_type, '')) = 'alteration' THEN 'A'
                ELSE 'M'
            END AS pfx,
            ROW_NUMBER() OVER (
                PARTITION BY
                    CASE
                        WHEN LOWER(ISNULL(o.order_type, '')) = 'tailoring' THEN 'T'
                        WHEN LOWER(ISNULL(o.order_type, '')) = 'alteration' THEN 'A'
                        ELSE 'M'
                    END
                ORDER BY o.created_at, o.id
            ) AS rn
        FROM orders o
        WHERE o.order_no IS NULL OR LTRIM(RTRIM(o.order_no)) = ''
    )
    UPDATE o
    SET o.order_no = CASE
        WHEN p.pfx = 'T' THEN RIGHT('000000' + CAST((b.max_num + p.rn) AS VARCHAR(10)), 6)
        ELSE p.pfx + RIGHT('0000' + CAST((b.max_num + p.rn) AS VARCHAR(10)), 4)
    END
    FROM orders o
    JOIN pending p ON p.id = o.id
    JOIN base b ON b.pfx = p.pfx
    """)

    create("""
    IF OBJECT_ID('vendor_purchase_orders', 'U') IS NOT NULL
       AND COL_LENGTH('vendor_purchase_orders', 'purchase_no') IS NULL
    BEGIN
        ALTER TABLE vendor_purchase_orders ADD purchase_no NVARCHAR(20) NULL
    END
    """)

    create("""
    IF OBJECT_ID('vendor_purchase_orders', 'U') IS NOT NULL
       AND COL_LENGTH('vendor_purchase_orders', 'payment_mode') IS NULL
    BEGIN
        ALTER TABLE vendor_purchase_orders ADD payment_mode NVARCHAR(20) NULL
    END
    """)

    create("""
    IF OBJECT_ID('vendor_purchase_items', 'U') IS NOT NULL
       AND COL_LENGTH('vendor_purchase_items', 'item_name_snapshot') IS NULL
    BEGIN
        ALTER TABLE vendor_purchase_items ADD item_name_snapshot NVARCHAR(255) NULL
    END
    """)

    create("""
    IF OBJECT_ID('vendor_purchase_orders', 'U') IS NOT NULL
    BEGIN
        ;WITH base AS (
            SELECT ISNULL(MAX(TRY_CAST(SUBSTRING(purchase_no, 2, 20) AS INT)), 0) AS max_num
            FROM vendor_purchase_orders
            WHERE purchase_no LIKE 'M%'
        ),
        pending AS (
            SELECT
                vpo.id,
                ROW_NUMBER() OVER (ORDER BY vpo.purchased_at, vpo.id) AS rn
            FROM vendor_purchase_orders vpo
            WHERE vpo.purchase_no IS NULL OR LTRIM(RTRIM(vpo.purchase_no)) = ''
        )
        UPDATE vpo
        SET vpo.purchase_no = 'M' + RIGHT('0000' + CAST((b.max_num + p.rn) AS VARCHAR(10)), 4)
        FROM vendor_purchase_orders vpo
        JOIN pending p ON p.id = vpo.id
        CROSS JOIN base b
    END
    """)

    create("""
    IF OBJECT_ID('vendor_purchase_orders', 'U') IS NOT NULL
    BEGIN
        UPDATE vendor_purchase_orders
        SET payment_mode = 'Cash'
        WHERE payment_mode IS NULL OR LTRIM(RTRIM(payment_mode)) = ''
    END
    """)

    create("""
    IF OBJECT_ID('vendor_purchase_items', 'U') IS NOT NULL
       AND OBJECT_ID('inventory', 'U') IS NOT NULL
    BEGIN
        UPDATE vpi
        SET item_name_snapshot = i.name
        FROM vendor_purchase_items vpi
        LEFT JOIN inventory i ON i.id = vpi.inventory_id
        WHERE vpi.item_name_snapshot IS NULL OR LTRIM(RTRIM(vpi.item_name_snapshot)) = ''
    END
    """)

    create("""
    IF OBJECT_ID('order_notifications', 'U') IS NOT NULL
    BEGIN
        INSERT INTO order_notifications (order_id, event_type, message, event_time, created_at)
        SELECT
            o.id,
            'completed',
            'Order completed',
            ISNULL(o.completed_at, o.created_at),
            ISNULL(o.completed_at, o.created_at)
        FROM orders o
        WHERE LOWER(ISNULL(o.status, '')) = 'completed'
          AND NOT EXISTS (
              SELECT 1
              FROM order_notifications n
              WHERE n.order_id = o.id
                AND n.event_type = 'completed'
          )
    END
    """)

    conn.commit()
    conn.close()


@app.before_request
def ensure_db_ready() -> None:
    global _db_ready
    if not _db_ready:
        init_db()
        _db_ready = True


@app.before_request
def require_login():
    public_endpoints = {"login", "logout", "static", "fonts"}
    endpoint = request.endpoint or ""
    if endpoint in public_endpoints:
        return None
    if endpoint.startswith("static"):
        return None
    if session.get("is_authenticated"):
        return None
    return redirect(url_for("login", next=request.path))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("is_authenticated"):
        return redirect(url_for("dashboard"))

    error = None
    next_url = request.args.get("next", url_for("dashboard"))
    login_username = get_setting("login_username", "admin").strip() or "admin"
    login_password = get_setting("login_password", "123")
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        next_url = (request.form.get("next") or url_for("dashboard")).strip() or url_for("dashboard")
        if username == login_username and password == login_password:
            session["is_authenticated"] = True
            session["username"] = login_username
            if (
                not next_url.startswith("/")
                or next_url.startswith("//")
                or next_url == url_for("login")
            ):
                next_url = url_for("dashboard")
            return redirect(next_url)
        error = "Invalid username or password."

    return render_template("login.html", error=error, next_url=next_url)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def create_completed_notification(conn, order_id: int, event_time: str | None = None) -> None:
    if not order_id:
        return
    existing = conn.execute(
        """
        SELECT TOP 1 id
        FROM order_notifications
        WHERE order_id = ? AND event_type = 'completed'
        """,
        (order_id,),
    ).fetchone()
    if existing:
        return
    stamp = event_time or now_str()
    conn.execute(
        """
        INSERT INTO order_notifications (order_id, event_type, message, event_time, created_at)
        VALUES (?, 'completed', ?, ?, ?)
        """,
        (order_id, "Order completed", stamp, stamp),
    )


def sync_completed_notification(conn, order_id: int, previous_status: str, new_status: str, completed_at: str | None = None) -> None:
    if not order_id:
        return
    if new_status == "Completed":
        if previous_status != "Completed":
            create_completed_notification(conn, order_id, completed_at)
        return
    conn.execute(
        """
        DELETE FROM order_notifications
        WHERE order_id = ? AND event_type = 'completed'
        """,
        (order_id,),
    )

def generate_expense_no(conn: sqlite3.Connection) -> str:
    cur = conn.cursor()
    cur.execute("SELECT expense_no FROM expenses ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()

    if row:
        last_num = int(row["expense_no"].split("-")[1])
        return f"EXP-{last_num + 1:04d}"

    return "EXP-0001"


def _order_type_prefix(order_type: str | None) -> str:
    key = (order_type or "").strip().lower()
    if key == "tailoring":
        return "T"
    if key == "alteration":
        return "A"
    return "M"


# def generate_order_no(conn: sqlite3.Connection, order_type: str) -> str:
#     prefix = _order_type_prefix(order_type)
#     if prefix == "T":
#         row = conn.execute(
#             """
#             SELECT MAX(
#                 CASE
#                     WHEN order_no LIKE 'T%' THEN TRY_CAST(SUBSTRING(order_no, 2, 20) AS INT)
#                     ELSE TRY_CAST(order_no AS INT)
#                 END
#             ) AS max_num
#             FROM orders
#             WHERE LOWER(ISNULL(order_type, '')) = 'tailoring'
#               AND (
#                   order_no LIKE 'T%'
#                   OR TRY_CAST(order_no AS INT) IS NOT NULL
#               )
#             """
#         ).fetchone()
#         max_num = int(row["max_num"] or 0) if row else 0
#         return f"{max_num + 1:06d}"
#     row = conn.execute(
#         """
#         SELECT MAX(TRY_CAST(SUBSTRING(order_no, 2, 20) AS INT)) AS max_num
#         FROM orders
#         WHERE order_no LIKE ?
#         """,
#         (f"{prefix}%",),
#     ).fetchone()
#     max_num = int(row["max_num"] or 0) if row else 0
#     return f"{prefix}{max_num + 1:04d}"

def generate_order_no(conn: sqlite3.Connection, customer_id: int) -> str:
    # 1ï¸âƒ£ Convert customer id â†’ 6 digit
    customer_part = str(customer_id).zfill(6)

    # 2ï¸âƒ£ Find last order number for this customer
    row = conn.execute(
        """
        SELECT MAX(
            TRY_CAST(
                SUBSTRING(order_no, CHARINDEX('\\', order_no) + 1, 10
            ) AS INT)
        ) AS max_order
        FROM orders
        WHERE customer_id = ?
        """,
        (customer_id,)
    ).fetchone()

    last_order = int(row["max_order"] or 0) if row else 0

    # 3ï¸âƒ£ Next order number
    next_order = last_order + 1

    # 4ï¸âƒ£ Final order id
    order_no = f"{customer_part}\\{next_order}"

    return order_no


def generate_invoice_id(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        """
        SELECT ISNULL(MAX(TRY_CAST(SUBSTRING(invoice_id, 4, 20) AS INT)), 0) AS max_num
        FROM orders
        WHERE invoice_id LIKE 'INV%'
        """
    ).fetchone()
    next_num = (int(row["max_num"] or 0) if row else 0) + 1
    return f"INV{next_num:03d}"

def display_order_no(order: dict) -> str:
    existing = str(order.get("order_no") or "").strip()
    prefix = _order_type_prefix(order.get("order_type"))
    if existing:
        if prefix == "T":
            if existing.isdigit():
                return f"{int(existing):06d}"
            if existing.upper().startswith("T") and existing[1:].isdigit():
                return f"{int(existing[1:]):06d}"
        return existing
    try:
        base_id = int(order.get("id") or 0)
    except (TypeError, ValueError):
        base_id = 0
    if prefix == "T":
        return f"{base_id:06d}" if base_id > 0 else "000001"
    return f"{prefix}{base_id:04d}" if base_id > 0 else f"{prefix}NEW"


def generate_purchase_no(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        """
        SELECT MAX(TRY_CAST(SUBSTRING(purchase_no, 2, 20) AS INT)) AS max_num
        FROM vendor_purchase_orders
        WHERE purchase_no LIKE 'M%'
        """
    ).fetchone()
    max_num = int(row["max_num"] or 0) if row else 0
    return f"M{max_num + 1:04d}"

def generate_expense_pdf_80mm(
    expense_no: str,
    name: str,
    amount: float,
    created_at: str,
    is_salary: bool = False,
    staff_no: str | None = None
):
    folder = os.path.join(APP_DIR, "static", "expense_pdfs")
    os.makedirs(folder, exist_ok=True)

    file_path = os.path.join(folder, f"{expense_no}.pdf")

    height = 140 * mm
    pdf = canvas.Canvas(file_path, pagesize=(THERMAL_WIDTH, height))
    regular_font, bold_font = get_reportlab_tamil_fonts()

    y = height - 10 * mm

    # def line(text, bold=False):
    #     nonlocal y
    #     pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 9)
    #     pdf.drawString(5 * mm, y, text)
    #     y -= 5 * mm
    def line(text, bold=False):
        nonlocal y
        pdf.setFont(bold_font if bold else regular_font, 9)
        pdf.drawString(5 * mm, y, text)
        y -= 5 * mm

    # HEADER
    line("PREMIER TAILORS", bold=True)
    line("Salary Receipt" if is_salary else "Expense Receipt", bold=True)
    line("-" * 32)

    # INFO
    line(f"Receipt No : {expense_no}")
    line(f"Date       : {date_only(created_at)}")

    if is_salary and staff_no:
        line(f"Staff No   : {staff_no}")

    line("-" * 32)

    # BODY
    if is_salary:
        line("Salary Paid To:")
        line(name)
        line(f"Salary Amount : â‚¹ {amount}", bold=True)
    else:
        line("Expense:")
        line(name)
        line(f"Amount : â‚¹ {amount}", bold=True)

    line("-" * 32)
    line("Thank you", bold=True)
    line("System Generated")

    pdf.showPage()
    pdf.save()


# def generate_order_pdf_80mm(order, measurements, order_items, mode: str = "tailor") -> str:
#     folder = os.path.join(APP_DIR, "static", "order_pdfs")
#     os.makedirs(folder, exist_ok=True)
#     file_path = os.path.join(folder, f"order_{order['id']}.pdf")

#     label_map = {
#         "neck": "Neck",
#         "chest": "Chest",
#         "waist": "Waist",
#         "hip": "Hip",
#         "shoulder": "Shoulder",
#         "sleeve": "Sleeve",
#         "length": "Length",
#         "cuff": "Cuff",
#         "inseam": "Inseam",
#         "outseam": "Outseam",
#         "thigh": "Thigh",
#         "knee": "Knee",
#         "bottom": "Bottom",
#     }

#     mode = mode.lower().strip() if mode else "tailor"
#     assigned_tailor = order["assigned_tailor"] or "Tailor"
#     if mode == "customer":
#         lines = [
#             "Customer Order Slip",
#             f"Order ID: #{order['id']}",
#             f"Customer: {order['name']}",
#             f"Phone: {order['phone']}",
#             f"Address: {order['address'] or '-'}",
#             f"Order Date: {order['created_at'] or '-'}",
#             f"Delivery Date: {order['due_date'] or '-'}",
#             "",
#         ]
#         total_amount = float(order.get("total_amount") or 0)
#         advance_amount = float(order.get("advance_amount") or 0)
#         paid_amount = float(order.get("paid_amount") or 0)
#         due_amount = max(total_amount - advance_amount - paid_amount, 0)
#         lines.extend(
#             [
#                 "Payment:",
#                 f"Total: â‚¹ {total_amount:.2f}",
#                 f"Advance: â‚¹ {advance_amount:.2f}",
#                 f"Paid: â‚¹ {paid_amount:.2f}",
#                 f"Due: â‚¹ {due_amount:.2f}",
#             ]
#         )
#     else:
#         lines = []

#     if mode != "customer":
#         for m in measurements:
#             kind = m["kind"] or "Measurement"
#             lines.append(f"[KIND]{kind}")
#             for key, label in label_map.items():
#                 value = m[key]
#                 if value:
#                     lines.append((label, str(value)))
#             if m["notes"]:
#                 lines.append(("Notes", m["notes"]))

#     line_height = 4 * mm
#     if mode == "customer":
#         line_count = len(lines)
#     else:
#         line_count = 3  # header + divider
#         if order_items:
#             line_count += 2 + len(order_items) + 1  # title + header + rows + divider
#         line_count += 2  # measurements title + header
#         for line in lines:
#             line_count += 1
#     height = max(80 * mm, (line_count + 6) * line_height)
#     pdf = canvas.Canvas(file_path, pagesize=(THERMAL_WIDTH, height))
#     y = height - 6 * mm

#     def draw(text, bold=False):
#         nonlocal y
#         pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 9)
#         pdf.drawString(5 * mm, y, text)
#         y -= line_height

#     if mode == "customer":
#         for i, line in enumerate(lines):
#             draw(line, bold=(i == 0))
#     else:
#         left_x = 5 * mm
#         right_x = THERMAL_WIDTH - (5 * mm)
#         col_item = left_x
#         col_mid = 50 * mm
#         col_right = right_x

#         pdf.setFont("Helvetica-Bold", 9)
#         pdf.drawCentredString(THERMAL_WIDTH / 2, y, f"{assigned_tailor} Order Slip")
#         y -= line_height
#         pdf.setFont("Helvetica", 9)
#         pdf.drawString(left_x, y, f"Order ID: #{order['id']}")
#         customer_text = f"Customer: {order['name']}"
#         pdf.drawString(right_x - pdf.stringWidth(customer_text, "Helvetica", 9), y, customer_text)
#         y -= line_height
#         pdf.line(left_x, y + 2, right_x, y + 2)

#         if order_items:
#             y -= line_height
#             pdf.setFont("Helvetica-Bold", 9)
#             pdf.drawString(left_x, y, "Items")
#             pdf.drawString(col_mid, y, "Qty")
#             y -= line_height
#             pdf.setFont("Helvetica", 9)
#             for item in order_items:
#                 item_type = item["item_type"] or "Item"
#                 qty = str(item["qty"] or 0)
#                 pdf.drawString(left_x, y, item_type)
#                 pdf.drawRightString(right_x, y, qty)
#                 y -= line_height
#             pdf.line(left_x, y + 2, right_x, y + 2)

#         y -= line_height
#         pdf.setFont("Helvetica-Bold", 9)
#         pdf.drawString(left_x, y, "Measurements")
#         y -= line_height
#         pdf.drawString(left_x, y, "Field")
#         pdf.drawRightString(right_x, y, "Value")
#         y -= line_height
#         pdf.setFont("Helvetica", 9)
#         for line in lines:
#             if isinstance(line, tuple):
#                 label, value = line
#                 pdf.drawString(left_x, y, label)
#                 pdf.drawRightString(right_x, y, value)
#                 y -= line_height
#             else:
#                 if line.startswith("[KIND]"):
#                     kind = line.replace("[KIND]", "", 1)
#                     pdf.setFont("Helvetica-Bold", 9)
#                     pdf.drawString(left_x, y, kind)
#                     y -= line_height
#                     pdf.setFont("Helvetica", 9)
#                 else:
#                     draw(line)

#     pdf.showPage()
#     pdf.save()
#     return file_path

def generate_order_pdf_80mm(
    order,
    measurements,
    order_items,
    mode: str = "tailor",
    landscape: bool = False,
    tailor_paper: str = "a4",
) -> str:
    def ensure_rupee_font() -> tuple[str, str, str, str]:
        # Prefer Tamil-capable Unicode fonts first so print output matches UI text.
        regular_candidates = [
            r"C:\Windows\Fonts\Nirmala.ttf",
            r"C:\Windows\Fonts\Latha.ttf",
            r"C:\Windows\Fonts\Vijaya.ttf",
            os.path.join(FONTS_FOLDER, "Nirmala.ttf"),
            os.path.join(FONTS_FOLDER, "Latha.ttf"),
            os.path.join(FONTS_FOLDER, "Vijaya.ttf"),
            os.path.join(FONTS_FOLDER, "NotoSansTamil-Regular.ttf"),
            os.path.join(APP_DIR, "fonts", "SunTommy.ttf"),
            os.path.join(APP_DIR, "fonts", "suntommy.ttf"),
            os.path.join(APP_DIR, "fonts", "Bamini.ttf"),
            os.path.join(APP_DIR, "fonts", "baamini.ttf"),
            r"C:\Windows\Fonts\SunTommy.ttf",
            r"C:\Windows\Fonts\suntommy.ttf",
            r"C:\Windows\Fonts\Bamini.ttf",
            r"C:\Windows\Fonts\baamini.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\DejaVuSans.ttf",
        ]
        tamil_candidates = [
            # Prefer Unicode Tamil fonts first for correct glyph shaping.
            r"C:\Windows\Fonts\Nirmala.ttf",
            r"C:\Windows\Fonts\Latha.ttf",
            r"C:\Windows\Fonts\Vijaya.ttf",
            os.path.join(FONTS_FOLDER, "Nirmala.ttf"),
            os.path.join(FONTS_FOLDER, "Latha.ttf"),
            os.path.join(FONTS_FOLDER, "Vijaya.ttf"),
            os.path.join(FONTS_FOLDER, "NotoSansTamil-Regular.ttf"),
            os.path.join(APP_DIR, "fonts", "Nirmala.ttf"),
            os.path.join(APP_DIR, "fonts", "Latha.ttf"),
            os.path.join(APP_DIR, "fonts", "Vijaya.ttf"),
            os.path.join(APP_DIR, "fonts", "SunTommy.ttf"),
            os.path.join(APP_DIR, "fonts", "suntommy.ttf"),
            os.path.join(APP_DIR, "fonts", "Bamini.ttf"),
            os.path.join(APP_DIR, "fonts", "baamini.ttf"),
            r"C:\Windows\Fonts\SunTommy.ttf",
            r"C:\Windows\Fonts\suntommy.ttf",
            r"C:\Windows\Fonts\Bamini.ttf",
            r"C:\Windows\Fonts\baamini.ttf",
        ]
        bold_candidates = [
            r"C:\Windows\Fonts\NirmalaB.ttf",
            r"C:\Windows\Fonts\Latha.ttf",
            r"C:\Windows\Fonts\Vijaya.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\DejaVuSans-Bold.ttf",
        ]
        brand_candidates = [
            os.path.join(APP_DIR, "fonts", "DS-DIGIB.TTF"),
            os.path.join(APP_DIR, "fonts", "DS-DIGI.TTF"),
            os.path.join(APP_DIR, "static", "fonts", "DS-DIGI.TTF"),
            os.path.join(APP_DIR, "static", "fonts", "ds-digi.ttf"),
            os.path.join(APP_DIR, "digital-7.ttf"),
            os.path.join(APP_DIR, "static", "fonts", "digital-7.ttf"),
            r"C:\Windows\Fonts\segoesc.ttf",
            r"C:\Windows\Fonts\Segoe Script.ttf",
            r"C:\Windows\Fonts\LucidaHandwritingItalic.ttf",
        ]

        regular_font_name = "Helvetica"
        bold_font_name = "Helvetica-Bold"
        brand_font_name = "Helvetica-Bold"
        tamil_font_name = "Helvetica"

        for reg_path in regular_candidates:
            if not os.path.exists(reg_path):
                continue
            try:
                pdfmetrics.registerFont(TTFont("Thermal-Regular", reg_path))
                regular_font_name = "Thermal-Regular"
                break
            except Exception:
                continue

        for bold_path in bold_candidates:
            if not os.path.exists(bold_path):
                continue
            try:
                pdfmetrics.registerFont(TTFont("Thermal-Bold", bold_path))
                bold_font_name = "Thermal-Bold"
                break
            except Exception:
                continue

        if bold_font_name == "Helvetica-Bold" and regular_font_name == "Thermal-Regular":
            bold_font_name = regular_font_name

        for tamil_path in tamil_candidates:
            if not os.path.exists(tamil_path):
                continue
            try:
                pdfmetrics.registerFont(TTFont("Thermal-Tamil", tamil_path))
                tamil_font_name = "Thermal-Tamil"
                break
            except Exception:
                continue

        if tamil_font_name == "Helvetica" and regular_font_name != "Helvetica":
            tamil_font_name = regular_font_name

        for brand_path in brand_candidates:
            if not os.path.exists(brand_path):
                continue
            try:
                pdfmetrics.registerFont(TTFont("Thermal-Brand", brand_path))
                brand_font_name = "Thermal-Brand"
                break
            except Exception:
                continue

        return regular_font_name, bold_font_name, brand_font_name, tamil_font_name

    folder = os.path.join(APP_DIR, "static", "order_pdfs")
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, f"order_{order['id']}.pdf")

    value_keys = [
        "neck", "chest", "waist", "hip", "shoulder",
        "sleeve", "length", "cuff",
        "inseam", "outseam", "thigh",
        "knee", "bottom",
    ]

    measurement_label_map = {
        "neck": "Neck",
        "chest": "Chest",
        "waist": "Waist",
        "hip": "Hip",
        "shoulder": "Shoulder",
        "sleeve": "Sleeve",
        "length": "Length",
        "cuff": "Cuff",
        "inseam": "Inseam",
        "outseam": "Outseam",
        "thigh": "Thigh",
        "knee": "Knee",
        "bottom": "Bottom",
    }

    # Canonical tailor-slip labels (Tamil) for clean, consistent printing.
    tailor_label_corrections = {
        # neck
        "neck": "\u0b95\u0bb4\u0bc1\u0ba4\u0bcd\u0ba4\u0bc1",
        "\u0b95\u0bb4\u0bc1\u0ba4\u0bcd\u0ba4\u0bc1": "\u0b95\u0bb4\u0bc1\u0ba4\u0bcd\u0ba4\u0bc1",
        "\u0b95\u0bb4\u0bc1\u0ba4\u0bcd\u0ba4": "\u0b95\u0bb4\u0bc1\u0ba4\u0bcd\u0ba4\u0bc1",
        "\u0b95\u0bb3\u0bc1\u0ba4\u0bcd\u0ba4\u0bc1": "\u0b95\u0bb4\u0bc1\u0ba4\u0bcd\u0ba4\u0bc1",
        # shoulder
        "shoulder": "\u0ba4\u0bcb\u0bb3\u0bcd",
        "\u0ba4\u0bcb\u0bb3\u0bcd": "\u0ba4\u0bcb\u0bb3\u0bcd",
        "\u0ba4\u0bcb\u0bb2": "\u0ba4\u0bcb\u0bb3\u0bcd",
        # chest
        "chest": "\u0bae\u0bbe\u0bb0\u0bcd\u0baa\u0bc1",
        "\u0bae\u0bbe\u0bb0\u0bcd\u0baa\u0bc1": "\u0bae\u0bbe\u0bb0\u0bcd\u0baa\u0bc1",
        "\u0b89\u0b9f\u0bb2\u0bcd": "\u0bae\u0bbe\u0bb0\u0bcd\u0baa\u0bc1",
        # collar
        "collar": "\u0b95\u0bbe\u0bb2\u0bb0\u0bcd",
        "\u0b95\u0bbe\u0bb2\u0bb0\u0bcd": "\u0b95\u0bbe\u0bb2\u0bb0\u0bcd",
        "\u0b95\u0ba9\u0bc8": "\u0b95\u0bbe\u0bb2\u0bb0\u0bcd",
        # cuff size
        "cuff": "\u0b95\u0baa\u0bcd \u0b85\u0bb3\u0bb5\u0bc1",
        "cubsize": "\u0b95\u0baa\u0bcd \u0b85\u0bb3\u0bb5\u0bc1",
        "cuffsize": "\u0b95\u0baa\u0bcd \u0b85\u0bb3\u0bb5\u0bc1",
        "\u0b95\u0baa\u0bcd\u0b85\u0bb3\u0bb5\u0bc1": "\u0b95\u0baa\u0bcd \u0b85\u0bb3\u0bb5\u0bc1",
        "\u0b95\u0baa\u0bcd\u0baa\u0bb3\u0bb5\u0bc1": "\u0b95\u0baa\u0bcd \u0b85\u0bb3\u0bb5\u0bc1",
        "\u0b95\u0baa\u0bb3\u0bb5\u0bc1": "\u0b95\u0baa\u0bcd \u0b85\u0bb3\u0bb5\u0bc1",
        "\u0b95\u0baa\u0bcd \u0b85\u0bb3\u0bb5\u0bc1": "\u0b95\u0baa\u0bcd \u0b85\u0bb3\u0bb5\u0bc1",
        # design
        "design": "\u0bb5\u0b9f\u0bbf\u0bb5\u0bae\u0bc8\u0baa\u0bcd\u0baa\u0bc1",
        "\u0bb5\u0b9f\u0bbf\u0bb5\u0bae\u0bc8\u0baa\u0bcd\u0baa\u0bc1": "\u0bb5\u0b9f\u0bbf\u0bb5\u0bae\u0bc8\u0baa\u0bcd\u0baa\u0bc1",
        "\u0bb5\u0b9f\u0bbf\u0bae\u0bc8\u0baa\u0bcd\u0baa\u0bc1": "\u0bb5\u0b9f\u0bbf\u0bb5\u0bae\u0bc8\u0baa\u0bcd\u0baa\u0bc1",
        # sleeve length
        "sleeve": "\u0b95\u0bc8 \u0ba8\u0bc0\u0bb3\u0bae\u0bcd",
        "handlength": "\u0b95\u0bc8 \u0ba8\u0bc0\u0bb3\u0bae\u0bcd",
        "\u0b95\u0bc8\u0ba8\u0bc0\u0bb3\u0bae\u0bcd": "\u0b95\u0bc8 \u0ba8\u0bc0\u0bb3\u0bae\u0bcd",
        "\u0b95\u0bc8 \u0ba8\u0bc0\u0bb3\u0bae\u0bcd": "\u0b95\u0bc8 \u0ba8\u0bc0\u0bb3\u0bae\u0bcd",
        "\u0b95\u0ba9\u0bc8\u0bb3\u0bae\u0bcd": "\u0b95\u0bc8 \u0ba8\u0bc0\u0bb3\u0bae\u0bcd",
        "\u0b95\u0ba9\u0bc8\u0bb2\u0bae\u0bcd": "\u0b95\u0bc8 \u0ba8\u0bc0\u0bb3\u0bae\u0bcd",
        # hand size
        "handsize": "\u0b95\u0bc8 \u0b85\u0bb3\u0bb5\u0bc1",
        "\u0b95\u0bc8\u0b85\u0bb3\u0bb5\u0bc1": "\u0b95\u0bc8 \u0b85\u0bb3\u0bb5\u0bc1",
        "\u0b95\u0bc8 \u0b85\u0bb3\u0bb5\u0bc1": "\u0b95\u0bc8 \u0b85\u0bb3\u0bb5\u0bc1",
        # height
        "height": "\u0b89\u0baf\u0bb0\u0bae\u0bcd",
        "\u0b89\u0baf\u0bb0\u0bae\u0bcd": "\u0b89\u0baf\u0bb0\u0bae\u0bcd",
        # M size
        "msize": "M \u0b85\u0bb3\u0bb5\u0bc1",
        "m\u0b85\u0bb3\u0bb5\u0bc1": "M \u0b85\u0bb3\u0bb5\u0bc1",
        "m \u0b85\u0bb3\u0bb5\u0bc1": "M \u0b85\u0bb3\u0bb5\u0bc1",
        "\u0b8e\u0bae\u0bcd\u0b85\u0bb3\u0bb5\u0bc1": "M \u0b85\u0bb3\u0bb5\u0bc1",
        "M \u0b85\u0bb3\u0bb5\u0bc1": "M \u0b85\u0bb3\u0bb5\u0bc1",
        # pocket
        "pocket": "\u0baa\u0bbe\u0b95\u0bcd\u0b95\u0bc6\u0b9f\u0bcd",
        "\u0b95\u0bc8\u0baa\u0bcd\u0baa\u0bc8": "\u0baa\u0bbe\u0b95\u0bcd\u0b95\u0bc6\u0b9f\u0bcd",
        "\u0baa\u0bbe\u0b95\u0bcd\u0b95\u0bc6\u0b9f\u0bcd": "\u0baa\u0bbe\u0b95\u0bcd\u0b95\u0bc6\u0b9f\u0bcd",
        # side size
        "sidesize": "\u0baa\u0b95\u0bcd\u0b95 \u0b85\u0bb3\u0bb5\u0bc1",
        "\u0baa\u0b95\u0bcd\u0b95\u0b85\u0bb3\u0bb5\u0bc1": "\u0baa\u0b95\u0bcd\u0b95 \u0b85\u0bb3\u0bb5\u0bc1",
        "\u0baa\u0b95\u0bcd\u0b95 \u0b85\u0bb3\u0bb5\u0bc1": "\u0baa\u0b95\u0bcd\u0b95 \u0b85\u0bb3\u0bb5\u0bc1",
    }

    def parse_measurement_note_pairs(notes_text: str | None) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        ignore_labels = {
            "label",
            "requirements",
            "requirement",
            "payment method",
            "worker delivery date",
            "completed date",
            "delivery date",
            "notes",
            "note",
        }
        for raw_line in str(notes_text or "").splitlines():
            clean = raw_line.strip()
            if not clean or ":" not in clean:
                continue
            p_label, p_value = clean.split(":", 1)
            label = p_label.strip()
            value = p_value.strip()
            if not label or not value:
                continue
            if label.lower() in ignore_labels:
                continue
            pairs.append((label, value))
        return pairs

    def _normalize_label_token(text: str | None) -> str:
        return "".join(ch for ch in str(text or "").strip().lower() if ch.isalnum())

    def canonical_measure_label(text: str | None) -> str:
        raw = str(text or "").strip()
        if not raw:
            return ""
        return tailor_label_corrections.get(_normalize_label_token(raw), raw)

    def _kind_to_keys(kind_text: str | None) -> tuple[str, str]:
        text = str(kind_text or "").strip()
        if not text:
            return "", ""
        if "-" in text:
            category_name, subcategory_name = text.split("-", 1)
            return category_name.strip().lower(), subcategory_name.strip().lower()
        return text.lower(), ""

    def _build_measurement_field_order_map() -> dict[str, list[str]]:
        order_map: dict[str, list[str]] = {}
        conn = None
        try:
            conn = get_db()
            rows = conn.execute(
                """
                SELECT
                    c.name AS category_name,
                    s.name AS subcategory_name,
                    f.field_key,
                    f.field_label
                FROM measurement_fields f
                JOIN subcategories s ON s.id = f.subcategory_id
                JOIN categories c ON c.id = s.category_id
                ORDER BY c.name, s.name, f.sort_order, f.id
                """
            ).fetchall()
        except Exception:
            rows = []
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

        grouped: dict[str, list[str]] = {}
        for row in rows:
            category_name = str(row["category_name"] or "").strip()
            subcategory_name = str(row["subcategory_name"] or "").strip()
            field_key = str(row["field_key"] or "").strip().lower()
            field_label = str(row["field_label"] or "").strip()
            if not subcategory_name:
                continue
            group_key = f"{category_name.lower()}::{subcategory_name.lower()}"
            # Keep PDF wording exactly as configured in Measurement fields UI.
            display_label = field_label or measurement_label_map.get(field_key, field_key.title())
            if not display_label:
                continue
            grouped.setdefault(group_key, []).append(display_label)

        sub_to_group_keys: dict[str, set[str]] = {}
        for group_key in grouped.keys():
            sub_key = group_key.split("::", 1)[1]
            sub_to_group_keys.setdefault(sub_key, set()).add(group_key)

        for group_key, labels in grouped.items():
            order_map[group_key] = labels

        # Fallback for cases where `kind` has only subcategory text and it is unique.
        for sub_key, group_keys in sub_to_group_keys.items():
            if len(group_keys) == 1:
                only_key = next(iter(group_keys))
                order_map[f"*::{sub_key}"] = grouped[only_key]

        return order_map

    measurement_field_order_map = _build_measurement_field_order_map()

    def measurement_values(row) -> list[tuple[str, str]]:
        values: list[tuple[str, str]] = []

        for key in value_keys:
            value = row[key]
            if value:
                val = fmt_measure(value)
                if val:
                    values.append((measurement_label_map.get(key, key.title()), val))

        notes = row["notes"] if "notes" in row.keys() else None
        for label, value in parse_measurement_note_pairs(notes):
            if label.strip().lower() == "label":
                continue
            clean_value = fmt_measure(value)
            if clean_value:
                values.append((label.strip(), clean_value))

        kind_value = row["kind"] if hasattr(row, "keys") and ("kind" in row.keys()) else ""
        category_key, subcategory_key = _kind_to_keys(kind_value)
        expected_order = (
            measurement_field_order_map.get(f"{category_key}::{subcategory_key}")
            or measurement_field_order_map.get(f"*::{subcategory_key}")
            or []
        )
        if not expected_order:
            return values

        grouped_values: dict[str, list[tuple[str, str]]] = {}
        for label, value in values:
            grouped_values.setdefault(_normalize_label_token(label), []).append((label, value))

        ordered_values: list[tuple[str, str]] = []
        used_tokens: set[str] = set()
        for expected_label in expected_order:
            token = _normalize_label_token(expected_label)
            entries = grouped_values.get(token, [])
            if not entries:
                continue
            ordered_values.extend(entries)
            used_tokens.add(token)

        for label, value in values:
            token = _normalize_label_token(label)
            if token in used_tokens:
                continue
            ordered_values.append((label, value))

        return ordered_values

    def wrap_comma_values(values: list[str], max_chars: int = 35) -> list[str]:
        if not values:
            return []
        tokens = [str(v).strip() for v in values if str(v).strip()]
        if not tokens:
            return []
        lines: list[str] = []
        current_tokens: list[str] = []
        for token in tokens:
            current = ",".join(current_tokens)
            candidate = token if not current else f"{current},{token}"
            if len(candidate) <= max_chars:
                current_tokens.append(token)
            else:
                if current_tokens:
                    lines.append(",".join(current_tokens))
                current_tokens = [token]
        if current_tokens:
            lines.append(",".join(current_tokens))

        # Avoid orphan last line with a single value by balancing with previous line.
        if len(lines) >= 2:
            tail_tokens = [t for t in lines[-1].split(",") if t]
            prev_tokens = [t for t in lines[-2].split(",") if t]
            while len(tail_tokens) == 1 and len(prev_tokens) > 2:
                tail_tokens.insert(0, prev_tokens.pop())
                if len(",".join(tail_tokens)) > max_chars:
                    prev_tokens.append(tail_tokens.pop(0))
                    break
                lines[-2] = ",".join(prev_tokens)
                lines[-1] = ",".join(tail_tokens)
        return lines

    def wrap_text(text: str, max_chars: int = 44) -> list[str]:
        clean = " ".join((text or "").split())
        if not clean:
            return []
        words = clean.split(" ")
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def extract_tailor_notes(notes_text: str) -> list[str]:
        lines: list[str] = []
        for raw_line in str(notes_text or "").splitlines():
            clean = raw_line.strip()
            if not clean:
                continue
            low = clean.lower()
            if low.startswith("payment method:"):
                continue
            if low.startswith("worker delivery date:"):
                continue
            if low.startswith("completed date:"):
                continue
            if low.startswith("delivery date:"):
                continue
            if low.startswith("qty:"):
                continue
            lines.extend(wrap_text(clean, 42))
        return lines

    def extract_item_notes(notes_text: str | None) -> list[str]:
        lines: list[str] = []
        text = str(notes_text or "").strip()
        if not text:
            return lines
        measurement_note_labels = {
            label.strip().lower() for label, _ in parse_measurement_note_pairs(text)
        }
        for raw_line in text.splitlines():
            clean = raw_line.strip()
            if not clean:
                continue
            low = clean.lower()
            if low.startswith("label:"):
                continue
            if low.startswith("requirements:"):
                continue
            if ":" in clean:
                key = clean.split(":", 1)[0].strip().lower()
                if key in measurement_note_labels:
                    continue
            lines.extend(extract_tailor_notes(clean))
        return lines

    mode = mode.lower().strip() if mode else "tailor"
    tailor_paper = (tailor_paper or "a4").strip().lower()
    if tailor_paper not in {"a4", "thermal"}:
        tailor_paper = "a4"
    assigned_tailor_raw = str(order["assigned_tailor"] or "").strip()
    assigned_tailor = "-" if not assigned_tailor_raw or assigned_tailor_raw.lower() == "tailor" else assigned_tailor_raw

    line_height = 4.8 * mm if mode == "customer" else 4 * mm

    # Estimate height safely
    base_lines = 15
    matched_measurements: list = []
    measurements_by_kind: dict[str, list] = {}
    measurements_by_type: dict[str, list] = {}

    def normalize_measure_type(raw_value: str | None) -> str:
        text = (raw_value or "").strip().lower()
        if not text:
            return ""
        base = text.split("-", 1)[0].strip()
        if base in {"s001", "shirt"}:
            return "shirt"
        if base in {"p001", "pant", "trouser", "jean", "jeans"}:
            return "pant"
        if base in {"coat", "blazer", "safari"}:
            return "coat"
        return base or text

    def measurement_row_key(row) -> int:
        if hasattr(row, "keys") and "id" in row.keys() and row["id"] is not None:
            try:
                return int(row["id"])
            except (TypeError, ValueError):
                pass
        return id(row)

    for m in measurements:
        kind = (m["kind"] or "").strip().lower()
        if not kind:
            continue
        measurements_by_kind.setdefault(kind, []).append(m)
        kind_norm = normalize_measure_type(kind)
        if kind_norm:
            measurements_by_type.setdefault(kind_norm, []).append(m)

    seen_item_kinds: set[str] = set()
    used_measurement_keys: set[int] = set()
    for item in order_items:
        item_kind = (item["item_type"] or "").strip().lower()
        if not item_kind:
            continue
        if item_kind in seen_item_kinds:
            continue
        seen_item_kinds.add(item_kind)
        item_kind_norm = normalize_measure_type(item_kind)

        candidates = []
        candidates.extend(measurements_by_kind.get(item_kind) or [])
        if item_kind_norm:
            candidates.extend(measurements_by_type.get(item_kind_norm) or [])
            candidates.extend(
                row for row in measurements
                if item_kind_norm in ((row["kind"] or "").strip().lower())
            )

        for row in candidates:
            row_key = measurement_row_key(row)
            if row_key in used_measurement_keys:
                continue
            used_measurement_keys.add(row_key)
            matched_measurements.append(row)
            break

    if mode == "customer":
        address_preview_lines = get_company_address_lines()
        company_phone_preview = get_setting("company_phone", "").strip()
        gst_no_preview = get_setting("gst_no", "").strip()
        header_lines = 1  # company title
        if gst_no_preview:
            header_lines += 1
        if address_preview_lines:
            header_lines += len(address_preview_lines)
        if company_phone_preview:
            header_lines += 1
        billing_preview = get_setting("sms_order_content", "").strip() or "Thank you for your order. Visit Again"
        footer_preview = get_setting("billing_footer_text", "").strip()
        if not footer_preview:
            powered_match_preview = re.search(r"(powered\s+by\s+@?[^\s].*)$", billing_preview, flags=re.IGNORECASE)
            if powered_match_preview:
                billing_preview = billing_preview[:powered_match_preview.start()].strip()
                footer_preview = powered_match_preview.group(1).strip()
        footer_lines = max(1, len(wrap_text(billing_preview, 44))) + (1 if footer_preview else 0)
        order_type_preview = ((order["order_type"] if "order_type" in order.keys() else "") or "").strip().lower()
        delivery_line_count = 1 if order_type_preview == "tailoring" else 0
        if order_type_preview == "alteration":
            detail_lines = 1
        else:
            tailoring_count = 0
            material_count = 0
            for item in order_items:
                item_group = ""
                if hasattr(item, "keys") and ("item_group" in item.keys()):
                    item_group = str(item["item_group"] or "").strip().lower()
                if not item_group:
                    uom_text = str(item["uom_name"] or "").strip().lower() if hasattr(item, "keys") and ("uom_name" in item.keys()) else ""
                    if order_type_preview == "material" or uom_text:
                        item_group = "material"
                    else:
                        item_group = "tailoring"
                if item_group.startswith("material"):
                    material_count += 1
                else:
                    tailoring_count += 1
            section_lines = (1 if tailoring_count > 0 else 0) + (1 if material_count > 0 else 0)
            extra_order_type_lines = 1 if (tailoring_count > 0 and material_count > 0) else 0
            detail_lines = len(order_items) + section_lines + extra_order_type_lines
        customer_lines = header_lines + detail_lines + footer_lines + 22 + delivery_line_count
        height = max(78 * mm, customer_lines * line_height)
    else:
        order_notes_raw = (order["notes"] or "").strip()
        global_requirements = extract_requirements(order_notes_raw)
        measurement_line_count = 0.0
        for m in matched_measurements:
            measurement_line_count += 1  # item title line
            clean_pairs = [
                (str(lbl).strip(), str(val).strip())
                for lbl, val in measurement_values(m)
                if str(lbl).strip() and str(val).strip()
            ]
            max_stack_rows = 1
            if clean_pairs:
                split_counts = []
                for _, raw_value in clean_pairs:
                    parts = [p.strip() for p in str(raw_value).split(",") if p and p.strip()]
                    split_counts.append(max(1, len(parts)))
                max_stack_rows = max(1, max(split_counts) if split_counts else 1)
            # 1 line labels + N stacked value lines
            measurement_line_count += (1 + max_stack_rows)
            m_notes = (m["notes"] or "").strip() if "notes" in m.keys() else ""
            req_lines = extract_requirements(m_notes) or global_requirements
            if req_lines:
                measurement_line_count += 1  # "Requirements" heading
                measurement_line_count += sum(len(wrap_text(req, 42)) or 1 for req in req_lines)
            note_lines = extract_item_notes(m_notes)
            if note_lines:
                measurement_line_count += 1  # "Notes" heading
                measurement_line_count += len(note_lines)
        extra_lines = len(order_items) + measurement_line_count + 16
        height = max(100 * mm, (base_lines + extra_lines) * line_height)

    if mode == "customer":
        content_width = 72 * mm
        canvas_width = content_width
        canvas_height = height
    else:
        # if tailor_paper == "thermal":
        #     # Tailor slip on thermal paper: dynamic height based on content.
        #     canvas_width = 80 * mm
        #     canvas_height = height
        # if tailor_paper == "thermal":
        #     canvas_width = 80 * mm
        #     canvas_height = 210 * mm   # FIXED HEIGHT
        #     content_width = 72 * mm
        if tailor_paper == "thermal":
            # Keep thermal width fixed and increase only height for clearer slip layout.
            canvas_width = 72 * mm
            canvas_height = max(240 * mm, height)

            LEFT_MARGIN = 2 * mm
            RIGHT_MARGIN = 2 * mm

            content_width = canvas_width - LEFT_MARGIN - RIGHT_MARGIN
            if landscape:
                # In landscape text mode, use the long side for content.
                content_width = canvas_height - (14 * mm)
            else:
                content_width = 72 * mm
        else:
            # Tailor slip on A4 sheet.
            if landscape:
                canvas_width, canvas_height = (A4[1], A4[0])
            else:
                canvas_width, canvas_height = A4
            content_width = canvas_width - (20 * mm)
    pdf = canvas.Canvas(file_path, pagesize=(canvas_width, canvas_height))
    
    regular_font, bold_font = get_reportlab_tamil_fonts()
    tamil_font = regular_font
    rotated_landscape_tailor = False
    logical_width = canvas_width
    logical_height = canvas_height
    if landscape and mode == "customer":
        pdf.setPageRotation(90)
    if landscape and mode == "tailor":
        rotated_landscape_tailor = True
        logical_width = canvas_height
        logical_height = canvas_width
        pdf.saveState()
        pdf.translate(0, canvas_height)
        pdf.rotate(-90)
    y = logical_height - (10 * mm if mode != "customer" else 6 * mm)

    # left_x = ((logical_width - content_width) / 2) + (5 * mm)
    # right_x = left_x + content_width - (10 * mm)
    LEFT_MARGIN = 2 * mm
    RIGHT_MARGIN = 2 * mm

    left_x = LEFT_MARGIN
    right_x = logical_width - RIGHT_MARGIN
    content_width = right_x - left_x
    center_x = (left_x + right_x) / 2
    regular_font, bold_font, brand_font, tamil_font = ensure_rupee_font()
    tamil_draw_font_path = None
    for tamil_candidate in [
        r"C:\Windows\Fonts\Nirmala.ttf",
        r"C:\Windows\Fonts\Latha.ttf",
        r"C:\Windows\Fonts\Vijaya.ttf",
        os.path.join(FONTS_FOLDER, "Nirmala.ttf"),
        os.path.join(FONTS_FOLDER, "Latha.ttf"),
        os.path.join(FONTS_FOLDER, "Vijaya.ttf"),
        os.path.join(FONTS_FOLDER, "NotoSansTamil-Regular.ttf"),
    ]:
        if os.path.exists(tamil_candidate):
            tamil_draw_font_path = tamil_candidate
            break
    can_shape_tamil_text = bool(tamil_draw_font_path and features.check_feature("raqm"))
    image_scale = 3

    @lru_cache(maxsize=2048)
    def _render_tamil_text_image(text: str, font_size: float) -> tuple[Image.Image, float, float]:
        if not can_shape_tamil_text:
            raise ValueError("Tamil shaping engine unavailable")
        px_font_size = max(12, int(round(float(font_size) * image_scale)))
        font_obj = ImageFont.truetype(
            tamil_draw_font_path,
            px_font_size,
            layout_engine=ImageFont.Layout.RAQM,
        )
        probe_img = Image.new("RGBA", (1, 1), (255, 255, 255, 0))
        probe_draw = ImageDraw.Draw(probe_img)
        x0, y0, x1, y1 = probe_draw.textbbox((0, 0), text, font=font_obj)
        pad = max(2, int(round(image_scale * 1.2)))
        width_px = max(2, (x1 - x0) + (pad * 2))
        height_px = max(2, (y1 - y0) + (pad * 2))
        text_img = Image.new("RGBA", (width_px, height_px), (255, 255, 255, 0))
        draw_obj = ImageDraw.Draw(text_img)
        draw_obj.text((pad - x0, pad - y0), text, font=font_obj, fill=(0, 0, 0, 255))
        return text_img, (width_px / float(image_scale)), (height_px / float(image_scale))

    def draw_string_safe(x: float, base_y: float, text: str, font_name: str, font_size: float):
        text = str(text or "")
        if text and has_tamil_chars(text) and can_shape_tamil_text:
            try:
                text_img, width_pt, height_pt = _render_tamil_text_image(text, font_size)
                # drawString uses baseline; image draw uses bottom-left. Apply a baseline offset.
                y_offset = max(0.0, (0.25 * float(font_size)))
                pdf.drawInlineImage(text_img, x, base_y - y_offset, width=width_pt, height=height_pt)
                return
            except Exception:
                pass
        pdf.setFont(font_name, font_size)
        pdf.drawString(x, base_y, text)

    def string_width_safe(text: str, font_name: str, font_size: float) -> float:
        text = str(text or "")
        if text and has_tamil_chars(text) and can_shape_tamil_text:
            try:
                _, width_pt, _ = _render_tamil_text_image(text, font_size)
                return width_pt
            except Exception:
                pass
        return pdf.stringWidth(text, font_name, font_size)

    def draw(text, bold=False, center=False, brand=False, size=11):
        nonlocal y
        if brand:
            pdf.setFont(brand_font, size)
        else:
            pdf.setFont(bold_font if bold else regular_font, size)
        if center:
            pdf.drawCentredString(center_x, y, text)
        else:
            pdf.drawString(left_x, y, text)
        y -= line_height

    def draw_pair(left: str, right: str | None = None, bold=False):
        nonlocal y
        pdf.setFont(bold_font if bold else regular_font, 11)
        pdf.drawString(left_x, y, left)
        if right is not None:
            pdf.drawRightString(right_x, y, right)
        y -= line_height

    def draw_rule(gap_before: float = 0.8 * mm, gap_after: float = 1.2 * mm):
        nonlocal y
        y -= gap_before
        pdf.setLineWidth(0.6)
        pdf.line(left_x, y, right_x, y)
        y -= gap_after

    def draw_kv(label: str, value: str | None, bold=False):
        nonlocal y
        font_name = bold_font if bold else regular_font
        font_size = 9
        label_x = left_x
        label_width = string_width_safe(label, font_name, font_size)
        min_colon_x = left_x + (21 * mm)
        colon_x = max(min_colon_x, label_x + label_width + (1.2 * mm))
        value_x = colon_x + (2.2 * mm)
        draw_string_safe(label_x, y, label, font_name, font_size)
        draw_string_safe(colon_x, y, ":", font_name, font_size)
        text = str(value).strip() if value is not None else ""
        draw_string_safe(value_x, y, text or "-", font_name, font_size)
        y -= line_height

    def draw_logo_watermark():
        print_logo_path = get_setting("print_logo_path", "").strip() or "Premier-Logo.png"
        logo_abs_path = os.path.join(APP_DIR, "static", print_logo_path)
        if not os.path.exists(logo_abs_path):
            return
        if mode == "tailor":
            # Keep tailor watermark fully visible and centered on compact/rotated slips.
            base_w = (right_x - left_x) * 0.42
            watermark_w = min(base_w, logical_width * 0.46, logical_height * 0.46)
        else:
            watermark_w = (right_x - left_x) * 0.62
        watermark_h = watermark_w
        watermark_x = center_x - (watermark_w / 2)
        watermark_y = (logical_height - watermark_h) / 2
        try:
            pdf.saveState()
            try:
                pdf.setFillAlpha(0.08)
            except Exception:
                pass
            pdf.drawImage(
                logo_abs_path,
                watermark_x,
                watermark_y,
                width=watermark_w,
                height=watermark_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass
        finally:
            try:
                pdf.restoreState()
            except Exception:
                pass

    draw_logo_watermark()

    # =========================
    # CUSTOMER COPY
    # =========================
    if mode == "customer":

        company_name = get_setting("company_name", get_setting("branch_name", "Premier Tailors")).strip()
        company_address_lines = get_company_address_lines()
        company_phone = get_setting("company_phone", "").strip()
        gst_no = get_setting("gst_no", "").strip()
        print_logo_path = get_setting("print_logo_path", "").strip() or "Premier-Logo.png"
        logo_abs_path = os.path.join(APP_DIR, "static", print_logo_path)
        customer_step = 4.1 * mm
        content_left_x = left_x + (1.0 * mm)
        content_right_x = right_x - (1.0 * mm)
        label_col_x = content_left_x
        colon_col_x = content_left_x + (31 * mm)
        value_col_x = colon_col_x + (2 * mm)
        amount_right_x = content_right_x - (1.0 * mm)
        qty_col_x = content_right_x - (29 * mm)
        dash_line = "-" * 70

        def draw_dash_rule():
            nonlocal y
            pdf.setFont(regular_font, 9)
            pdf.drawString(content_left_x, y, dash_line)
            y -= customer_step

        def draw_customer_kv(label: str, value: str | None):
            nonlocal y
            pdf.setFont(regular_font, 10)
            pdf.drawString(label_col_x, y, label)
            pdf.drawString(colon_col_x, y, ":")
            text = str(value).strip() if value is not None else ""
            pdf.drawString(value_col_x, y, text or "-")
            y -= customer_step

        def draw_customer_kv_wrapped(label: str, value: str | None, wrap_width: int = 26):
            nonlocal y
            text = str(value).strip() if value is not None else ""
            lines = wrap_text(text or "-", wrap_width) or ["-"]
            pdf.setFont(regular_font, 10)
            pdf.drawString(label_col_x, y, label)
            pdf.drawString(colon_col_x, y, ":")
            pdf.drawString(value_col_x, y, lines[0])
            y -= customer_step
            for line in lines[1:]:
                pdf.drawString(value_col_x, y, line)
                y -= customer_step

        def draw_customer_kv_lines(label: str, lines: list[str] | None):
            nonlocal y
            values = [str(v).strip() for v in (lines or []) if str(v).strip()]
            if not values:
                values = ["-"]
            pdf.setFont(regular_font, 10)
            pdf.drawString(label_col_x, y, label)
            pdf.drawString(colon_col_x, y, ":")
            pdf.drawString(value_col_x, y, values[0])
            y -= customer_step
            for line in values[1:]:
                pdf.drawString(value_col_x, y, line)
                y -= customer_step

        def draw_amount_row(label: str, amount: float, bold=False):
            nonlocal y
            font_name = bold_font if bold else regular_font
            font_size = 10
            pdf.setFont(font_name, font_size)
            pdf.drawString(label_col_x, y, label)
            pdf.drawRightString(amount_right_x, y, f"{amount:.2f}")
            y -= customer_step

        logo_w = 19 * mm
        logo_h = 19 * mm
        has_logo = os.path.exists(logo_abs_path)
        title_y = y - (1.0 * mm)

        if company_name:
            pdf.setFont("Times-Bold", 17)
            pdf.drawCentredString(center_x, title_y, company_name)

        addr_start_y = title_y - (customer_step + 0.9 * mm)
        address_lines: list[str] = []
        if company_address_lines:
            address_lines.extend(company_address_lines)
        if company_phone:
            address_lines.append(f"Phone: {company_phone}")
        if gst_no:
            address_lines.append(f"GST NO: {gst_no}")

        # Place logo closer to right edge to avoid title overlap.
        logo_x = content_right_x - logo_w
        address_line_count = max(1, len(address_lines))
        address_center_y = addr_start_y - ((address_line_count - 1) * customer_step / 2) + (1.0 * mm)
        logo_y = address_center_y - (logo_h / 2)

        header_bottom_y = title_y
        if has_logo:
            try:
                pdf.drawImage(
                    logo_abs_path,
                    logo_x,
                    logo_y,
                    width=logo_w,
                    height=logo_h,
                    preserveAspectRatio=True,
                    mask="auto",
                )
                pdf.drawImage(
                    logo_abs_path,
                    logo_x,
                    logo_y - (0.2 * mm),
                    width=logo_w,
                    height=logo_h,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass
            header_bottom_y = min(header_bottom_y, logo_y)

        if address_lines:
            addr_y = addr_start_y
            for line in address_lines:
                pdf.setFont(regular_font, 10)
                pdf.drawString(content_left_x, addr_y, line)
                header_bottom_y = min(header_bottom_y, addr_y - customer_step)
                addr_y -= customer_step

        y = header_bottom_y - (1.0 * mm)
        draw_dash_rule()

        order_type_value = ((order["order_type"] if "order_type" in order.keys() else "") or "").strip()
        is_tailoring_order = order_type_value.lower() == "tailoring"

        draw_customer_kv("Customer Name", order["name"])
        customer_order_type_label = " ".join(order_type_value.lower().split())
        use_order_id_label = ("alteration" in customer_order_type_label) or ("material" in customer_order_type_label)
        id_label = "Order ID" if use_order_id_label else "Invoice ID"
        id_value = display_order_no(dict(order)) if use_order_id_label else (
            order["invoice_id"] if "invoice_id" in order.keys() and order["invoice_id"] else display_order_no(dict(order))
        )
        draw_customer_kv(id_label, id_value)
        draw_customer_kv("Phone Number", order["phone"])
        draw_customer_kv("Order Date", datetime_display(order["created_at"]))
        if is_tailoring_order:
            draw_customer_kv("Delivery Date", date_only(order["due_date"]))

        y -= 0.2 * mm
        draw_dash_rule()

        order_type = order_type_value or "-"
        draw_customer_kv("Order Type", order_type)
        y -= 0.3 * mm

        material_line_total_sum = 0.0
        tailoring_charge_amount = 0.0
        if order_type_value.lower() == "alteration":
            note_lines = []
            for raw_line in str(order.get("notes") or "").splitlines():
                cleaned = raw_line.strip()
                if not cleaned:
                    continue
                if cleaned.lower().startswith("payment method"):
                    continue
                note_lines.append(cleaned)
            note_value = note_lines[0] if note_lines else "-"
            draw_customer_kv_wrapped("Order Notes", note_value)
        else:
            tailoring_items: list = []
            material_items: list = []
            if order_items:
                for item in order_items:
                    item_group = ""
                    if "item_group" in item.keys():
                        item_group = str(item["item_group"] or "").strip().lower()
                    if not item_group:
                        uom_text = str(item["uom_name"] or "").strip().lower() if "uom_name" in item.keys() else ""
                        if order_type_value.lower() == "material" or uom_text:
                            item_group = "material"
                        else:
                            item_group = "tailoring"
                    if item_group.startswith("material"):
                        material_items.append(item)
                    else:
                        tailoring_items.append(item)

            def draw_items_section(
                title: str,
                rows: list,
                split_header: bool = False,
                show_title: bool = True,
                include_amount: bool = False,
                trim_subcategory: bool = False,
                title_bold: bool = True,
            ):
                nonlocal y, material_line_total_sum
                if not rows:
                    return
                pdf.setFont(bold_font, 11)
                if split_header:
                    if show_title:
                        pdf.setFont(bold_font if title_bold else regular_font, 11)
                        pdf.drawString(label_col_x, y, title)
                        y -= customer_step
                        pdf.setFont(bold_font, 11)
                    pdf.drawString(label_col_x, y, "Items")
                    if include_amount:
                        pdf.drawRightString(amount_right_x, y, "Amount")
                    y -= customer_step
                else:
                    pdf.setFont(bold_font if title_bold else regular_font, 11)
                    pdf.drawString(label_col_x, y, title)
                    if include_amount:
                        pdf.drawRightString(amount_right_x, y, "Amount")
                    y -= customer_step
                pdf.setFont(regular_font, 11)
                for row in rows:
                    item_type = (row["item_type"] or "Item").strip() or "Item"
                    if trim_subcategory and "-" in item_type:
                        row_group = str(row["item_group"] or "").strip().lower() if "item_group" in row.keys() else ""
                        if not row_group.startswith("material"):
                            item_type = item_type.split("-", 1)[0].strip() or item_type
                    qty_value = float(row["qty"] or 0)
                    qty = f"{qty_value:.2f}".rstrip("0").rstrip(".")
                    uom_name = (row["uom_name"] or "").strip() if "uom_name" in row.keys() else ""
                    if uom_name.lower() in {"meter", "meters", "mtr", "mtrs"}:
                        uom_name = "MTRS"
                    qty_text = f"{qty} {uom_name}".strip()
                    item_lines = wrap_text(item_type, 24) or ["Item"]
                    pdf.drawString(label_col_x, y, item_lines[0])
                    if include_amount:
                        line_total = row["line_total"] if "line_total" in row.keys() else None
                        if line_total is None:
                            unit_price = float(row["unit_price"] or 0) if "unit_price" in row.keys() else 0
                            line_total = qty_value * unit_price
                        if "item_group" in row.keys() and str(row["item_group"] or "").strip().lower().startswith("material"):
                            material_line_total_sum += float(line_total or 0)
                        pdf.drawRightString(amount_right_x, y, f"{float(line_total or 0):.2f}")
                    y -= customer_step
                    for line in item_lines[1:]:
                        pdf.drawString(label_col_x, y, line)
                        y -= customer_step

            if is_tailoring_order:
                if tailoring_items:
                    draw_items_section("Items", tailoring_items, trim_subcategory=True)
                if material_items:
                    if tailoring_items:
                        draw_dash_rule()
                    draw_items_section(
                        "Materials",
                        material_items,
                        split_header=True,
                        show_title=True,
                        include_amount=True,
                        title_bold=False,
                    )
                elif matched_measurements:
                    pdf.setFont(bold_font, 11)
                    pdf.drawString(label_col_x, y, "Items")
                    y -= customer_step
                    pdf.setFont(regular_font, 11)
                    for m in matched_measurements:
                        full_kind = (m["kind"] or "Item").strip() or "Item"
                        item_type = full_kind.split("-", 1)[0].strip() if "-" in full_kind else full_kind
                        pdf.drawString(label_col_x, y, item_type)
                        y -= customer_step
            elif tailoring_items or material_items:
                if tailoring_items:
                    draw_items_section("Items", tailoring_items)
                if material_items:
                    draw_items_section(
                        "Material Purchase",
                        material_items,
                        split_header=True,
                        show_title=False,
                        include_amount=True,
                    )
            elif is_tailoring_order and matched_measurements:
                for m in matched_measurements:
                    full_kind = (m["kind"] or "Item").strip() or "Item"
                    item_type = full_kind.split("-", 1)[0].strip() if "-" in full_kind else full_kind
                    item_lines = wrap_text(item_type, 24) or ["Item"]
                    pdf.drawString(label_col_x, y, item_lines[0])
                    y -= customer_step
                    for line in item_lines[1:]:
                        pdf.drawString(label_col_x, y, line)
                        y -= customer_step

        draw_dash_rule()

        total_amount = float(order["total_amount"] or 0)
        advance_amount = float(order["advance_amount"] or 0)
        paid_amount = float(order["paid_amount"] or 0)
        due_amount = max(total_amount - advance_amount - paid_amount, 0)
        gst_amount = float(order["gst_amount"] or 0)
        gst_percent = float(order["gst_percent"] or 0)
        taxable_amount = float(order["taxable_amount"] or max(total_amount - gst_amount, 0))
        # GST fields are read-only here: use saved values only (no recalculation/splitting).
        cgst_amount = float(order["cgst_amount"] or 0)
        sgst_amount = float(order["sgst_amount"] or 0)
        cgst_percent = float(order["cgst_percent"] or 0)
        sgst_percent = float(order["sgst_percent"] or 0)

        stored_discount = float(order["discount_amount"] or 0) if "discount_amount" in order.keys() else 0.0
        discount_amount = max(stored_discount, 0)
        sub_total = max(taxable_amount + discount_amount, 0)
        total_amount_display = total_amount
        customer_order_type = " ".join(order_type_value.lower().split())
        if customer_order_type == "material" and material_line_total_sum > 0:
            sub_total = max(material_line_total_sum, 0)
            total_amount_display = max(sub_total - discount_amount + gst_amount, 0)
        due_amount = max(total_amount_display - advance_amount - paid_amount, 0)
        gst_pct_text = f"{gst_percent:.2f}".rstrip("0").rstrip(".")
        cgst_pct_text = f"{cgst_percent:.2f}".rstrip("0").rstrip(".")
        sgst_pct_text = f"{sgst_percent:.2f}".rstrip("0").rstrip(".")

        pdf.setFont(bold_font, 12)
        payment_title = "Payment Summary - Rs." if customer_order_type == "tailoring" else "Payment Summary"
        pdf.drawString(label_col_x, y, payment_title)
        y -= customer_step

        draw_amount_row("Sub Total", sub_total)
        draw_amount_row("Discount", discount_amount)
        if gst_amount > 0:
            cgst_label = f"CGST ({cgst_pct_text}%)" if cgst_percent > 0 else "CGST"
            sgst_label = f"SGST ({sgst_pct_text}%)" if sgst_percent > 0 else "SGST"
            draw_amount_row(cgst_label, cgst_amount)
            draw_amount_row(sgst_label, sgst_amount)
            draw_amount_row("Total GST", gst_amount)
        elif gst_percent > 0:
            draw_amount_row(f"GST ({gst_pct_text}%)", gst_amount)
        hide_payment_rows = ("alteration" in customer_order_type) or ("material" in customer_order_type)
        show_advance_balance = not hide_payment_rows
        draw_dash_rule()
        if show_advance_balance:
            draw_amount_row("Advance", advance_amount)
            draw_amount_row("Paid", paid_amount)
            draw_amount_row("Balance", due_amount)
            draw_dash_rule()
        draw_amount_row("Total Amount", total_amount_display, bold=True)

        billing_message = get_setting("sms_order_content", "").strip() or "Thank you for your order. Visit Again"
        footer_text = get_setting("billing_footer_text", "").strip()
        if billing_message or footer_text:
            y -= 2.8 * mm
            footer_center_x = (content_left_x + content_right_x) / 2
            message_part = " ".join((billing_message or "").split())
            powered_part = " ".join((footer_text or "").split())
            if not powered_part:
                powered_match = re.search(r"(powered\s+by\s+@?[^\s].*)$", message_part, flags=re.IGNORECASE)
                if powered_match:
                    message_part = message_part[:powered_match.start()].strip()
                    powered_part = powered_match.group(1).strip()

            if message_part:
                pdf.setFont(bold_font, 11)
                for line in wrap_text(message_part, 44):
                    pdf.drawCentredString(footer_center_x, y, line)
                    y -= customer_step

            if powered_part:
                # Keep "Powered by ..." on its own centered line with slightly smaller text.
                pdf.setFont(regular_font, 8)
                pdf.drawCentredString(footer_center_x, y, powered_part)
                y -= customer_step


    # =========================
    # TAILOR SLIP (CLEAN VERSION)
    # =========================
    else:
        tailor_left_x = left_x
        tailor_right_x = right_x
        tailor_center_x = (tailor_left_x + tailor_right_x) / 2
        tailor_colon_x = tailor_left_x + (22 * mm)
        tailor_value_x = tailor_colon_x + (3.2 * mm)
        wrap_len = 88 if mode != "customer" else (42 if not landscape else 72)
        dash_rule = "-" * 150
        tailor_font_size = 11.6
        req_note_font_size = tailor_font_size + 0.8
        min_tailor_y = 12 * mm if mode != "customer" else 6 * mm
        page_state_active = bool(rotated_landscape_tailor)
        tailor_page_no = 1
        req_note_label_col_width = 0.0
        tailor_header_invoice = (
            order["invoice_id"] if "invoice_id" in order.keys() and order["invoice_id"] else display_order_no(dict(order))
        )
        tailor_header_date = datetime_display(order["created_at"])
        tailor_header_delivery = date_only(order["due_date"]) if "due_date" in order.keys() and order["due_date"] else "-"

        try:
            req_note_label_col_width = max(
                pdf.stringWidth("Requirements", bold_font, req_note_font_size),
                pdf.stringWidth("Notes", bold_font, req_note_font_size),
            )
        except Exception:
            req_note_label_col_width = 22 * mm

        def _fit_tailor_header_text(text: str, max_width: float, font_name: str, font_size: float) -> str:
            value = str(text or "").strip()
            if max_width <= 0:
                return value
            while value and pdf.stringWidth(value, font_name, font_size) > max_width:
                value = value[:-1]
            return value

        def draw_tailor_page_header(include_rule: bool = True):
            nonlocal y
            header_font_size = max(8.0, float(tailor_font_size) + 0.5)
            col_gap = 2.2 * mm
            total_width = max(1.0, tailor_right_x - tailor_left_x)
            col_width = max(1.0, (total_width - (2.0 * col_gap)) / 3.0)
            col1_x = tailor_left_x
            col2_x = col1_x + col_width + col_gap
            col3_x = col2_x + col_width + col_gap
            inv_text = _fit_tailor_header_text(f"INVOICE NO: {tailor_header_invoice or '-'}", col_width, bold_font, header_font_size)
            order_text = _fit_tailor_header_text(f"ORDER DATE: {tailor_header_date or '-'}", col_width, bold_font, header_font_size)
            delivery_text = _fit_tailor_header_text(f"DELIVERY DATE: {tailor_header_delivery or '-'}", col_width, bold_font, header_font_size)
            pdf.setFont(bold_font, header_font_size)
            pdf.drawString(col1_x, y, inv_text)
            pdf.drawString(col2_x, y, order_text)
            pdf.drawString(col3_x, y, delivery_text)
            y -= line_height
            if include_rule:
                draw_tailor_rule(allow_page_break=False)
                draw_tailor_gap(0.15)

        def ensure_tailor_space(lines_needed: int = 1):
            nonlocal y, page_state_active
            required = max(1, lines_needed) * line_height
            if (y - required) >= min_tailor_y:
                return
            draw_tailor_page_footer()
            if rotated_landscape_tailor and page_state_active:
                pdf.restoreState()
                page_state_active = False
            pdf.showPage()
            if rotated_landscape_tailor:
                pdf.saveState()
                pdf.translate(0, canvas_height)
                pdf.rotate(-90)
                page_state_active = True
            elif landscape and mode == "customer":
                pdf.setPageRotation(90)
            draw_logo_watermark()
            y = logical_height - 6 * mm
            draw_tailor_page_header(include_rule=True)

        def draw_tailor_line(text: str, bold: bool = False):
            nonlocal y
            ensure_tailor_space(1)
            pdf.setFont(bold_font if bold else regular_font, tailor_font_size)
            pdf.drawString(tailor_left_x, y, text)
            y -= line_height

        def draw_tailor_rule(allow_page_break: bool = True):
            nonlocal y
            if allow_page_break:
                ensure_tailor_space(1)
            elif (y - line_height) < min_tailor_y:
                return
            pdf.setFont("Courier", tailor_font_size)
            pdf.drawString(tailor_left_x, y, dash_rule)
            y -= line_height

        def draw_tailor_gap(multiplier: float = 0.35):
            nonlocal y
            y -= (line_height * multiplier)

        def align_tailor_requirements_start():
            # Keep natural flow so slip height adapts to content length.
            return

        def draw_tailor_page_footer():
            nonlocal tailor_page_no
            pdf.setFont(regular_font, 9)
            pdf.drawCentredString(logical_width / 2, 4 * mm, f"Page {tailor_page_no}")
            tailor_page_no += 1

        def draw_tailor_kv(label: str, value: str | None):
            nonlocal y
            ensure_tailor_space(1)
            pdf.setFont(bold_font, tailor_font_size)
            pdf.drawString(tailor_left_x, y, label)
            pdf.drawString(tailor_colon_x, y, ":")
            text = str(value).strip() if value is not None else ""
            pdf.drawString(tailor_value_x, y, text or "-")
            y -= line_height

        def draw_tailor_item(item_name: str, qty_value: int):
            nonlocal y
            item_lines = wrap_text(item_name or "Item", max(20, wrap_len - 18)) or ["Item"]
            pdf.setFont(bold_font, tailor_font_size)
            pdf.drawString(tailor_left_x, y, item_lines[0])
            y -= line_height
            for extra in item_lines[1:]:
                pdf.drawString(tailor_left_x, y, extra)
                y -= line_height

        def draw_tailor_labeled_value(
            label: str,
            value_text: str | None,
            single_line: bool = False,
            font_size: float | None = None,
        ):
            nonlocal y
            def has_tamil_chars(text: str) -> bool:
                return any(0x0B80 <= ord(ch) <= 0x0BFF for ch in str(text or ""))
            text_font_size = float(font_size if font_size is not None else tailor_font_size)
            text = str(value_text or "").strip()
            lines = wrap_text(text or "-", max(12, wrap_len - 24)) or ["-"]
            # Keep label/colon/value columns fixed for equal alignment.
            colon_x = max(tailor_colon_x, tailor_left_x + req_note_label_col_width + (1.5 * mm))
            value_x = colon_x + (2.5 * mm)
            label_font_name = tamil_font if has_tamil_chars(label) else bold_font
            if single_line:
                one_line = lines[0]
                max_width = max(0.0, tailor_right_x - value_x)
                one_font_name = tamil_font if has_tamil_chars(one_line) else bold_font
                while one_line and string_width_safe(one_line, one_font_name, text_font_size) > max_width:
                    one_line = one_line[:-1]
                if one_line != lines[0]:
                    while one_line and string_width_safe(one_line + "...", one_font_name, text_font_size) > max_width:
                        one_line = one_line[:-1]
                    one_line = one_line.rstrip() + "..."
                lines = [one_line or "-"]
            ensure_tailor_space(len(lines))
            draw_string_safe(tailor_left_x, y, label, label_font_name, text_font_size)
            draw_string_safe(colon_x, y, ":", bold_font, text_font_size)
            value_first_font = tamil_font if has_tamil_chars(lines[0]) else bold_font
            draw_string_safe(value_x, y, lines[0], value_first_font, text_font_size)
            y -= line_height
            for extra in lines[1:]:
                ensure_tailor_space(1)
                extra_font_name = tamil_font if has_tamil_chars(extra) else bold_font
                draw_string_safe(value_x, y, extra, extra_font_name, text_font_size)
                y -= line_height

        def draw_tailor_item_labeled(item_name: str, qty_value: int):
            nonlocal y
            def has_tamil_chars(text: str) -> bool:
                return any(0x0B80 <= ord(ch) <= 0x0BFF for ch in str(text or ""))
            text = str(item_name or "").strip() or "Item"
            lines = wrap_text(text, max(12, wrap_len - 24)) or ["Item"]
            ensure_tailor_space(len(lines))
            draw_string_safe(tailor_left_x, y, "Items", bold_font, tailor_font_size)
            draw_string_safe(tailor_colon_x, y, ":", regular_font, tailor_font_size)
            first_font_name = tamil_font if has_tamil_chars(lines[0]) else bold_font
            draw_string_safe(tailor_value_x, y, lines[0], first_font_name, tailor_font_size)
            pdf.setFont(bold_font, tailor_font_size)
            y -= line_height
            for extra in lines[1:]:
                ensure_tailor_space(1)
                extra_font_name = tamil_font if has_tamil_chars(extra) else bold_font
                draw_string_safe(tailor_value_x, y, extra, extra_font_name, tailor_font_size)
                y -= line_height

        def draw_tailor_measure_values(values: list[tuple[str, str]], is_shirt: bool = False):
            nonlocal y
            def has_tamil_chars(text: str) -> bool:
                return any(0x0B80 <= ord(ch) <= 0x0BFF for ch in str(text or ""))

            clean_pairs = [
                (str(label).strip(), str(value).strip())
                for label, value in values
                if str(label).strip() and str(value).strip()
            ]
            if not clean_pairs:
                draw_tailor_line("-")
                return
            columns: list[tuple[str, list[str]]] = []
            for label, raw_value in clean_pairs:
                parts = [p.strip() for p in str(raw_value).split(",") if p and p.strip()]
                if not parts:
                    continue
                # Keep PDF wording exactly as the incoming measurement label.
                display_label = str(label).strip()
                columns.append((display_label, parts))

            if not columns:
                draw_tailor_line("-")
                return

            available_width = max(0.0, tailor_right_x - tailor_left_x)
            # Keep measurement names smaller than the slip body text.
            label_font_size = max(7.8, float(tailor_font_size) - 4.0)
            # Make measurement values larger and stronger for readability.
            value_font_size = max(11.8, float(tailor_font_size) + 2)
            column_gap = 1.8 * mm
            value_font_name = bold_font
            row_height = line_height

            def wrap_token_lines(
                token: str,
                font_name: str,
                font_size: float,
                max_width: float,
                min_chars_before_split: int = 10,
            ) -> list[str]:
                text = str(token or "").strip() or "-"
                if max_width <= 0:
                    return [text]
                if pdf.stringWidth(text, font_name, font_size) <= max_width:
                    return [text]
                def split_clusters(value: str) -> list[str]:
                    clusters: list[str] = []
                    for ch in str(value or ""):
                        if not clusters:
                            clusters.append(ch)
                            continue
                        cp = ord(ch)
                        is_mark = unicodedata.combining(ch) != 0
                        is_joiner = ch in ("\u200c", "\u200d")
                        # Tamil dependent vowel signs and virama should stay with base glyph.
                        is_tamil_sign = 0x0BBE <= cp <= 0x0BCD
                        if is_mark or is_joiner or is_tamil_sign:
                            clusters[-1] += ch
                        else:
                            clusters.append(ch)
                    return clusters or ["-"]

                def slice_by_clusters(value: str, cluster_count: int) -> tuple[str, str]:
                    if cluster_count <= 0:
                        return "", value
                    clusters = split_clusters(value)
                    left = "".join(clusters[:cluster_count])
                    right = "".join(clusters[cluster_count:])
                    return left, right

                lines: list[str] = []
                remaining = text
                while remaining:
                    if pdf.stringWidth(remaining, font_name, font_size) <= max_width:
                        lines.append(remaining)
                        break
                    cut = len(remaining)
                    while cut > 0 and pdf.stringWidth(remaining[:cut], font_name, font_size) > max_width:
                        cut -= 1
                    if cut <= 0:
                        lines.append(remaining)
                        break
                    split_at = remaining.rfind(" ", 0, cut + 1)
                    if split_at > 0:
                        line_part = remaining[:split_at].rstrip()
                        remaining = remaining[split_at + 1 :].lstrip()
                    else:
                        remaining_clusters = split_clusters(remaining)
                        min_cut = min(len(remaining_clusters), max(1, int(min_chars_before_split)))
                        if cut < min_cut:
                            probe = min_cut
                            while probe > cut:
                                probe_text, _ = slice_by_clusters(remaining, probe)
                                if pdf.stringWidth(probe_text, font_name, font_size) <= max_width:
                                    cut = probe
                                    break
                                probe -= 1
                        line_part, remaining = slice_by_clusters(remaining, cut)
                        line_part = line_part.rstrip()
                        remaining = remaining.lstrip()
                    if line_part:
                        lines.append(line_part)
                    elif remaining:
                        first_cluster, rest_clusters = slice_by_clusters(remaining, 1)
                        lines.append(first_cluster)
                        remaining = rest_clusters.lstrip()
                return lines or ["-"]

            def draw_measure_columns(columns_slice: list[tuple[str, list[str]]]):
                nonlocal y
                if not columns_slice:
                    return
                count = len(columns_slice)
                total_gap = column_gap * float(max(0, count - 1))
                slot_width = (available_width - total_gap) / float(max(1, count))
                if slot_width <= 0:
                    slot_width = available_width / float(max(1, count))
                slot_inner_width = slot_width * 0.92

                prepared_columns: list[tuple[float, float, float, list[tuple[str, str]], list[tuple[str, str]]]] = []
                max_label_lines = 1
                max_value_lines = 1

                for idx, (label, value_parts) in enumerate(columns_slice):
                    slot_left_x = tailor_left_x + ((slot_width + column_gap) * idx)
                    slot_right_x = slot_left_x + slot_width
                    slot_center_x = slot_left_x + (slot_width / 2.0)

                    label_font_name = tamil_font if has_tamil_chars(label) else bold_font
                    label_lines = [
                        (token, label_font_name)
                        for token in wrap_token_lines(label, label_font_name, label_font_size, slot_inner_width)
                    ]
                    value_lines: list[tuple[str, str]] = []
                    for token in value_parts:
                        token_font_name = tamil_font if has_tamil_chars(token) else value_font_name
                        for wrapped in wrap_token_lines(token, token_font_name, value_font_size, slot_inner_width):
                            value_lines.append((wrapped, token_font_name))
                    if not value_lines:
                        value_lines = [("-", value_font_name)]

                    prepared_columns.append((slot_left_x, slot_right_x, slot_center_x, label_lines, value_lines))
                    max_label_lines = max(max_label_lines, len(label_lines))
                    max_value_lines = max(max_value_lines, len(value_lines))

                total_lines = max_label_lines + max_value_lines
                ensure_tailor_space(total_lines)

                def draw_aligned(token: str, line_index: int, font_name: str, font_size: float, slot_left_x: float, slot_right_x: float, slot_center_x: float):
                    text = str(token or "").strip() or "-"
                    token_width = string_width_safe(text, font_name, font_size)
                    draw_x = slot_center_x - (token_width / 2.0)
                    draw_x = max(slot_left_x, min(draw_x, slot_right_x - token_width))
                    draw_x = max(tailor_left_x, min(draw_x, tailor_right_x - token_width))
                    draw_y = y - (row_height * line_index)
                    draw_string_safe(draw_x, draw_y, text, font_name, font_size)

                for slot_left_x, slot_right_x, slot_center_x, label_lines, value_lines in prepared_columns:
                    for idx_label, (token, token_font) in enumerate(label_lines):
                        draw_aligned(token, idx_label, token_font, label_font_size, slot_left_x, slot_right_x, slot_center_x)
                    for idx_value, (token, token_font) in enumerate(value_lines):
                        draw_aligned(
                            token,
                            max_label_lines + idx_value,
                            token_font,
                            value_font_size,
                            slot_left_x,
                            slot_right_x,
                            slot_center_x,
                        )

                y -= (row_height * total_lines)

            min_slot_width = 13.5 * mm
            max_cols_per_row = max(1, int((available_width + column_gap) // (min_slot_width + column_gap)))
            max_cols_per_row = min(max_cols_per_row, len(columns))
            if max_cols_per_row <= 0:
                max_cols_per_row = len(columns)

            start_idx = 0
            while start_idx < len(columns):
                draw_measure_columns(columns[start_idx:start_idx + max_cols_per_row])
                start_idx += max_cols_per_row
                if start_idx < len(columns):
                    draw_tailor_gap(0.1)

        def start_new_tailor_page():
            nonlocal y, page_state_active
            draw_tailor_page_footer()
            if rotated_landscape_tailor and page_state_active:
                pdf.restoreState()
                page_state_active = False
            pdf.showPage()
            if rotated_landscape_tailor:
                pdf.saveState()
                pdf.translate(0, canvas_height)
                pdf.rotate(-90)
                page_state_active = True
            draw_logo_watermark()
            y = logical_height - 6 * mm
            draw_tailor_page_header(include_rule=True)

        def measurement_item_for_row(row):
            row_kind = (row["kind"] or "").strip()
            row_kind_lower = row_kind.lower()
            row_kind_norm = normalize_measure_type(row_kind)
            for item in order_items:
                item_kind = (item["item_type"] or "").strip()
                if not item_kind:
                    continue
                item_kind_lower = item_kind.lower()
                item_kind_norm = normalize_measure_type(item_kind)
                if item_kind_lower == row_kind_lower:
                    return item
                if row_kind_norm and item_kind_norm and row_kind_norm == item_kind_norm:
                    return item
                if row_kind_norm and row_kind_norm in item_kind_lower:
                    return item
            return None

        y = logical_height - 6 * mm
        draw_tailor_page_header(include_rule=True)

        if matched_measurements:
            order_no_text = str(order.get("order_no") or order.get("id") or "").replace("\\", "/")
            order_prefix = order_no_text.split("/", 1)[0] if "/" in order_no_text else order_no_text
            prev_item_page_key = ""
            for idx, m in enumerate(matched_measurements, start=1):
                item_row = measurement_item_for_row(m)
                item_name = (m["kind"] or "Item").strip()
                qty_value = 1
                if item_row is not None:
                    item_name = (item_row["item_type"] or item_name).strip()
                    try:
                        qty_value = int(round(float(item_row["qty"] or 0)))
                    except Exception:
                        qty_value = 1
                qty_value = max(1, qty_value)
                item_page_key = normalize_measure_type(item_name) or item_name.lower()

                # Start a new page only when the item changes.
                if idx > 1 and item_page_key != prev_item_page_key:
                    start_new_tailor_page()
                prev_item_page_key = item_page_key

                draw_tailor_item_labeled(item_name, qty_value)
                draw_tailor_gap(0.0)

                draw_tailor_line("Measurements", bold=True)
                draw_tailor_gap(0.0)
                draw_tailor_line(f"{order_prefix}/{idx} - {item_name}", bold=True)
                # Keep size row visually aligned with the measurement heading block.
                draw_tailor_gap(0.05)
                values = measurement_values(m)
                draw_tailor_measure_values(values, is_shirt=("shirt" in item_page_key))

                m_notes = (m["notes"] or "").strip() if "notes" in m.keys() else ""
                item_requirements = extract_requirements(m_notes) or global_requirements
                if item_requirements:
                    align_tailor_requirements_start()
                    draw_tailor_gap(0.25)
                    req_text = ", ".join([str(r).strip() for r in item_requirements if str(r).strip()])
                    draw_tailor_labeled_value("Requirements", req_text, single_line=True, font_size=req_note_font_size)
                    draw_tailor_gap(0.1)

                item_note_lines = extract_item_notes(m_notes)
                if item_note_lines:
                    note_text = " ".join([str(n).strip() for n in item_note_lines if str(n).strip()])
                    draw_tailor_labeled_value("Notes", note_text, single_line=True, font_size=req_note_font_size)
                    draw_tailor_gap(0.1)

                draw_tailor_gap(0.2)

        notes_lines: list[str] = []
        if order_notes_raw:
            for line in str(order_notes_raw).splitlines():
                if line.strip().lower().startswith("requirements:"):
                    continue
                notes_lines.extend(extract_tailor_notes(line))

        for item in order_items:
            item_note = (item["notes"] or "").strip() if "notes" in item.keys() else ""
            if item_note:
                notes_lines.extend(extract_tailor_notes(item_note))

        if not matched_measurements:
            if global_requirements:
                align_tailor_requirements_start()
                draw_tailor_gap(0.25)
                req_text = ", ".join([str(r).strip() for r in global_requirements if str(r).strip()])
                draw_tailor_labeled_value("Requirements", req_text, single_line=True, font_size=req_note_font_size)
                draw_tailor_gap(0.1)
                draw_tailor_gap(0.2)

            if notes_lines:
                note_text = " ".join([str(n).strip() for n in notes_lines if str(n).strip()])
                draw_tailor_labeled_value("Notes", note_text, single_line=True, font_size=req_note_font_size)
                draw_tailor_gap(0.1)

        draw_tailor_page_footer()

    if rotated_landscape_tailor and page_state_active:
        pdf.restoreState()
    pdf.save()
    return file_path

def upsert_customer(
    conn_or_name: sqlite3.Connection | str,
    name: str | None = None,
    phone: str | None = None,
    notes: str | None = None,
    address: str | None = None
) -> int:
    owns_conn = False
    if isinstance(conn_or_name, sqlite3.Connection):
        conn = conn_or_name
    else:
        name, phone, notes = conn_or_name, name, phone
        conn = get_db()
        owns_conn = True
    if name is None or phone is None:
        raise ValueError("Customer name and phone are required.")
    cur = conn.cursor()
    phone = phone.strip()
    if not is_valid_phone(phone):
        raise ValueError("Phone number can contain only digits and leading +.")

    row = find_customer_by_phone(conn, phone)

    if row:
        cur.execute(
            "UPDATE customers SET name = ?, phone = ?, address = ?, notes = ? WHERE id = ?",
            (name, phone, address, notes, row["id"]),
        )
        if owns_conn:
            conn.commit()
            conn.close()
        return int(row["id"])
    else:
        cur.execute(
            """
            INSERT INTO customers (name, phone, address, notes, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, phone, address, notes, now_str()),
        )
        if owns_conn:
            conn.commit()
            conn.close()
        if cur.lastrowid is None:
            raise RuntimeError("Customer insert failed: could not read new ID from database.")
        return int(cur.lastrowid)


# def upsert_customer(name: str, phone: str, notes: str | None, address: str | None = None) -> int:
#     conn = get_db()
#     cur = conn.cursor()
#     cur.execute("SELECT id FROM customers WHERE phone = ?", (phone,))
#     row = cur.fetchone()
#     if row:
#         cur.execute(
#             "UPDATE customers SET name = ?, address = ?, notes = ? WHERE id = ?",
#             (name, address, notes, row["id"]),
#         )
#         customer_id = row["id"]
#     else:
#         cur.execute(
#             "INSERT INTO customers (name, phone, address, notes, created_at) VALUES (?, ?, ?, ?, ?)",
#             (name, phone, address, notes, now_str()),
#         )
#         customer_id = cur.lastrowid
#     conn.commit()
#     conn.close()
#     return int(customer_id)


def create_measurement(
    customer_id: int,
    kind: str,
    fields: dict[str, str],
    allow_empty: bool = False,
    order_id: int | None = None,
    conn: sqlite3.Connection | None = None,
) -> None:
    numeric_keys = [
        "neck",
        "chest",
        "waist",
        "hip",
        "shoulder",
        "sleeve",
        "length",
        "cuff",
        "inseam",
        "outseam",
        "thigh",
        "knee",
        "bottom",
    ]
    invalid_lines: list[str] = []
    numeric_values: dict[str, float | None] = {}
    for key in numeric_keys:
        raw = str(fields.get(key) or "").strip()
        if not raw:
            numeric_values[key] = None
            continue
        parsed = parse_measure_value(raw)
        if parsed is None:
            numeric_values[key] = None
            invalid_lines.append(f"{key}: {raw}")
            continue
        numeric_values[key] = parsed

    notes_text = str(fields.get("notes") or "").strip()
    if invalid_lines:
        invalid_text = "Invalid measurement values:\n" + "\n".join(invalid_lines)
        notes_text = f"{notes_text}\n{invalid_text}".strip() if notes_text else invalid_text

    values = {
        "measure_status": (fields.get("measure_status") or "In-Progress"),
        "neck": numeric_values["neck"],
        "chest": numeric_values["chest"],
        "waist": numeric_values["waist"],
        "hip": numeric_values["hip"],
        "shoulder": numeric_values["shoulder"],
        "sleeve": numeric_values["sleeve"],
        "length": numeric_values["length"],
        "cuff": numeric_values["cuff"],
        "inseam": numeric_values["inseam"],
        "outseam": numeric_values["outseam"],
        "thigh": numeric_values["thigh"],
        "knee": numeric_values["knee"],
        "bottom": numeric_values["bottom"],
        "assigned_tailor": fields.get("assigned_tailor") or None,
        "notes": notes_text or None,
    }
    if not allow_empty and not any(values.values()):
        return

    owns_conn = conn is None
    conn = conn or get_db()
    conn.execute(
        """
        INSERT INTO measurements (
            customer_id, order_id, measure_status, kind, neck, chest, waist, hip, shoulder, sleeve, length, cuff,
            inseam, outseam, thigh, knee, bottom, assigned_tailor, notes, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            customer_id,
            order_id,
            values["measure_status"],
            kind,
            values["neck"],
            values["chest"],
            values["waist"],
            values["hip"],
            values["shoulder"],
            values["sleeve"],
            values["length"],
            values["cuff"],
            values["inseam"],
            values["outseam"],
            values["thigh"],
            values["knee"],
            values["bottom"],
            values["assigned_tailor"],
            values["notes"],
            now_str(),
        ),
    )
    if owns_conn:
        conn.commit()
        conn.close()


def generate_tailor_code(conn: sqlite3.Connection) -> str:
    return next_staff_code_for_role(conn, "shirt")


def _staff_prefix(role: str | None) -> str:
    role_text = (role or "").strip().lower()
    if "pant" in role_text:
        return "P"
    return "S"


def staff_code_from_role(role: str | None, staff_id: int) -> str:
    prefix = _staff_prefix(role)
    return f"{prefix}{int(staff_id):03d}"


def next_staff_code_for_role(conn: sqlite3.Connection, role: str | None) -> str:
    prefix = _staff_prefix(role)
    rows = conn.execute(
        "SELECT tailor_code FROM tailors WHERE tailor_code LIKE ?",
        (f"{prefix}%",),
    ).fetchall()
    max_num = 0
    for row in rows:
        value = str(row["tailor_code"] or "").strip()
        if not value.startswith(prefix):
            continue
        digits = value[1:]
        if digits.isdigit():
            max_num = max(max_num, int(digits))
    return f"{prefix}{(max_num + 1):03d}"


def clean_staff_name(name: str | None) -> str:
    text = (name or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    prefixes = [
        "pant tailor ",
        "shirt tailor ",
        "tailor ",
    ]
    for p in prefixes:
        if lowered.startswith(p):
            return text[len(p):].strip() or text
    return text


def get_setting(key: str, default: str = "") -> str:
    conn = get_db()
    row = conn.execute("SELECT value FROM app_settings WHERE [key] = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    conn = get_db()
    exists = conn.execute(
        "SELECT id FROM app_settings WHERE [key] = ?",
        (key,),
    ).fetchone()
    if exists:
        conn.execute(
            "UPDATE app_settings SET value = ? WHERE [key] = ?",
            (value, key),
        )
    else:
        conn.execute(
            "INSERT INTO app_settings ([key], value) VALUES (?, ?)",
            (key, value),
        )
    conn.commit()
    conn.close()


@app.context_processor
def inject_app_setting():
    return {"app_setting": get_setting}


def parse_order_tax_payload(form, total_value: float | None) -> dict[str, float]:
    def to_float(name: str, default: float = 0.0) -> float:
        raw = (form.get(name) or "").strip()
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return default
        return value if math.isfinite(value) else default

    taxable_amount = max(0.0, to_float("taxable_amount", 0.0))
    gst_percent = max(0.0, to_float("gst_percent", 0.0))
    gst_amount = max(0.0, to_float("gst_amount", 0.0))
    cgst_percent = max(0.0, to_float("cgst_percent", 0.0))
    cgst_amount = max(0.0, to_float("cgst_amount", 0.0))
    sgst_percent = max(0.0, to_float("sgst_percent", 0.0))
    sgst_amount = max(0.0, to_float("sgst_amount", 0.0))

    if taxable_amount <= 0 and total_value:
        taxable_amount = max(0.0, float(total_value) - gst_amount)

    if gst_amount <= 0 and taxable_amount > 0 and gst_percent > 0:
        gst_amount = taxable_amount * gst_percent / 100.0

    if gst_percent <= 0 and taxable_amount > 0 and gst_amount > 0:
        gst_percent = (gst_amount * 100.0) / taxable_amount

    if cgst_amount <= 0 and gst_amount > 0:
        cgst_amount = gst_amount / 2.0
    if sgst_amount <= 0 and gst_amount > 0:
        sgst_amount = gst_amount / 2.0
    if cgst_percent <= 0 and gst_percent > 0:
        cgst_percent = gst_percent / 2.0
    if sgst_percent <= 0 and gst_percent > 0:
        sgst_percent = gst_percent / 2.0

    return {
        "taxable_amount": round(taxable_amount, 2),
        "gst_percent": round(gst_percent, 2),
        "gst_amount": round(gst_amount, 2),
        "cgst_percent": round(cgst_percent, 2),
        "cgst_amount": round(cgst_amount, 2),
        "sgst_percent": round(sgst_percent, 2),
        "sgst_amount": round(sgst_amount, 2),
    }


def parse_order_discount_amount(form, taxable_amount: float) -> float:
    raw_discount = (form.get("discount") or "").strip()
    try:
        discount_value = float(raw_discount) if raw_discount else 0.0
    except (TypeError, ValueError):
        discount_value = 0.0
    if not math.isfinite(discount_value):
        discount_value = 0.0
    discount_value = max(0.0, discount_value)

    discount_mode = (form.get("discount_type") or "percent").strip().lower()
    if discount_mode == "amount":
        return round(discount_value, 2)

    if discount_value <= 0:
        return 0.0
    if discount_value >= 100:
        return 0.0
    subtotal = taxable_amount / (1.0 - (discount_value / 100.0))
    discount_amount = max(0.0, subtotal - taxable_amount)
    return round(discount_amount, 2)


def is_gst_enabled_for_order_type(order_type: str) -> bool:
    key = (order_type or "").strip().lower()
    setting_map = {
        "tailoring": ("gst_enable_tailoring", "1"),
        "alteration": ("gst_enable_alteration", "0"),
        "material": ("gst_enable_material", "0"),
    }
    setting_key, default_value = setting_map.get(key, ("gst_enable_tailoring", "1"))
    return get_setting(setting_key, default_value).strip() == "1"


def apply_gst_toggle_to_tax_payload(
    tax_payload: dict[str, float],
    total_value: float | None,
    gst_enabled: bool,
) -> dict[str, float]:
    if gst_enabled:
        return tax_payload
    safe_total = max(0.0, float(total_value or 0.0))
    return {
        "taxable_amount": round(safe_total, 2),
        "gst_percent": 0.0,
        "gst_amount": 0.0,
        "cgst_percent": 0.0,
        "cgst_amount": 0.0,
        "sgst_percent": 0.0,
        "sgst_amount": 0.0,
    }


def get_installed_printer_names() -> list[str]:
    if os.name != "nt":
        return []
    try:
        import win32print  # type: ignore
    except Exception:
        return []
    try:
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        rows = win32print.EnumPrinters(flags)
        names = [str(row[2]).strip() for row in rows if len(row) > 2 and str(row[2]).strip()]
        return sorted(set(names), key=str.lower)
    except Exception:
        return []


def archive_print_softcopy(pdf_path: str, order_id: int, mode: str) -> str:
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = APP_DIR
    target_dir = os.path.join(base_dir, "print_softcopies")
    os.makedirs(target_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_name = f"order_{order_id}_{mode}_{stamp}.pdf"
    target_path = os.path.join(target_dir, target_name)
    shutil.copy2(pdf_path, target_path)
    return target_path


def print_pdf_to_configured_printer(pdf_path: str, printer_name: str) -> tuple[bool, str]:
    if os.name != "nt":
        return False, "Auto print is supported on Windows only."
    clean_printer = printer_name.strip()
    errors: list[str] = []

    try:
        import win32api  # type: ignore
        try:
            if clean_printer:
                win32api.ShellExecute(0, "printto", pdf_path, f'"{clean_printer}"', ".", 0)
                return True, ""
        except Exception as ex:
            errors.append(f"win32 printto: {ex}")
        try:
            win32api.ShellExecute(0, "print", pdf_path, None, ".", 0)
            return True, ""
        except Exception as ex:
            errors.append(f"win32 print: {ex}")
    except Exception:
        errors.append("win32api not available")

    # Fallback path: use PowerShell print verbs.
    try:
        safe_pdf = pdf_path.replace("'", "''")
        if clean_printer:
            safe_printer = clean_printer.replace("'", "''")
            script = (
                f"Start-Process -FilePath '{safe_pdf}' "
                f"-Verb PrintTo -ArgumentList '\"{safe_printer}\"' -WindowStyle Hidden"
            )
        else:
            script = f"Start-Process -FilePath '{safe_pdf}' -Verb Print -WindowStyle Hidden"
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return True, ""
    except Exception as ex:
        errors.append(f"powershell print verb: {ex}")

    return False, "; ".join(errors)


def process_post_print_actions(pdf_path: str, order_id: int, mode: str) -> None:
    if not pdf_path or not os.path.exists(pdf_path):
        return
    try:
        archive_print_softcopy(pdf_path, order_id, mode)
    except Exception as ex:
        print(f"[PRINT] Softcopy save failed for order {order_id}: {ex}")
    if get_setting("auto_print_on_click", "0").strip() == "1":
        printer_name = get_setting("default_printer_name", "").strip()
        ok, err = print_pdf_to_configured_printer(pdf_path, printer_name)
        if not ok:
            print(f"[PRINT] Auto print failed for order {order_id}: {err}")


def force_print_to_selected_printer(pdf_path: str, order_id: int, mode: str) -> tuple[bool, str]:
    if not pdf_path or not os.path.exists(pdf_path):
        return False, "Print file not found."
    try:
        archive_print_softcopy(pdf_path, order_id, mode)
    except Exception as ex:
        print(f"[PRINT] Softcopy save failed for order {order_id}: {ex}")
    printer_name = get_setting("default_printer_name", "").strip()
    if not printer_name:
        return False, "Default printer is not configured in Settings."
    return print_pdf_to_configured_printer(pdf_path, printer_name)


def get_company_address_lines() -> list[str]:
    line1 = get_setting("address_line1", "").strip()
    line2 = get_setting("address_line2", "").strip()
    line3 = get_setting("address_line3", "").strip()
    lines = [line for line in (line1, line2, line3) if line]
    if lines:
        return lines

    # Backward compatibility for existing single-line address setting.
    fallback = get_setting("address_name", "").strip()
    if not fallback:
        return []
    parts = [part.strip() for part in re.split(r"[\r\n,]+", fallback) if part.strip()]
    return parts[:3]


def generate_inventory_code(conn: sqlite3.Connection, name: str) -> str:
    base = "".join(ch for ch in name.upper() if ch.isalnum())
    prefix = base[:3] if len(base) >= 3 else (base or "INV")
    cur = conn.cursor()
    cur.execute(
        "SELECT inventory_code FROM inventory WHERE inventory_code LIKE ? ORDER BY id DESC LIMIT 1",
        (f"{prefix}-%",),
    )
    row = cur.fetchone()
    if row and row["inventory_code"]:
        try:
            last_num = int(row["inventory_code"].split("-")[-1])
            return f"{prefix}-{last_num + 1:03d}"
        except ValueError:
            pass
    return f"{prefix}-001"


def generate_vendor_code(conn: sqlite3.Connection) -> str:
    cur = conn.cursor()
    cur.execute("SELECT vendor_code FROM vendors ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    if row and row["vendor_code"] and row["vendor_code"].startswith("VND"):
        try:
            last_num = int(row["vendor_code"][3:])
            return f"VND{last_num + 1:04d}"
        except ValueError:
            pass
    cur.execute("SELECT COUNT(*) FROM vendors")
    count = cur.fetchone()[0] + 1
    return f"VND{count:04d}"

@app.route("/")
def home():
    if session.get("is_authenticated"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    q = request.args.get("q", "").strip()
    profit_range = request.args.get("profit_range", "today").strip().lower()
    orders_range = request.args.get("orders_range", "today").strip().lower()
    from_date = request.args.get("from_date", "").strip()
    to_date = request.args.get("to_date", "").strip()

    def _is_valid_iso_date(value: str) -> bool:
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    if from_date and not _is_valid_iso_date(from_date):
        from_date = ""
    if to_date and not _is_valid_iso_date(to_date):
        to_date = ""
    if from_date and to_date and from_date > to_date:
        from_date, to_date = to_date, from_date

    date_filter_active = bool(from_date and to_date)
    total_order_chip = "Range" if date_filter_active else "Today"
    conn = get_db()
    counts_sql = "SELECT orders.status, COUNT(*) as total FROM orders"
    counts_params = []
    if date_filter_active:
        counts_sql += " WHERE date(orders.created_at) BETWEEN ? AND ?"
        counts_params.extend([from_date, to_date])
    counts_sql += " GROUP BY orders.status"
    counts = {
        row["status"]: row["total"]
        for row in conn.execute(counts_sql, tuple(counts_params)).fetchall()
    }
    now_dt = datetime.now()
    today = now_dt.date()
    if date_filter_active:
        total_orders_today = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM orders
            WHERE date(created_at) BETWEEN ? AND ?
            """,
            (from_date, to_date),
        ).fetchone()
        total_items = conn.execute(
            """
            SELECT COUNT(*) AS total_items
            FROM orders
            WHERE order_type = 'Tailoring'
              AND status = 'Completed'
              AND date(created_at) BETWEEN ? AND ?
            """,
            (from_date, to_date),
        ).fetchone()
    else:
        total_orders_today = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM orders
            WHERE date(created_at) = ?
            """,
            (today.isoformat(),),
        ).fetchone()
        total_items = conn.execute(
            """
            SELECT COUNT(*) AS total_items
            FROM orders
            WHERE order_type = 'Tailoring' AND status = 'Completed'
            """
        ).fetchone()
    tomorrow = (today + timedelta(days=1)).isoformat()
    if date_filter_active:
        urgent_count = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM orders
            WHERE status NOT IN ('Cancelled', 'Delivered')
              AND due_date IS NOT NULL
              AND date(due_date) BETWEEN ? AND ?
            """,
            (from_date, to_date),
        ).fetchone()
    else:
        urgent_count = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM orders
            WHERE status NOT IN ('Cancelled', 'Delivered')
              AND due_date IS NOT NULL
              AND date(due_date) BETWEEN ? AND ?
            """,
            (today.isoformat(), tomorrow),
        ).fetchone()
    left2_date = (today + timedelta(days=2)).isoformat()
    if date_filter_active:
        left2_count = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM orders
            WHERE status != 'Cancelled'
              AND date(due_date) BETWEEN ? AND ?
            """,
            (from_date, to_date),
        ).fetchone()
    else:
        left2_count = conn.execute(
            """
            SELECT COUNT(*) AS total
            FROM orders
            WHERE status != 'Cancelled'
              AND date(due_date) = ?
            """,
            (left2_date,),
        ).fetchone()
    stock_units = conn.execute(
        "SELECT COALESCE(SUM(qty), 0) AS stock_units FROM inventory"
    ).fetchone()
    low_stock_count = conn.execute(
        "SELECT COUNT(*) AS low_stock FROM inventory WHERE qty <= 5"
    ).fetchone()

    if date_filter_active:
        recent_orders = conn.execute(
            """
            SELECT orders.*, customers.name, customers.phone
            FROM orders
            JOIN customers ON customers.id = orders.customer_id
            WHERE date(orders.created_at) BETWEEN ? AND ?
            ORDER BY orders.created_at DESC
            LIMIT 8
            """,
            (from_date, to_date),
        ).fetchall()

        active_orders = conn.execute(
            """
            SELECT orders.*, customers.name, customers.phone
            FROM orders
            JOIN customers ON customers.id = orders.customer_id
            WHERE orders.status != 'Delivered'
              AND date(orders.created_at) BETWEEN ? AND ?
            ORDER BY CASE WHEN orders.due_date IS NULL THEN 1 ELSE 0 END, orders.due_date ASC, orders.created_at DESC
            LIMIT 8
            """,
            (from_date, to_date),
        ).fetchall()
    else:
        recent_orders = conn.execute(
            """
            SELECT orders.*, customers.name, customers.phone
            FROM orders
            JOIN customers ON customers.id = orders.customer_id
            ORDER BY orders.created_at DESC
            LIMIT 8
            """
        ).fetchall()

        active_orders = conn.execute(
            """
            SELECT orders.*, customers.name, customers.phone
            FROM orders
            JOIN customers ON customers.id = orders.customer_id
            WHERE orders.status != 'Delivered'
            ORDER BY CASE WHEN orders.due_date IS NULL THEN 1 ELSE 0 END, orders.due_date ASC, orders.created_at DESC
            LIMIT 8
            """
        ).fetchall()

    completed_notifications = conn.execute(
        """
        SELECT n.order_id AS id,
               o.due_date,
               ISNULL(o.completed_at, n.event_time) AS completed_at,
               o.created_at,
               c.name,
               c.phone
        FROM order_notifications n
        JOIN orders o ON o.id = n.order_id
        JOIN customers c ON c.id = o.customer_id
        WHERE n.event_type = 'completed'
          AND LOWER(ISNULL(o.status, '')) = 'completed'
        ORDER BY n.event_time DESC, n.id DESC
        LIMIT 12
        """
    ).fetchall()

    search_orders = []
    if q:
        q_like = f"%{q}%"
        q_numeric = q.replace("#", "").strip()
        q_numeric_value = int(q_numeric) if q_numeric.isdigit() else None
        search_sql = """
            SELECT orders.*, customers.name, customers.phone
            FROM orders
            JOIN customers ON customers.id = orders.customer_id
            WHERE (
                customers.name LIKE ?
                OR customers.phone LIKE ?
                OR customers.address LIKE ?
                OR ISNULL(orders.invoice_id, '') LIKE ?
                OR ISNULL(orders.order_no, '') LIKE ?
                OR ISNULL(orders.assigned_tailor, '') LIKE ?
                OR EXISTS (
                    SELECT 1
                    FROM measurements m
                    WHERE m.order_id = orders.id
                      AND ISNULL(m.assigned_tailor, '') LIKE ?
                )
                OR (? IS NOT NULL AND (
                    orders.id = ?
                    OR customers.id = ?
                    OR ISNULL(orders.customer_display_id, -1) = ?
                ))
            )
        """
        search_params = [
            q_like,
            q_like,
            q_like,
            q_like,
            q_like,
            q_like,
            q_like,
            q_numeric_value,
            q_numeric_value,
            q_numeric_value,
            q_numeric_value,
        ]
        if date_filter_active:
            search_sql += " AND date(orders.created_at) BETWEEN ? AND ?"
            search_params.extend([from_date, to_date])
        search_sql += " ORDER BY orders.created_at DESC LIMIT 12"
        search_orders = conn.execute(
            search_sql,
            tuple(search_params),
        ).fetchall()

    low_stock = conn.execute(
        """
        SELECT * FROM inventory
        WHERE qty <= 5
        ORDER BY qty ASC
        LIMIT 6
        """
    ).fetchall()

    shirt_queue = conn.execute(
        """
        SELECT orders.id, orders.status, orders.due_date, customers.name, SUM(order_items.qty) as total_qty
        FROM orders
        JOIN customers ON customers.id = orders.customer_id
        JOIN order_items ON order_items.order_id = orders.id
        WHERE order_items.item_type = 'Shirt' AND orders.status != 'Delivered'
        GROUP BY orders.id, orders.status, orders.due_date, customers.name
        ORDER BY CASE WHEN orders.due_date IS NULL THEN 1 ELSE 0 END, orders.due_date ASC
        LIMIT 6
        """
    ).fetchall()

    pant_queue = conn.execute(
        """
        SELECT orders.id, orders.status, orders.due_date, customers.name, SUM(order_items.qty) as total_qty
        FROM orders
        JOIN customers ON customers.id = orders.customer_id
        JOIN order_items ON order_items.order_id = orders.id
        WHERE order_items.item_type = 'Pant' AND orders.status != 'Delivered'
        GROUP BY orders.id, orders.status, orders.due_date, customers.name
        ORDER BY CASE WHEN orders.due_date IS NULL THEN 1 ELSE 0 END, orders.due_date ASC
        LIMIT 6
        """
    ).fetchall()

    tailors = conn.execute("SELECT * FROM tailors ORDER BY team, name").fetchall()

    if date_filter_active:
        tailoring_sales = conn.execute(
            """
            SELECT COALESCE(SUM(total_amount), 0) AS total
            FROM orders
            WHERE order_type IN ('Tailoring', 'Alteration')
              AND status != 'Cancelled'
              AND date(created_at) BETWEEN ? AND ?
            """,
            (from_date, to_date),
        ).fetchone()
        material_sales = conn.execute(
            """
            SELECT COALESCE(SUM(total_amount), 0) AS total
            FROM orders
            WHERE order_type = 'Material'
              AND status != 'Cancelled'
              AND date(created_at) BETWEEN ? AND ?
            """,
            (from_date, to_date),
        ).fetchone()
        total_expense = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM expenses
            WHERE date(created_at) BETWEEN ? AND ?
            """,
            (from_date, to_date),
        ).fetchone()
    else:
        tailoring_sales = conn.execute(
            """
            SELECT COALESCE(SUM(total_amount), 0) AS total
            FROM orders
            WHERE order_type IN ('Tailoring', 'Alteration') AND status != 'Cancelled'
            """
        ).fetchone()
        material_sales = conn.execute(
            """
            SELECT COALESCE(SUM(total_amount), 0) AS total
            FROM orders
            WHERE order_type = 'Material' AND status != 'Cancelled'
            """
        ).fetchone()
        total_expense = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses"
        ).fetchone()
    total_salary = conn.execute(
        "SELECT COALESCE(SUM(salary_amount), 0) AS total FROM salaries"
    ).fetchone()
    if date_filter_active:
        spent = conn.execute(
            """
            SELECT COALESCE(SUM(total_amount), 0) AS spent
            FROM vendor_purchase_orders
            WHERE date(purchased_at) BETWEEN ? AND ?
            """,
            (from_date, to_date),
        ).fetchone()
    else:
        spent = conn.execute(
            "SELECT COALESCE(SUM(total_amount), 0) AS spent FROM vendor_purchase_orders"
        ).fetchone()
    if date_filter_active:
        material_purchase_summary = conn.execute(
            """
            SELECT inventory.name AS material_name, COALESCE(SUM(order_material_items.qty), 0) AS total_qty
            FROM order_material_items
            JOIN inventory ON inventory.id = order_material_items.inventory_id
            JOIN orders ON orders.id = order_material_items.order_id
            WHERE orders.order_type = 'Material'
              AND orders.status != 'Cancelled'
              AND date(orders.created_at) BETWEEN ? AND ?
            GROUP BY inventory.name
            ORDER BY total_qty DESC, inventory.name ASC
            LIMIT 3
            """,
            (from_date, to_date),
        ).fetchall()
    else:
        material_purchase_summary = conn.execute(
            """
            SELECT inventory.name AS material_name, COALESCE(SUM(order_material_items.qty), 0) AS total_qty
            FROM order_material_items
            JOIN inventory ON inventory.id = order_material_items.inventory_id
            JOIN orders ON orders.id = order_material_items.order_id
            WHERE orders.order_type = 'Material' AND orders.status != 'Cancelled'
            GROUP BY inventory.name
            ORDER BY total_qty DESC, inventory.name ASC
            LIMIT 3
            """
        ).fetchall()
    tailoring_sales_value = float(tailoring_sales["total"] or 0)
    material_sales_value = float(material_sales["total"] or 0)
    total_profit = material_sales_value + tailoring_sales_value
    # `expenses` is the single source of truth for expense entries
    # (salary is also stored as an expense row). Do not add salary/purchase again.
    total_loss = float(total_expense["total"] or 0)
    revenue_value = total_profit - total_loss

    def month_start(d: datetime) -> datetime:
        return datetime(d.year, d.month, 1)

    def add_months(d: datetime, months: int) -> datetime:
        year = d.year + (d.month - 1 + months) // 12
        month = (d.month - 1 + months) % 12 + 1
        return datetime(year, month, 1)

    def normalize_range(key: str) -> str:
        if key in {"today", "yesterday", "week", "6month", "1year"}:
            return key
        return "today"

    def build_range_config(range_key: str):
        key = normalize_range(range_key)
        if key == "today":
            start = today
            end = today
            bucket = "hour"
            keys = [f"{h:02d}" for h in range(24)]
            labels = [f"{h:02d}:00" for h in range(24)]
        elif key == "yesterday":
            start = today - timedelta(days=1)
            end = start
            bucket = "hour"
            keys = [f"{h:02d}" for h in range(24)]
            labels = [f"{h:02d}:00" for h in range(24)]
        elif key == "week":
            start = today - timedelta(days=6)
            end = today
            bucket = "day"
            keys = [(start + timedelta(days=i)).isoformat() for i in range(7)]
            labels = [(start + timedelta(days=i)).strftime("%d %b") for i in range(7)]
        elif key == "6month":
            end_month = month_start(now_dt)
            start_month = add_months(end_month, -5)
            month_list = [add_months(start_month, i) for i in range(6)]
            start = start_month.date()
            end = (add_months(end_month, 1) - timedelta(days=1)).date()
            bucket = "month"
            keys = [f"{m.year:04d}-{m.month:02d}" for m in month_list]
            labels = [m.strftime("%b") for m in month_list]
        else:
            end_month = month_start(now_dt)
            start_month = add_months(end_month, -11)
            month_list = [add_months(start_month, i) for i in range(12)]
            start = start_month.date()
            end = (add_months(end_month, 1) - timedelta(days=1)).date()
            bucket = "month"
            keys = [f"{m.year:04d}-{m.month:02d}" for m in month_list]
            labels = [m.strftime("%b") for m in month_list]
        return key, start, end, bucket, keys, labels

    def bucket_format(bucket: str) -> str:
        if bucket == "hour":
            return "%H"
        if bucket == "month":
            return "%Y-%m"
        return "%Y-%m-%d"

    def sum_map(table: str, date_col: str, amount_col: str, start_date: str, end_date: str, fmt: str):
        rows = conn.execute(
            f"""
            SELECT strftime('{fmt}', {date_col}) AS bucket, COALESCE(SUM({amount_col}), 0) AS total
            FROM {table}
            WHERE date({date_col}) BETWEEN ? AND ?
            GROUP BY strftime('{fmt}', {date_col})
            """,
            (start_date, end_date),
        ).fetchall()
        return {row["bucket"]: float(row["total"] or 0) for row in rows}

    def orders_profit_map(start_date: str, end_date: str, fmt: str):
        rows = conn.execute(
            f"""
            SELECT strftime('{fmt}', created_at) AS bucket, COALESCE(SUM(total_amount), 0) AS total
            FROM orders
            WHERE status != 'Cancelled'
              AND order_type IN ('Material', 'Tailoring', 'Alteration')
              AND date(created_at) BETWEEN ? AND ?
            GROUP BY strftime('{fmt}', created_at)
            """,
            (start_date, end_date),
        ).fetchall()
        return {row["bucket"]: float(row["total"] or 0) for row in rows}

    profit_key, profit_start, profit_end, profit_bucket, profit_keys, profit_labels = build_range_config(profit_range)
    profit_fmt = bucket_format(profit_bucket)
    profit_orders_map = orders_profit_map(profit_start.isoformat(), profit_end.isoformat(), profit_fmt)
    expense_map = sum_map("expenses", "created_at", "amount", profit_start.isoformat(), profit_end.isoformat(), profit_fmt)
    salary_map = sum_map("salaries", "created_at", "salary_amount", profit_start.isoformat(), profit_end.isoformat(), profit_fmt)
    purchase_map = sum_map(
        "vendor_purchase_orders",
        "purchased_at",
        "total_amount",
        profit_start.isoformat(),
        profit_end.isoformat(),
        profit_fmt,
    )

    profit_values = [profit_orders_map.get(key, 0) for key in profit_keys]
    loss_values = [
        expense_map.get(key, 0) + salary_map.get(key, 0) + purchase_map.get(key, 0)
        for key in profit_keys
    ]

    orders_key, orders_start, orders_end, orders_bucket, orders_keys, orders_timeline_labels = build_range_config(orders_range)
    status_rows = conn.execute(
        """
        SELECT orders.status, COUNT(*) AS total
        FROM orders
        WHERE date(created_at) BETWEEN ? AND ?
        GROUP BY orders.status
        """,
        (orders_start.isoformat(), orders_end.isoformat()),
    ).fetchall()
    status_map = {row["status"]: int(row["total"] or 0) for row in status_rows}

    urgent_count_range = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM orders
        WHERE status != 'Cancelled'
          AND date(created_at) BETWEEN ? AND ?
          AND due_date IS NOT NULL
          AND DATEDIFF(day, CAST(created_at AS DATE), CAST(due_date AS DATE)) IN (0, 1)
        """,
        (orders_start.isoformat(), orders_end.isoformat()),
    ).fetchone()
    left2_count_range = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM orders
        WHERE status != 'Cancelled'
          AND date(due_date) BETWEEN ? AND ?
        """,
        (orders_start.isoformat(), orders_end.isoformat()),
    ).fetchone()

    orders_labels = ["Urgent", "In-Progress", "Completed", "Ready for Delivery", "Delivered", "Cancelled"]
    orders_values = [
        int(urgent_count_range["total"] or 0),
        status_map.get("In-Progress", 0),
        status_map.get("Completed", 0),
        int(left2_count_range["total"] or 0),
        status_map.get("Delivered", 0),
        status_map.get("Cancelled", 0),
    ]

    orders_fmt = bucket_format(orders_bucket)
    stitch_rows = conn.execute(
        f"""
        SELECT strftime('{orders_fmt}', orders.created_at) AS bucket,
               order_items.item_type AS item_type,
               COALESCE(SUM(order_items.qty), 0) AS total_qty
        FROM orders
        JOIN order_items ON order_items.order_id = orders.id
        WHERE LOWER(ISNULL(orders.order_type, '')) = 'tailoring'
          AND LOWER(ISNULL(orders.status, '')) != 'cancelled'
          AND date(orders.created_at) BETWEEN ? AND ?
        GROUP BY strftime('{orders_fmt}', orders.created_at), order_items.item_type
        """,
        (orders_start.isoformat(), orders_end.isoformat()),
    ).fetchall()

    category_rows = conn.execute(
        "SELECT name FROM categories ORDER BY name ASC"
    ).fetchall()
    category_names = [str(row["name"] or "").strip() for row in category_rows if str(row["name"] or "").strip()]
    stitched_by_type: dict[str, dict[str, float]] = {
        name: {} for name in category_names
    }

    def normalize_item_base(raw: str | None) -> str:
        text = str(raw or "").strip().lower()
        if not text:
            return ""
        if "-" in text:
            return text.split("-", 1)[0].strip()
        return text

    category_lookup = {name.lower(): name for name in category_names}
    for row in stitch_rows:
        item_type = str(row["item_type"] or "").strip()
        bucket = str(row["bucket"] or "")
        qty = float(row["total_qty"] or 0)
        base = normalize_item_base(item_type)
        key = category_lookup.get(base)
        if not key:
            for cat_name, label in category_lookup.items():
                if cat_name and cat_name in item_type.lower():
                    key = label
                    break
        if not key:
            continue
        stitched_by_type[key][bucket] = stitched_by_type[key].get(bucket, 0.0) + qty

    orders_stitching_series = [
        {
            "label": label,
            "data": [float(stitched_by_type[label].get(bucket, 0)) for bucket in orders_keys],
        }
        for label in stitched_by_type.keys()
    ]

    inventory_rows = conn.execute(
        """
        SELECT name, COALESCE(SUM(qty), 0) AS qty
        FROM inventory
        GROUP BY name
        ORDER BY name
        """
    ).fetchall()
    inventory_labels = [row["name"] for row in inventory_rows]
    inventory_values = [float(row["qty"] or 0) for row in inventory_rows]
    report_count = 0
    try:
        report_count = len(
            [
                name
                for name in os.listdir(REPORT_DIR)
                if name.lower().endswith(".pdf")
            ]
        )
    except OSError:
        report_count = 0

    if date_filter_active:
        advance_collection = conn.execute(
            """
            SELECT COALESCE(SUM(advance_amount), 0) AS total
            FROM orders
            WHERE date(created_at) BETWEEN ? AND ?
            """,
            (from_date, to_date),
        ).fetchone()["total"]
        delivery_collection = conn.execute(
            """
            SELECT COALESCE(SUM(paid_amount), 0) AS total
            FROM orders
            WHERE status = 'Delivered'
              AND date(created_at) BETWEEN ? AND ?
            """,
            (from_date, to_date),
        ).fetchone()["total"]
    else:
        advance_collection = conn.execute(
            "SELECT COALESCE(SUM(advance_amount), 0) AS total FROM orders"
        ).fetchone()["total"]
        delivery_collection = conn.execute(
            """
            SELECT COALESCE(SUM(paid_amount), 0) AS total
            FROM orders
            WHERE status = 'Delivered'
            """
        ).fetchone()["total"]
    cash_in_drawer = float(advance_collection or 0) + float(delivery_collection or 0)

    if date_filter_active:
        advance_orders = conn.execute(
            """
            SELECT
              orders.id AS order_id,
              customers.name AS customer_name,
              orders.due_date AS delivery_date,
              orders.status AS status,
              COALESCE(orders.total_amount, 0) AS total_amount,
              COALESCE(orders.advance_amount, 0) AS paid_amount,
              COALESCE(orders.total_amount, 0) - COALESCE(orders.advance_amount, 0) AS unpaid_amount
            FROM orders
            JOIN customers ON customers.id = orders.customer_id
            WHERE COALESCE(orders.advance_amount, 0) > 0
              AND date(orders.created_at) BETWEEN ? AND ?
            ORDER BY orders.created_at DESC
            LIMIT 25
            """,
            (from_date, to_date),
        ).fetchall()
    else:
        advance_orders = conn.execute(
            """
            SELECT
              orders.id AS order_id,
              customers.name AS customer_name,
              orders.due_date AS delivery_date,
              orders.status AS status,
              COALESCE(orders.total_amount, 0) AS total_amount,
              COALESCE(orders.advance_amount, 0) AS paid_amount,
              COALESCE(orders.total_amount, 0) - COALESCE(orders.advance_amount, 0) AS unpaid_amount
            FROM orders
            JOIN customers ON customers.id = orders.customer_id
            WHERE COALESCE(orders.advance_amount, 0) > 0
            ORDER BY orders.created_at DESC
            LIMIT 25
            """
        ).fetchall()

    if date_filter_active:
        delivery_orders = conn.execute(
            """
            SELECT
              orders.id AS order_id,
              customers.name AS customer_name,
              orders.due_date AS delivery_date,
              orders.status AS status,
              COALESCE(orders.total_amount, 0) AS total_amount,
              COALESCE(orders.paid_amount, 0) AS paid_amount,
              COALESCE(orders.total_amount, 0) - COALESCE(orders.paid_amount, 0) AS unpaid_amount
            FROM orders
            JOIN customers ON customers.id = orders.customer_id
            WHERE orders.status = 'Delivered'
              AND date(orders.created_at) BETWEEN ? AND ?
            ORDER BY orders.created_at DESC
            LIMIT 25
            """,
            (from_date, to_date),
        ).fetchall()
    else:
        delivery_orders = conn.execute(
            """
            SELECT
              orders.id AS order_id,
              customers.name AS customer_name,
              orders.due_date AS delivery_date,
              orders.status AS status,
              COALESCE(orders.total_amount, 0) AS total_amount,
              COALESCE(orders.paid_amount, 0) AS paid_amount,
              COALESCE(orders.total_amount, 0) - COALESCE(orders.paid_amount, 0) AS unpaid_amount
            FROM orders
            JOIN customers ON customers.id = orders.customer_id
            WHERE orders.status = 'Delivered'
            ORDER BY orders.created_at DESC
            LIMIT 25
            """
        ).fetchall()

    if date_filter_active:
        misc_expenses = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM expenses
            WHERE date(created_at) BETWEEN ? AND ?
            """,
            (from_date, to_date),
        ).fetchone()["total"]
        salary_expenses = conn.execute(
            """
            SELECT COALESCE(SUM(salary_amount), 0) AS total
            FROM salaries
            WHERE date(created_at) BETWEEN ? AND ?
            """,
            (from_date, to_date),
        ).fetchone()["total"]
    else:
        misc_expenses = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses"
        ).fetchone()["total"]
        salary_expenses = conn.execute(
            "SELECT COALESCE(SUM(salary_amount), 0) AS total FROM salaries"
        ).fetchone()["total"]
    total_expenses = float(misc_expenses or 0) + float(salary_expenses or 0)

    tailoring_sales = tailoring_sales_value

    conn.close()
    return render_template(
        "dashboard.html",
        counts=counts,
        total_order_chip=total_order_chip,
        total_orders_today=int(total_orders_today["total"] or 0),
        total_items=int(total_items["total_items"]),
        urgent_count=int(urgent_count["total"] or 0),
        left2_count=int(left2_count["total"] or 0),
        stock_units=int(stock_units["stock_units"]),
        low_stock_count=int(low_stock_count["low_stock"]),
        recent_orders=recent_orders,
        low_stock=low_stock,
        shirt_queue=shirt_queue,
        pant_queue=pant_queue,
        tailors=tailors,
        active_orders=active_orders,
        completed_notifications=completed_notifications,
        search_orders=search_orders,
        q=q,
        from_date=from_date,
        to_date=to_date,
        date_filter_active=date_filter_active,
        revenue=revenue_value,
        spent=float(spent["spent"]),
        material_sales=material_sales_value,
        total_profit=total_profit,
        total_loss=total_loss,
        profit_labels=profit_labels,
        profit_values=profit_values,
        loss_values=loss_values,
        profit_range=profit_key,
        orders_labels=orders_labels,
        orders_values=orders_values,
        orders_range=orders_key,
        orders_timeline_labels=orders_timeline_labels,
        orders_stitching_series=orders_stitching_series,
        inventory_labels=inventory_labels,
        inventory_values=inventory_values,
        material_purchase_summary=material_purchase_summary,
        inventory_rows=inventory_rows,
        report_count=int(report_count),
        advance_collection=float(advance_collection or 0),
        delivery_collection=float(delivery_collection or 0),
        cash_in_drawer=float(cash_in_drawer or 0),
        advance_orders=advance_orders,
        delivery_orders=delivery_orders,
        misc_expenses=float(misc_expenses or 0),
        salary_expenses=float(salary_expenses or 0),
        total_expenses=float(total_expenses or 0),
        tailoring_sales=tailoring_sales,
    )

@app.route("/dashboard/charts")
def dashboard_chart_data():
    profit_range = request.args.get("profit_range", "today").strip().lower()
    orders_range = request.args.get("orders_range", "today").strip().lower()
    conn = get_db()
    now_dt = datetime.now()
    today = now_dt.date()

    def month_start(d: datetime) -> datetime:
        return datetime(d.year, d.month, 1)

    def add_months(d: datetime, months: int) -> datetime:
        year = d.year + (d.month - 1 + months) // 12
        month = (d.month - 1 + months) % 12 + 1
        return datetime(year, month, 1)

    def normalize_range(key: str) -> str:
        if key in {"today", "yesterday", "week", "6month", "1year"}:
            return key
        return "today"

    def build_range_config(range_key: str):
        key = normalize_range(range_key)
        if key == "today":
            start = today
            end = today
            bucket = "hour"
            keys = [f"{h:02d}" for h in range(24)]
            labels = [f"{h:02d}:00" for h in range(24)]
        elif key == "yesterday":
            start = today - timedelta(days=1)
            end = start
            bucket = "hour"
            keys = [f"{h:02d}" for h in range(24)]
            labels = [f"{h:02d}:00" for h in range(24)]
        elif key == "week":
            start = today - timedelta(days=6)
            end = today
            bucket = "day"
            keys = [(start + timedelta(days=i)).isoformat() for i in range(7)]
            labels = [(start + timedelta(days=i)).strftime("%d %b") for i in range(7)]
        elif key == "6month":
            end_month = month_start(now_dt)
            start_month = add_months(end_month, -5)
            month_list = [add_months(start_month, i) for i in range(6)]
            start = start_month.date()
            end = (add_months(end_month, 1) - timedelta(days=1)).date()
            bucket = "month"
            keys = [f"{m.year:04d}-{m.month:02d}" for m in month_list]
            labels = [m.strftime("%b") for m in month_list]
        else:
            end_month = month_start(now_dt)
            start_month = add_months(end_month, -11)
            month_list = [add_months(start_month, i) for i in range(12)]
            start = start_month.date()
            end = (add_months(end_month, 1) - timedelta(days=1)).date()
            bucket = "month"
            keys = [f"{m.year:04d}-{m.month:02d}" for m in month_list]
            labels = [m.strftime("%b") for m in month_list]
        return key, start, end, bucket, keys, labels

    def bucket_format(bucket: str) -> str:
        if bucket == "hour":
            return "%H"
        if bucket == "month":
            return "%Y-%m"
        return "%Y-%m-%d"

    def sum_map(table: str, date_col: str, amount_col: str, start_date: str, end_date: str, fmt: str):
        rows = conn.execute(
            f"""
            SELECT strftime('{fmt}', {date_col}) AS bucket, COALESCE(SUM({amount_col}), 0) AS total
            FROM {table}
            WHERE date({date_col}) BETWEEN ? AND ?
            GROUP BY strftime('{fmt}', {date_col})
            """,
            (start_date, end_date),
        ).fetchall()
        return {row["bucket"]: float(row["total"] or 0) for row in rows}

    def orders_profit_map(start_date: str, end_date: str, fmt: str):
        rows = conn.execute(
            f"""
            SELECT strftime('{fmt}', created_at) AS bucket, COALESCE(SUM(total_amount), 0) AS total
            FROM orders
            WHERE status != 'Cancelled'
              AND order_type IN ('Material', 'Tailoring', 'Alteration')
              AND date(created_at) BETWEEN ? AND ?
            GROUP BY strftime('{fmt}', created_at)
            """,
            (start_date, end_date),
        ).fetchall()
        return {row["bucket"]: float(row["total"] or 0) for row in rows}

    profit_key, profit_start, profit_end, profit_bucket, profit_keys, profit_labels = build_range_config(profit_range)
    profit_fmt = bucket_format(profit_bucket)
    profit_orders_map = orders_profit_map(profit_start.isoformat(), profit_end.isoformat(), profit_fmt)
    expense_map = sum_map("expenses", "created_at", "amount", profit_start.isoformat(), profit_end.isoformat(), profit_fmt)
    salary_map = sum_map("salaries", "created_at", "salary_amount", profit_start.isoformat(), profit_end.isoformat(), profit_fmt)
    purchase_map = sum_map(
        "vendor_purchase_orders",
        "purchased_at",
        "total_amount",
        profit_start.isoformat(),
        profit_end.isoformat(),
        profit_fmt,
    )
    profit_values = [profit_orders_map.get(key, 0) for key in profit_keys]
    loss_values = [
        expense_map.get(key, 0) + salary_map.get(key, 0) + purchase_map.get(key, 0)
        for key in profit_keys
    ]

    orders_key, orders_start, orders_end, orders_bucket, orders_keys, orders_timeline_labels = build_range_config(orders_range)
    orders_fmt = bucket_format(orders_bucket)
    stitch_rows = conn.execute(
        f"""
        SELECT strftime('{orders_fmt}', orders.created_at) AS bucket,
               order_items.item_type AS item_type,
               COALESCE(SUM(order_items.qty), 0) AS total_qty
        FROM orders
        JOIN order_items ON order_items.order_id = orders.id
        WHERE LOWER(ISNULL(orders.order_type, '')) = 'tailoring'
          AND LOWER(ISNULL(orders.status, '')) != 'cancelled'
          AND date(orders.created_at) BETWEEN ? AND ?
        GROUP BY strftime('{orders_fmt}', orders.created_at), order_items.item_type
        """,
        (orders_start.isoformat(), orders_end.isoformat()),
    ).fetchall()
    category_rows = conn.execute(
        "SELECT name FROM categories ORDER BY name ASC"
    ).fetchall()
    category_names = [str(row["name"] or "").strip() for row in category_rows if str(row["name"] or "").strip()]
    stitched_by_type: dict[str, dict[str, float]] = {
        name: {} for name in category_names
    }

    def normalize_item_base(raw: str | None) -> str:
        text = str(raw or "").strip().lower()
        if not text:
            return ""
        if "-" in text:
            return text.split("-", 1)[0].strip()
        return text

    category_lookup = {name.lower(): name for name in category_names}
    for row in stitch_rows:
        item_type = str(row["item_type"] or "").strip()
        bucket = str(row["bucket"] or "")
        qty = float(row["total_qty"] or 0)
        base = normalize_item_base(item_type)
        key = category_lookup.get(base)
        if not key:
            for cat_name, label in category_lookup.items():
                if cat_name and cat_name in item_type.lower():
                    key = label
                    break
        if not key:
            continue
        stitched_by_type[key][bucket] = stitched_by_type[key].get(bucket, 0.0) + qty

    orders_stitching_series = [
        {
            "label": label,
            "data": [float(stitched_by_type[label].get(bucket, 0)) for bucket in orders_keys],
        }
        for label in stitched_by_type.keys()
    ]
    conn.close()
    return jsonify(
        {
            "profit": {
                "range": profit_key,
                "labels": profit_labels,
                "values": profit_values,
                "loss": loss_values,
            },
            "orders": {
                "range": orders_key,
                "labels": orders_timeline_labels,
                "series": orders_stitching_series,
            },
        }
    )

#gallery
@app.route("/gallery")
def gallery():
    conn = get_db()
    default_gallery_tabs = ["Coat", "Safari", "Shirt", "Pant", "Jeans", "Kurta"]
    existing_names = {
        str(row["name"]).strip().lower()
        for row in conn.execute("SELECT name FROM gallery_categories").fetchall()
    }
    for tab_name in default_gallery_tabs:
        if tab_name.strip().lower() in existing_names:
            continue
        conn.execute("INSERT INTO gallery_categories (name) VALUES (?)", (tab_name,))
    conn.commit()
    categories = conn.execute(
        "SELECT * FROM gallery_categories ORDER BY name"
    ).fetchall()
    preferred_tabs = ["coat", "safari", "shirt", "pant", "jeans", "kurta"]
    categories = sorted(
        categories,
        key=lambda c: (
            preferred_tabs.index(str(c["name"]).strip().lower())
            if str(c["name"]).strip().lower() in preferred_tabs
            else len(preferred_tabs) + 1,
            str(c["name"]).strip().lower(),
        ),
    )
    cover_rows = conn.execute(
        """
        SELECT gi.*
        FROM gallery_items gi
        JOIN (
            SELECT category_id, MAX(id) AS max_id
            FROM gallery_items
            GROUP BY category_id
        ) latest ON latest.category_id = gi.category_id AND latest.max_id = gi.id
        """
    ).fetchall()
    cover_map = {row["category_id"]: row for row in cover_rows}
    item_rows = conn.execute(
        """
        SELECT id, category_id, image_filename, item_name
        FROM gallery_items
        ORDER BY id DESC
        """
    ).fetchall()
    items_by_category: dict[int, list] = {}
    for row in item_rows:
        key = int(row["category_id"])
        items_by_category.setdefault(key, []).append(row)
    active_category_id = request.args.get("category_id", "").strip()
    if active_category_id.isdigit():
        active_category = int(active_category_id)
    else:
        active_category = int(categories[0]["id"]) if categories else None
    conn.close()
    return render_template(
        "gallery.html",
        categories=categories,
        cover_map=cover_map,
        items_by_category=items_by_category,
        active_category=active_category,
    )

@app.route("/gallery/<int:category_id>")
def gallery_view(category_id: int):
    conn = get_db()
    category = conn.execute(
        "SELECT * FROM gallery_categories WHERE id = ?",
        (category_id,),
    ).fetchone()
    if not category:
        conn.close()
        return redirect(url_for("gallery"))
    items = conn.execute(
        """
        SELECT * FROM gallery_items
        WHERE category_id = ?
        ORDER BY id DESC
        """,
        (category_id,),
    ).fetchall()
    conn.close()
    return render_template(
        "gallery_view.html",
        category=category,
        items=items,
    )

@app.route("/gallery/add", methods=["GET", "POST"])
def gallery_add():
    conn = get_db()
    categories = conn.execute(
        "SELECT * FROM gallery_categories ORDER BY name"
    ).fetchall()
    if request.method == "POST":
        category_id = request.form.get("category_id", "").strip()
        category_name = request.form.get("category_name", "").strip()
        base_name = request.form.get("item_name", "").strip()
        images = request.files.getlist("images")
        valid_images = [img for img in images if img and img.filename]
        if not (category_id or category_name) or not valid_images:
            conn.close()
            return render_template(
                "gallery_add.html",
                categories=categories,
                error="Category and at least one image are required.",
            )
        cat_row = None
        if category_id:
            cat_row = conn.execute(
                "SELECT id, name FROM gallery_categories WHERE id = ?",
                (int(category_id),),
            ).fetchone()
        if not cat_row and category_name:
            existing = conn.execute(
                "SELECT id, name FROM gallery_categories WHERE lower(name) = ?",
                (category_name.lower(),),
            ).fetchone()
            if existing:
                cat_row = existing
            else:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO gallery_categories (name) VALUES (?)",
                    (category_name,),
                )
                cat_row = {"id": cur.lastrowid, "name": category_name}
        if not cat_row:
            conn.close()
            return render_template(
                "gallery_add.html",
                categories=categories,
                error="Selected category does not exist.",
            )
        for idx, image in enumerate(valid_images, start=1):
            filename = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
            filepath = os.path.join(app.config["GALLERY_FOLDER"], filename)
            image.save(filepath)
            if base_name:
                item_name = f"{base_name} {idx}" if len(valid_images) > 1 else base_name
            else:
                original = os.path.splitext(secure_filename(image.filename))[0]
                item_name = original or cat_row["name"]
            conn.execute(
                """
                INSERT INTO gallery_items (category_id, item_name, image_filename, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (int(cat_row["id"]), item_name, filename, now_str()),
            )
        conn.commit()
        conn.close()
        return redirect(url_for("gallery"))
    conn.close()
    return render_template(
        "gallery_add.html",
        categories=categories,
    )

def _gallery_items_by_ids(conn: sqlite3.Connection, ids: list[int]) -> list[sqlite3.Row]:
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    query = f"SELECT id, image_filename, category_id FROM gallery_items WHERE id IN ({placeholders})"
    return conn.execute(query, ids).fetchall()

@app.route("/gallery/delete", methods=["POST"])
def gallery_delete():
    raw_ids = request.form.getlist("image_ids")
    category_id = request.form.get("category_id")
    ids = [int(x) for x in raw_ids if str(x).isdigit()]
    if not ids:
        if category_id and category_id.isdigit():
            return redirect(url_for("gallery", category_id=int(category_id)))
        return redirect(url_for("gallery"))
    conn = get_db()
    rows = _gallery_items_by_ids(conn, ids)
    for row in rows:
        filename = row["image_filename"]
        filepath = os.path.join(app.config["GALLERY_FOLDER"], filename)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
    placeholders = ",".join("?" for _ in ids)
    conn.execute(f"DELETE FROM gallery_items WHERE id IN ({placeholders})", ids)
    conn.commit()
    conn.close()
    if category_id and category_id.isdigit():
        return redirect(url_for("gallery", category_id=int(category_id)))
    return redirect(url_for("gallery"))

@app.route("/gallery/download", methods=["POST"])
def gallery_download():
    raw_ids = request.form.getlist("image_ids")
    ids = [int(x) for x in raw_ids if str(x).isdigit()]
    if not ids:
        category_id = request.form.get("category_id")
        if category_id and category_id.isdigit():
            return redirect(url_for("gallery", category_id=int(category_id)))
        return redirect(url_for("gallery"))
    conn = get_db()
    rows = _gallery_items_by_ids(conn, ids)
    conn.close()
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zipf:
        for row in rows:
            filename = row["image_filename"]
            filepath = os.path.join(app.config["GALLERY_FOLDER"], filename)
            if os.path.exists(filepath):
                zipf.write(filepath, arcname=filename)
    memory_file.seek(0)
    return send_file(
        memory_file,
        as_attachment=True,
        download_name="gallery_images.zip",
        mimetype="application/zip",
    )

# def generate_orders_report_80mm(from_date, to_date):
#     conn = get_db()
#     rows = conn.execute(
#         """
#         SELECT o.id, c.name, c.phone, o.total_amount, o.advance_amount, o.created_at
#         FROM orders o
#         JOIN customers c ON c.id = o.customer_id
#         WHERE date(o.created_at) BETWEEN ? AND ?
#         ORDER BY o.created_at
#         """,
#         (from_date, to_date),
#     ).fetchall()
#     conn.close()

#     # file_path = "static/reports/orders_report.pdf"
#     ts = datetime.now().strftime("%Y%m%d_%H%M%S")
#     # file_path = f"static/reports/orders_report_{ts}.pdf"
#     file_path = os.path.join(REPORT_DIR, f"orders_report_{ts}.pdf")
#     os.makedirs(os.path.dirname(file_path), exist_ok=True)

#     doc = SimpleDocTemplate(
#         file_path,
#         pagesize=(THERMAL_WIDTH, 500 * mm),
#         leftMargin=2,
#         rightMargin=2,
#         topMargin=3,
#         bottomMargin=3
#     )

#     styles = getSampleStyleSheet()
#     receipt_style = ParagraphStyle(
#         name="Receipt",
#         fontName="Courier",
#         fontSize=8,
#         leading=10
#     )

#     elements = []

#     elements.append(Preformatted("ORDERS REPORT", receipt_style))
#     elements.append(Preformatted(f"From {from_date} To {to_date}", receipt_style))
#     elements.append(Preformatted("_" * 42, receipt_style))
#     elements.append(Preformatted(
#         "ID  Name               Total   Adv    Date\n" +
#         "_" * 42,
#         receipt_style
#     ))

#     for r in rows:
#         line = (
#             str(r["id"]).ljust(3) + " "
#             + r["name"][:18].ljust(18) + " "
#             + f'{r["total_amount"]:.2f}'.rjust(6) + " "
#             + f'{r["advance_amount"]:.2f}'.rjust(6) + " "
#             + r["created_at"][:10]
#         )
#         elements.append(Preformatted(line, receipt_style))

#     elements.append(Preformatted("_" * 42, receipt_style))
#     doc.build(elements)
#     # return redirect("/" + file_path)
#     return redirect(url_for("static", filename=f"reports/orders_report_{ts}.pdf"))

def format_report_date(value):
    """Return YYYY-MM-DD for date-like values, or a safe string fallback."""
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%Y-%m-%d")
        except Exception:
            pass
    return str(value)[:10]


def build_report_page_header():
    company_name = get_setting("company_name", "Premier Tailors").strip() or "Premier Tailors"
    company_address_lines = get_company_address_lines()
    company_phone = get_setting("company_phone", "").strip()
    print_logo_path = get_setting("print_logo_path", "").strip() or "Premier-Logo.png"
    logo_abs_path = os.path.join(APP_DIR, "static", print_logo_path)
    regular_font, bold_font = get_reportlab_tamil_fonts()

    def _draw(canvas_obj, doc_obj):
        canvas_obj.saveState()
        page_w, page_h = doc_obj.pagesize
        header_margin = 5
        header_padding = 5

        # Left: logo
        if os.path.exists(logo_abs_path):
            logo_w = 60
            logo_h = 60
            logo_x = doc_obj.leftMargin + header_margin
            logo_y = page_h - logo_h - header_margin
            try:
                canvas_obj.drawImage(
                    logo_abs_path,
                    logo_x,
                    logo_y,
                    width=logo_w,
                    height=logo_h,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass

        # Right: company name + address + phone
        text_right_x = page_w - doc_obj.rightMargin - header_margin
        name_font_size = 18
        detail_font_size = 10
        top_y = page_h - header_margin - name_font_size
        canvas_obj.setFillColor(colors.HexColor("#111111"))
        canvas_obj.setFont(bold_font if has_tamil_chars(company_name) else "Helvetica-Bold", name_font_size)
        canvas_obj.drawRightString(text_right_x, top_y, company_name)

        details = []
        details.extend(company_address_lines)
        if company_phone:
            details.append(f"Phone: {company_phone}")
        if details:
            detail_y = top_y - detail_font_size - header_padding
            for idx, line in enumerate(details):
                detail_font_name = regular_font if has_tamil_chars(line) else "Helvetica"
                canvas_obj.setFont(detail_font_name, detail_font_size)
                canvas_obj.drawRightString(text_right_x, detail_y, line)
                detail_y -= (detail_font_size + header_padding)
        canvas_obj.restoreState()

    return _draw


REPORT_TOP_MARGIN = 96


def generate_orders_report_80mm(from_date, to_date, payment_mode: str = ""):
    from_dt = from_date + " 00:00:00"
    to_dt = to_date + " 23:59:59"

    print("[ORDERS] From:", from_dt, "To:", to_dt)

    conn = get_db()
    params: list[str] = [from_dt, to_dt]
    payment_filter = ""
    if payment_mode:
        payment_filter = "AND LOWER(ISNULL(o.notes, '')) LIKE ?"
        params.append(f"%payment method: {payment_mode.lower()}%")
    rows = conn.execute(
        f"""
        SELECT
            o.id,
            o.order_type,
            c.name,
            c.phone,
            o.total_amount,
            o.advance_amount,
            o.paid_amount,
            o.created_at
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        WHERE o.created_at BETWEEN ? AND ?
        {payment_filter}
        ORDER BY o.created_at
        """,
        tuple(params),
    ).fetchall()
    conn.close()

    print("[ORDERS] Rows fetched:", len(rows))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(REPORT_DIR, f"orders_report_{ts}.pdf")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        leftMargin=24,
        rightMargin=24,
        topMargin=REPORT_TOP_MARGIN,
        bottomMargin=24
    )

    regular_report_font, bold_report_font = get_reportlab_tamil_fonts()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="ReportTitle",
        parent=styles["Heading2"],
        fontName=bold_report_font,
        fontSize=15,
        leading=18,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        name="ReportSubtitle",
        parent=styles["Normal"],
        fontName=regular_report_font,
        fontSize=10,
        textColor=colors.HexColor("#333333"),
        spaceAfter=12,
    )
    normal_style = ParagraphStyle(
        name="ReportNormalTamil",
        parent=styles["Normal"],
        fontName=regular_report_font,
    )

    elements = []
    elements.append(Paragraph("Orders Report", title_style))
    elements.append(Paragraph(f"From {from_date} To {to_date}", subtitle_style))

    table_data = [["ID", "Customer", "Total", "Paid", "Pay Status", "Date"]]
    for r in rows:
        total_amount = float(r["total_amount"] or 0)
        advance_amount = float(r["advance_amount"] or 0)
        paid_amount = float(r["paid_amount"] or 0)
        paid_total = advance_amount + paid_amount
        due_amount = max(total_amount - paid_total, 0)
        if due_amount <= 0:
            payment_status = "Paid"
        elif paid_total > 0:
            payment_status = "Partial"
        else:
            payment_status = "Unpaid"
        table_data.append(
            [
                fmt_order_id(r["id"], r["order_type"]),
                str(r["name"] or ""),
                f"{total_amount:.2f}",
                f"{paid_total:.2f}",
                payment_status,
                format_report_date(r["created_at"]),
            ]
        )

    if len(table_data) == 1:
        elements.append(Paragraph("No orders found for selected date range.", normal_style))
    else:
        col_widths = [45, 170, 70, 70, 80, 90]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("FONTNAME", (0, 0), (-1, 0), bold_report_font),
                    ("FONTNAME", (0, 1), (-1, -1), regular_report_font),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (2, 1), (3, -1), "RIGHT"),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("ALIGN", (0, 1), (0, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b5b5b5")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elements.append(table)
        elements.append(Spacer(1, 8))
    header_draw = build_report_page_header()
    doc.build(elements, onFirstPage=header_draw, onLaterPages=header_draw)

    print("[ORDERS] PDF generated:", file_path)

    return redirect(url_for("static", filename=f"reports/orders_report_{ts}.pdf"))

def generate_inventory_report_80mm():
    print("[INVENTORY] Generating inventory report")

    conn = get_db()
    rows = conn.execute(
        "SELECT inventory_code, name, qty FROM inventory ORDER BY name"
    ).fetchall()
    conn.close()

    print("[INVENTORY] Rows fetched:", len(rows))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(REPORT_DIR, f"inventory_report_{ts}.pdf")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=24
    )

    receipt_style = ParagraphStyle(
        name="Receipt",
        fontName="Courier",
        fontSize=8,
        leading=10
    )

    elements = []
    elements.append(Preformatted("INVENTORY REPORT", receipt_style))
    elements.append(Preformatted("_" * 42, receipt_style))
    elements.append(Preformatted(
        "Code       Item               Qty\n" +
        "_" * 42,
        receipt_style
    ))

    if not rows:
        elements.append(Preformatted("No inventory items found", receipt_style))
    else:
        for r in rows:
            line = (
                r["inventory_code"][:10].ljust(10) + " "
                + r["name"][:20].ljust(20) + " "
                + str(r["qty"]).rjust(4)
            )
            elements.append(Preformatted(line, receipt_style))

    elements.append(Preformatted("_" * 42, receipt_style))
    doc.build(elements)

    print("[INVENTORY] PDF generated:", file_path)

    return redirect(url_for("static", filename=f"reports/inventory_report_{ts}.pdf"))

def generate_vendor_report_80mm(from_date, to_date):
    from_dt = from_date + " 00:00:00"
    to_dt = to_date + " 23:59:59"

    print("[VENDOR] From:", from_dt, "To:", to_dt)

    conn = get_db()
    rows = conn.execute("""
        SELECT
            v.name AS vendor_name,
            COALESCE(vpi.item_name_snapshot, i.name) AS material_name,
            vpi.qty,
            vpi.line_total AS total_price,
            vpo.purchased_at
        FROM vendor_purchase_orders vpo
        JOIN vendors v ON v.id = vpo.vendor_id
        JOIN vendor_purchase_items vpi ON vpi.purchase_id = vpo.id
        LEFT JOIN inventory i ON i.id = vpi.inventory_id
        WHERE vpo.purchased_at BETWEEN ? AND ?
        ORDER BY vpo.purchased_at
    """, (from_dt, to_dt)).fetchall()
    conn.close()

    print("[VENDOR] Rows fetched:", len(rows))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(REPORT_DIR, f"vendor_report_{ts}.pdf")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=24
    )

    receipt_style = ParagraphStyle(
        name="Receipt",
        fontName="Courier",
        fontSize=8,
        leading=10
    )

    elements = []
    elements.append(Preformatted("VENDOR PURCHASE REPORT", receipt_style))
    elements.append(Preformatted(f"{from_date} to {to_date}", receipt_style))
    elements.append(Preformatted("_" * 42, receipt_style))
    elements.append(Preformatted(
        "Vendor      Material        Qty   Amt   Date\n" +
        "_" * 42,
        receipt_style
    ))

    if not rows:
        elements.append(Preformatted("No vendor purchases found", receipt_style))
    else:
        for r in rows:
            line = (
                r["vendor_name"][:10].ljust(10) + " "
                + r["material_name"][:14].ljust(14) + " "
                + str(r["qty"]).rjust(4) + " "
                + f'{r["total_price"]:.2f}'.rjust(7) + " "
                + format_report_date(r["purchased_at"])
            )
            elements.append(Preformatted(line, receipt_style))

    elements.append(Preformatted("_" * 42, receipt_style))
    doc.build(elements)

    print("[VENDOR] PDF generated:", file_path)

    return redirect(url_for("static", filename=f"reports/vendor_report_{ts}.pdf"))

def generate_expenses_report_80mm(from_date, to_date):
    # expand date range to full day
    from_dt = from_date + " 00:00:00"
    to_dt = to_date + " 23:59:59"

    print("[EXPENSES] From:", from_dt, "To:", to_dt)

    conn = get_db()
    rows = conn.execute(
        """
        SELECT expense_name, amount, created_at
        FROM expenses
        WHERE created_at BETWEEN ? AND ?
        ORDER BY created_at
        """,
        (from_dt, to_dt),
    ).fetchall()
    conn.close()

    print("[EXPENSES] Rows fetched:", len(rows))

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(REPORT_DIR, f"expenses_report_{ts}.pdf")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        leftMargin=24,
        rightMargin=24,
        topMargin=REPORT_TOP_MARGIN,
        bottomMargin=24
    )

    receipt_style = ParagraphStyle(
        name="Receipt",
        fontName="Courier",
        fontSize=8,
        leading=10
    )

    elements = []

    elements.append(Preformatted("EXPENSE REPORT", receipt_style))
    elements.append(Preformatted(f"From {from_date} To {to_date}", receipt_style))
    elements.append(Preformatted("_" * 42, receipt_style))
    elements.append(Preformatted(
        "Expense               Amount   Date\n" +
        "_" * 42,
        receipt_style
    ))

    for r in rows:
        if hasattr(r, "keys"):
            expense_name = r["expense_name"]
            amount = r["amount"]
            created_at = r["created_at"]
        elif isinstance(r, (tuple, list)) and len(r) >= 3:
            expense_name, amount, created_at = r[0], r[1], r[2]
        else:
            # Fallback for unexpected row shapes
            expense_name, amount, created_at = "", 0, r

        date_text = format_report_date(created_at)
        line = (
            str(expense_name)[:22].ljust(22) + " "
            + f'{float(amount):.2f}'.rjust(7) + " "
            + date_text
        )
        elements.append(Preformatted(line, receipt_style))

    elements.append(Preformatted("_" * 42, receipt_style))
    header_draw = build_report_page_header()
    doc.build(elements, onFirstPage=header_draw, onLaterPages=header_draw)

    print("[EXPENSES] PDF generated:", file_path)

    return redirect(url_for("static", filename=f"reports/expenses_report_{ts}.pdf"))

@app.route("/reports", methods=["GET", "POST"])
def reports():
    preview_data = None
    form_data = {}
    selected_range = ""
    payment_mode = ""
    selected_type = (request.args.get("type") or "").strip().lower()
    if selected_type not in {"orders", "expenses", "inventory", "vendors"}:
        selected_type = "orders"
    form_data = {"type": selected_type}
    conn = get_db()
    inventory_list = conn.execute(
        """
        SELECT inventory_code, name, qty
        FROM inventory
        ORDER BY name
        """
    ).fetchall()
    expense_list = conn.execute(
        """
        SELECT expense_no, expense_name, amount, created_at
        FROM expenses
        ORDER BY created_at DESC
        """
    ).fetchall()
    orders_list = conn.execute(
        """
        SELECT o.id, o.order_type, o.created_at, c.name, o.total_amount, o.status, o.notes
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        ORDER BY o.created_at DESC
        LIMIT 50
        """
    ).fetchall()
    orders_list = [dict(row) for row in orders_list]
    for row in orders_list:
        row["payment_mode"] = extract_payment_mode(row.get("notes"))
    vendors_list = conn.execute(
        """
        SELECT v.id, v.vendor_code, v.name, v.phone, v.created_at
        FROM vendors v
        ORDER BY v.created_at DESC
        LIMIT 50
        """
    ).fetchall()

    if request.method == "POST":
        report_type = request.form["type"]
        from_date = request.form["from_date"]
        to_date = request.form["to_date"]
        selected_range = request.form.get("range", "").strip().lower()
        payment_mode = request.form.get("payment_mode", "").strip()

        form_data = request.form

        cur = conn.cursor()

        # if report_type == "expenses":
        #     cur.execute("""
        #         SELECT created_at, expense_name, amount
        #         FROM expenses
        #         WHERE date(created_at) BETWEEN ? AND ?
        #     """, (from_date, to_date))

        #     preview_data = cur.fetchall()

        if report_type == "expenses":
            cur.execute("""
                SELECT created_at, expense_name, amount
                FROM expenses
                WHERE date(created_at) BETWEEN ? AND ?
            """, (from_date, to_date))

        elif report_type == "orders":
            query = """
                SELECT o.created_at, c.name, o.total_amount, o.notes
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                WHERE date(o.created_at) BETWEEN ? AND ?
            """
            params: list[str] = [from_date, to_date]
            if payment_mode:
                query += " AND LOWER(ISNULL(o.notes, '')) LIKE ?"
                params.append(f"%payment method: {payment_mode.lower()}%")
            cur.execute(query, tuple(params))

        elif report_type == "inventory":
            cur.execute("""
                SELECT '', name, qty
                FROM inventory
                ORDER BY name
            """)

        elif report_type == "vendors":
            cur.execute("""
                SELECT
                    vpo.purchased_at,
                    v.name,
                    vpo.total_amount
                FROM vendor_purchase_orders vpo
                JOIN vendors v ON v.id = vpo.vendor_id
                WHERE date(vpo.purchased_at) BETWEEN ? AND ?
            """, (from_date, to_date))

        preview_data = cur.fetchall()

        if report_type == "orders":
            query = """
                SELECT o.id, o.order_type, o.created_at, c.name, o.total_amount, o.status, o.notes
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                WHERE date(o.created_at) BETWEEN ? AND ?
            """
            params: list[str] = [from_date, to_date]
            if payment_mode:
                query += " AND LOWER(ISNULL(o.notes, '')) LIKE ?"
                params.append(f"%payment method: {payment_mode.lower()}%")
            query += " ORDER BY o.created_at DESC LIMIT 200"
            cur.execute(
                query,
                tuple(params),
            )
            orders_list = cur.fetchall()
            orders_list = [dict(row) for row in orders_list]
            for row in orders_list:
                row["payment_mode"] = extract_payment_mode(row.get("notes"))

    report_files = []
    try:
        for name in os.listdir(REPORT_DIR):
            if name.lower().endswith(".pdf"):
                report_files.append(name)
    except Exception:
        report_files = []
    report_files.sort(reverse=True)

    conn.close()
    return render_template(
        "reports.html",
        preview_data=preview_data,
        form_data=form_data,
        selected_range=selected_range,
        inventory_list=inventory_list,
        expense_list=expense_list,
        orders_list=orders_list,
        vendors_list=vendors_list,
        report_files=report_files[:30],
    )

@app.route("/reports/import_pdf", methods=["POST"])
def reports_import_pdf():
    upload = request.files.get("report_pdf")
    if not upload or not upload.filename:
        return redirect(url_for("reports"))
    filename = secure_filename(upload.filename)
    if not filename.lower().endswith(".pdf"):
        return redirect(url_for("reports"))
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_name = f"imported_{ts}_{filename}"
    save_path = os.path.join(REPORT_DIR, final_name)
    upload.save(save_path)
    return redirect(url_for("reports"))

@app.route("/reports/generate", methods=["POST"])
def report_generate():
    rtype = request.form.get("type")
    from_date = request.form.get("from_date")
    to_date = request.form.get("to_date")
    payment_mode = request.form.get("payment_mode", "").strip()

    if rtype == "orders":
        return generate_orders_report_80mm(from_date, to_date, payment_mode)

    if rtype == "expenses":
        return generate_expenses_report_80mm(from_date, to_date)

    if rtype == "inventory":
        return generate_inventory_report_80mm()

    if rtype == "vendors":
        return generate_vendor_report_80mm(from_date, to_date)

    return redirect(url_for("reports"))

@app.route("/reports/export_excel", methods=["POST"])
def reports_export_excel():
    rtype = (request.form.get("type") or "orders").strip().lower()
    from_date = request.form.get("from_date")
    to_date = request.form.get("to_date")
    payment_mode = request.form.get("payment_mode", "").strip()

    if rtype in {"orders", "expenses", "vendors"} and (not from_date or not to_date):
        return redirect(url_for("reports"))

    conn = get_db()
    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{rtype}_report_{ts}.xls"

    if rtype == "orders":
        query = """
            SELECT o.id, o.order_no, o.order_type, o.created_at, c.name, o.total_amount, o.status, o.notes
            FROM orders o
            JOIN customers c ON c.id = o.customer_id
            WHERE date(o.created_at) BETWEEN ? AND ?
        """
        params: list[str] = [from_date, to_date]
        if payment_mode:
            query += " AND LOWER(IFNULL(o.notes, '')) LIKE ?"
            params.append(f"%payment method: {payment_mode.lower()}%")
        query += " ORDER BY o.created_at DESC"
        rows = conn.execute(query, tuple(params)).fetchall()

        writer.writerow(["Order ID", "Date", "Customer", "Total", "Status", "Payment Mode"])
        for row in rows:
            row_data = dict(row)
            writer.writerow(
                [
                    row_data.get("order_no") or display_order_no(row_data),
                    format_report_date(row_data.get("created_at")),
                    row_data.get("name") or "",
                    f'{float(row_data.get("total_amount") or 0):.2f}',
                    row_data.get("status") or "",
                    extract_payment_mode(row_data.get("notes")),
                ]
            )

    elif rtype == "expenses":
        rows = conn.execute(
            """
            SELECT expense_no, expense_name, amount, created_at
            FROM expenses
            WHERE date(created_at) BETWEEN ? AND ?
            ORDER BY created_at DESC
            """,
            (from_date, to_date),
        ).fetchall()
        writer.writerow(["No", "Expense", "Amount", "Date"])
        for row in rows:
            writer.writerow(
                [
                    row["expense_no"] or "",
                    row["expense_name"] or "",
                    f'{float(row["amount"] or 0):.2f}',
                    format_report_date(row["created_at"]),
                ]
            )

    elif rtype == "inventory":
        rows = conn.execute(
            """
            SELECT inventory_code, name, qty
            FROM inventory
            ORDER BY name
            """
        ).fetchall()
        writer.writerow(["Code", "Item", "Stock Quantity"])
        for row in rows:
            writer.writerow([row["inventory_code"] or "", row["name"] or "", row["qty"] or 0])

    elif rtype == "vendors":
        rows = conn.execute(
            """
            SELECT v.vendor_code, v.name, v.phone, vpo.total_amount, vpo.purchased_at
            FROM vendor_purchase_orders vpo
            JOIN vendors v ON v.id = vpo.vendor_id
            WHERE date(vpo.purchased_at) BETWEEN ? AND ?
            ORDER BY vpo.purchased_at DESC
            """,
            (from_date, to_date),
        ).fetchall()
        writer.writerow(["Vendor Code", "Name", "Phone", "Amount", "Date"])
        for row in rows:
            writer.writerow(
                [
                    row["vendor_code"] or "",
                    row["name"] or "",
                    row["phone"] or "",
                    f'{float(row["total_amount"] or 0):.2f}',
                    format_report_date(row["purchased_at"]),
                ]
            )
    else:
        conn.close()
        return redirect(url_for("reports"))

    conn.close()
    response = Response(output.getvalue(), mimetype="application/vnd.ms-excel")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

def generate_expenses_report_80mm(from_date, to_date):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT expense_name, amount, created_at
        FROM expenses
        WHERE date(created_at) BETWEEN ? AND ?
        ORDER BY created_at
        """,
        (from_date, to_date),
    ).fetchall()
    conn.close()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(REPORT_DIR, f"expenses_report_{ts}.pdf")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        leftMargin=24,
        rightMargin=24,
        topMargin=56,
        bottomMargin=24
    )
    regular_report_font, bold_report_font = get_reportlab_tamil_fonts()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="ExpenseReportTitle",
        parent=styles["Heading2"],
        fontName=bold_report_font,
        fontSize=15,
        leading=18,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        name="ExpenseReportSubtitle",
        parent=styles["Normal"],
        fontName=regular_report_font,
        fontSize=10,
        textColor=colors.HexColor("#333333"),
        spaceAfter=12,
    )
    normal_style = ParagraphStyle(
        name="ExpenseReportNormalTamil",
        parent=styles["Normal"],
        fontName=regular_report_font,
    )

    elements = []
    elements.append(Paragraph("Expenses Report", title_style))
    elements.append(Paragraph(f"From {from_date} To {to_date}", subtitle_style))

    table_data = [["Expense", "Amount", "Date"]]
    for r in rows:
        table_data.append(
            [
                str(r["expense_name"] or ""),
                f'{float(r["amount"] or 0):.2f}',
                format_report_date(r["created_at"]),
            ]
        )

    if len(table_data) == 1:
        elements.append(Paragraph("No expenses found for selected date range.", normal_style))
    else:
        col_widths = [320, 110, 110]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("FONTNAME", (0, 0), (-1, 0), bold_report_font),
                    ("FONTNAME", (0, 1), (-1, -1), regular_report_font),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b5b5b5")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elements.append(table)
        elements.append(Spacer(1, 8))

    header_draw = build_report_page_header()
    doc.build(elements, onFirstPage=header_draw, onLaterPages=header_draw)

    return redirect(url_for("static", filename=f"reports/expenses_report_{ts}.pdf"))

def generate_inventory_report_80mm():
    conn = get_db()
    rows = conn.execute(
        "SELECT inventory_code, name, qty FROM inventory ORDER BY name"
    ).fetchall()
    conn.close()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(REPORT_DIR, f"inventory_report_{ts}.pdf")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        leftMargin=24,
        rightMargin=24,
        topMargin=REPORT_TOP_MARGIN,
        bottomMargin=24
    )
    regular_report_font, bold_report_font = get_reportlab_tamil_fonts()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="InventoryReportTitle",
        parent=styles["Heading2"],
        fontName=bold_report_font,
        fontSize=15,
        leading=18,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        name="InventoryReportSubtitle",
        parent=styles["Normal"],
        fontName=regular_report_font,
        fontSize=10,
        textColor=colors.HexColor("#333333"),
        spaceAfter=12,
    )
    normal_style = ParagraphStyle(
        name="InventoryReportNormalTamil",
        parent=styles["Normal"],
        fontName=regular_report_font,
    )

    elements = []
    elements.append(Paragraph("Inventory Report", title_style))
    elements.append(Paragraph("Current inventory snapshot", subtitle_style))

    table_data = [["Code", "Item", "Qty"]]
    for r in rows:
        table_data.append(
            [
                str(r["inventory_code"] or "-"),
                str(r["name"] or ""),
                str(r["qty"] if r["qty"] is not None else 0),
            ]
        )

    if len(table_data) == 1:
        elements.append(Paragraph("No inventory items found.", normal_style))
    else:
        col_widths = [110, 320, 110]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("FONTNAME", (0, 0), (-1, 0), bold_report_font),
                    ("FONTNAME", (0, 1), (-1, -1), regular_report_font),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b5b5b5")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elements.append(table)
        elements.append(Spacer(1, 8))

    header_draw = build_report_page_header()
    doc.build(elements, onFirstPage=header_draw, onLaterPages=header_draw)

    return redirect(url_for("static", filename=f"reports/inventory_report_{ts}.pdf"))

def generate_vendor_report_80mm(from_date, to_date):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT
            v.name AS vendor_name,
            COALESCE(vpi.item_name_snapshot, i.name) AS material_name,
            vpi.qty,
            vpi.line_total AS total_price,
            vpo.purchased_at,
            vpo.status AS payment_status
        FROM vendor_purchase_orders vpo
        JOIN vendors v ON v.id = vpo.vendor_id
        JOIN vendor_purchase_items vpi ON vpi.purchase_id = vpo.id
        LEFT JOIN inventory i ON i.id = vpi.inventory_id
        WHERE date(vpo.purchased_at) BETWEEN ? AND ?
        ORDER BY vpo.purchased_at
        """,
        (from_date, to_date),
    ).fetchall()
    conn.close()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(REPORT_DIR, f"vendor_report_{ts}.pdf")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        leftMargin=24,
        rightMargin=24,
        topMargin=REPORT_TOP_MARGIN,
        bottomMargin=24
    )
    regular_report_font, bold_report_font = get_reportlab_tamil_fonts()
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="VendorReportTitle",
        parent=styles["Heading2"],
        fontName=bold_report_font,
        fontSize=15,
        leading=18,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        name="VendorReportSubtitle",
        parent=styles["Normal"],
        fontName=regular_report_font,
        fontSize=10,
        textColor=colors.HexColor("#333333"),
        spaceAfter=12,
    )
    normal_style = ParagraphStyle(
        name="VendorReportNormalTamil",
        parent=styles["Normal"],
        fontName=regular_report_font,
    )

    elements = []
    elements.append(Paragraph("Vendor Purchase Report", title_style))
    elements.append(Paragraph(f"From {from_date} To {to_date}", subtitle_style))

    table_data = [["Vendor", "Material", "Qty", "Amount", "Pay Status", "Date"]]
    for r in rows:
        qty_value = float(r["qty"] or 0)
        qty_text = f"{qty_value:.2f}".rstrip("0").rstrip(".")
        table_data.append(
            [
                str(r["vendor_name"] or ""),
                str(r["material_name"] or ""),
                qty_text or "0",
                f'{float(r["total_price"] or 0):.2f}',
                str(r["payment_status"] or "Unpaid"),
                format_report_date(r["purchased_at"]),
            ]
        )

    if len(table_data) == 1:
        elements.append(Paragraph("No vendor purchases found for selected date range.", normal_style))
    else:
        col_widths = [100, 150, 55, 70, 80, 80]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efefef")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("FONTNAME", (0, 0), (-1, 0), bold_report_font),
                    ("FONTNAME", (0, 1), (-1, -1), regular_report_font),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (2, 1), (3, -1), "RIGHT"),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b5b5b5")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elements.append(table)
        elements.append(Spacer(1, 8))

    header_draw = build_report_page_header()
    doc.build(elements, onFirstPage=header_draw, onLaterPages=header_draw)

    return redirect(url_for("static", filename=f"reports/vendor_report_{ts}.pdf"))

# @app.route("/reports", methods=["GET", "POST"])
# def reports():
#     preview_data = None
#     form_data = {}

#     if request.method == "POST":
#         report_type = request.form["type"]
#         from_date = request.form["from_date"]
#         to_date = request.form["to_date"]

#         form_data = request.form

#         con = sqlite3.connect(DB_PATH)
#         cur = con.cursor()

#         if report_type == "expenses":
#             cur.execute("""
#                 SELECT created_at, expense_name, amount
#                 FROM expenses
#                 WHERE date(created_at) BETWEEN ? AND ?
#             """, (from_date, to_date))

#             preview_data = cur.fetchall()

#         con.close()

#     return render_template(
#         "reports.html",
#         preview_data=preview_data,
#         form_data=form_data
#     )

@app.route("/orders")
def orders():
    status = request.args.get("status", "").strip()
    conn = get_db()
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    left2_date = today + timedelta(days=2)
    if status in {"Urgent", "Ready for Delivery"}:
        date_filter = ""
        params: tuple = ()
        if status == "Urgent":
            date_filter = (
                "AND orders.status NOT IN ('Cancelled', 'Delivered') "
                "AND orders.due_date IS NOT NULL "
                "AND date(orders.due_date) BETWEEN ? AND ?"
            )
            params = (today.isoformat(), tomorrow.isoformat())
        else:
            date_filter = "AND date(orders.due_date) = ?"
            params = (left2_date.isoformat(),)
        rows = conn.execute(
            f"""
            SELECT orders.*, customers.name, customers.phone,
                   (
                       SELECT GROUP_CONCAT(DISTINCT m.assigned_tailor)
                       FROM order_items oi
                       JOIN measurements m ON m.customer_id = orders.customer_id
                       WHERE oi.order_id = orders.id
                         AND m.assigned_tailor IS NOT NULL
                         AND m.assigned_tailor != ''
                         AND m.kind LIKE '%' || oi.item_type || '%'
                   ) AS assigned_tailors,
                   (
                       SELECT GROUP_CONCAT(DISTINCT oi.item_type)
                       FROM order_items oi
                       WHERE oi.order_id = orders.id
                   ) AS item_types
            FROM orders
            JOIN customers ON (
                customers.id = orders.customer_id
                OR customers.id = orders.customer_display_id
            )
            WHERE orders.status != 'Cancelled'
            {date_filter}
            ORDER BY orders.created_at DESC
            """,
            params,
        ).fetchall()
    elif status:
        rows = conn.execute(
            """
            SELECT orders.*, customers.name, customers.phone,
                   (
                       SELECT GROUP_CONCAT(DISTINCT m.assigned_tailor)
                       FROM order_items oi
                       JOIN measurements m ON m.customer_id = orders.customer_id
                       WHERE oi.order_id = orders.id
                         AND m.assigned_tailor IS NOT NULL
                         AND m.assigned_tailor != ''
                         AND m.kind LIKE '%' || oi.item_type || '%'
                   ) AS assigned_tailors,
                   (
                       SELECT GROUP_CONCAT(DISTINCT oi.item_type)
                       FROM order_items oi
                       WHERE oi.order_id = orders.id
                   ) AS item_types
            FROM orders
            JOIN customers ON (
                customers.id = orders.customer_id
                OR customers.id = orders.customer_display_id
            )
            WHERE orders.status = ?
            ORDER BY orders.created_at DESC
            """,
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT orders.*, customers.name, customers.phone,
                   (
                       SELECT GROUP_CONCAT(DISTINCT m.assigned_tailor)
                       FROM order_items oi
                       JOIN measurements m ON m.customer_id = orders.customer_id
                       WHERE oi.order_id = orders.id
                         AND m.assigned_tailor IS NOT NULL
                         AND m.assigned_tailor != ''
                         AND m.kind LIKE '%' || oi.item_type || '%'
                   ) AS assigned_tailors,
                   (
                       SELECT GROUP_CONCAT(DISTINCT oi.item_type)
                       FROM order_items oi
                       WHERE oi.order_id = orders.id
                   ) AS item_types
            FROM orders
            JOIN customers ON (
                customers.id = orders.customer_id
                OR customers.id = orders.customer_display_id
            )
            ORDER BY orders.created_at DESC
            """
        ).fetchall()
    conn.close()
    def parse_date(value) -> datetime.date | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value.date()
        if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
            try:
                return value
            except Exception:
                return None
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.strip()[:10]).date()
        except ValueError:
            return None
    def format_date_only(value) -> str:
        parsed = parse_date(value)
        return parsed.isoformat() if parsed else "-"
    def apply_delivery_display(order_rows: list[dict]) -> None:
        for row in order_rows:
            order_type = (row.get("order_type") or "").strip().lower()
            created_at = row.get("created_at")
            due_date = row.get("due_date")
            if order_type in {"material", "alteration"}:
                row["delivery_date_display"] = format_date_only(created_at or due_date)
                row["due_urgent"] = False
            else:
                row["delivery_date_display"] = format_date_only(due_date or created_at)
                due = parse_date(due_date)
                due_urgent = bool(due and today <= due <= left2_date)
                row["due_urgent"] = due_urgent

    rows = [dict(row) for row in rows]
    for row in rows:
        row["order_no_display"] = display_order_no(row)
        row["status_display"] = row.get("status") or "-"
        row["status_display_lines"] = [row["status_display"]]
        row["status_detail_lines"] = [f"{row['order_no_display']}@@{row['status_display']}"]
        row["delivery_date_display_lines"] = [row.get("delivery_date_display") or "-"]
        row["delivery_detail_lines"] = [f"{row['order_no_display']}@@{(row.get('delivery_date_display') or '-')}"]
    apply_delivery_display(rows)
    order_ids = [int(row["id"]) for row in rows if row.get("id")]
    if order_ids:
        conn = get_db()
        placeholders = ",".join("?" for _ in order_ids)
        measure_rows = conn.execute(
            f"""
            SELECT order_id, kind, measure_status, notes
            FROM measurements
            WHERE order_id IN ({placeholders})
            ORDER BY id ASC
            """,
            tuple(order_ids),
        ).fetchall()
        conn.close()
        per_order_measure_status: dict[int, list[tuple[str, str, str]]] = {}
        for mrow in measure_rows:
            oid = int(mrow["order_id"]) if mrow["order_id"] is not None else 0
            if oid <= 0:
                continue
            kind_text = str(mrow["kind"] or "").strip() or "Item"
            status_text = str(mrow["measure_status"] or "").strip()
            delivery_text = ""
            notes_text = str(mrow["notes"] or "")
            for raw_line in notes_text.splitlines():
                clean = raw_line.strip()
                if clean.lower().startswith("delivery date:"):
                    delivery_text = clean.split(":", 1)[1].strip()
                    break
            per_order_measure_status.setdefault(oid, []).append((kind_text, status_text, delivery_text))
        for row in rows:
            oid = int(row["id"])
            pair_list = per_order_measure_status.get(oid) or []
            if not pair_list:
                continue
            seen_kinds: set[str] = set()
            status_parts: list[str] = []
            status_detail_parts: list[str] = []
            delivery_parts: list[str] = []
            delivery_detail_parts: list[str] = []
            fallback_status = str(row.get("status") or "In-Progress").strip() or "In-Progress"
            fallback_delivery = str(row.get("delivery_date_display") or "-").strip() or "-"
            order_no_text = str(row.get("order_no") or row.get("order_no_display") or row.get("id") or "").replace("\\", "/")
            order_prefix = order_no_text.split("/", 1)[0] if "/" in order_no_text else order_no_text
            display_index = 0
            for kind_text, status_text, delivery_text in pair_list:
                kind_key = kind_text.lower()
                if kind_key in seen_kinds:
                    continue
                seen_kinds.add(kind_key)
                display_index += 1
                status_value = status_text or fallback_status
                status_parts.append(f"{display_index}-{status_value}")
                kind_main = kind_text.split("-", 1)[0].strip() if "-" in kind_text else kind_text
                detail_label = f"{order_prefix}/{display_index} - {kind_main}"
                status_detail_parts.append(f"{detail_label}@@{status_value}")
                due_value = delivery_text or fallback_delivery
                delivery_parts.append(f"{display_index}-{due_value}")
                delivery_detail_parts.append(f"{detail_label}@@{due_value}")
            if status_parts:
                row["status_display"] = " ".join(status_parts)
                row["status_display_lines"] = status_parts
            if status_detail_parts:
                row["status_detail_lines"] = status_detail_parts
            if delivery_parts:
                row["delivery_date_display_lines"] = delivery_parts
            if delivery_detail_parts:
                row["delivery_detail_lines"] = delivery_detail_parts
    conn = get_db()
    customer_rows = conn.execute(
        """
        SELECT
            c.*,
            (
                SELECT MAX(o.created_at)
                FROM orders o
                WHERE o.customer_id = c.id
                   OR o.customer_display_id = c.id
            ) AS last_ordered,
            (
                SELECT TOP 1 o.order_no
                FROM orders o
                WHERE o.customer_id = c.id
                   OR o.customer_display_id = c.id
                ORDER BY o.created_at DESC, o.id DESC
            ) AS latest_order_no,
            (
                SELECT TOP 1 o.id
                FROM orders o
                WHERE o.customer_id = c.id
                   OR o.customer_display_id = c.id
                ORDER BY o.created_at DESC, o.id DESC
            ) AS latest_order_id,
            (
                SELECT TOP 1 o.order_type
                FROM orders o
                WHERE o.customer_id = c.id
                   OR o.customer_display_id = c.id
                ORDER BY o.created_at DESC, o.id DESC
            ) AS latest_order_type,
            (
                SELECT TOP 1 oi.filename
                FROM order_images oi
                JOIN orders o ON o.id = oi.order_id
                WHERE (o.customer_id = c.id OR o.customer_display_id = c.id)
                  AND (
                    LOWER(LTRIM(RTRIM(ISNULL(oi.item_type, '')))) = 'customer'
                    OR LOWER(LTRIM(RTRIM(ISNULL(oi.label, '')))) = 'customer'
                  )
                ORDER BY oi.id DESC
            ) AS customer_photo_filename,
            (
                SELECT GROUP_CONCAT(DISTINCT o.id)
                FROM orders o
                WHERE o.customer_id = c.id
                   OR o.customer_display_id = c.id
            ) AS order_ids
        FROM customers c
        ORDER BY last_ordered DESC
        """
    ).fetchall()
    conn.close()
    customer_rows = [dict(row) for row in customer_rows]
    for row in customer_rows:
        row["display_id"] = customer_display_id(int(row["id"]))
        if row.get("latest_order_no") or row.get("latest_order_id"):
            row["latest_order_no_display"] = display_order_no(
                {
                    "order_no": row.get("latest_order_no"),
                    "id": row.get("latest_order_id"),
                    "order_type": row.get("latest_order_type"),
                }
            )
        else:
            row["latest_order_no_display"] = "-"
    conn = get_db()
    tailor_rows = conn.execute("SELECT id, name FROM tailors").fetchall()
    conn.close()
    tailor_map = {row["name"]: row["id"] for row in tailor_rows}
    return render_template(
        "orders.html",
        orders=rows,
        customers=customer_rows,
        status=status,
        tailor_map=tailor_map,
        auto_print_on_click=get_setting("auto_print_on_click", "0") == "1",
    )


@app.route("/orders/<int:order_id>/status", methods=["POST"])
def order_update_status(order_id: int):
    status = request.form.get("status", "").strip()
    if not status:
        return ("", 400)
    conn = get_db()
    current = conn.execute(
        "SELECT status, completed_at, delivered_at FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    previous_status = (current["status"] or "").strip() if current else ""
    if previous_status == "Cancelled" and status != "Cancelled":
        conn.close()
        return jsonify({"ok": False, "message": "Cancelled bills cannot be changed."}), 409
    completed_at = current["completed_at"] if current else None
    delivered_at = current["delivered_at"] if current else None
    if status == "Completed":
        completed_at = completed_at or now_str()
    if status == "Delivered":
        delivered_at = delivered_at or now_str()
        completed_at = completed_at or now_str()
    conn.execute(
        """
        UPDATE orders
        SET status = ?, completed_at = ?, delivered_at = ?
        WHERE id = ?
        """,
        (status, completed_at, delivered_at, order_id),
    )
    sync_completed_notification(conn, order_id, previous_status, status, completed_at)
    conn.commit()
    conn.close()
    return ("", 204)


@app.route("/orders/<int:order_id>/details/lines")
def order_detail_lines(order_id: int):
    conn = get_db()
    order = conn.execute(
        "SELECT id, order_no, invoice_id, status, due_date FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    if not order:
        conn.close()
        return jsonify({"ok": False, "message": "Order not found"}), 404

    measure_rows = conn.execute(
        """
        SELECT id, kind, measure_status, notes
        FROM measurements
        WHERE order_id = ?
        ORDER BY id ASC
        """,
        (order_id,),
    ).fetchall()
    conn.close()

    order_no = str(order["order_no"] or order["id"] or "").replace("\\", "/")
    order_prefix = order_no.split("/", 1)[0] if "/" in order_no else order_no
    invoice_id = str(order["invoice_id"] or "").strip()
    fallback_status = str(order["status"] or "In-Progress").strip() or "In-Progress"
    is_cancelled_order = fallback_status == "Cancelled"
    fallback_delivery = date_only(order["due_date"]) if order["due_date"] else "-"

    status_lines: list[str] = []
    delivery_lines: list[str] = []
    status_items: list[dict] = []
    seen_kinds: set[str] = set()
    display_index = 0
    for row in measure_rows:
        measure_id = int(row["id"]) if row["id"] is not None else 0
        kind_text = str(row["kind"] or "").strip() or "Item"
        kind_key = kind_text.lower()
        if kind_key in seen_kinds:
            continue
        seen_kinds.add(kind_key)
        display_index += 1
        kind_main = kind_text.split("-", 1)[0].strip() if "-" in kind_text else kind_text
        label = f"{order_prefix}/{display_index} - {kind_main}"
        status_value = str(row["measure_status"] or "").strip() or fallback_status
        delivery_value = ""
        for raw_line in str(row["notes"] or "").splitlines():
            clean = raw_line.strip()
            if clean.lower().startswith("delivery date:"):
                delivery_value = clean.split(":", 1)[1].strip()
                break
        if not delivery_value:
            delivery_value = fallback_delivery
        status_lines.append(f"{label}@@{status_value}")
        delivery_lines.append(f"{label}@@{delivery_value}")
        status_items.append(
            {
                "measurement_id": measure_id,
                "label": label,
                "status": status_value,
                "can_edit": not is_cancelled_order,
            }
        )

    if not status_lines:
        label = order_no or str(order_id)
        status_lines = [f"{label}@@{fallback_status}"]
    if not delivery_lines:
        label = order_no or str(order_id)
        delivery_lines = [f"{label}@@{fallback_delivery}"]

    return jsonify(
        {
            "ok": True,
            "invoice_id": invoice_id,
            "order_no": order_no,
            "status_lines": status_lines,
            "status_items": status_items,
            "delivery_lines": delivery_lines,
        }
    )


@app.route("/measurements/<int:measurement_id>/status", methods=["POST"])
def measurement_update_status(measurement_id: int):
    allowed_measure_statuses = {"In-Progress", "Completed", "Delivered"}
    status = (request.form.get("status") or "").strip()
    if status not in allowed_measure_statuses:
        return jsonify({"ok": False, "message": "Invalid status"}), 400

    conn = get_db()
    measurement = conn.execute(
        "SELECT id, order_id, notes FROM measurements WHERE id = ?",
        (measurement_id,),
    ).fetchone()
    if not measurement:
        conn.close()
        return jsonify({"ok": False, "message": "Measurement not found"}), 404

    order_id = int(measurement["order_id"]) if measurement["order_id"] is not None else 0
    if order_id > 0:
        parent_order = conn.execute(
            "SELECT status FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        parent_status = str(parent_order["status"] or "").strip() if parent_order else ""
        if parent_status == "Cancelled":
            conn.close()
            return jsonify({"ok": False, "message": "Cancelled bills cannot be changed."}), 409

    notes_text = str(measurement["notes"] or "")
    existing_completed = None
    existing_delivery = None
    for raw_line in notes_text.splitlines():
        clean = raw_line.strip()
        low = clean.lower()
        if low.startswith("completed date:"):
            existing_completed = clean.split(":", 1)[1].strip()
        elif low.startswith("delivery date:"):
            existing_delivery = clean.split(":", 1)[1].strip()

    today_date = datetime.now().date().isoformat()
    next_completed = existing_completed
    next_delivery = existing_delivery
    if status == "Completed":
        next_completed = today_date
    elif status == "Delivered":
        next_delivery = today_date

    kept_lines: list[str] = []
    for raw_line in notes_text.splitlines():
        clean = raw_line.strip()
        if not clean:
            continue
        low = clean.lower()
        if low.startswith("completed date:") or low.startswith("delivery date:"):
            continue
        kept_lines.append(clean)
    prefixed_lines: list[str] = []
    if next_completed:
        prefixed_lines.append(f"Completed date: {next_completed}")
    if next_delivery:
        prefixed_lines.append(f"Delivery date: {next_delivery}")
    updated_notes = "\n".join(prefixed_lines + kept_lines) if (prefixed_lines or kept_lines) else None

    conn.execute(
        "UPDATE measurements SET measure_status = ?, notes = ? WHERE id = ?",
        (status, updated_notes, measurement_id),
    )

    if order_id > 0:
        status_rows = conn.execute(
            """
            SELECT DISTINCT LTRIM(RTRIM(ISNULL(measure_status, '')))
            FROM measurements
            WHERE order_id = ?
            """,
            (order_id,),
        ).fetchall()
        status_set = {
            str(row[0]).strip()
            for row in status_rows
            if str(row[0] or "").strip() in allowed_measure_statuses
        }
        if not status_set:
            derived_order_status = "In-Progress"
        elif status_set == {"Delivered"}:
            derived_order_status = "Delivered"
        elif status_set.issubset({"Completed", "Delivered"}):
            derived_order_status = "Completed"
        else:
            derived_order_status = "In-Progress"

        current_order = conn.execute(
            "SELECT status, completed_at, delivered_at FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        previous_status = (current_order["status"] or "").strip() if current_order else ""
        completed_at = current_order["completed_at"] if current_order else None
        delivered_at = current_order["delivered_at"] if current_order else None
        if derived_order_status in {"Completed", "Delivered"}:
            status_now = now_str()
            completed_at = completed_at or status_now
            delivered_at = delivered_at or status_now
        conn.execute(
            """
            UPDATE orders
            SET status = ?, completed_at = ?, delivered_at = ?
            WHERE id = ?
            """,
            (derived_order_status, completed_at, delivered_at, order_id),
        )
        sync_completed_notification(conn, order_id, previous_status, derived_order_status, completed_at)

    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/orders/download")
def orders_download():
    conn = get_db()
    value_keys = [
        "neck", "chest", "waist", "hip", "shoulder",
        "sleeve", "length", "cuff",
        "inseam", "outseam", "thigh",
        "knee", "bottom",
    ]
    def extract_payment_method(notes_text: str | None) -> str:
        for raw in str(notes_text or "").splitlines():
            line = raw.strip()
            if line.lower().startswith("payment method:"):
                return line.split(":", 1)[1].strip() or "-"
        return "-"

    def extract_measurement_details(customer_id: int, order_id: int, created_at: str | None) -> str:
        try:
            ms = fetch_order_measurements(conn, int(customer_id), int(order_id), created_at)
        except Exception:
            return "-"
        chunks: list[str] = []
        for m in ms:
            kind = (m["kind"] or "Item").strip()
            vals: list[str] = []
            for key in value_keys:
                val = m[key] if key in m.keys() else None
                if val is not None and str(val).strip() != "":
                    vals.append(fmt_measure(val))
            if vals:
                chunks.append(f"{kind}: {', '.join(vals)}")
            else:
                chunks.append(f"{kind}: -")
        return " | ".join(chunks) if chunks else "-"

    def extract_category(order_id: int) -> str:
        rows = conn.execute(
            "SELECT item_type FROM order_items WHERE order_id = ?",
            (order_id,),
        ).fetchall()
        names = []
        for r in rows:
            item = str(r["item_type"] or "").strip()
            if not item:
                continue
            base = item.split("-", 1)[0].strip()
            if base and base.lower() not in [x.lower() for x in names]:
                names.append(base)
        return ", ".join(names) if names else "-"

    rows = conn.execute(
        """
        SELECT orders.*, customers.name, customers.phone,
               (
                   SELECT GROUP_CONCAT(DISTINCT m.assigned_tailor)
                   FROM order_items oi
                   JOIN measurements m ON m.customer_id = orders.customer_id
                   WHERE oi.order_id = orders.id
                     AND m.assigned_tailor IS NOT NULL
                     AND m.assigned_tailor != ''
                     AND m.kind LIKE '%' || oi.item_type || '%'
               ) AS assigned_tailors
        FROM orders
        JOIN customers ON (
            customers.id = orders.customer_id
            OR customers.id = orders.customer_display_id
        )
        ORDER BY orders.created_at DESC
        """
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t")
    writer.writerow([
        "Order ID",
        "Customer",
        "Phone",
        "Type",
        "Status",
        "Tailor",
        "Total",
        "Delivery Date",
        "Order Date",
        "Measurement Details",
        "Order Status",
        "Payment Summary",
        "Payment Method",
        "Order Type",
        "Category",
    ])
    for row in rows:
        total_amount = float(row["total_amount"] or 0)
        advance_amount = float(row["advance_amount"] or 0)
        paid_amount = float(row["paid_amount"] or 0)
        balance_amount = max(total_amount - advance_amount - paid_amount, 0)
        measurement_details = extract_measurement_details(
            int(row["customer_id"]),
            int(row["id"]),
            row["created_at"] if "created_at" in row.keys() else None,
        )
        payment_summary = (
            f"Total: {total_amount:.2f}, "
            f"Advance: {advance_amount:.2f}, "
            f"Paid: {paid_amount:.2f}, "
            f"Balance: {balance_amount:.2f}"
        )
        writer.writerow([
            row.get("order_no") or display_order_no(dict(row)),
            row["name"],
            row["phone"],
            row["order_type"] or "-",
            row["status"] or "-",
            row["assigned_tailors"] or row["assigned_tailor"] or "-",
            f"{total_amount:.2f}",
            row["due_date"] or "-",
            row["created_at"] or "-",
            measurement_details,
            row["status"] or "-",
            payment_summary,
            extract_payment_method(row["notes"] if "notes" in row.keys() else None),
            row["order_type"] or "-",
            extract_category(int(row["id"])),
        ])
    conn.close()

    filename = f"order_list_{datetime.now().strftime('%Y%m%d')}.xls"
    response = Response(output.getvalue(), mimetype="application/vnd.ms-excel")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


# @app.route("/orders/new", methods=["GET", "POST"])
# def order_new():
#     conn = get_db()
#     tailors = conn.execute("SELECT * FROM tailors ORDER BY team, name").fetchall()
#     categories = conn.execute(
#         "SELECT * FROM categories ORDER BY name"
#     ).fetchall()
#     subcategories = conn.execute(
#         "SELECT * FROM subcategories ORDER BY name"
#     ).fetchall()
#     measurement_fields = conn.execute(
#         "SELECT * FROM measurement_fields ORDER BY subcategory_id, sort_order, field_label"
#     ).fetchall()
#     requirement_icons = conn.execute(
#         "SELECT * FROM requirement_icons ORDER BY name"
#     ).fetchall()
#     inventory = conn.execute(
#         """
#         SELECT inventory.id, inventory.inventory_code, inventory.name, inventory.qty, inventory.uom_id,
#                uoms.name AS uom_name
#         FROM inventory
#         LEFT JOIN uoms ON uoms.id = inventory.uom_id
#         ORDER BY inventory.name ASC
#         """
#     ).fetchall()
#     uoms = conn.execute("SELECT * FROM uoms ORDER BY name").fetchall()
#     next_customer_display_id = conn.execute(
#         "SELECT COALESCE(MAX(customer_display_id), 100) + 1 FROM orders"
#     ).fetchone()[0]
#     next_order_id = conn.execute(
#         "SELECT COALESCE(MAX(id), 0) + 1 FROM orders"
#     ).fetchone()[0]
#     now_dt = datetime.now()
#     today_date = now_dt.strftime("%Y-%m-%d %H:%M")
#     base_date = now_dt.date()
#     worker_days = int(get_setting("worker_delivery_days", "0") or 0)
#     delivery_days = int(get_setting("delivery_days", "0") or 0)
#     worker_default = (base_date + timedelta(days=worker_days)).isoformat() if worker_days else ""
#     delivery_default = (base_date + timedelta(days=delivery_days)).isoformat() if delivery_days else ""
#     field_map = {}
#     for row in measurement_fields:
#         field_map.setdefault(str(row["subcategory_id"]), []).append(
#             {"key": row["field_key"], "label": row["field_label"]}
#         )
#     conn.close()

#     prefill_name = request.args.get("name", "").strip()
#     prefill_phone = request.args.get("phone", "").strip()
#     prefill_address = request.args.get("address", "").strip()
#     prefill_customer_id = request.args.get("customer_id", "").strip()
#     if prefill_customer_id.isdigit():
#         conn = get_db()
#         row = conn.execute(
#             "SELECT id, name, phone, address FROM customers WHERE id = ?",
#             (int(prefill_customer_id),),
#         ).fetchone()
#         conn.close()
#         if row:
#             prefill_name = row["name"] or prefill_name
#             prefill_phone = row["phone"] or prefill_phone
#             prefill_address = row["address"] or prefill_address
#             prefill_customer_id = str(row["id"])
#     display_customer_id = int(next_customer_display_id)

#     if request.method == "POST":
#         name = request.form.get("name", "").strip()
#         phone = request.form.get("phone", "").strip()
#         notes = request.form.get("customer_notes", "").strip()
#         address = request.form.get("address", "").strip()
#         material_source = request.form.get("material_source", "customer").strip().lower()
#         if not name or not phone:
#             return render_template(
#                 "order_new.html",
#                 tailors=tailors,
#                 categories=categories,
#                 subcategories=subcategories,
#                 measurement_fields=measurement_fields,
#                 measurement_field_map=field_map,
#                 requirement_icons=requirement_icons,
#                 inventory=inventory,
#                 uoms=uoms,
#                 next_order_id=next_order_id,
#                 display_customer_id=display_customer_id,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 error="Customer name and phone are required.",
#                 prefill_name=name,
#                 prefill_phone=phone,
#                 prefill_address=address,
#             )

#         customer_id = upsert_customer(name, phone, notes, address)
#         category_ids = request.form.getlist("measure_category_id")
#         subcategory_ids = request.form.getlist("measure_subcategory_id")
#         qty_values = request.form.getlist("measure_qty")
#         label_values = request.form.getlist("measure_label")
#         tailor_values = request.form.getlist("measure_assigned_tailor")
#         note_values = request.form.getlist("measure_notes")
#         known_fields = {
#             "neck",
#             "chest",
#             "waist",
#             "hip",
#             "shoulder",
#             "sleeve",
#             "length",
#             "cuff",
#             "inseam",
#             "outseam",
#             "thigh",
#             "knee",
#             "bottom",
#             "notes",
#         }
#         field_keys = [row["field_key"] for row in measurement_fields]
#         label_map = {row["field_key"]: row["field_label"] for row in measurement_fields}
#         values_by_field = {
#             key: request.form.getlist(f"measure_{key}") for key in field_keys
#         }

#         map_conn = get_db()
#         cat_rows = map_conn.execute("SELECT id, name FROM categories").fetchall()
#         sub_rows = map_conn.execute("SELECT id, name FROM subcategories").fetchall()
#         category_map = {str(row["id"]): row["name"] for row in cat_rows}
#         subcategory_map = {str(row["id"]): row["name"] for row in sub_rows}

#         max_len = max(
#             len(category_ids),
#             len(subcategory_ids),
#             len(qty_values),
#             len(label_values),
#             len(note_values),
#             max((len(items) for items in values_by_field.values()), default=0),
#         )
#         order_item_rows = []
#         for idx in range(max_len):
#             category_id = category_ids[idx].strip() if idx < len(category_ids) else ""
#             if not category_id:
#                 continue
#             subcategory_id = subcategory_ids[idx].strip() if idx < len(subcategory_ids) else ""
#             category_name = category_map.get(category_id, "Category")
#             subcategory_name = subcategory_map.get(subcategory_id, "")
#             kind = f"{category_name} - {subcategory_name}" if subcategory_name else category_name
#             qty_raw = qty_values[idx].strip() if idx < len(qty_values) and qty_values[idx] else ""
#             if qty_raw.isdigit():
#                 qty_value = max(int(qty_raw), 1)
#             else:
#                 qty_value = 1

#             payload = {}
#             extra_lines = []
#             for field_key in field_keys:
#                 items = values_by_field.get(field_key, [])
#                 value = items[idx].strip() if idx < len(items) and items[idx] else ""
#                 if not value:
#                     continue
#                 if field_key in known_fields:
#                     payload[field_key] = value
#                 else:
#                     label = label_map.get(field_key, field_key)
#                     extra_lines.append(f"{label}: {value}")

#             base_note = note_values[idx].strip() if idx < len(note_values) and note_values[idx] else ""
#             if extra_lines:
#                 extra_text = "\n".join(extra_lines)
#                 base_note = f"{base_note}\n{extra_text}".strip() if base_note else extra_text
#             if base_note:
#                 payload["notes"] = base_note

#             tailor_name = tailor_values[idx].strip() if idx < len(tailor_values) and tailor_values[idx] else ""
#             if tailor_name:
#                 payload["assigned_tailor"] = tailor_name

#             label = label_values[idx].strip() if idx < len(label_values) and label_values[idx] else ""
#             if label:
#                 notes = payload.get("notes") or ""
#                 label_note = f"Label: {label}"
#                 payload["notes"] = f"{label_note}\n{notes}".strip()

#             create_measurement(customer_id, kind, payload, map_conn)
#             order_item_rows.append((kind, qty_value))

#         map_conn.commit()
#         map_conn.close()

#         due_date = request.form.get("due_date", "").strip() or None
#         priority = "Normal"
#         status = request.form.get("status", "In-Progress")
#         assigned_tailor = request.form.get("assigned_tailor", "").strip() or None
#         order_notes = request.form.get("order_notes", "").strip() or None
#         worker_delivery_date = request.form.get("worker_delivery_date", "").strip()
#         extra_date_lines = []
#         if worker_delivery_date:
#             extra_date_lines.append(f"Worker delivery date: {worker_delivery_date}")
#         if extra_date_lines:
#             date_text = "\n".join(extra_date_lines)
#             order_notes = f"{order_notes}\n{date_text}".strip() if order_notes else date_text
#         requirements = [r.strip() for r in request.form.getlist("requirements") if r.strip()]
#         if requirements:
#             req_text = "Requirements: " + ", ".join(requirements)
#             order_notes = f"{req_text}\n{order_notes}" if order_notes else req_text
#         advance_amount = request.form.get("advance_amount", "").strip()
#         total_amount = request.form.get("total_amount", "").strip()
#         advance_value = float(advance_amount) if advance_amount else None
#         total_value = float(total_amount) if total_amount else None
#         if not total_value or total_value <= 0:
#             return render_template(
#                 "order_new.html",
#                 tailors=tailors,
#                 categories=categories,
#                 subcategories=subcategories,
#                 measurement_fields=measurement_fields,
#                 measurement_field_map=field_map,
#                 requirement_icons=requirement_icons,
#                 inventory=inventory,
#                 uoms=uoms,
#                 next_order_id=next_order_id,
#                 display_customer_id=display_customer_id,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 error="Total cost must be greater than 0.",
#                 prefill_name=name,
#                 prefill_phone=phone,
#                 prefill_address=address,
#             )

#         conn = get_db()
#         cur = conn.cursor()
#         cur.execute(
#             """
#             INSERT INTO orders (
#                 customer_id, customer_display_id, due_date, status, priority,
#                 assigned_team, assigned_tailor, notes,
#                 advance_amount, total_amount, order_type, order_material_source,
#                 inventory_applied, created_at
#             )
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """,
#             (
#                 customer_id,
#                 display_customer_id,
#                 due_date,
#                 status,
#                 priority,
#                 None,
#                 assigned_tailor,
#                 order_notes,
#                 advance_value,
#                 total_value,
#                 "Tailoring",
#                 "inventory" if material_source == "inventory" else "customer",
#                 1 if material_source == "inventory" else 0,
#                 now_str(),
#             ),
#         )
#         order_id = cur.lastrowid

#         for item_type, qty_value in order_item_rows:
#             cur.execute(
#                 "INSERT INTO order_items (order_id, item_type, qty, notes) VALUES (?, ?, ?, ?)",
#                 (order_id, item_type, qty_value, None),
#             )

#         if material_source == "inventory":
#             item_ids = request.form.getlist("material_item_id")
#             qty_values = request.form.getlist("material_qty")
#             price_values = request.form.getlist("material_price")
#             inv_rows = cur.execute(
#                 """
#                 SELECT inventory.id, inventory.name, inventory.qty, inventory.uom_id
#                 FROM inventory
#                 """
#             ).fetchall()
#             inv_map = {str(row["id"]): row for row in inv_rows}
#             had_item = False
#             for item_id, qty_raw, price_raw in zip(item_ids, qty_values, price_values, strict=False):
#                 if not item_id or item_id not in inv_map:
#                     continue
#                 try:
#                     qty = float(qty_raw)
#                     line_total = float(price_raw)
#                 except (TypeError, ValueError):
#                     continue
#                 if qty <= 0 or line_total < 0:
#                     continue
#                 inv_row = inv_map[item_id]
#                 unit_price = line_total / qty if qty else 0
#                 cur.execute(
#                     """
#                     INSERT INTO order_material_items
#                         (order_id, inventory_id, uom_id, qty, unit_price, line_total)
#                     VALUES (?, ?, ?, ?, ?, ?)
#                     """,
#                     (order_id, int(item_id), inv_row["uom_id"], qty, unit_price, line_total),
#                 )
#                 new_qty = max(float(inv_row["qty"] or 0) - qty, 0)
#                 cur.execute(
#                     "UPDATE inventory SET qty = ?, updated_at = ? WHERE id = ?",
#                     (new_qty, now_str(), int(item_id)),
#                 )
#                 had_item = True
#             if not had_item:
#                 conn.rollback()
#                 conn.close()
#                 return render_template(
#                     "order_new.html",
#                     tailors=tailors,
#                     categories=categories,
#                     subcategories=subcategories,
#                     measurement_fields=measurement_fields,
#                     measurement_field_map=field_map,
#                     requirement_icons=requirement_icons,
#                     inventory=inventory,
#                     uoms=uoms,
#                     next_order_id=next_order_id,
#                     display_customer_id=display_customer_id,
#                     today_date=today_date,
#                     worker_default=worker_default,
#                     delivery_default=delivery_default,
#                     error="Select at least one inventory item when using inventory materials.",
#                     prefill_name=name,
#                     prefill_phone=phone,
#                 )

#         files = request.files.getlist("order_images")
#         labels = request.form.getlist("image_labels")
#         item_types = request.form.getlist("image_item_types")
#         seen = set()
#         for i, file in enumerate(files):
#             if not file or not file.filename:
#                 continue
#             key = (file.filename, file.content_length)
#             if key in seen:
#                 continue
#             seen.add(key)
#             filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
#             filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
#             file.save(filepath)
#             label = labels[i] if i < len(labels) else ""
#             item_type = item_types[i] if i < len(item_types) else ""
#             cur.execute(
#                 "INSERT INTO order_images (order_id, filename, label, item_type) VALUES (?, ?, ?, ?)",
#                 (order_id, filename, label, item_type or None),
#             )

#         conn.commit()
#         conn.close()
#         return redirect(url_for("order_detail", order_id=order_id))

#     return render_template(
#         "order_new.html",
#         tailors=tailors,
#         categories=categories,
#         subcategories=subcategories,
#         measurement_fields=measurement_fields,
#         measurement_field_map=field_map,
#         requirement_icons=requirement_icons,
#         inventory=inventory,
#         uoms=uoms,
#         next_order_id=next_order_id,
#         display_customer_id=display_customer_id,
#         today_date=today_date,
#         worker_default=worker_default,
#         delivery_default=delivery_default,
#         prefill_name=prefill_name,
#         prefill_phone=prefill_phone,
#         prefill_address=prefill_address,
#     )

# @app.route("/orders/new", methods=["GET", "POST"])
# def order_new():
#     conn = get_db()
#     reseed_identity_if_empty(conn, "customers", seed=0)
#     tailors = conn.execute("SELECT * FROM tailors ORDER BY team, name").fetchall()
#     categories = conn.execute(
#         "SELECT * FROM categories ORDER BY sort_order, name"
#     ).fetchall()
#     subcategories = conn.execute(
#         "SELECT * FROM subcategories ORDER BY name"
#     ).fetchall()
#     measurement_fields = conn.execute(
#         "SELECT * FROM measurement_fields ORDER BY subcategory_id, sort_order, field_label"
#     ).fetchall()
#     requirement_icons = conn.execute(
#         "SELECT * FROM requirement_icons ORDER BY sort_order, name"
#     ).fetchall()
#     inventory = conn.execute(
#         """
#         SELECT inventory.id, inventory.inventory_code, inventory.name, inventory.qty,
#                inventory.selling_price, inventory.uom_id, uoms.name AS uom_name
#         FROM inventory
#         LEFT JOIN uoms ON uoms.id = inventory.uom_id
#         ORDER BY inventory.name ASC
#         """
#     ).fetchall()
#     uoms = conn.execute("SELECT * FROM uoms ORDER BY name").fetchall()
#     next_customer_display_id = conn.execute(
#         "SELECT COALESCE(MAX(id), 0) + 1 FROM customers"
#     ).fetchone()[0]
#     next_order_id = conn.execute(
#         "SELECT COALESCE(MAX(id), 0) + 1 FROM orders"
#     ).fetchone()[0]
#     next_order_code = generate_order_no(conn, "Tailoring")
#     now_dt = datetime.now()
#     order_date_offset_days = int(get_setting("order_date_offset_days", "0") or 0)
#     if order_date_offset_days:
#         now_dt = now_dt + timedelta(days=order_date_offset_days)
#     today_date = now_dt.strftime("%Y-%m-%d %H:%M")
#     base_date = now_dt.date()
#     worker_days = int(get_setting("worker_delivery_days", "0") or 0)
#     delivery_days = int(get_setting("delivery_days", "0") or 0)
#     worker_default = (base_date + timedelta(days=worker_days)).isoformat() if worker_days else ""
#     delivery_default = (base_date + timedelta(days=delivery_days)).isoformat() if delivery_days else ""
#     field_map = {}
#     for row in measurement_fields:
#         field_map.setdefault(str(row["subcategory_id"]), []).append(
#             {"key": row["field_key"], "label": row["field_label"]}
#         )
#     conn.close()

#     prefill_name = request.args.get("name", "").strip()
#     prefill_phone = request.args.get("phone", "").strip()
#     prefill_address = request.args.get("address", "").strip()
#     prefill_customer_id = request.args.get("customer_id", "").strip()
#     if prefill_customer_id.isdigit():
#         conn = get_db()
#         row = conn.execute(
#             "SELECT id, name, phone, address FROM customers WHERE id = ?",
#             (int(prefill_customer_id),),
#         ).fetchone()
#         conn.close()
#         if row:
#             prefill_name = row["name"] or prefill_name
#             prefill_phone = row["phone"] or prefill_phone
#             prefill_address = row["address"] or prefill_address
#             prefill_customer_id = str(row["id"])
#     display_customer_id = int(next_customer_display_id)

#     if request.method == "POST":
#         name = request.form.get("name", "").strip()
#         phone = request.form.get("phone", "").strip()
#         notes = request.form.get("customer_notes", "").strip()
#         address = request.form.get("address", "").strip()
#         material_source = request.form.get("material_source", "customer").strip().lower()
#         if not name or not phone:
#             return render_template(
#                 "order_new.html",
#                 tailors=tailors,
#                 categories=categories,
#                 subcategories=subcategories,
#                 measurement_fields=measurement_fields,
#                 measurement_field_map=field_map,
#                 requirement_icons=requirement_icons,
#                 inventory=inventory,
#                 uoms=uoms,
#                 next_order_id=next_order_id,
#                 next_order_code=next_order_code,
#                 display_customer_id=display_customer_id,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 error="Customer name and phone are required.",
#                 prefill_name=name,
#                 prefill_phone=phone,
#                 prefill_address=address,
#             )
#         if not is_valid_phone(phone):
#             return render_template(
#                 "order_new.html",
#                 tailors=tailors,
#                 categories=categories,
#                 subcategories=subcategories,
#                 measurement_fields=measurement_fields,
#                 measurement_field_map=field_map,
#                 requirement_icons=requirement_icons,
#                 inventory=inventory,
#                 uoms=uoms,
#                 next_order_id=next_order_id,
#                 next_order_code=next_order_code,
#                 display_customer_id=display_customer_id,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 error="Phone number can contain only digits and leading +.",
#                 prefill_name=name,
#                 prefill_phone=phone,
#                 prefill_address=address,
#             )
#         # Always resolve customer by phone first; reuse existing ID when matched.
#         customer_id = upsert_customer(name, phone, notes, address)

#         category_ids = request.form.getlist("measure_category_id")
#         subcategory_ids = request.form.getlist("measure_subcategory_id")
#         qty_values = request.form.getlist("measure_qty")
#         label_values = request.form.getlist("measure_label")
#         tailor_values = request.form.getlist("measure_assigned_tailor")
#         note_values = request.form.getlist("measure_notes")
#         requirement_values = request.form.getlist("measure_requirements")
#         known_fields = {
#             "neck",
#             "chest",
#             "waist",
#             "hip",
#             "shoulder",
#             "sleeve",
#             "length",
#             "cuff",
#             "inseam",
#             "outseam",
#             "thigh",
#             "knee",
#             "bottom",
#             "notes",
#         }
#         field_keys = [row["field_key"] for row in measurement_fields]
#         label_map = {row["field_key"]: row["field_label"] for row in measurement_fields}
#         subcategory_field_keys: dict[str, list[str]] = {}
#         for row in measurement_fields:
#             sub_key = str(row["subcategory_id"])
#             subcategory_field_keys.setdefault(sub_key, []).append(row["field_key"])
#         values_by_field = {
#             key: request.form.getlist(f"measure_{key}") for key in field_keys
#         }

#         map_conn = get_db()
#         cat_rows = map_conn.execute("SELECT id, name FROM categories").fetchall()
#         sub_rows = map_conn.execute("SELECT id, name FROM subcategories").fetchall()
#         category_map = {str(row["id"]): row["name"] for row in cat_rows}
#         subcategory_map = {str(row["id"]): row["name"] for row in sub_rows}

#         max_len = max(
#             len(category_ids),
#             len(subcategory_ids),
#             len(qty_values),
#             len(label_values),
#             len(tailor_values),
#             len(note_values),
#             len(requirement_values),
#             max((len(items) for items in values_by_field.values()), default=0),
#         )
#         pending_measurements: list[tuple[str, int, dict[str, str]]] = []
#         row_error = None
#         for idx in range(max_len):
#             category_id = category_ids[idx].strip() if idx < len(category_ids) else ""
#             subcategory_id = subcategory_ids[idx].strip() if idx < len(subcategory_ids) else ""
#             qty_raw = qty_values[idx].strip() if idx < len(qty_values) and qty_values[idx] else ""
#             note_raw = note_values[idx].strip() if idx < len(note_values) and note_values[idx] else ""
#             req_text_raw = requirement_values[idx].strip() if idx < len(requirement_values) and requirement_values[idx] else ""
#             tailor_name = tailor_values[idx].strip() if idx < len(tailor_values) and tailor_values[idx] else ""

#             has_measure_field_value = False
#             for items in values_by_field.values():
#                 if idx < len(items) and str(items[idx] or "").strip():
#                     has_measure_field_value = True
#                     break

#             has_row_input = any(
#                 [
#                     category_id,
#                     subcategory_id,
#                     note_raw,
#                     req_text_raw,
#                     tailor_name,
#                     has_measure_field_value,
#                     qty_raw and qty_raw != "1",
#                 ]
#             )
#             if not has_row_input:
#                 continue
#             if not category_id or not subcategory_id:
#                 row_error = (
#                     f"Measurement row {idx + 1} is incomplete. "
#                     "Select both Category and Sub category."
#                 )
#                 break

#             category_name = category_map.get(category_id, "Category")
#             subcategory_name = subcategory_map.get(subcategory_id, "")
#             kind = f"{category_name} - {subcategory_name}" if subcategory_name else category_name
#             if qty_raw.isdigit():
#                 qty_value = max(int(qty_raw), 1)
#             else:
#                 qty_value = 1

#             payload = {}
#             extra_lines = []
#             active_field_keys = subcategory_field_keys.get(subcategory_id, field_keys)
#             for field_key in active_field_keys:
#                 items = values_by_field.get(field_key, [])
#                 value = items[idx].strip() if idx < len(items) and items[idx] else ""
#                 if not value:
#                     continue
#                 if field_key in known_fields:
#                     payload[field_key] = value
#                 else:
#                     label = label_map.get(field_key, field_key)
#                     extra_lines.append(f"{label}: {value}")

#             base_note = note_raw
#             if req_text_raw:
#                 req_line = f"Requirements: {req_text_raw}"
#                 base_note = f"{req_line}\n{base_note}".strip() if base_note else req_line
#             if extra_lines:
#                 extra_text = "\n".join(extra_lines)
#                 base_note = f"{base_note}\n{extra_text}".strip() if base_note else extra_text
#             if base_note:
#                 payload["notes"] = base_note

#             if tailor_name:
#                 payload["assigned_tailor"] = tailor_name

#             label = label_values[idx].strip() if idx < len(label_values) and label_values[idx] else ""
#             if label:
#                 notes = payload.get("notes") or ""
#                 label_note = f"Label: {label}"
#                 payload["notes"] = f"{label_note}\n{notes}".strip()

#             pending_measurements.append((kind, qty_value, payload))

#         if row_error:
#             map_conn.close()
#             return render_template(
#                 "order_new.html",
#                 tailors=tailors,
#                 categories=categories,
#                 subcategories=subcategories,
#                 measurement_fields=measurement_fields,
#                 measurement_field_map=field_map,
#                 requirement_icons=requirement_icons,
#                 inventory=inventory,
#                 uoms=uoms,
#                 next_order_id=next_order_id,
#                 next_order_code=next_order_code,
#                 display_customer_id=display_customer_id,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 error=row_error,
#                 prefill_name=name,
#                 prefill_phone=phone,
#                 prefill_address=address,
#             )

#         if not pending_measurements:
#             map_conn.close()
#             return render_template(
#                 "order_new.html",
#                 tailors=tailors,
#                 categories=categories,
#                 subcategories=subcategories,
#                 measurement_fields=measurement_fields,
#                 measurement_field_map=field_map,
#                 requirement_icons=requirement_icons,
#                 inventory=inventory,
#                 uoms=uoms,
#                 next_order_id=next_order_id,
#                 next_order_code=next_order_code,
#                 display_customer_id=display_customer_id,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 error="Add at least one measurement row with Category and Sub category.",
#                 prefill_name=name,
#                 prefill_phone=phone,
#                 prefill_address=address,
#         )

#         map_conn.close()

#         due_date = request.form.get("due_date", "").strip() or None
#         priority = "Normal"
#         status = request.form.get("status", "In-Progress")
#         assigned_tailor = request.form.get("assigned_tailor", "").strip() or None
#         order_notes = request.form.get("order_notes", "").strip() or None
#         worker_delivery_date = request.form.get("worker_delivery_date", "").strip()
#         extra_date_lines = []
#         if worker_delivery_date:
#             extra_date_lines.append(f"Worker delivery date: {worker_delivery_date}")
#         if extra_date_lines:
#             date_text = "\n".join(extra_date_lines)
#             order_notes = f"{order_notes}\n{date_text}".strip() if order_notes else date_text
#         payment_method = request.form.get("payment_method", "Cash").strip()
#         allowed_payment_methods = {"Cash", "GPay", "Card"}
#         if payment_method not in allowed_payment_methods:
#             payment_method = "Cash"
#         payment_text = f"Payment method: {payment_method}"
#         order_notes = f"{payment_text}\n{order_notes}" if order_notes else payment_text
#         advance_amount = request.form.get("advance_amount", "").strip()
#         total_amount = request.form.get("total_amount", "").strip()
#         advance_value = float(advance_amount) if advance_amount else None
#         total_value = float(total_amount) if total_amount else None
#         if not total_value or total_value <= 0:
#             return render_template(
#                 "order_new.html",
#                 tailors=tailors,
#                 categories=categories,
#                 subcategories=subcategories,
#                 measurement_fields=measurement_fields,
#                 measurement_field_map=field_map,
#                 requirement_icons=requirement_icons,
#                 inventory=inventory,
#                 uoms=uoms,
#                 next_order_id=next_order_id,
#                 next_order_code=next_order_code,
#                 display_customer_id=display_customer_id,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 error="Total cost must be greater than 0.",
#                 prefill_name=name,
#                 prefill_phone=phone,
#                 prefill_address=address,
#             )

#         order_customer_display_id = customer_display_id(customer_id)
#         conn = get_db()
#         cur = conn.cursor()
#         order_no = generate_order_no(conn, "Tailoring")
#         cur.execute(
#             """
#             INSERT INTO orders (
#                 customer_id, customer_display_id, order_no, due_date, status, priority,
#                 assigned_team, assigned_tailor, notes,
#                 advance_amount, total_amount, order_type, order_material_source,
#                 inventory_applied, created_at
#             )
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """,
#             (
#                 customer_id,
#                 order_customer_display_id,
#                 order_no,
#                 due_date,
#                 status,
#                 priority,
#                 None,
#                 assigned_tailor,
#                 order_notes,
#                 advance_value,
#                 total_value,
#                 "Tailoring",
#                 "inventory" if material_source == "inventory" else "customer",
#                 1 if material_source == "inventory" else 0,
#                 now_str(),
#             ),
#         )
#         order_id = cur.lastrowid
#         if order_id is None:
#             conn.rollback()
#             conn.close()
#             return render_template(
#                 "order_new.html",
#                 tailors=tailors,
#                 categories=categories,
#                 subcategories=subcategories,
#                 measurement_fields=measurement_fields,
#                 measurement_field_map=field_map,
#                 requirement_icons=requirement_icons,
#                 inventory=inventory,
#                 uoms=uoms,
#                 next_order_id=next_order_id,
#                 next_order_code=next_order_code,
#                 display_customer_id=display_customer_id,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 error="Unable to save order. Please try again.",
#                 prefill_name=name,
#                 prefill_phone=phone,
#                 prefill_address=address,
#             )

#         for item_type, qty_value, payload in pending_measurements:
#             create_measurement(
#                 customer_id,
#                 item_type,
#                 payload,
#                 allow_empty=True,
#                 order_id=int(order_id),
#                 conn=conn,
#             )
#             cur.execute(
#                 "INSERT INTO order_items (order_id, item_type, qty, notes) VALUES (?, ?, ?, ?)",
#                 (order_id, item_type, qty_value, None),
#             )

#         if material_source == "inventory":
#             item_ids = request.form.getlist("material_item_id")
#             qty_values = request.form.getlist("material_qty")
#             price_values = request.form.getlist("material_price")
#             inv_rows = cur.execute(
#                 """
#                 SELECT inventory.id, inventory.name, inventory.qty, inventory.uom_id
#                 FROM inventory
#                 """
#             ).fetchall()
#             inv_map = {str(row["id"]): row for row in inv_rows}
#             had_item = False
#             for item_id, qty_raw, price_raw in zip(item_ids, qty_values, price_values, strict=False):
#                 if not item_id or item_id not in inv_map:
#                     continue
#                 try:
#                     qty = float(qty_raw)
#                     line_total = float(price_raw)
#                 except (TypeError, ValueError):
#                     continue
#                 if qty <= 0:
#                     continue
#                 inv_row = inv_map[item_id]
#                 cur.execute(
#                     """
#                     INSERT INTO order_material_items
#                         (order_id, inventory_id, uom_id, qty, unit_price, line_total)
#                     VALUES (?, ?, ?, ?, ?, ?)
#                     """,
#                     (
#                         order_id,
#                         int(item_id),
#                         inv_row["uom_id"],
#                         qty,
#                         line_total / qty if qty else 0,
#                         line_total,
#                     ),
#                 )
#                 new_qty = max(float(inv_row["qty"] or 0) - qty, 0)
#                 cur.execute(
#                     "UPDATE inventory SET qty = ?, updated_at = ? WHERE id = ?",
#                     (new_qty, now_str(), int(item_id)),
#                 )
#                 had_item = True
#             if not had_item:
#                 conn.rollback()
#                 conn.close()
#                 return render_template(
#                     "order_new.html",
#                     tailors=tailors,
#                     categories=categories,
#                     subcategories=subcategories,
#                     measurement_fields=measurement_fields,
#                     measurement_field_map=field_map,
#                     requirement_icons=requirement_icons,
#                     inventory=inventory,
#                     uoms=uoms,
#                     next_order_id=next_order_id,
#                     next_order_code=next_order_code,
#                     display_customer_id=display_customer_id,
#                     today_date=today_date,
#                     worker_default=worker_default,
#                     delivery_default=delivery_default,
#                     error="Add at least one valid inventory material row.",
#                     prefill_name=name,
#                     prefill_phone=phone,
#                     prefill_address=address,
#                 )

#         files = request.files.getlist("order_images")
#         image_item_types = request.form.getlist("image_item_types")
#         image_labels = request.form.getlist("image_labels")
#         for idx, file in enumerate(files):
#             if not file or not file.filename:
#                 continue
#             filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
#             file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
#             item_type = image_item_types[idx].strip() if idx < len(image_item_types) else ""
#             label = image_labels[idx].strip() if idx < len(image_labels) else ""
#             cur.execute(
#                 "INSERT INTO order_images (order_id, item_type, label, filename) VALUES (?, ?, ?, ?)",
#                 (order_id, item_type or None, label or None, filename),
#             )

#         conn.commit()
#         conn.close()
#         return redirect(url_for("order_detail", order_id=order_id))

#     return render_template(
#         "order_new.html",
#         tailors=tailors,
#         categories=categories,
#         subcategories=subcategories,
#         measurement_fields=measurement_fields,
#         measurement_field_map=field_map,
#         requirement_icons=requirement_icons,
#         inventory=inventory,
#         uoms=uoms,
#         next_order_id=next_order_id,
#         next_order_code=next_order_code,
#         display_customer_id=display_customer_id,
#         today_date=today_date,
#         worker_default=worker_default,
#         delivery_default=delivery_default,
#         prefill_name=prefill_name,
#         prefill_phone=prefill_phone,
#         prefill_address=prefill_address,
#         prefill_customer_id=prefill_customer_id,
#     )


@app.route("/orders/new", methods=["GET", "POST"])
def order_new():
    conn = get_db()
    reseed_identity_if_empty(conn, "customers", seed=0)
    tailors = conn.execute("SELECT * FROM tailors ORDER BY team, name").fetchall()
    categories = conn.execute(
        "SELECT * FROM categories ORDER BY sort_order, name"
    ).fetchall()
    subcategories = conn.execute(
        "SELECT * FROM subcategories ORDER BY name"
    ).fetchall()
    measurement_fields = conn.execute(
        "SELECT * FROM measurement_fields ORDER BY subcategory_id, sort_order, field_label"
    ).fetchall()
    requirement_icons = conn.execute(
        "SELECT * FROM requirement_icons ORDER BY sort_order, name"
    ).fetchall()
    inventory = conn.execute(
        """
        SELECT inventory.id, inventory.inventory_code, inventory.name, inventory.qty,
               inventory.selling_price, inventory.uom_id, uoms.name AS uom_name
        FROM inventory
        LEFT JOIN uoms ON uoms.id = inventory.uom_id
        ORDER BY inventory.name ASC
        """
    ).fetchall()
    uoms = conn.execute("SELECT * FROM uoms ORDER BY name").fetchall()
    next_customer_display_id = conn.execute(
        "SELECT COALESCE(MAX(id), 0) + 1 FROM customers"
    ).fetchone()[0]
    next_order_id = conn.execute(
        "SELECT COALESCE(MAX(id), 0) + 1 FROM orders"
    ).fetchone()[0]
    next_invoice_id = generate_invoice_id(conn)
    # next_order_code = generate_order_no(conn, "Tailoring")
    next_order_code = "Will generate after customer selected"
    now_dt = datetime.now()
    order_date_offset_days = int(get_setting("order_date_offset_days", "0") or 0)
    if order_date_offset_days:
        now_dt = now_dt + timedelta(days=order_date_offset_days)
    today_date = now_dt.strftime("%Y-%m-%d %H:%M")
    base_date = now_dt.date()
    worker_days = int(get_setting("worker_delivery_days", "0") or 0)
    delivery_days = int(get_setting("delivery_days", "0") or 0)
    worker_default = (base_date + timedelta(days=worker_days)).isoformat() if worker_days else ""
    delivery_default = (base_date + timedelta(days=delivery_days)).isoformat() if delivery_days else ""
    field_map: dict[str, dict[str, str]] = {}
    for row in measurement_fields:
        sub_key = str(row["subcategory_id"])
        f_key = str(row["field_key"] or "").strip()
        f_label = str(row["field_label"] or "").strip()
        if not f_key:
            continue
        field_map.setdefault(sub_key, {})[f_key] = f_label
    conn.close()

    prefill_name = request.args.get("name", "").strip()
    prefill_phone = request.args.get("phone", "").strip()
    prefill_address = request.args.get("address", "").strip()
    prefill_customer_id = request.args.get("customer_id", "").strip()
    if prefill_customer_id.isdigit():
        conn = get_db()
        row = conn.execute(
            "SELECT id, name, phone, address FROM customers WHERE id = ?",
            (int(prefill_customer_id),),
        ).fetchone()
        conn.close()
        if row:
            prefill_name = row["name"] or prefill_name
            prefill_phone = row["phone"] or prefill_phone
            prefill_address = row["address"] or prefill_address
            prefill_customer_id = str(row["id"])
    display_customer_id = int(next_customer_display_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        notes = request.form.get("customer_notes", "").strip()
        address = request.form.get("address", "").strip()
        material_source = request.form.get("material_source", "customer").strip().lower()
        if not name or not phone:
            return render_template(
                "order_new.html",
                tailors=tailors,
                categories=categories,
                subcategories=subcategories,
                measurement_fields=measurement_fields,
                measurement_field_map=field_map,
                requirement_icons=requirement_icons,
                inventory=inventory,
                uoms=uoms,
                next_order_id=next_order_id,
                next_order_code=next_order_code,
                next_invoice_id=next_invoice_id,
                display_customer_id=display_customer_id,
                today_date=today_date,
                worker_default=worker_default,
                delivery_default=delivery_default,
                error="Customer name and phone are required.",
                prefill_name=name,
                prefill_phone=phone,
                prefill_address=address,
            )
        if not is_valid_phone(phone):
            return render_template(
                "order_new.html",
                tailors=tailors,
                categories=categories,
                subcategories=subcategories,
                measurement_fields=measurement_fields,
                measurement_field_map=field_map,
                requirement_icons=requirement_icons,
                inventory=inventory,
                uoms=uoms,
                next_order_id=next_order_id,
                next_order_code=next_order_code,
                next_invoice_id=next_invoice_id,
                display_customer_id=display_customer_id,
                today_date=today_date,
                worker_default=worker_default,
                delivery_default=delivery_default,
                error="Phone number can contain only digits and leading +.",
                prefill_name=name,
                prefill_phone=phone,
                prefill_address=address,
            )
        # Always resolve customer by phone first; reuse existing ID when matched.
        customer_id = upsert_customer(name, phone, notes, address)

        category_ids = request.form.getlist("measure_category_id")
        subcategory_ids = request.form.getlist("measure_subcategory_id")
        qty_values = request.form.getlist("measure_qty")
        label_values = request.form.getlist("measure_label")
        tailor_values = request.form.getlist("measure_assigned_tailor")
        note_values = request.form.getlist("measure_notes")
        requirement_values = request.form.getlist("measure_requirements")
        measure_completed_dates = request.form.getlist("measure_completed_date")
        measure_delivery_dates = request.form.getlist("measure_delivery_date")
        known_fields = {
            "neck",
            "chest",
            "waist",
            "hip",
            "shoulder",
            "sleeve",
            "length",
            "cuff",
            "inseam",
            "outseam",
            "thigh",
            "knee",
            "bottom",
            "notes",
        }
        field_keys = [row["field_key"] for row in measurement_fields]
        label_map = {row["field_key"]: row["field_label"] for row in measurement_fields}
        subcategory_field_keys: dict[str, list[str]] = {}
        for row in measurement_fields:
            sub_key = str(row["subcategory_id"])
            subcategory_field_keys.setdefault(sub_key, []).append(row["field_key"])
        values_by_field = {
            key: request.form.getlist(f"measure_{key}") for key in field_keys
        }

        map_conn = get_db()
        cat_rows = map_conn.execute("SELECT id, name FROM categories").fetchall()
        sub_rows = map_conn.execute("SELECT id, name FROM subcategories").fetchall()
        category_map = {str(row["id"]): row["name"] for row in cat_rows}
        subcategory_map = {str(row["id"]): row["name"] for row in sub_rows}

        max_len = max(
            len(category_ids),
            len(subcategory_ids),
            len(qty_values),
            len(label_values),
            len(tailor_values),
            len(note_values),
            len(requirement_values),
            len(measure_completed_dates),
            len(measure_delivery_dates),
            max((len(items) for items in values_by_field.values()), default=0),
        )
        pending_measurements: list[tuple[str, int, dict[str, str]]] = []
        row_error = None
        for idx in range(max_len):
            category_id = category_ids[idx].strip() if idx < len(category_ids) else ""
            subcategory_id = subcategory_ids[idx].strip() if idx < len(subcategory_ids) else ""
            qty_raw = qty_values[idx].strip() if idx < len(qty_values) and qty_values[idx] else ""
            note_raw = note_values[idx].strip() if idx < len(note_values) and note_values[idx] else ""
            req_text_raw = requirement_values[idx].strip() if idx < len(requirement_values) and requirement_values[idx] else ""
            completed_date_raw = (
                measure_completed_dates[idx].strip()
                if idx < len(measure_completed_dates) and measure_completed_dates[idx]
                else ""
            )
            delivery_date_raw = (
                measure_delivery_dates[idx].strip()
                if idx < len(measure_delivery_dates) and measure_delivery_dates[idx]
                else ""
            )
            tailor_name = tailor_values[idx].strip() if idx < len(tailor_values) and tailor_values[idx] else ""

            has_measure_field_value = False
            for items in values_by_field.values():
                if idx < len(items) and str(items[idx] or "").strip():
                    has_measure_field_value = True
                    break

            has_row_input = any(
                [
                    category_id,
                    subcategory_id,
                    note_raw,
                    req_text_raw,
                    completed_date_raw,
                    delivery_date_raw,
                    tailor_name,
                    has_measure_field_value,
                    qty_raw and qty_raw != "1",
                ]
            )
            if not has_row_input:
                continue
            if not category_id or not subcategory_id:
                row_error = (
                    f"Measurement row {idx + 1} is incomplete. "
                    "Select both Category and Sub category."
                )
                break

            category_name = category_map.get(category_id, "Category")
            subcategory_name = subcategory_map.get(subcategory_id, "")
            kind = f"{category_name} - {subcategory_name}" if subcategory_name else category_name
            if qty_raw.isdigit():
                qty_value = max(int(qty_raw), 1)
            else:
                qty_value = 1

            payload = {}
            extra_lines = []
            active_field_keys = subcategory_field_keys.get(subcategory_id, field_keys)
            for field_key in active_field_keys:
                items = values_by_field.get(field_key, [])
                value = items[idx].strip() if idx < len(items) and items[idx] else ""
                if not value:
                    continue
                if field_key in known_fields:
                    payload[field_key] = value
                else:
                    label = label_map.get(field_key, field_key)
                    extra_lines.append(f"{label}: {value}")

            base_note = note_raw
            if req_text_raw:
                req_line = f"Requirements: {req_text_raw}"
                base_note = f"{req_line}\n{base_note}".strip() if base_note else req_line
            if completed_date_raw:
                completed_line = f"Completed date: {completed_date_raw}"
                base_note = f"{completed_line}\n{base_note}".strip() if base_note else completed_line
            if delivery_date_raw:
                delivery_line = f"Delivery date: {delivery_date_raw}"
                base_note = f"{delivery_line}\n{base_note}".strip() if base_note else delivery_line
            if extra_lines:
                extra_text = "\n".join(extra_lines)
                base_note = f"{base_note}\n{extra_text}".strip() if base_note else extra_text
            if base_note:
                payload["notes"] = base_note

            if tailor_name:
                payload["assigned_tailor"] = tailor_name

            label = label_values[idx].strip() if idx < len(label_values) and label_values[idx] else ""
            if label:
                notes = payload.get("notes") or ""
                label_note = f"Label: {label}"
                payload["notes"] = f"{label_note}\n{notes}".strip()

            pending_measurements.append((kind, qty_value, payload))

        if row_error:
            map_conn.close()
            return render_template(
                "order_new.html",
                tailors=tailors,
                categories=categories,
                subcategories=subcategories,
                measurement_fields=measurement_fields,
                measurement_field_map=field_map,
                requirement_icons=requirement_icons,
                inventory=inventory,
                uoms=uoms,
                next_order_id=next_order_id,
                next_order_code=next_order_code,
                next_invoice_id=next_invoice_id,
                display_customer_id=display_customer_id,
                today_date=today_date,
                worker_default=worker_default,
                delivery_default=delivery_default,
                error=row_error,
                prefill_name=name,
                prefill_phone=phone,
                prefill_address=address,
            )

        if not pending_measurements:
            map_conn.close()
            return render_template(
                "order_new.html",
                tailors=tailors,
                categories=categories,
                subcategories=subcategories,
                measurement_fields=measurement_fields,
                measurement_field_map=field_map,
                requirement_icons=requirement_icons,
                inventory=inventory,
                uoms=uoms,
                next_order_id=next_order_id,
                next_order_code=next_order_code,
                next_invoice_id=next_invoice_id,
                display_customer_id=display_customer_id,
                today_date=today_date,
                worker_default=worker_default,
                delivery_default=delivery_default,
                error="Add at least one measurement row with Category and Sub category.",
                prefill_name=name,
                prefill_phone=phone,
                prefill_address=address,
        )

        map_conn.close()

        due_date = request.form.get("due_date", "").strip() or None
        priority = "Normal"
        status = request.form.get("status", "In-Progress")
        assigned_tailor = request.form.get("assigned_tailor", "").strip() or None
        order_notes = request.form.get("order_notes", "").strip() or None
        worker_delivery_date = request.form.get("worker_delivery_date", "").strip()
        extra_date_lines = []
        if worker_delivery_date:
            extra_date_lines.append(f"Worker delivery date: {worker_delivery_date}")
        if extra_date_lines:
            date_text = "\n".join(extra_date_lines)
            order_notes = f"{order_notes}\n{date_text}".strip() if order_notes else date_text
        payment_method = request.form.get("payment_method", "Cash").strip()
        allowed_payment_methods = {"Cash", "GPay", "Card"}
        if payment_method not in allowed_payment_methods:
            payment_method = "Cash"
        payment_text = f"Payment method: {payment_method}"
        order_notes = f"{payment_text}\n{order_notes}" if order_notes else payment_text
        advance_amount = request.form.get("advance_amount", "").strip()
        total_amount = request.form.get("total_amount", "").strip()
        advance_value = float(advance_amount) if advance_amount else None
        total_value = float(total_amount) if total_amount else None
        if not total_value or total_value <= 0:
            return render_template(
                "order_new.html",
                tailors=tailors,
                categories=categories,
                subcategories=subcategories,
                measurement_fields=measurement_fields,
                measurement_field_map=field_map,
                requirement_icons=requirement_icons,
                inventory=inventory,
                uoms=uoms,
                next_order_id=next_order_id,
                next_order_code=next_order_code,
                next_invoice_id=next_invoice_id,
                display_customer_id=display_customer_id,
                today_date=today_date,
                worker_default=worker_default,
                delivery_default=delivery_default,
                error="Total cost must be greater than 0.",
                prefill_name=name,
                prefill_phone=phone,
                prefill_address=address,
            )
        gst_enabled = is_gst_enabled_for_order_type("Tailoring")
        tax_payload = parse_order_tax_payload(request.form, total_value)
        tax_payload = apply_gst_toggle_to_tax_payload(tax_payload, total_value, gst_enabled)
        discount_amount = parse_order_discount_amount(request.form, tax_payload["taxable_amount"])

        order_customer_display_id = customer_display_id(customer_id)
        conn = get_db()
        cur = conn.cursor()
        # order_no = generate_order_no(conn, "Tailoring")
        order_no = generate_order_no(conn, customer_id)
        invoice_id = (request.form.get("invoice_id") or "").strip() or generate_invoice_id(conn)
        cur.execute(
            """
            INSERT INTO orders (
                customer_id, customer_display_id, order_no, invoice_id, due_date, status, priority,
                assigned_team, assigned_tailor, notes,
                advance_amount, discount_amount, total_amount, taxable_amount, gst_percent, gst_amount,
                cgst_percent, cgst_amount, sgst_percent, sgst_amount,
                order_type, order_material_source,
                inventory_applied, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_id,
                order_customer_display_id,
                order_no,
                invoice_id,
                due_date,
                status,
                priority,
                None,
                assigned_tailor,
                order_notes,
                advance_value,
                discount_amount,
                total_value,
                tax_payload["taxable_amount"],
                tax_payload["gst_percent"],
                tax_payload["gst_amount"],
                tax_payload["cgst_percent"],
                tax_payload["cgst_amount"],
                tax_payload["sgst_percent"],
                tax_payload["sgst_amount"],
                "Tailoring",
                "inventory" if material_source == "inventory" else "customer",
                1 if material_source == "inventory" else 0,
                now_str(),
            ),
        )
        order_id = cur.lastrowid
        if order_id is None:
            conn.rollback()
            conn.close()
            return render_template(
                "order_new.html",
                tailors=tailors,
                categories=categories,
                subcategories=subcategories,
                measurement_fields=measurement_fields,
                measurement_field_map=field_map,
                requirement_icons=requirement_icons,
                inventory=inventory,
                uoms=uoms,
                next_order_id=next_order_id,
                next_order_code=next_order_code,
                next_invoice_id=next_invoice_id,
                display_customer_id=display_customer_id,
                today_date=today_date,
                worker_default=worker_default,
                delivery_default=delivery_default,
                error="Unable to save order. Please try again.",
                prefill_name=name,
                prefill_phone=phone,
                prefill_address=address,
            )

        for item_type, qty_value, payload in pending_measurements:
            create_measurement(
                customer_id,
                item_type,
                payload,
                allow_empty=True,
                order_id=int(order_id),
                conn=conn,
            )
            cur.execute(
                "INSERT INTO order_items (order_id, item_type, qty, notes) VALUES (?, ?, ?, ?)",
                (order_id, item_type, qty_value, None),
            )

        if material_source == "inventory":
            item_ids = request.form.getlist("material_item_id")
            qty_values = request.form.getlist("material_qty")
            price_values = request.form.getlist("material_price")
            inv_rows = cur.execute(
                """
                SELECT inventory.id, inventory.name, inventory.qty, inventory.uom_id
                FROM inventory
                """
            ).fetchall()
            inv_map = {str(row["id"]): row for row in inv_rows}
            had_item = False
            for item_id, qty_raw, price_raw in zip(item_ids, qty_values, price_values, strict=False):
                if not item_id or item_id not in inv_map:
                    continue
                try:
                    qty = float(qty_raw)
                    line_total = float(price_raw)
                except (TypeError, ValueError):
                    continue
                if qty <= 0:
                    continue
                inv_row = inv_map[item_id]
                cur.execute(
                    """
                    INSERT INTO order_material_items
                        (order_id, inventory_id, uom_id, qty, unit_price, line_total)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_id,
                        int(item_id),
                        inv_row["uom_id"],
                        qty,
                        line_total / qty if qty else 0,
                        line_total,
                    ),
                )
                new_qty = max(float(inv_row["qty"] or 0) - qty, 0)
                cur.execute(
                    "UPDATE inventory SET qty = ?, updated_at = ? WHERE id = ?",
                    (new_qty, now_str(), int(item_id)),
                )
                had_item = True
            if not had_item:
                conn.rollback()
                conn.close()
                return render_template(
                    "order_new.html",
                    tailors=tailors,
                    categories=categories,
                    subcategories=subcategories,
                    measurement_fields=measurement_fields,
                    measurement_field_map=field_map,
                    requirement_icons=requirement_icons,
                    inventory=inventory,
                    uoms=uoms,
                    next_order_id=next_order_id,
                    next_order_code=next_order_code,
                    next_invoice_id=next_invoice_id,
                    display_customer_id=display_customer_id,
                    today_date=today_date,
                    worker_default=worker_default,
                    delivery_default=delivery_default,
                    error="Add at least one valid inventory material row.",
                    prefill_name=name,
                    prefill_phone=phone,
                    prefill_address=address,
                )

        files = request.files.getlist("order_images")
        image_item_types = request.form.getlist("image_item_types")
        image_labels = request.form.getlist("image_labels")
        for idx, file in enumerate(files):
            if not file or not file.filename:
                continue
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            item_type = image_item_types[idx].strip() if idx < len(image_item_types) else ""
            label = image_labels[idx].strip() if idx < len(image_labels) else ""
            cur.execute(
                "INSERT INTO order_images (order_id, item_type, label, filename) VALUES (?, ?, ?, ?)",
                (order_id, item_type or None, label or None, filename),
            )

        customer_images = request.files.getlist("customer_images")
        for customer_file in customer_images:
            if not customer_file or not customer_file.filename:
                continue
            filename = f"{uuid.uuid4().hex}_{secure_filename(customer_file.filename)}"
            customer_file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            cur.execute(
                "INSERT INTO order_images (order_id, item_type, label, filename) VALUES (?, ?, ?, ?)",
                (order_id, "Customer", "Customer", filename),
            )

        conn.commit()
        conn.close()
        return redirect(url_for("order_detail", order_id=order_id))

    return render_template(
        "order_new.html",
        tailors=tailors,
        categories=categories,
        subcategories=subcategories,
        measurement_fields=measurement_fields,
        measurement_field_map=field_map,
        requirement_icons=requirement_icons,
        inventory=inventory,
        uoms=uoms,
        next_order_id=next_order_id,
        next_order_code=next_order_code,
        next_invoice_id=next_invoice_id,
        display_customer_id=display_customer_id,
        today_date=today_date,
        worker_default=worker_default,
        delivery_default=delivery_default,
        prefill_name=prefill_name,
        prefill_phone=prefill_phone,
        prefill_address=prefill_address,
        prefill_customer_id=prefill_customer_id,
    )
    
# @app.route("/orders/new/alteration", methods=["GET", "POST"])
# def order_new_alteration():
#     conn = get_db()
#     reseed_identity_if_empty(conn, "customers", seed=0)
#     next_order_id = conn.execute(
#         "SELECT COALESCE(MAX(id), 0) + 1 FROM orders"
#     ).fetchone()[0]
#     next_order_code = generate_order_no(conn, "Alteration")
#     next_customer_display_id = conn.execute(
#         "SELECT COALESCE(MAX(id), 0) + 1 FROM customers"
#     ).fetchone()[0]
#     now_dt = datetime.now()
#     order_date_offset_days = int(get_setting("order_date_offset_days", "0") or 0)
#     if order_date_offset_days:
#         now_dt = now_dt + timedelta(days=order_date_offset_days)
#     today_date = now_dt.strftime("%Y-%m-%d %H:%M")
#     base_date = now_dt.date()
#     worker_days = int(get_setting("worker_delivery_days", "0") or 0)
#     delivery_days = int(get_setting("delivery_days", "0") or 0)
#     worker_default = (base_date + timedelta(days=worker_days)).isoformat() if worker_days else ""
#     delivery_default = (base_date + timedelta(days=delivery_days)).isoformat() if delivery_days else ""

#     customer_id_param = request.args.get("customer_id", "").strip()
#     prefill_customer_id = None
#     prefill_name = ""
#     prefill_phone = ""
#     prefill_address = ""
#     prefill_notes = ""

#     if customer_id_param.isdigit():
#         prefill_customer_id = int(customer_id_param)
#         row = conn.execute(
#             "SELECT id, name, phone, address, notes FROM customers WHERE id = ?",
#             (prefill_customer_id,),
#         ).fetchone()
#         if row:
#             prefill_name = row["name"]
#             prefill_phone = row["phone"]
#             prefill_address = row["address"]
#             prefill_notes = row["notes"]
#     display_customer_id = int(next_customer_display_id)
#     conn.close()

#     if request.method == "POST":
#         name = request.form.get("name", "").strip()
#         phone = request.form.get("phone", "").strip()
#         notes = request.form.get("customer_notes", "").strip()
#         address = request.form.get("address", "").strip()
#         if not name or not phone:
#             return render_template(
#                 "order_new_alteration.html",
#                 next_order_id=next_order_id,
#                 next_order_code=next_order_code,
#                 display_customer_id=display_customer_id,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 prefill_customer_id=prefill_customer_id,
#                 prefill_name=name,
#                 prefill_phone=phone,
#                 prefill_address=address,
#                 prefill_notes=notes,
#                 error="Customer name and phone are required.",
#             )
#         if not is_valid_phone(phone):
#             return render_template(
#                 "order_new_alteration.html",
#                 next_order_id=next_order_id,
#                 next_order_code=next_order_code,
#                 display_customer_id=display_customer_id,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 prefill_customer_id=prefill_customer_id,
#                 prefill_name=name,
#                 prefill_phone=phone,
#                 prefill_address=address,
#                 prefill_notes=notes,
#                 error="Phone number can contain only digits and leading +.",
#             )

#         # Always resolve customer by phone first; reuse existing ID when matched.
#         customer_id = upsert_customer(name, phone, notes, address)
#         order_notes = request.form.get("order_notes", "").strip() or None
#         if not order_notes:
#             order_notes = request.form.get("customer_notes", "").strip() or None
#         payment_method = request.form.get("payment_method", "Cash").strip()
#         allowed_payment_methods = {"Cash", "GPay", "Card"}
#         if payment_method not in allowed_payment_methods:
#             payment_method = "Cash"
#         payment_text = f"Payment method: {payment_method}"
#         order_notes = f"{payment_text}\n{order_notes}" if order_notes else payment_text
#         due_date = None
#         advance_amount = request.form.get("advance_amount", "").strip()
#         total_amount = request.form.get("total_amount", "").strip()
#         advance_value = float(advance_amount) if advance_amount else None
#         total_value = float(total_amount) if total_amount else None
#         if not total_value or total_value <= 0:
#             return render_template(
#                 "order_new_alteration.html",
#                 next_order_id=next_order_id,
#                 next_order_code=next_order_code,
#                 display_customer_id=display_customer_id,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 prefill_customer_id=prefill_customer_id,
#                 prefill_name=prefill_name,
#                 prefill_phone=prefill_phone,
#                 prefill_address=prefill_address,
#                 prefill_notes=prefill_notes,
#                 error="Total cost must be greater than 0.",
#             )

#         order_customer_display_id = customer_display_id(customer_id)
#         conn = get_db()
#         cur = conn.cursor()
#         order_no = generate_order_no(conn, "Alteration")
#         cur.execute(
#             """
#             INSERT INTO orders (
#                 customer_id, customer_display_id, order_no, due_date, status, priority,
#                 assigned_team, assigned_tailor, notes,
#                 advance_amount, total_amount, order_type, order_material_source,
#                 inventory_applied, created_at
#             )
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """,
#             (
#                 customer_id,
#                 order_customer_display_id,
#                 order_no,
#                 due_date,
#                 "Delivered",
#                 "Normal",
#                 None,
#                 None,
#                 order_notes,
#                 advance_value,
#                 total_value,
#                 "Alteration",
#                 "customer",
#                 0,
#                 now_str(),
#             ),
#         )
#         order_id = cur.lastrowid
#         if order_id is None:
#             conn.rollback()
#             conn.close()
#             return render_template(
#                 "order_new_alteration.html",
#                 next_order_id=next_order_id,
#                 next_order_code=next_order_code,
#                 display_customer_id=display_customer_id,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 prefill_customer_id=prefill_customer_id,
#                 prefill_name=prefill_name,
#                 prefill_phone=prefill_phone,
#                 prefill_address=prefill_address,
#                 prefill_notes=prefill_notes,
#                 error="Unable to save order. Please try again.",
#             )
#         conn.commit()
#         conn.close()
#         return redirect(url_for("order_detail", order_id=order_id))

#     return render_template(
#         "order_new_alteration.html",
#         next_order_id=next_order_id,
#         next_order_code=next_order_code,
#         display_customer_id=display_customer_id,
#         today_date=today_date,
#         worker_default=worker_default,
#         delivery_default=delivery_default,
#         prefill_customer_id=prefill_customer_id,
#         prefill_name=prefill_name,
#         prefill_phone=prefill_phone,
#         prefill_address=prefill_address,
#         prefill_notes=prefill_notes,
#     )


@app.route("/orders/new/alteration", methods=["GET", "POST"])
def order_new_alteration():
    conn = get_db()
    reseed_identity_if_empty(conn, "customers", seed=0)
    next_order_id = conn.execute(
        "SELECT COALESCE(MAX(id), 0) + 1 FROM orders"
    ).fetchone()[0]
    # next_order_code = generate_order_no(conn, "Alteration")
    next_order_code = "Will generate after customer selected"
    next_customer_display_id = conn.execute(
        "SELECT COALESCE(MAX(id), 0) + 1 FROM customers"
    ).fetchone()[0]
    now_dt = datetime.now()
    order_date_offset_days = int(get_setting("order_date_offset_days", "0") or 0)
    if order_date_offset_days:
        now_dt = now_dt + timedelta(days=order_date_offset_days)
    today_date = now_dt.strftime("%Y-%m-%d %H:%M")
    base_date = now_dt.date()
    worker_days = int(get_setting("worker_delivery_days", "0") or 0)
    delivery_days = int(get_setting("delivery_days", "0") or 0)
    worker_default = (base_date + timedelta(days=worker_days)).isoformat() if worker_days else ""
    delivery_default = (base_date + timedelta(days=delivery_days)).isoformat() if delivery_days else ""

    customer_id_param = request.args.get("customer_id", "").strip()
    prefill_customer_id = None
    prefill_name = ""
    prefill_phone = ""
    prefill_address = ""
    prefill_notes = ""

    if customer_id_param.isdigit():
        prefill_customer_id = int(customer_id_param)
        row = conn.execute(
            "SELECT id, name, phone, address, notes FROM customers WHERE id = ?",
            (prefill_customer_id,),
        ).fetchone()
        if row:
            prefill_name = row["name"]
            prefill_phone = row["phone"]
            prefill_address = row["address"]
            prefill_notes = row["notes"]
    display_customer_id = int(next_customer_display_id)
    conn.close()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        notes = request.form.get("customer_notes", "").strip()
        address = request.form.get("address", "").strip()
        if not name or not phone:
            return render_template(
                "order_new_alteration.html",
                next_order_id=next_order_id,
                next_order_code=next_order_code,
                display_customer_id=display_customer_id,
                today_date=today_date,
                worker_default=worker_default,
                delivery_default=delivery_default,
                prefill_customer_id=prefill_customer_id,
                prefill_name=name,
                prefill_phone=phone,
                prefill_address=address,
                prefill_notes=notes,
                error="Customer name and phone are required.",
            )
        if not is_valid_phone(phone):
            return render_template(
                "order_new_alteration.html",
                    next_order_id=next_order_id,
                    next_order_code=next_order_code,
                    display_customer_id=display_customer_id,
                today_date=today_date,
                worker_default=worker_default,
                delivery_default=delivery_default,
                prefill_customer_id=prefill_customer_id,
                prefill_name=name,
                prefill_phone=phone,
                prefill_address=address,
                prefill_notes=notes,
                error="Phone number can contain only digits and leading +.",
            )

        # Always resolve customer by phone first; reuse existing ID when matched.
        customer_id = upsert_customer(name, phone, notes, address)
        order_notes = request.form.get("order_notes", "").strip() or None
        if not order_notes:
            order_notes = request.form.get("customer_notes", "").strip() or None
        payment_method = request.form.get("payment_method", "Cash").strip()
        allowed_payment_methods = {"Cash", "GPay", "Card"}
        if payment_method not in allowed_payment_methods:
            payment_method = "Cash"
        payment_text = f"Payment method: {payment_method}"
        order_notes = f"{payment_text}\n{order_notes}" if order_notes else payment_text
        due_date = None
        advance_amount = request.form.get("advance_amount", "").strip()
        total_amount = request.form.get("total_amount", "").strip()
        advance_value = float(advance_amount) if advance_amount else None
        total_value = float(total_amount) if total_amount else None
        if not total_value or total_value <= 0:
            return render_template(
                "order_new_alteration.html",
                next_order_id=next_order_id,
                next_order_code=next_order_code,
                display_customer_id=display_customer_id,
                today_date=today_date,
                worker_default=worker_default,
                delivery_default=delivery_default,
                prefill_customer_id=prefill_customer_id,
                prefill_name=prefill_name,
                prefill_phone=prefill_phone,
                prefill_address=prefill_address,
                prefill_notes=prefill_notes,
                error="Total cost must be greater than 0.",
            )
        gst_enabled = is_gst_enabled_for_order_type("Alteration")
        tax_payload = parse_order_tax_payload(request.form, total_value)
        tax_payload = apply_gst_toggle_to_tax_payload(tax_payload, total_value, gst_enabled)
        discount_amount = parse_order_discount_amount(request.form, tax_payload["taxable_amount"])

        order_customer_display_id = customer_display_id(customer_id)
        conn = get_db()
        cur = conn.cursor()
        # order_no = generate_order_no(conn, "Alteration")
        order_no = generate_order_no(conn, customer_id)
        cur.execute(
            """
            INSERT INTO orders (
                customer_id, customer_display_id, order_no, due_date, status, priority,
                assigned_team, assigned_tailor, notes,
                advance_amount, discount_amount, total_amount, taxable_amount, gst_percent, gst_amount,
                cgst_percent, cgst_amount, sgst_percent, sgst_amount,
                order_type, order_material_source,
                inventory_applied, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_id,
                order_customer_display_id,
                order_no,
                due_date,
                "Delivered",
                "Normal",
                None,
                None,
                order_notes,
                advance_value,
                discount_amount,
                total_value,
                tax_payload["taxable_amount"],
                tax_payload["gst_percent"],
                tax_payload["gst_amount"],
                tax_payload["cgst_percent"],
                tax_payload["cgst_amount"],
                tax_payload["sgst_percent"],
                tax_payload["sgst_amount"],
                "Alteration",
                "customer",
                0,
                now_str(),
            ),
        )
        order_id = cur.lastrowid
        if order_id is None:
            conn.rollback()
            conn.close()
            return render_template(
                "order_new_alteration.html",
                next_order_id=next_order_id,
                next_order_code=next_order_code,
                display_customer_id=display_customer_id,
                today_date=today_date,
                worker_default=worker_default,
                delivery_default=delivery_default,
                prefill_customer_id=prefill_customer_id,
                prefill_name=prefill_name,
                prefill_phone=prefill_phone,
                prefill_address=prefill_address,
                prefill_notes=prefill_notes,
                error="Unable to save order. Please try again.",
            )
        conn.commit()
        conn.close()
        return redirect(url_for("order_detail", order_id=order_id))

    return render_template(
        "order_new_alteration.html",
        next_order_id=next_order_id,
        next_order_code=next_order_code,
        display_customer_id=display_customer_id,
        today_date=today_date,
        worker_default=worker_default,
        delivery_default=delivery_default,
        prefill_customer_id=prefill_customer_id,
        prefill_name=prefill_name,
        prefill_phone=prefill_phone,
        prefill_address=prefill_address,
        prefill_notes=prefill_notes,
    )
    
# @app.route("/orders/new/material", methods=["GET", "POST"])
# def order_new_material():
#     conn = get_db()
#     reseed_identity_if_empty(conn, "customers", seed=0)
#     next_order_id = conn.execute(
#         "SELECT COALESCE(MAX(id), 0) + 1 FROM orders"
#     ).fetchone()[0]
#     next_order_code = generate_order_no(conn, "Material")
#     next_customer_display_id = conn.execute(
#         "SELECT COALESCE(MAX(id), 0) + 1 FROM customers"
#     ).fetchone()[0]
#     now_dt = datetime.now()
#     order_date_offset_days = int(get_setting("order_date_offset_days", "0") or 0)
#     if order_date_offset_days:
#         now_dt = now_dt + timedelta(days=order_date_offset_days)
#     today_date = now_dt.strftime("%Y-%m-%d %H:%M")
#     base_date = now_dt.date()
#     worker_days = int(get_setting("worker_delivery_days", "0") or 0)
#     delivery_days = int(get_setting("delivery_days", "0") or 0)
#     worker_default = (base_date + timedelta(days=worker_days)).isoformat() if worker_days else ""
#     delivery_default = (base_date + timedelta(days=delivery_days)).isoformat() if delivery_days else ""
#     inventory = conn.execute(
#         """
#         SELECT inventory.id, inventory.inventory_code, inventory.name, inventory.qty,
#                inventory.selling_price, inventory.uom_id, uoms.name AS uom_name
#         FROM inventory
#         LEFT JOIN uoms ON uoms.id = inventory.uom_id
#         ORDER BY inventory.name ASC
#         """
#     ).fetchall()

#     customer_id_param = request.args.get("customer_id", "").strip()
#     prefill_customer_id = None
#     prefill_name = ""
#     prefill_phone = ""
#     prefill_address = ""
#     prefill_notes = ""

#     if customer_id_param.isdigit():
#         prefill_customer_id = int(customer_id_param)
#         row = conn.execute(
#             "SELECT id, name, phone, address, notes FROM customers WHERE id = ?",
#             (prefill_customer_id,),
#         ).fetchone()
#         if row:
#             prefill_name = row["name"]
#             prefill_phone = row["phone"]
#             prefill_address = row["address"]
#             prefill_notes = row["notes"]
#     display_customer_id = int(next_customer_display_id)
#     conn.close()

#     if request.method == "POST":
#         name = request.form.get("name", "").strip()
#         phone = request.form.get("phone", "").strip()
#         notes = request.form.get("customer_notes", "").strip()
#         address = request.form.get("address", "").strip()
#         if not name or not phone:
#             return render_template(
#                 "order_new_material.html",
#                 next_order_id=next_order_id,
#                 next_order_code=next_order_code,
#                 display_customer_id=display_customer_id,
#                 inventory=inventory,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 prefill_customer_id=prefill_customer_id,
#                 prefill_name=name,
#                 prefill_phone=phone,
#                 prefill_address=address,
#                 prefill_notes=notes,
#                 error="Customer name and phone are required.",
#             )
#         if not is_valid_phone(phone):
#             return render_template(
#                 "order_new_material.html",
#                 next_order_id=next_order_id,
#                 next_order_code=next_order_code,
#                 display_customer_id=display_customer_id,
#                 inventory=inventory,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 prefill_customer_id=prefill_customer_id,
#                 prefill_name=name,
#                 prefill_phone=phone,
#                 prefill_address=address,
#                 prefill_notes=notes,
#                 error="Phone number can contain only digits and leading +.",
#             )

#         # Always resolve customer by phone first; reuse existing ID when matched.
#         customer_id = upsert_customer(name, phone, notes, address)
#         order_notes = request.form.get("order_notes", "").strip() or None
#         payment_method = request.form.get("payment_method", "Cash").strip()
#         allowed_payment_methods = {"Cash", "GPay", "Card"}
#         if payment_method not in allowed_payment_methods:
#             payment_method = "Cash"
#         payment_text = f"Payment method: {payment_method}"
#         order_notes = f"{payment_text}\n{order_notes}" if order_notes else payment_text
#         due_date = None
#         advance_amount = request.form.get("advance_amount", "").strip()
#         total_amount = request.form.get("total_amount", "").strip()
#         advance_value = float(advance_amount) if advance_amount else None
#         total_value = float(total_amount) if total_amount else None
#         if not total_value or total_value <= 0:
#             return render_template(
#                 "order_new_material.html",
#                 next_order_id=next_order_id,
#                 next_order_code=next_order_code,
#                 display_customer_id=display_customer_id,
#                 inventory=inventory,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 prefill_customer_id=prefill_customer_id,
#                 prefill_name=prefill_name,
#                 prefill_phone=prefill_phone,
#                 prefill_address=prefill_address,
#                 prefill_notes=prefill_notes,
#                 error="Total cost must be greater than 0.",
#             )

#         item_ids = request.form.getlist("material_item_id")
#         qty_values = request.form.getlist("material_qty")
#         unit_price_values = request.form.getlist("material_unit_price")

#         order_customer_display_id = customer_display_id(customer_id)
#         conn = get_db()
#         cur = conn.cursor()
#         order_no = generate_order_no(conn, "Material")
#         cur.execute(
#             """
#             INSERT INTO orders (
#                 customer_id, customer_display_id, order_no, due_date, status, priority,
#                 assigned_team, assigned_tailor, notes,
#                 advance_amount, total_amount, order_type, order_material_source,
#                 inventory_applied, created_at
#             )
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """,
#             (
#                 customer_id,
#                 order_customer_display_id,
#                 order_no,
#                 due_date,
#                 "Delivered",
#                 "Normal",
#                 None,
#                 None,
#                 order_notes,
#                 advance_value,
#                 total_value,
#                 "Material",
#                 "inventory",
#                 1,
#                 now_str(),
#             ),
#         )
#         order_id = cur.lastrowid
#         if order_id is None:
#             conn.rollback()
#             conn.close()
#             return render_template(
#                 "order_new_material.html",
#                 next_order_id=next_order_id,
#                 next_order_code=next_order_code,
#                 display_customer_id=display_customer_id,
#                 inventory=inventory,
#                 today_date=today_date,
#                 worker_default=worker_default,
#                 delivery_default=delivery_default,
#                 prefill_customer_id=prefill_customer_id,
#                 prefill_name=prefill_name,
#                 prefill_phone=prefill_phone,
#                 prefill_address=prefill_address,
#                 prefill_notes=prefill_notes,
#                 error="Unable to save order. Please try again.",
#             )

#         inv_rows = cur.execute(
#             """
#             SELECT inventory.id, inventory.name, inventory.qty, inventory.uom_id,
#                    uoms.name AS uom_name
#             FROM inventory
#             LEFT JOIN uoms ON uoms.id = inventory.uom_id
#             """
#         ).fetchall()
#         inv_map = {str(row["id"]): row for row in inv_rows}

#         for item_id, qty_raw, unit_price_raw in zip(item_ids, qty_values, unit_price_values, strict=False):
#             if not item_id or item_id not in inv_map:
#                 continue
#             try:
#                 qty = float(qty_raw)
#                 unit_price = float(unit_price_raw)
#             except (TypeError, ValueError):
#                 continue
#             if qty <= 0 or unit_price < 0:
#                 continue
#             inv_row = inv_map[item_id]
#             line_total = unit_price * qty
#             cur.execute(
#                 """
#                 INSERT INTO order_material_items
#                     (order_id, inventory_id, uom_id, qty, unit_price, line_total)
#                 VALUES (?, ?, ?, ?, ?, ?)
#                 """,
#                 (order_id, int(item_id), inv_row["uom_id"], qty, unit_price, line_total),
#             )
#             new_qty = max(float(inv_row["qty"] or 0) - qty, 0)
#             cur.execute(
#                 "UPDATE inventory SET qty = ?, updated_at = ? WHERE id = ?",
#                 (new_qty, now_str(), int(item_id)),
#             )

#         conn.commit()
#         conn.close()
#         return redirect(url_for("order_detail", order_id=order_id))

#     return render_template(
#         "order_new_material.html",
#         next_order_id=next_order_id,
#         next_order_code=next_order_code,
#         display_customer_id=display_customer_id,
#         inventory=inventory,
#         today_date=today_date,
#         worker_default=worker_default,
#         delivery_default=delivery_default,
#         prefill_customer_id=prefill_customer_id,
#         prefill_name=prefill_name,
#         prefill_phone=prefill_phone,
#         prefill_address=prefill_address,
#         prefill_notes=prefill_notes,
#     )


@app.route("/orders/new/material", methods=["GET", "POST"])
def order_new_material():
    conn = get_db()
    reseed_identity_if_empty(conn, "customers", seed=0)
    next_order_id = conn.execute(
        "SELECT COALESCE(MAX(id), 0) + 1 FROM orders"
    ).fetchone()[0]
    # next_order_code = generate_order_no(conn, "Material")
    next_order_code = "Will generate after customer selected"
    next_customer_display_id = conn.execute(
        "SELECT COALESCE(MAX(id), 0) + 1 FROM customers"
    ).fetchone()[0]
    now_dt = datetime.now()
    order_date_offset_days = int(get_setting("order_date_offset_days", "0") or 0)
    if order_date_offset_days:
        now_dt = now_dt + timedelta(days=order_date_offset_days)
    today_date = now_dt.strftime("%Y-%m-%d %H:%M")
    base_date = now_dt.date()
    worker_days = int(get_setting("worker_delivery_days", "0") or 0)
    delivery_days = int(get_setting("delivery_days", "0") or 0)
    worker_default = (base_date + timedelta(days=worker_days)).isoformat() if worker_days else ""
    delivery_default = (base_date + timedelta(days=delivery_days)).isoformat() if delivery_days else ""
    inventory = conn.execute(
        """
        SELECT inventory.id, inventory.inventory_code, inventory.name, inventory.qty,
               inventory.selling_price, inventory.uom_id, uoms.name AS uom_name
        FROM inventory
        LEFT JOIN uoms ON uoms.id = inventory.uom_id
        ORDER BY inventory.name ASC
        """
    ).fetchall()

    customer_id_param = request.args.get("customer_id", "").strip()
    prefill_customer_id = None
    prefill_name = ""
    prefill_phone = ""
    prefill_address = ""
    prefill_notes = ""

    if customer_id_param.isdigit():
        prefill_customer_id = int(customer_id_param)
        row = conn.execute(
            "SELECT id, name, phone, address, notes FROM customers WHERE id = ?",
            (prefill_customer_id,),
        ).fetchone()
        if row:
            prefill_name = row["name"]
            prefill_phone = row["phone"]
            prefill_address = row["address"]
            prefill_notes = row["notes"]
    display_customer_id = int(next_customer_display_id)
    conn.close()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        notes = request.form.get("customer_notes", "").strip()
        address = request.form.get("address", "").strip()
        if not name or not phone:
            return render_template(
                "order_new_material.html",
                next_order_id=next_order_id,
                next_order_code=next_order_code,
                display_customer_id=display_customer_id,
                inventory=inventory,
                today_date=today_date,
                worker_default=worker_default,
                delivery_default=delivery_default,
                prefill_customer_id=prefill_customer_id,
                prefill_name=name,
                prefill_phone=phone,
                prefill_address=address,
                prefill_notes=notes,
                error="Customer name and phone are required.",
            )
        if not is_valid_phone(phone):
            return render_template(
                "order_new_material.html",
                next_order_id=next_order_id,
                next_order_code=next_order_code,
                display_customer_id=display_customer_id,
                inventory=inventory,
                today_date=today_date,
                worker_default=worker_default,
                delivery_default=delivery_default,
                prefill_customer_id=prefill_customer_id,
                prefill_name=name,
                prefill_phone=phone,
                prefill_address=address,
                prefill_notes=notes,
                error="Phone number can contain only digits and leading +.",
            )

        # Always resolve customer by phone first; reuse existing ID when matched.
        customer_id = upsert_customer(name, phone, notes, address)
        order_notes = request.form.get("order_notes", "").strip() or None
        payment_method = request.form.get("payment_method", "Cash").strip()
        allowed_payment_methods = {"Cash", "GPay", "Card"}
        if payment_method not in allowed_payment_methods:
            payment_method = "Cash"
        payment_text = f"Payment method: {payment_method}"
        order_notes = f"{payment_text}\n{order_notes}" if order_notes else payment_text
        due_date = None
        advance_amount = request.form.get("advance_amount", "").strip()
        total_amount = request.form.get("total_amount", "").strip()
        advance_value = float(advance_amount) if advance_amount else None
        total_value = float(total_amount) if total_amount else None
        if not total_value or total_value <= 0:
            return render_template(
                "order_new_material.html",
                next_order_id=next_order_id,
                next_order_code=next_order_code,
                display_customer_id=display_customer_id,
                inventory=inventory,
                today_date=today_date,
                worker_default=worker_default,
                delivery_default=delivery_default,
                prefill_customer_id=prefill_customer_id,
                prefill_name=prefill_name,
                prefill_phone=prefill_phone,
                prefill_address=prefill_address,
                prefill_notes=prefill_notes,
                error="Total cost must be greater than 0.",
            )
        gst_enabled = is_gst_enabled_for_order_type("Material")
        tax_payload = parse_order_tax_payload(request.form, total_value)
        tax_payload = apply_gst_toggle_to_tax_payload(tax_payload, total_value, gst_enabled)
        discount_amount = parse_order_discount_amount(request.form, tax_payload["taxable_amount"])

        item_ids = request.form.getlist("material_item_id")
        qty_values = request.form.getlist("material_qty")
        unit_price_values = request.form.getlist("material_unit_price")

        order_customer_display_id = customer_display_id(customer_id)
        conn = get_db()
        cur = conn.cursor()
        # order_no = generate_order_no(conn, "Material")
        order_no = generate_order_no(conn, customer_id)
        cur.execute(
            """
            INSERT INTO orders (
                customer_id, customer_display_id, order_no, due_date, status, priority,
                assigned_team, assigned_tailor, notes,
                advance_amount, discount_amount, total_amount, taxable_amount, gst_percent, gst_amount,
                cgst_percent, cgst_amount, sgst_percent, sgst_amount,
                order_type, order_material_source,
                inventory_applied, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_id,
                order_customer_display_id,
                order_no,
                due_date,
                "Delivered",
                "Normal",
                None,
                None,
                order_notes,
                advance_value,
                discount_amount,
                total_value,
                tax_payload["taxable_amount"],
                tax_payload["gst_percent"],
                tax_payload["gst_amount"],
                tax_payload["cgst_percent"],
                tax_payload["cgst_amount"],
                tax_payload["sgst_percent"],
                tax_payload["sgst_amount"],
                "Material",
                "inventory",
                1,
                now_str(),
            ),
        )
        order_id = cur.lastrowid
        if order_id is None:
            conn.rollback()
            conn.close()
            return render_template(
                "order_new_material.html",
                next_order_id=next_order_id,
                next_order_code=next_order_code,
                display_customer_id=display_customer_id,
                inventory=inventory,
                today_date=today_date,
                worker_default=worker_default,
                delivery_default=delivery_default,
                prefill_customer_id=prefill_customer_id,
                prefill_name=prefill_name,
                prefill_phone=prefill_phone,
                prefill_address=prefill_address,
                prefill_notes=prefill_notes,
                error="Unable to save order. Please try again.",
            )

        inv_rows = cur.execute(
            """
            SELECT inventory.id, inventory.name, inventory.qty, inventory.uom_id,
                   uoms.name AS uom_name
            FROM inventory
            LEFT JOIN uoms ON uoms.id = inventory.uom_id
            """
        ).fetchall()
        inv_map = {str(row["id"]): row for row in inv_rows}

        for item_id, qty_raw, unit_price_raw in zip(item_ids, qty_values, unit_price_values, strict=False):
            if not item_id or item_id not in inv_map:
                continue
            try:
                qty = float(qty_raw)
                unit_price = float(unit_price_raw)
            except (TypeError, ValueError):
                continue
            if qty <= 0 or unit_price < 0:
                continue
            inv_row = inv_map[item_id]
            line_total = unit_price * qty
            cur.execute(
                """
                INSERT INTO order_material_items
                    (order_id, inventory_id, uom_id, qty, unit_price, line_total)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (order_id, int(item_id), inv_row["uom_id"], qty, unit_price, line_total),
            )
            new_qty = max(float(inv_row["qty"] or 0) - qty, 0)
            cur.execute(
                "UPDATE inventory SET qty = ?, updated_at = ? WHERE id = ?",
                (new_qty, now_str(), int(item_id)),
            )

        conn.commit()
        conn.close()
        return redirect(url_for("order_detail", order_id=order_id))

    return render_template(
        "order_new_material.html",
        next_order_id=next_order_id,
        next_order_code=next_order_code,
        display_customer_id=display_customer_id,
        inventory=inventory,
        today_date=today_date,
        worker_default=worker_default,
        delivery_default=delivery_default,
        prefill_customer_id=prefill_customer_id,
        prefill_name=prefill_name,
        prefill_phone=prefill_phone,
        prefill_address=prefill_address,
        prefill_notes=prefill_notes,
    )

@app.route("/expense")
def expense_dashboard():
    filter_type = request.args.get("type", "all")  # all | expense | salary
    conn = get_db()

    total_expense = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses"
    ).fetchone()[0]

    total_salary = conn.execute(
        "SELECT COALESCE(SUM(salary_amount), 0) FROM salaries"
    ).fetchone()[0]

    base_query = """
        SELECT e.id,
               e.expense_no,
               e.expense_name,
               e.amount,
               e.created_at,
               s.staff_no,
               s.shift_no,
               s.salary_amount
        FROM expenses e
        LEFT JOIN salaries s ON s.expense_id = e.id
    """

    if filter_type == "salary":
        base_query += " WHERE s.id IS NOT NULL"
    elif filter_type == "expense":
        base_query += " WHERE s.id IS NULL"

    base_query += " ORDER BY e.created_at DESC"

    expenses = conn.execute(base_query).fetchall()
    conn.close()

    return render_template(
        "expense_dashboard.html",
        total_expense=total_expense,
        total_salary=total_salary,
        expenses=expenses,
        filter_type=filter_type
    )


@app.route("/settings", methods=["GET", "POST"])
def settings():
    active_tab = request.args.get("tab", "data-settings").strip() or "data-settings"
    status = request.args.get("status", "").strip()
    valid_tabs = {"data-settings", "billing-message", "gst-settings", "printer-settings", "login-settings"}
    if active_tab not in valid_tabs:
        active_tab = "data-settings"

    if request.method == "POST":
        if request.form.get("action") == "date_settings":
            set_setting("worker_delivery_days", request.form.get("worker_days", "0"))
            set_setting("delivery_days", request.form.get("delivery_days", "0"))
            set_setting("order_date_offset_days", request.form.get("order_date_offset_days", "0"))
            return redirect(url_for("settings", tab="data-settings", status="date_saved"))
        elif request.form.get("action") == "sms_settings":
            set_setting("sms_order_content", request.form.get("sms_order_content", "").strip())
            posted_company_name = request.form.get("company_name")
            if posted_company_name is None:
                company_name = get_setting("company_name", get_setting("branch_name", "")).strip()
            else:
                company_name = posted_company_name.strip()
            address_line1 = request.form.get("address_line1", "").strip()
            address_line2 = request.form.get("address_line2", "").strip()
            address_line3 = request.form.get("address_line3", "").strip()
            address_name = ", ".join([line for line in [address_line1, address_line2, address_line3] if line])
            company_phone = request.form.get("company_phone", "").strip()
            print_logo_path = request.form.get("print_logo_path", "").strip()
            set_setting("company_name", company_name)
            if company_name:
                set_setting("branch_name", company_name)
            set_setting("address_line1", address_line1)
            set_setting("address_line2", address_line2)
            set_setting("address_line3", address_line3)
            set_setting("address_name", address_name)
            set_setting("company_phone", company_phone)
            set_setting("print_logo_path", print_logo_path)
            return redirect(url_for("settings", tab="billing-message", status="sms_saved"))
        elif request.form.get("action") == "gst_settings":
            gst_no = request.form.get("gst_no", "").strip()
            gst_value_mode = request.form.get("gst_value_mode", "percent").strip().lower()
            if gst_value_mode not in {"percent", "amount"}:
                gst_value_mode = "percent"
            default_gst_percent = request.form.get("default_gst_percent", "0").strip()
            default_gst_amount = request.form.get("default_gst_amount", "0").strip()
            gst_enable_tailoring = "1" if request.form.get("gst_enable_tailoring") == "1" else "0"
            gst_enable_alteration = "1" if request.form.get("gst_enable_alteration") == "1" else "0"
            gst_enable_material = "1" if request.form.get("gst_enable_material") == "1" else "0"
            set_setting("gst_no", gst_no)
            set_setting("gst_value_mode", gst_value_mode)
            set_setting("default_gst_percent", default_gst_percent)
            set_setting("default_gst_amount", default_gst_amount)
            set_setting("gst_enable_tailoring", gst_enable_tailoring)
            set_setting("gst_enable_alteration", gst_enable_alteration)
            set_setting("gst_enable_material", gst_enable_material)
            return redirect(url_for("settings", tab="gst-settings", status="gst_saved"))
        elif request.form.get("action") == "printer_settings":
            default_printer_name = request.form.get("default_printer_name", "").strip()
            auto_print_on_click = "1" if request.form.get("auto_print_on_click") == "1" else "0"
            set_setting("default_printer_name", default_printer_name)
            set_setting("auto_print_on_click", auto_print_on_click)
            return redirect(url_for("settings", tab="printer-settings", status="printer_saved"))
        elif request.form.get("action") == "login_settings":
            current_username = get_setting("login_username", "admin").strip() or "admin"
            current_password = get_setting("login_password", "123")
            posted_username = (request.form.get("login_username") or "").strip()
            current_password_input = request.form.get("current_password") or ""
            new_password = request.form.get("new_password") or ""
            confirm_password = request.form.get("confirm_password") or ""

            if not posted_username:
                return redirect(url_for("settings", tab="login-settings", status="login_username_required"))
            if current_password_input != current_password:
                return redirect(url_for("settings", tab="login-settings", status="login_current_password_invalid"))
            if not new_password:
                return redirect(url_for("settings", tab="login-settings", status="login_new_password_required"))
            if new_password != confirm_password:
                return redirect(url_for("settings", tab="login-settings", status="login_password_mismatch"))

            set_setting("login_username", posted_username)
            set_setting("login_password", new_password)

            if session.get("is_authenticated"):
                session["username"] = posted_username

            if current_username != posted_username:
                return redirect(url_for("settings", tab="login-settings", status="login_saved_username_changed"))
            return redirect(url_for("settings", tab="login-settings", status="login_saved"))
        return redirect(url_for("settings", tab=active_tab))

    default_sms_order_content = "Thank you for your order. We appreciate your trust."
    address_lines = get_company_address_lines()
    address_line1 = address_lines[0] if len(address_lines) > 0 else ""
    address_line2 = address_lines[1] if len(address_lines) > 1 else ""
    address_line3 = address_lines[2] if len(address_lines) > 2 else ""
    status_messages = {
        "date_saved": "Data settings updated.",
        "sms_saved": "Thank you message settings updated.",
        "gst_saved": "GST settings updated.",
        "printer_saved": "Printer settings updated.",
        "login_saved": "Login credentials updated.",
        "login_saved_username_changed": "Login credentials updated. Use the new username next time you sign in.",
        "login_username_required": "Username is required.",
        "login_current_password_invalid": "Current password is incorrect.",
        "login_new_password_required": "New password is required.",
        "login_password_mismatch": "New password and confirm password do not match.",
    }

    return render_template(
        "settings.html",
        active_tab=active_tab,
        status_message=status_messages.get(status, ""),
        worker_days=get_setting("worker_delivery_days", "0"),
        delivery_days=get_setting("delivery_days", "0"),
        order_date_offset_days=get_setting("order_date_offset_days", "0"),
        sms_order_content=get_setting("sms_order_content", default_sms_order_content),
        billing_footer_text=get_setting("billing_footer_text", ""),
        company_name=get_setting("company_name", get_setting("branch_name", "")),
        company_phone=get_setting("company_phone", ""),
        gst_no=get_setting("gst_no", ""),
        print_logo_path=get_setting("print_logo_path", "Premier-Logo.png"),
        gst_value_mode=get_setting("gst_value_mode", "percent"),
        default_gst_percent=get_setting("default_gst_percent", "0"),
        default_gst_amount=get_setting("default_gst_amount", "0"),
        gst_enable_tailoring=get_setting("gst_enable_tailoring", "1") == "1",
        gst_enable_alteration=get_setting("gst_enable_alteration", "0") == "1",
        gst_enable_material=get_setting("gst_enable_material", "0") == "1",
        address_name=", ".join([line for line in address_lines if line]),
        address_line1=address_line1,
        address_line2=address_line2,
        address_line3=address_line3,
        default_printer_name=get_setting("default_printer_name", ""),
        auto_print_on_click=get_setting("auto_print_on_click", "0") == "1",
        installed_printers=get_installed_printer_names(),
        login_username=get_setting("login_username", "admin"),
    )
    
    
@app.route("/orders/<int:order_id>/edit", methods=["GET", "POST"])
def order_edit(order_id):
    conn = get_db()

    order = conn.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if not order:
        conn.close()
        return redirect(url_for("orders"))

    customer = conn.execute(
        "SELECT * FROM customers WHERE id = ?", (order["customer_id"],)
    ).fetchone()

    order_items = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
    ).fetchall()

    measurements = conn.execute(
        "SELECT * FROM measurements WHERE customer_id = ?", (customer["id"],)
    ).fetchall()

    images = conn.execute(
        "SELECT * FROM order_images WHERE order_id = ?", (order_id,)
    ).fetchall()

    images_by_item = {}
    for img in images:
        images_by_item.setdefault(img["item_type"], []).append(img)

    # ---------------- POST : UPDATE ONLY ----------------
    if request.method == "POST":

        status = request.form.get("order_status")
        due_date = request.form.get("due_date") or None
        advance_amount = request.form.get("advance_amount") or 0
        paid_amount = request.form.get("paid_amount") or 0

        # 1ï¸âƒ£ UPDATE ORDER TABLE
        conn.execute(
            """
            UPDATE orders
            SET status = ?, due_date = ?, advance_amount = ?, paid_amount = ?
            WHERE id = ?
            """,
            (status, due_date, advance_amount, paid_amount, order_id),
        )
        # 2ï¸âƒ£ UPDATE ORDER ITEMS (THIS IS WHAT YOU ASKED)
        item_ids = request.form.getlist("item_id[]")
        item_qtys = request.form.getlist("item_qty[]")

        for iid, qty in zip(item_ids, item_qtys):
            conn.execute(
                "UPDATE order_items SET qty = ? WHERE id = ?",
                (qty, iid)
            )

        conn.commit()
        conn.close()

        return redirect(
            url_for(
                "customer_detail",
                customer_id=customer["id"],
                order_id=order_id
            )
        )

    # ---------------- GET : LOAD EDIT PAGE ----------------
    conn.close()
    return render_template(
        "order_edit.html",
        order=order,
        customer=customer,
        order_items=order_items,
        measurements=measurements,
        images_by_item=images_by_item,
    )
    
@app.route("/expense/add", methods=["GET", "POST"])
def expense_add():
    conn = get_db()

    if request.method == "POST":
        name = request.form.get("expense_name", "").strip()
        expense_amount = request.form.get("expense_amount", "").strip()
        salary_amount = request.form.get("salary_amount", "").strip()
        is_salary = request.form.get("is_salary") == "1"

        expense_no = generate_expense_no(conn)

        # âœ… PRIORITY VALIDATION
        if not name:
            return render_template(
                "expense_add.html",
                error="Expense name is required",
                expense_no=expense_no
            )

        if is_salary:
            if not salary_amount:
                return render_template(
                    "expense_add.html",
                    error="Salary amount is required",
                    expense_no=expense_no
                )
            final_amount = float(salary_amount)
        else:
            if not expense_amount:
                return render_template(
                    "expense_add.html",
                    error="Expense amount is required",
                    expense_no=expense_no
                )
            final_amount = float(expense_amount)

        created_at = now_str()
        cur = conn.cursor()

        # âœ… EXPENSE INSERT (single source of truth)
        cur.execute(
            """
            INSERT INTO expenses (expense_no, expense_name, amount, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (expense_no, name, final_amount, created_at),
        )
        expense_id = cur.lastrowid

        # âœ… SALARY INSERT ONLY WHEN CHECKED
        if is_salary:
            staff_no = request.form.get("staff_no") or "-"
            shift_no = request.form.get("shift_no") or "-"   # âœ… prevents NOT NULL crash

            cur.execute(
                """
                INSERT INTO salaries (
                    expense_id, staff_no, shift_no, salary_amount, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    expense_id,
                    staff_no,
                    shift_no,
                    float(salary_amount),
                    created_at,
                ),
            )


        conn.commit()
        conn.close()

        # âœ… PRINT USES FINAL PRIORITY AMOUNT
        # generate_expense_pdf_80mm(expense_no, name, final_amount, created_at)
        generate_expense_pdf_80mm(
            expense_no,
            name,
            final_amount,
            created_at,
            is_salary=is_salary,
            staff_no=request.form.get("staff_no")
        )

        return redirect(url_for("expense_dashboard"))

    # expense_no = generate_expense_no(conn)
    # conn.close()
    # return render_template("expense_add.html", expense_no=expense_no)

    expense_no = generate_expense_no(conn)

    # âœ… FETCH STAFF LIST FOR DROPDOWN
    staffs = conn.execute(
        "SELECT tailor_code, name FROM tailors WHERE status = 'Active' ORDER BY name"
    ).fetchall()

    conn.close()

    return render_template(
        "expense_add.html",
        expense_no=expense_no,
        staffs=staffs
    )


@app.route("/expense/<int:expense_id>/edit", methods=["GET", "POST"])
def expense_edit(expense_id: int):
    conn = get_db()
    expense = conn.execute(
        "SELECT * FROM expenses WHERE id = ?",
        (expense_id,),
    ).fetchone()
    salary = conn.execute(
        "SELECT * FROM salaries WHERE expense_id = ?",
        (expense_id,),
    ).fetchone()
    staffs = conn.execute(
        "SELECT tailor_code, name FROM tailors WHERE status = 'Active' ORDER BY name"
    ).fetchall()
    if not expense:
        conn.close()
        return redirect(url_for("expense_dashboard"))

    if request.method == "POST":
        name = request.form.get("expense_name", "").strip()
        amount = request.form.get("expense_amount", "").strip()
        if not name or not amount:
            conn.close()
            return render_template(
                "expense_edit.html",
                expense=expense,
                salary=salary,
                staffs=staffs,
                error="Name and amount are required.",
            )
        conn.execute(
            "UPDATE expenses SET expense_name = ?, amount = ? WHERE id = ?",
            (name, float(amount), expense_id),
        )
        if salary:
            staff_no = request.form.get("staff_no", "").strip() or "-"
            shift_no = salary["shift_no"] if salary["shift_no"] else "-"
            conn.execute(
                """
                UPDATE salaries
                SET staff_no = ?, shift_no = ?, salary_amount = ?
                WHERE expense_id = ?
                """,
                (staff_no, shift_no, float(amount), expense_id),
            )
        conn.commit()
        conn.close()
        return redirect(url_for("expense_dashboard"))

    conn.close()
    return render_template(
        "expense_edit.html",
        expense=expense,
        salary=salary,
        staffs=staffs,
    )


@app.route("/expense/<int:expense_id>/delete", methods=["POST"])
def expense_delete(expense_id: int):
    conn = get_db()
    conn.execute("DELETE FROM salaries WHERE expense_id = ?", (expense_id,))
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("expense_dashboard"))


@app.route("/categories", methods=["GET", "POST"])
def categories():
    if request.method == "POST":
        action = request.form.get("action", "")
        conn = get_db()
        cur = conn.cursor()

        if action == "add_category":
            name = request.form.get("category_name", "").strip()
            measurement_type = request.form.get("measurement_type", "Shirt").strip()
            if name:
                existing = cur.execute(
                    """
                    SELECT id
                    FROM categories
                    WHERE LOWER(LTRIM(RTRIM(name))) = LOWER(LTRIM(RTRIM(?)))
                    """,
                    (name,),
                ).fetchone()
                if not existing:
                    try:
                        next_sort = cur.execute(
                            "SELECT ISNULL(MAX(sort_order), -1) + 1 AS next_sort FROM categories"
                        ).fetchone()["next_sort"]
                        cur.execute(
                            "INSERT INTO categories (name, measurement_type, sort_order) VALUES (?, ?, ?)",
                            (name, measurement_type, int(next_sort)),
                        )
                    except pyodbc.IntegrityError:
                        # Another request inserted the same category concurrently.
                        pass

        elif action == "delete_category":
            category_id = request.form.get("category_id")
            if category_id:
                cur.execute(
                    "DELETE FROM measurement_labels WHERE category_id = ?",
                    (category_id,),
                )
                cur.execute(
                    "DELETE FROM subcategories WHERE category_id = ?",
                    (category_id,),
                )
                cur.execute("DELETE FROM categories WHERE id = ?", (category_id,))

        elif action == "add_subcategory":
            category_id = request.form.get("subcategory_category_id")
            name = request.form.get("subcategory_name", "").strip()
            if category_id and name:
                existing = cur.execute(
                    """
                    SELECT id
                    FROM subcategories
                    WHERE category_id = ?
                      AND LOWER(LTRIM(RTRIM(name))) = LOWER(LTRIM(RTRIM(?)))
                    """,
                    (category_id, name),
                ).fetchone()
                if not existing:
                    try:
                        cur.execute(
                            "INSERT INTO subcategories (category_id, name) VALUES (?, ?)",
                            (category_id, name),
                        )
                    except pyodbc.IntegrityError:
                        # Duplicate-race/case-space variant, ignore.
                        pass

        elif action == "delete_subcategory":
            subcategory_id = request.form.get("subcategory_id")
            if subcategory_id:
                cur.execute(
                    "DELETE FROM measurement_labels WHERE subcategory_id = ?",
                    (subcategory_id,),
                )
                cur.execute("DELETE FROM subcategories WHERE id = ?", (subcategory_id,))

        elif action == "add_requirement":
            name = request.form.get("requirement_name", "").strip()
            icon = request.files.get("requirement_icon")
            if name and icon and icon.filename:
                filename = f"{uuid.uuid4().hex}_{secure_filename(icon.filename)}"
                filepath = os.path.join(app.config["REQ_ICON_FOLDER"], filename)
                icon.save(filepath)
                next_sort = cur.execute(
                    "SELECT ISNULL(MAX(sort_order), -1) + 1 AS next_sort FROM requirement_icons"
                ).fetchone()["next_sort"]
                cur.execute(
                    "INSERT INTO requirement_icons (name, filename, sort_order) VALUES (?, ?, ?)",
                    (name, filename, int(next_sort)),
                )

        elif action == "delete_requirement":
            req_id = request.form.get("requirement_id")
            if req_id:
                row = cur.execute(
                    "SELECT filename FROM requirement_icons WHERE id = ?",
                    (req_id,),
                ).fetchone()
                if row:
                    try:
                        os.remove(os.path.join(app.config["REQ_ICON_FOLDER"], row["filename"]))
                    except OSError:
                        pass
                cur.execute("DELETE FROM requirement_icons WHERE id = ?", (req_id,))

        elif action == "add_uom":
            name = request.form.get("uom_name", "").strip()
            if name:
                existing = cur.execute("SELECT id FROM uoms WHERE name = ?", (name,)).fetchone()
                if not existing:
                    cur.execute("INSERT INTO uoms (name) VALUES (?)", (name,))

        elif action == "delete_uom":
            uom_id = request.form.get("uom_id")
            if uom_id:
                cur.execute("DELETE FROM uoms WHERE id = ?", (uom_id,))

        elif action == "save_fields":
            subcategory_id = request.form.get("fields_subcategory_id")
            field_keys = request.form.getlist("field_key")
            field_labels = request.form.getlist("field_label")
            if subcategory_id:
                cur.execute(
                    "DELETE FROM measurement_fields WHERE subcategory_id = ?",
                    (subcategory_id,),
                )
                used = set()
                for idx, (key, label) in enumerate(
                    zip(field_keys, field_labels, strict=False)
                ):
                    key = (key or "").strip()
                    label = (label or "").strip()
                    if label.lower() == "[object object]":
                        continue
                    if not label:
                        continue
                    base = "".join(ch for ch in (key or label).lower() if ch.isalnum())
                    base = base[:12] if base else "field"
                    key = base
                    counter = 2
                    while key.lower() in used:
                        key = f"{base}{counter}"
                        counter += 1
                    used.add(key.lower())
                    cur.execute(
                        """
                        INSERT INTO measurement_fields (subcategory_id, field_key, field_label, sort_order)
                        VALUES (?, ?, ?, ?)
                        """,
                        (subcategory_id, key, label, idx),
                    )

        elif action == "save_category_order":
            ordered_ids = request.form.getlist("category_order_ids")
            for idx, raw_id in enumerate(ordered_ids):
                if not str(raw_id).strip().isdigit():
                    continue
                cur.execute(
                    "UPDATE categories SET sort_order = ? WHERE id = ?",
                    (idx, int(raw_id)),
                )

        elif action == "save_requirement_order":
            ordered_ids = request.form.getlist("requirement_order_ids")
            for idx, raw_id in enumerate(ordered_ids):
                if not str(raw_id).strip().isdigit():
                    continue
                cur.execute(
                    "UPDATE requirement_icons SET sort_order = ? WHERE id = ?",
                    (idx, int(raw_id)),
                )

        active_tab = request.form.get("active_tab", "").strip()
        conn.commit()
        conn.close()
        if active_tab:
            return redirect(url_for("categories", tab=active_tab))
        return redirect(url_for("categories"))

    conn = get_db()
    categories = conn.execute(
        "SELECT * FROM categories ORDER BY sort_order, name"
    ).fetchall()
    subcategories = conn.execute(
        """
        SELECT s.*, c.name as category_name
        FROM subcategories s
        JOIN categories c ON c.id = s.category_id
        ORDER BY c.sort_order, c.name, s.name
        """
    ).fetchall()
    measurement_fields = conn.execute(
        """
        SELECT f.*, s.name as subcategory_name, c.name as category_name
        FROM measurement_fields f
        JOIN subcategories s ON s.id = f.subcategory_id
        JOIN categories c ON c.id = s.category_id
        ORDER BY c.name, s.name, f.sort_order
        """
    ).fetchall()
    requirement_icons = conn.execute(
        "SELECT * FROM requirement_icons ORDER BY sort_order, name"
    ).fetchall()
    uoms = conn.execute("SELECT * FROM uoms ORDER BY name").fetchall()
    field_map: dict[str, dict[str, str]] = {}
    for row in measurement_fields:
        sub_key = str(row["subcategory_id"])
        f_key = str(row["field_key"] or "").strip()
        f_label = str(row["field_label"] or "").strip()
        if not f_key:
            continue
        field_map.setdefault(sub_key, {})[f_key] = f_label
    conn.close()

    return render_template(
        "categories.html",
        categories=categories,
        subcategories=subcategories,
        measurement_fields=measurement_fields,
        measurement_field_map=field_map,
        requirement_icons=requirement_icons,
        uoms=uoms,
        active_tab=request.args.get("tab", "categories"),
    )

@app.route("/api/staff/<staff_code>")
def get_staff_name(staff_code):
    conn = get_db()
    row = conn.execute(
        "SELECT name, phone, role, status FROM tailors WHERE tailor_code = ?",
        (staff_code,)
    ).fetchone()
    conn.close()

    if not row:
        return {"name": "", "phone": "", "role": "", "status": ""}
    return {
        "name": row["name"] or "",
        "phone": row["phone"] or "",
        "role": row["role"] or "",
        "status": row["status"] or "",
    }



@app.route("/orders/<int:order_id>", methods=["GET", "POST"])
def order_detail(order_id: int):
    conn = get_db()
    source = (request.args.get("source") or "").strip().lower()
    if source not in {"orders", "customers"}:
        source = ""
    if request.method == "POST":
        status = request.form.get("status", "In-Progress")
        assigned_tailor = request.form.get("assigned_tailor", "").strip() or None
        due_date = request.form.get("due_date", "").strip() or None
        notes = request.form.get("notes", "").strip() or None
        advance_amount = request.form.get("advance_amount", "").strip()
        total_amount = request.form.get("total_amount", "").strip()
        paid_flag = request.form.get("paid") == "1"
        picked_up_flag = request.form.get("picked_up") == "1"

        current = conn.execute(
            "SELECT status, paid_at, delivered_at, completed_at, picked_up_at FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        if not current:
            conn.close()
            return redirect(url_for("orders"))
        previous_status = (current["status"] or "").strip() if current else ""
        now = now_str()
        paid_at = current["paid_at"]
        completed_at = current["completed_at"]
        picked_up_at = current["picked_up_at"]
        if status == "Completed" and not completed_at:
            completed_at = now
        if status == "Delivered" and not completed_at:
            completed_at = now
        if paid_flag and not paid_at:
            paid_at = now
        if picked_up_flag and not picked_up_at:
            picked_up_at = now

        conn.execute(
            """
            UPDATE orders
            SET status = ?, assigned_tailor = ?, due_date = ?, notes = ?,
                advance_amount = ?, total_amount = ?, paid_at = ?,
                completed_at = ?, picked_up_at = ?
            WHERE id = ?
            """,
            (
                status,
                assigned_tailor,
                due_date,
                notes,
                float(advance_amount) if advance_amount else None,
                float(total_amount) if total_amount else None,
                paid_at,
                completed_at,
                picked_up_at,
                order_id,
            ),
        )
        sync_completed_notification(conn, order_id, previous_status, status, completed_at)
        conn.commit()
        row = conn.execute(
            "SELECT customer_id FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        if row:
            customer_id = row["customer_id"]
            conn.close()
            return redirect(url_for("customer_detail", customer_id=customer_id, order_id=order_id, source=source))

    order = conn.execute(
        """
        SELECT orders.*, customers.name, customers.phone, customers.notes AS customer_notes
        FROM orders
        JOIN customers ON customers.id = orders.customer_id
        WHERE orders.id = ?
        """,
        (order_id,),
    ).fetchone()
    if not order:
        conn.close()
        return redirect(url_for("orders"))
    if order and request.method == "GET":
        customer_id = order["customer_id"]
        conn.close()
        return redirect(url_for("customer_detail", customer_id=customer_id, order_id=order_id, source=source))
    requirement_names = extract_requirements(order["notes"] if order else None)
    requirement_icons = []
    if requirement_names:
        placeholders = ",".join("?" for _ in requirement_names)
        requirement_icons = conn.execute(
            f"SELECT name, filename FROM requirement_icons WHERE name IN ({placeholders})",
            requirement_names,
        ).fetchall()
    items = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
    ).fetchall()
    material_items = conn.execute(
        """
        SELECT inventory.name AS item_name,
               order_material_items.qty,
               uoms.name AS uom_name,
               order_material_items.unit_price,
               order_material_items.line_total
        FROM order_material_items
        JOIN inventory ON inventory.id = order_material_items.inventory_id
        LEFT JOIN uoms ON uoms.id = order_material_items.uom_id
        WHERE order_material_items.order_id = ?
        """,
        (order_id,),
    ).fetchall()
    measurements = fetch_order_measurements(
        conn,
        int(order["customer_id"]),
        int(order["id"]),
        order["created_at"],
    )
    tailors = conn.execute("SELECT * FROM tailors ORDER BY team, name").fetchall()
    images = conn.execute(
        "SELECT filename, label, item_type FROM order_images WHERE order_id = ?",
        (order_id,),
    ).fetchall()
    images_by_item = {}
    customer_images = []
    for img in images:
        key = img["item_type"] or "Uncategorized"
        key_norm = (key or "").strip().lower()
        label_norm = str(img["label"] or "").strip().lower()
        if key_norm == "customer" or label_norm == "customer":
            customer_images.append(img)
            continue
        images_by_item.setdefault(key, []).append(img)
    if not customer_images:
        fallback_customer_photo = conn.execute(
            """
            SELECT oi.filename, oi.label, oi.item_type
            FROM order_images oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.customer_id = ?
              AND (
                LOWER(LTRIM(RTRIM(COALESCE(oi.item_type, '')))) = 'customer'
                OR LOWER(LTRIM(RTRIM(COALESCE(oi.label, '')))) = 'customer'
              )
            ORDER BY oi.id DESC
            LIMIT 1
            """,
            (int(order["customer_id"]),),
        ).fetchall()
        if fallback_customer_photo:
            customer_images = list(fallback_customer_photo)
    conn.close()

    worker_delivery_date = None
    if order and order["notes"]:
        for line in order["notes"].splitlines():
            if line.lower().startswith("worker delivery date:"):
                worker_delivery_date = date_only(line.split(":", 1)[1].strip())

    total_amount = float(order["total_amount"] or 0)
    advance_amount = float(order["advance_amount"] or 0)
    paid_amount = float(order["paid_amount"] or 0)
    gst_amount = float(order["gst_amount"] or 0)
    gst_percent = float(order["gst_percent"] or 0)
    taxable_amount = float(order["taxable_amount"] or max(total_amount - gst_amount, 0))
    stored_discount = float(order["discount_amount"] or 0) if "discount_amount" in order.keys() else 0.0
    cgst_amount = float(order["cgst_amount"] or (gst_amount / 2.0 if gst_amount > 0 else 0))
    sgst_amount = float(order["sgst_amount"] or (gst_amount / 2.0 if gst_amount > 0 else 0))
    cgst_percent = float(order["cgst_percent"] or (gst_percent / 2.0 if gst_percent > 0 else 0))
    sgst_percent = float(order["sgst_percent"] or (gst_percent / 2.0 if gst_percent > 0 else 0))
    discount_amount = max(stored_discount, 0)
    sub_total = max(taxable_amount + discount_amount, 0)
    due_amount = max(total_amount - advance_amount - paid_amount, 0)

    return render_template(
        "order_detail.html",
        order=order,
        items=items,
        material_items=material_items,
        tailors=tailors,
        images=images,
        images_by_item=images_by_item,
        customer_images=customer_images,
        worker_delivery_date=worker_delivery_date,
        sub_total=sub_total,
        discount_amount=discount_amount,
        gst_amount=gst_amount,
        cgst_amount=cgst_amount,
        sgst_amount=sgst_amount,
        gst_percent=gst_percent,
        cgst_percent=cgst_percent,
        sgst_percent=sgst_percent,
        paid_amount=paid_amount,
        due_amount=due_amount,
        measurements=measurements,
        requirement_icons=requirement_icons,
    )


def _render_order_print_tailor(order_id: int, paper: str = "a4"):
    conn = get_db()
    order = conn.execute(
        """
        SELECT orders.*, customers.name, customers.phone, customers.address
        FROM orders
        JOIN customers ON customers.id = orders.customer_id
        WHERE orders.id = ?
        """,
        (order_id,),
    ).fetchone()
    if not order:
        conn.close()
        return redirect(url_for("orders"))
    measurements = fetch_order_measurements(
        conn,
        int(order["customer_id"]),
        int(order["id"]),
        order["created_at"],
    )
    items = conn.execute(
        "SELECT * FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()
    conn.close()
    selected_item_type = request.args.get("item_type", "").strip().lower()
    if selected_item_type:
        items = [
            item for item in items
            if (item["item_type"] or "").strip().lower() == selected_item_type
        ]
        measurements = [
            row for row in measurements
            if selected_item_type in (row["kind"] or "").strip().lower()
        ]
        order = dict(order)
        order["notes"] = ""
    # Tailor slip is fixed to landscape text orientation.
    is_landscape = True
    pdf_path = generate_order_pdf_80mm(
        order,
        measurements,
        items,
        mode="tailor",
        landscape=is_landscape,
        tailor_paper=paper,
    )
    if request.method == "POST" or request.args.get("direct", "").strip() == "1":
        ok, err = force_print_to_selected_printer(pdf_path, order_id, "tailor")
        if not ok:
            return jsonify({"ok": False, "message": err}), 500
        return jsonify({"ok": True, "message": "Sent to selected printer."})
    process_post_print_actions(pdf_path, order_id, "tailor")
    download_requested = request.args.get("download", "").strip() == "1"
    if os.path.exists(pdf_path):
        return send_file(
            pdf_path,
            as_attachment=download_requested,
            download_name=f"order_{order_id}_tailor.pdf",
            mimetype="application/pdf",
        )
    return jsonify({"ok": False, "message": "Tailor PDF was not generated."}), 500


@app.route("/orders/<int:order_id>/print/a4", methods=["GET", "POST"])
def order_print_a4(order_id: int):
    return _render_order_print_tailor(order_id, paper="a4")


@app.route("/orders/<int:order_id>/print/thermal", methods=["GET", "POST"])
def order_print_thermal(order_id: int):
    return _render_order_print_tailor(order_id, paper="thermal")


@app.route("/orders/<int:order_id>/print/customer", methods=["GET", "POST"])
def order_print_customer(order_id: int):
    def normalize_measure_type(raw_value: str | None) -> str:
        text = (raw_value or "").strip().lower()
        if not text:
            return ""
        base = text.split("-", 1)[0].strip()
        if base in {"s001", "shirt"}:
            return "shirt"
        if base in {"p001", "pant", "trouser", "jean", "jeans"}:
            return "pant"
        if base in {"coat", "blazer", "safari"}:
            return "coat"
        return base or text

    conn = get_db()
    order = conn.execute(
        """
        SELECT orders.*, customers.name, customers.phone, customers.address
        FROM orders
        JOIN customers ON customers.id = orders.customer_id
        WHERE orders.id = ?
        """,
        (order_id,),
    ).fetchone()
    if not order:
        conn.close()
        return redirect(url_for("orders"))
    measurements = fetch_order_measurements(
        conn,
        int(order["customer_id"]),
        int(order["id"]),
        order["created_at"],
    )
    order_type_lower = (order["order_type"] or "").strip().lower()
    material_items = conn.execute(
        """
        SELECT inventory.name AS item_type,
               order_material_items.qty,
               uoms.name AS uom_name,
               order_material_items.unit_price,
               order_material_items.line_total,
               'material' AS item_group
        FROM order_material_items
        JOIN inventory ON inventory.id = order_material_items.inventory_id
        LEFT JOIN uoms ON uoms.id = order_material_items.uom_id
        WHERE order_material_items.order_id = ?
        """,
        (order_id,),
    ).fetchall()
    if order_type_lower == "material":
        items = material_items
    else:
        tailoring_items = conn.execute(
            "SELECT item_type, qty, NULL AS uom_name, NULL AS unit_price, NULL AS line_total, 'tailoring' AS item_group FROM order_items WHERE order_id = ?",
            (order_id,),
        ).fetchall()
        if order_type_lower == "tailoring":
            delivered_types = {
                normalize_measure_type(m["kind"] if "kind" in m.keys() else "")
                for m in measurements
                if str(m["measure_status"] if "measure_status" in m.keys() else "").strip().lower() == "delivered"
            }
            delivered_types = {x for x in delivered_types if x}
            if delivered_types:
                tailoring_items = [
                    item for item in tailoring_items
                    if normalize_measure_type(item["item_type"] if "item_type" in item.keys() else "") in delivered_types
                ]
        # Customer copy should include tailoring + material items for mixed bills.
        items = list(tailoring_items) + list(material_items)
    conn.close()
    layout_value = request.args.get("layout", "").strip().lower()
    if layout_value in {"portrait", "vertical", "0", "false", "no"}:
        is_landscape = False
    elif layout_value in {"landscape", "horizontal", "1", "true", "yes"}:
        is_landscape = True
    else:
        is_landscape = False
    thermal_style_value = request.args.get("thermal_style", "").strip().lower()
    use_thermal_style = thermal_style_value in {"1", "true", "yes", "thermal"}
    render_mode = "tailor" if use_thermal_style else "customer"
    pdf_path = generate_order_pdf_80mm(order, measurements, items, mode=render_mode, landscape=is_landscape)
    if request.method == "POST" or request.args.get("direct", "").strip() == "1":
        ok, err = force_print_to_selected_printer(pdf_path, order_id, "customer")
        if not ok:
            return jsonify({"ok": False, "message": err}), 500
        return jsonify({"ok": True, "message": "Sent to selected printer."})
    process_post_print_actions(pdf_path, order_id, "customer")
    download_requested = request.args.get("download", "").strip() == "1"
    if os.path.exists(pdf_path):
        return send_file(
            pdf_path,
            as_attachment=download_requested,
            download_name=f"order_{order_id}_customer.pdf",
            mimetype="application/pdf",
        )
    return jsonify({"ok": False, "message": "Customer PDF was not generated."}), 500


@app.route("/orders/<int:order_id>/print/all/download")
def order_print_all_download(order_id: int):
    def normalize_measure_type(raw_value: str | None) -> str:
        text = (raw_value or "").strip().lower()
        if not text:
            return ""
        base = text.split("-", 1)[0].strip()
        if base in {"s001", "shirt"}:
            return "shirt"
        if base in {"p001", "pant", "trouser", "jean", "jeans"}:
            return "pant"
        if base in {"coat", "blazer", "safari"}:
            return "coat"
        return base or text

    conn = get_db()
    order = conn.execute(
        """
        SELECT orders.*, customers.name, customers.phone, customers.address
        FROM orders
        JOIN customers ON customers.id = orders.customer_id
        WHERE orders.id = ?
        """,
        (order_id,),
    ).fetchone()
    if not order:
        conn.close()
        return redirect(url_for("orders"))

    order_type_lower = (order["order_type"] or "").strip().lower()
    tailoring_items = conn.execute(
        "SELECT item_type, qty, NULL AS uom_name, NULL AS unit_price, NULL AS line_total, 'tailoring' AS item_group FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()
    material_items = conn.execute(
        """
        SELECT inventory.name AS item_type,
               order_material_items.qty,
               uoms.name AS uom_name,
               order_material_items.unit_price,
               order_material_items.line_total,
               'material' AS item_group
        FROM order_material_items
        JOIN inventory ON inventory.id = order_material_items.inventory_id
        LEFT JOIN uoms ON uoms.id = order_material_items.uom_id
        WHERE order_material_items.order_id = ?
        """,
        (order_id,),
    ).fetchall()
    measurements = fetch_order_measurements(
        conn,
        int(order["customer_id"]),
        int(order["id"]),
        order["created_at"],
    )
    conn.close()

    layout_value = request.args.get("layout", "").strip().lower()
    is_landscape = layout_value in {"landscape", "horizontal", "1", "true", "yes"}
    modes = ["tailor", "customer"] if order_type_lower == "tailoring" else ["customer"]
    generated_files: list[tuple[str, str]] = []

    try:
        for mode in modes:
            mode_items = tailoring_items
            if mode == "customer":
                if order_type_lower == "material":
                    mode_items = material_items
                else:
                    if order_type_lower == "tailoring":
                        delivered_types = {
                            normalize_measure_type(m["kind"] if "kind" in m.keys() else "")
                            for m in measurements
                            if str(m["measure_status"] if "measure_status" in m.keys() else "").strip().lower() == "delivered"
                        }
                        delivered_types = {x for x in delivered_types if x}
                        if delivered_types:
                            mode_items = [
                                item for item in tailoring_items
                                if normalize_measure_type(item["item_type"] if "item_type" in item.keys() else "") in delivered_types
                            ]
                    mode_items = list(mode_items) + list(material_items)

            mode_landscape = is_landscape
            pdf_path = generate_order_pdf_80mm(order, measurements, mode_items, mode=mode, landscape=mode_landscape)
            out_name = f"order_{order_id}_{mode}.pdf"
            out_path = os.path.join(APP_DIR, "static", "order_pdfs", out_name)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            shutil.copy2(pdf_path, out_path)
            generated_files.append((out_name, out_path))
    except Exception:
        return redirect(url_for("orders"))

    if not generated_files:
        return redirect(url_for("orders"))

    if len(generated_files) == 1:
        customer_url_params = {
            "order_id": order_id,
            "download": 1,
            "v": int(datetime.now().timestamp() * 1000),
        }
        if is_landscape:
            customer_url_params["layout"] = "landscape"
        return redirect(url_for("order_print_customer", **customer_url_params))

    return Response(
        f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>Downloading bills...</title></head>
<body>
<script>
  const urls = [
    "/orders/{order_id}/print/thermal?download=1{('&layout=landscape' if is_landscape else '')}",
    "/orders/{order_id}/print/customer?download=1{('&layout=landscape' if is_landscape else '')}"
  ];
  urls.forEach((url, idx) => {{
    setTimeout(() => {{
      const a = document.createElement("a");
      a.href = url;
      a.download = "";
      document.body.appendChild(a);
      a.click();
      a.remove();
    }}, idx * 450);
  }});
  setTimeout(() => {{ window.close(); }}, 1800);
</script>
</body>
</html>""",
        mimetype="text/html",
    )


@app.route("/orders/<int:order_id>/print/all/direct", methods=["POST"])
def order_print_all_direct(order_id: int):
    def normalize_measure_type(raw_value: str | None) -> str:
        text = (raw_value or "").strip().lower()
        if not text:
            return ""
        base = text.split("-", 1)[0].strip()
        if base in {"s001", "shirt"}:
            return "shirt"
        if base in {"p001", "pant", "trouser", "jean", "jeans"}:
            return "pant"
        if base in {"coat", "blazer", "safari"}:
            return "coat"
        return base or text

    conn = get_db()
    order = conn.execute(
        """
        SELECT orders.*, customers.name, customers.phone, customers.address
        FROM orders
        JOIN customers ON customers.id = orders.customer_id
        WHERE orders.id = ?
        """,
        (order_id,),
    ).fetchone()
    if not order:
        conn.close()
        return jsonify({"ok": False, "message": "Order not found."}), 404

    order_type = (order["order_type"] or "").strip()
    items = conn.execute(
        "SELECT *, NULL AS uom_name, NULL AS unit_price, NULL AS line_total, 'tailoring' AS item_group FROM order_items WHERE order_id = ?",
        (order_id,),
    ).fetchall()
    material_items = conn.execute(
        """
        SELECT inventory.name AS item_type,
               order_material_items.qty,
               uoms.name AS uom_name,
               order_material_items.unit_price,
               order_material_items.line_total,
               'material' AS item_group
        FROM order_material_items
        JOIN inventory ON inventory.id = order_material_items.inventory_id
        LEFT JOIN uoms ON uoms.id = order_material_items.uom_id
        WHERE order_material_items.order_id = ?
        """,
        (order_id,),
    ).fetchall()
    tailor_measurements = fetch_order_measurements(
        conn,
        int(order["customer_id"]),
        int(order["id"]),
        order["created_at"],
    )
    customer_measurements = fetch_order_measurements(
        conn,
        int(order["customer_id"]),
        int(order["id"]),
        order["created_at"],
    )
    conn.close()

    layout_value = request.args.get("layout", "").strip().lower()
    is_landscape = layout_value in {"landscape", "horizontal", "1", "true", "yes"}
    modes = ["customer"] if order_type.lower() != "tailoring" else ["tailor", "customer"]
    errors: list[str] = []

    for mode in modes:
        temp_pdf_path = ""
        measurements = tailor_measurements if mode == "tailor" else customer_measurements
        mode_items = items
        if mode == "customer" and order_type.lower() == "tailoring":
            delivered_types = {
                normalize_measure_type(m["kind"] if "kind" in m.keys() else "")
                for m in measurements
                if str(m["measure_status"] if "measure_status" in m.keys() else "").strip().lower() == "delivered"
            }
            delivered_types = {x for x in delivered_types if x}
            if delivered_types:
                mode_items = [
                    item for item in items
                    if normalize_measure_type(item["item_type"] if "item_type" in item.keys() else "") in delivered_types
                ]
        if mode == "customer":
            mode_items = list(mode_items) + list(material_items)
        try:
            mode_landscape = is_landscape
            generated_path = generate_order_pdf_80mm(order, measurements, mode_items, mode=mode, landscape=mode_landscape)
            fd, temp_pdf_path = tempfile.mkstemp(prefix=f"order_{order_id}_{mode}_", suffix=".pdf")
            os.close(fd)
            shutil.copy2(generated_path, temp_pdf_path)
            ok, err = force_print_to_selected_printer(temp_pdf_path, order_id, mode)
            if not ok:
                errors.append(f"{mode}: {err}")
        except Exception as ex:
            errors.append(f"{mode}: {ex}")
        finally:
            try:
                if temp_pdf_path and os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
            except Exception:
                pass

    if errors:
        return jsonify({"ok": False, "message": "Print failed.", "errors": errors}), 500
    return jsonify({"ok": True, "message": "Sent to selected printer."})


@app.route("/orders/<int:order_id>/cancel", methods=["POST"])
def order_cancel(order_id: int):
    wants_json = (
        request.headers.get("X-Requested-With", "").lower() == "xmlhttprequest"
        or "application/json" in (request.headers.get("Accept") or "").lower()
    )
    conn = get_db()
    order = conn.execute(
        "SELECT id, status, inventory_applied FROM orders WHERE id = ?",
        (order_id,),
    ).fetchone()
    def with_cancelled_flag(url_value: str, value: str = "1") -> str:
        base = (url_value or "").strip()
        if not base:
            base = url_for("orders")
        if "cancelled=" in base:
            return base
        joiner = "&" if "?" in base else "?"
        return f"{base}{joiner}cancelled={value}"

    if not order:
        conn.close()
        if wants_json:
            return jsonify({"ok": False, "message": "Order not found."}), 404
        return redirect(with_cancelled_flag(url_for("orders"), "0"))
    if order["status"] == "Cancelled":
        conn.close()
        if wants_json:
            return jsonify({"ok": True, "message": "Bill already cancelled.", "status": "Cancelled"})
        return redirect(with_cancelled_flag(request.form.get("next") or request.referrer or url_for("orders"), "1"))

    if order["inventory_applied"]:
        items = conn.execute(
            "SELECT inventory_id, qty FROM order_material_items WHERE order_id = ?",
            (order_id,),
        ).fetchall()
        for item in items:
            inv = conn.execute(
                "SELECT qty FROM inventory WHERE id = ?",
                (item["inventory_id"],),
            ).fetchone()
            current_qty = float(inv["qty"] or 0) if inv else 0
            new_qty = current_qty + float(item["qty"] or 0)
            conn.execute(
                "UPDATE inventory SET qty = ?, updated_at = ? WHERE id = ?",
                (new_qty, now_str(), item["inventory_id"]),
            )
        conn.execute(
            "UPDATE orders SET inventory_applied = 0 WHERE id = ?",
            (order_id,),
        )

    conn.execute(
        "UPDATE orders SET status = ?, cancelled_at = ? WHERE id = ?",
        ("Cancelled", now_str(), order_id),
    )
    conn.commit()
    conn.close()
    if wants_json:
        return jsonify({"ok": True, "message": "Bill successfully cancelled.", "status": "Cancelled"})
    return redirect(with_cancelled_flag(request.form.get("next") or request.referrer or url_for("orders"), "1"))

@app.route("/tailors")
def tailors():
    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            t.id,
            t.tailor_code,
            t.name,
            t.role,
            t.phone,
            t.status,
            (
                SELECT GROUP_CONCAT(DISTINCT o.id)
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                JOIN measurements m ON m.customer_id = o.customer_id
                WHERE m.assigned_tailor = t.name
                  AND m.assigned_tailor IS NOT NULL
                  AND m.assigned_tailor != ''
                  AND m.kind LIKE '%' || oi.item_type || '%'
            ) AS order_ids,
            (
                SELECT COUNT(DISTINCT o.id)
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                JOIN measurements m ON m.customer_id = o.customer_id
                WHERE m.assigned_tailor = t.name
                  AND m.assigned_tailor IS NOT NULL
                  AND m.assigned_tailor != ''
                  AND m.kind LIKE '%' || oi.item_type || '%'
            ) AS order_count
        FROM tailors t
        ORDER BY t.id DESC
        """
    ).fetchall()

    conn.close()
    return render_template("tailors.html", tailors=rows, title="Tailors")


@app.route("/tailors/<int:tailor_id>")
def tailor_detail(tailor_id: int):
    conn = get_db()
    tailor = conn.execute(
        "SELECT * FROM tailors WHERE id = ?",
        (tailor_id,),
    ).fetchone()
    if not tailor:
        conn.close()
        return redirect(url_for("tailors"))

    orders = conn.execute(
        """
        SELECT DISTINCT o.*, c.name AS customer_name, c.phone AS customer_phone
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        JOIN order_items oi ON oi.order_id = o.id
        JOIN measurements m ON m.customer_id = o.customer_id
        WHERE m.assigned_tailor = ?
          AND m.assigned_tailor IS NOT NULL
          AND m.assigned_tailor != ''
          AND m.kind LIKE '%' || oi.item_type || '%'
        ORDER BY o.created_at DESC
        """,
        (tailor["name"],),
    ).fetchall()
    measurements = conn.execute(
        """
        SELECT m.*, c.name AS customer_name, c.phone AS customer_phone
        FROM measurements m
        JOIN customers c ON c.id = m.customer_id
        WHERE m.assigned_tailor = ?
        ORDER BY m.created_at DESC
        """,
        (tailor["name"],),
    ).fetchall()
    salary_total_row = conn.execute(
        """
        SELECT COALESCE(SUM(salary_amount), 0) AS total_salary
        FROM salaries
        WHERE staff_no = ?
        """,
        (tailor["tailor_code"],),
    ).fetchone()
    salary_total = float(salary_total_row["total_salary"] or 0) if salary_total_row else 0.0
    conn.close()
    return render_template(
        "tailor_detail.html",
        tailor=tailor,
        orders=orders,
        measurements=measurements,
        salary_total=salary_total,
        title="Tailor Orders",
    )


@app.route("/tailors/add", methods=["GET", "POST"])
def tailor_add():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        role_text = request.form.get("role", "").strip()
        phone = request.form.get("phone", "").strip()
        status = request.form.get("status", "Active").strip() or "Active"
        if not name or not role_text or not phone:
            conn = get_db()
            tailor_code = generate_tailor_code(conn)
            conn.close()
            return render_template(
                "tailor_add.html",
                tailor_code=tailor_code,
                title="Add Tailor",
                error="Name, role, and phone are required.",
            )
        if not is_valid_phone(phone):
            conn = get_db()
            tailor_code = generate_tailor_code(conn)
            conn.close()
            return render_template(
                "tailor_add.html",
                tailor_code=tailor_code,
                title="Add Tailor",
                error="Phone number can contain only digits and leading +.",
            )
        conn = get_db()
        try:
            cur = conn.execute(
                """
                INSERT INTO tailors (tailor_code, name, role, phone, status, team)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    None,
                    name,
                    role_text,
                    phone,
                    status,
                    role_text,
                ),
            )
            tailor_id = cur.lastrowid
            if tailor_id is None:
                raise ValueError("Failed to generate tailor ID.")
            tailor_code = next_staff_code_for_role(conn, role_text)
            conn.execute(
                "UPDATE tailors SET tailor_code = ? WHERE id = ?",
                (tailor_code, int(tailor_id)),
            )
            conn.commit()
            return redirect(url_for("tailors"))
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    conn = get_db()
    tailor_code = generate_tailor_code(conn)
    conn.close()
    return render_template(
        "tailor_add.html",
        tailor_code=tailor_code,
        title="Add Tailor",
    )


@app.route("/tailors/edit/<int:tailor_id>", methods=["GET", "POST"])
def tailor_edit(tailor_id):
    conn = get_db()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        role_text = request.form.get("role", "").strip()
        phone = request.form.get("phone", "").strip()
        status = request.form.get("status", "Active").strip() or "Active"
        if not name or not role_text or not phone:
            tailor = conn.execute(
                "SELECT * FROM tailors WHERE id = ?",
                (tailor_id,),
            ).fetchone()
            conn.close()
            return render_template(
                "tailor_edit.html",
                tailor=tailor,
                title="Edit Tailor",
                error="Name, role, and phone are required.",
            )
        if not is_valid_phone(phone):
            tailor = conn.execute(
                "SELECT * FROM tailors WHERE id = ?",
                (tailor_id,),
            ).fetchone()
            conn.close()
            return render_template(
                "tailor_edit.html",
                tailor=tailor,
                title="Edit Tailor",
                error="Phone number can contain only digits and leading +.",
            )
        existing = conn.execute(
            "SELECT tailor_code FROM tailors WHERE id = ?",
            (tailor_id,),
        ).fetchone()
        existing_code = str(existing["tailor_code"]).strip() if existing and existing["tailor_code"] else ""
        expected_prefix = _staff_prefix(role_text)
        if existing_code.startswith(expected_prefix):
            staff_code = existing_code
        else:
            staff_code = next_staff_code_for_role(conn, role_text)
        conn.execute(
            """
            UPDATE tailors
            SET tailor_code = ?, name = ?, role = ?, phone = ?, status = ?, team = ?
            WHERE id = ?
            """,
            (
                staff_code,
                name,
                role_text,
                phone,
                status,
                role_text,   # team = role (same logic as add)
                tailor_id,
            ),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("tailors"))

    tailor = conn.execute(
        "SELECT * FROM tailors WHERE id = ?",
        (tailor_id,),
    ).fetchone()

    conn.close()
    return render_template("tailor_edit.html", tailor=tailor, title="Edit Tailor")


@app.route("/tailors/delete/<int:tailor_id>", methods=["POST"])
def tailor_delete(tailor_id):
    conn = get_db()
    conn.execute("DELETE FROM tailors WHERE id = ?", (tailor_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("tailors"))


@app.route("/customers")
def customers():
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "last_ordered").strip()
    direction = request.args.get("dir", "desc").strip().lower()
    direction = "asc" if direction == "asc" else "desc"
    sort_map = {
        "name": "c.name",
        "phone": "c.phone",
        "last_ordered": "last_ordered",
    }
    sort_col = sort_map.get(sort, "last_ordered")
    conn = get_db()
    base_sql = """
        SELECT
            c.*,
            (
                SELECT MAX(o.created_at)
                FROM orders o
                WHERE o.customer_id = c.id
                   OR o.customer_display_id = c.id
            ) AS last_ordered
        FROM customers c
    """
    params = []
    if q:
        base_sql += " WHERE c.name LIKE ? OR c.phone LIKE ?"
        params.extend([f"%{q}%", f"%{q}%"])
    if sort_col == "last_ordered":
        base_sql += f" ORDER BY last_ordered {direction} NULLS LAST"
    else:
        base_sql += f" ORDER BY {sort_col} {direction}"
    rows = conn.execute(base_sql, params).fetchall()
    conn.close()
    rows = [dict(row) for row in rows]
    for row in rows:
        row["display_id"] = customer_display_id(int(row["id"]))
    return render_template(
        "customers.html",
        customers=rows,
        q=q,
        sort=sort,
        direction=direction,
    )


@app.route("/customers/<int:customer_id>", methods=["GET", "POST"])
def customer_detail(customer_id: int):
    allowed_payment_methods = {"Cash", "GPay", "Card"}
    allowed_measure_statuses = {"In-Progress", "Completed", "Delivered", "Cancelled"}

    def derive_order_status_from_measure_statuses(status_rows) -> str:
        status_set = {
            str(row[0]).strip()
            for row in status_rows
            if str(row[0] or "").strip() in allowed_measure_statuses
        }
        if not status_set:
            return "In-Progress"
        if "In-Progress" in status_set:
            return "In-Progress"
        active_set = {s for s in status_set if s != "Cancelled"}
        if not active_set:
            return "Cancelled"
        if active_set == {"Delivered"}:
            return "Delivered"
        if active_set.issubset({"Completed", "Delivered"}):
            return "Completed"
        return "In-Progress"

    def with_payment_method(notes_text: str | None, method: str) -> str | None:
        cleaned = []
        for raw_line in str(notes_text or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.lower().startswith("payment method:"):
                continue
            cleaned.append(line)
        cleaned.insert(0, f"Payment method: {method}")
        return "\n".join(cleaned) if cleaned else None

    def with_measure_dates(notes_text: str | None, completed_date: str | None, delivery_date: str | None) -> str | None:
        kept: list[str] = []
        for raw_line in str(notes_text or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            low = line.lower()
            if low.startswith("completed date:"):
                continue
            if low.startswith("delivery date:"):
                continue
            kept.append(line)
        prefix: list[str] = []
        if completed_date:
            prefix.append(f"Completed date: {completed_date}")
        if delivery_date:
            prefix.append(f"Delivery date: {delivery_date}")
        merged = prefix + kept
        return "\n".join(merged) if merged else None

    def extract_measure_dates(notes_text: str | None) -> tuple[str | None, str | None]:
        completed_date = None
        delivery_date = None
        for raw_line in str(notes_text or "").splitlines():
            line = raw_line.strip()
            if not line or ":" not in line:
                continue
            key, value = line.split(":", 1)
            key_low = key.strip().lower()
            val = value.strip()
            if not val:
                continue
            if key_low == "completed date":
                completed_date = val
            elif key_low == "delivery date":
                delivery_date = val
        return completed_date, delivery_date

    def apply_order_payment_updates(
        order_id_value: int,
        payment_method_value: str,
        payment_amount_value: float | None,
    ) -> None:
        current_payment = conn.execute(
            """
            SELECT paid_at, paid_amount, total_amount, advance_amount, notes
            FROM orders
            WHERE id = ?
              AND (customer_id = ? OR customer_display_id = ?)
            """,
            (order_id_value, customer_id, customer_id),
        ).fetchone()
        if not current_payment:
            return

        paid_at_value = current_payment["paid_at"]
        existing_paid_value = float(current_payment["paid_amount"] or 0)
        total_amount_value = float(current_payment["total_amount"] or 0)
        advance_amount_value = float(current_payment["advance_amount"] or 0)
        remaining_value = max(total_amount_value - advance_amount_value - existing_paid_value, 0)

        normalized_payment_amount = payment_amount_value
        if normalized_payment_amount is not None and normalized_payment_amount < 0:
            normalized_payment_amount = None
        if normalized_payment_amount is not None:
            normalized_payment_amount = min(normalized_payment_amount, remaining_value)

        next_paid_amount = existing_paid_value + (normalized_payment_amount or 0)
        if normalized_payment_amount is not None and normalized_payment_amount > 0 and not paid_at_value:
            paid_at_value = now_str()

        updated_notes = with_payment_method(current_payment["notes"], payment_method_value)
        conn.execute(
            """
            UPDATE orders
            SET paid_amount = ?, paid_at = ?, notes = ?
            WHERE id = ?
              AND (customer_id = ? OR customer_display_id = ?)
            """,
            (
                next_paid_amount,
                paid_at_value,
                updated_notes,
                order_id_value,
                customer_id,
                customer_id,
            ),
        )

    conn = get_db()
    if request.method == "POST":
        source = (request.form.get("source") or request.args.get("source") or "").strip().lower()
        if source not in {"orders", "customers"}:
            source = ""
        order_status = request.form.get("order_status", "").strip()
        order_id = request.form.get("order_id", "").strip()
        measurement_save_id = request.form.get("measurement_save_id", "").strip()
        payment_method = request.form.get("payment_method", "").strip()
        if payment_method not in allowed_payment_methods:
            payment_method = "Cash"
        paid_amount_raw = request.form.get("paid_amount", "").strip()
        payment_amount = None
        if paid_amount_raw:
            try:
                payment_amount = float(paid_amount_raw)
            except ValueError:
                payment_amount = None
        measurement_cancel_id = request.form.get("measurement_cancel_id", "").strip()
        if measurement_cancel_id.isdigit() and order_id.isdigit():
            measurement_id = int(measurement_cancel_id)
            target_order_id = int(order_id)
            measurement_row = conn.execute(
                """
                SELECT id, order_id, notes
                FROM measurements
                WHERE id = ?
                  AND customer_id = ?
                """,
                (measurement_id, customer_id),
            ).fetchone()
            if measurement_row and (
                measurement_row["order_id"] is None or int(measurement_row["order_id"]) == target_order_id
            ):
                updated_measure_notes = with_measure_dates(
                    measurement_row["notes"] if measurement_row else None,
                    None,
                    None,
                )
                conn.execute(
                    "UPDATE measurements SET measure_status = ?, notes = ? WHERE id = ?",
                    ("Cancelled", updated_measure_notes, measurement_id),
                )
                status_rows = conn.execute(
                    """
                    SELECT DISTINCT LTRIM(RTRIM(ISNULL(measure_status, '')))
                    FROM measurements
                    WHERE order_id = ?
                    """,
                    (target_order_id,),
                ).fetchall()
                derived_order_status = derive_order_status_from_measure_statuses(status_rows)
                current_order = conn.execute(
                    "SELECT status, completed_at, delivered_at FROM orders WHERE id = ?",
                    (target_order_id,),
                ).fetchone()
                previous_status = (current_order["status"] or "").strip() if current_order else ""
                completed_at = current_order["completed_at"] if current_order else None
                delivered_at = current_order["delivered_at"] if current_order else None
                if derived_order_status in {"Completed", "Delivered"}:
                    status_now = now_str()
                    completed_at = completed_at or status_now
                    delivered_at = delivered_at or status_now
                conn.execute(
                    """
                    UPDATE orders
                    SET status = ?, completed_at = ?, delivered_at = ?
                    WHERE id = ?
                      AND (customer_id = ? OR customer_display_id = ?)
                    """,
                    (derived_order_status, completed_at, delivered_at, target_order_id, customer_id, customer_id),
                )
                sync_completed_notification(conn, target_order_id, previous_status, derived_order_status, completed_at)
                conn.commit()
            conn.close()
            return redirect(
                url_for(
                    "customer_detail",
                    customer_id=customer_id,
                    order_id=order_id,
                    saved="1",
                    source=source,
                )
            )
        if measurement_save_id.isdigit() and order_id.isdigit():
            measurement_id = int(measurement_save_id)
            target_order_id = int(order_id)
            current_order_status_row = conn.execute(
                "SELECT status FROM orders WHERE id = ? AND (customer_id = ? OR customer_display_id = ?)",
                (target_order_id, customer_id, customer_id),
            ).fetchone()
            if current_order_status_row and (str(current_order_status_row["status"] or "").strip() == "Cancelled"):
                conn.close()
                return redirect(
                    url_for(
                        "customer_detail",
                        customer_id=customer_id,
                        order_id=order_id,
                        cancelled="1",
                        source=source,
                    )
                )
            measurement_status = request.form.get(f"measurement_status_{measurement_id}", "").strip()
            if measurement_status not in allowed_measure_statuses:
                measurement_status = "In-Progress"
            measurement_row = conn.execute(
                """
                SELECT id, order_id
                FROM measurements
                WHERE id = ?
                  AND customer_id = ?
                """,
                (measurement_id, customer_id),
            ).fetchone()
            if measurement_row and (
                measurement_row["order_id"] is None or int(measurement_row["order_id"]) == target_order_id
            ):
                measurement_date = None
                if measurement_status in {"Completed", "Delivered"}:
                    measurement_date = datetime.now().date().isoformat()
                existing_measure = conn.execute(
                    "SELECT notes FROM measurements WHERE id = ?",
                    (measurement_id,),
                ).fetchone()
                current_completed_date, current_delivery_date = extract_measure_dates(
                    existing_measure["notes"] if existing_measure else None
                )
                next_completed_date = current_completed_date
                next_delivery_date = current_delivery_date
                if measurement_status == "Completed" and measurement_date:
                    next_completed_date = measurement_date
                if measurement_status == "Delivered" and measurement_date:
                    next_delivery_date = measurement_date
                updated_measure_notes = with_measure_dates(
                    existing_measure["notes"] if existing_measure else None,
                    next_completed_date,
                    next_delivery_date,
                )
                conn.execute(
                    "UPDATE measurements SET measure_status = ?, notes = ? WHERE id = ?",
                    (measurement_status, updated_measure_notes, measurement_id),
                )
                status_rows = conn.execute(
                    """
                    SELECT DISTINCT LTRIM(RTRIM(ISNULL(measure_status, '')))
                    FROM measurements
                    WHERE order_id = ?
                    """,
                    (target_order_id,),
                ).fetchall()
                derived_order_status = derive_order_status_from_measure_statuses(status_rows)

                current_order = conn.execute(
                    "SELECT status, completed_at, delivered_at FROM orders WHERE id = ?",
                    (target_order_id,),
                ).fetchone()
                previous_status = (current_order["status"] or "").strip() if current_order else ""
                completed_at = current_order["completed_at"] if current_order else None
                delivered_at = current_order["delivered_at"] if current_order else None
                if derived_order_status in {"Completed", "Delivered"}:
                    status_now = now_str()
                    completed_at = completed_at or status_now
                    delivered_at = delivered_at or status_now
                conn.execute(
                    """
                    UPDATE orders
                    SET status = ?, completed_at = ?, delivered_at = ?
                    WHERE id = ?
                      AND (customer_id = ? OR customer_display_id = ?)
                    """,
                    (derived_order_status, completed_at, delivered_at, target_order_id, customer_id, customer_id),
                )
                apply_order_payment_updates(target_order_id, payment_method, payment_amount)
                sync_completed_notification(conn, target_order_id, previous_status, derived_order_status, completed_at)
                conn.commit()
            conn.close()
            return redirect(
                url_for(
                    "customer_detail",
                    customer_id=customer_id,
                    order_id=order_id,
                    saved="1",
                    source=source,
                )
            )
        if order_status and order_id.isdigit():
            target_order_id = int(order_id)
            current = conn.execute(
                """
                SELECT status, completed_at, delivered_at
                FROM orders
                WHERE id = ?
                  AND (customer_id = ? OR customer_display_id = ?)
                """,
                (target_order_id, customer_id, customer_id),
            ).fetchone()
            previous_status = (current["status"] or "").strip() if current else ""
            if previous_status == "Cancelled" and order_status != "Cancelled":
                conn.close()
                return redirect(
                    url_for(
                        "customer_detail",
                        customer_id=customer_id,
                        order_id=target_order_id,
                        cancelled="1",
                        source=source,
                    )
                )
            completed_at = current["completed_at"] if current else None
            delivered_at = current["delivered_at"] if current else None
            if order_status in {"Completed", "Delivered"}:
                status_now = now_str()
                completed_at = completed_at or status_now
                delivered_at = delivered_at or status_now
            apply_order_payment_updates(target_order_id, payment_method, payment_amount)
            conn.execute(
                """
                UPDATE orders
                SET status = ?, completed_at = ?, delivered_at = ?
                WHERE id = ?
                  AND (customer_id = ? OR customer_display_id = ?)
                """,
                (
                    order_status,
                    completed_at,
                    delivered_at,
                    target_order_id,
                    customer_id,
                    customer_id,
                ),
            )
            sync_completed_notification(conn, target_order_id, previous_status, order_status, completed_at)
            conn.commit()
            conn.close()
            return redirect(url_for("customer_detail", customer_id=customer_id, order_id=target_order_id, saved="1", source=source))
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        notes = request.form.get("notes", "").strip()
        if name and phone:
            if not is_valid_phone(phone):
                conn.close()
                return redirect(url_for("customer_detail", customer_id=customer_id, phone_error="1"))
            conn.execute(
                "UPDATE customers SET name = ?, phone = ?, address = ?, notes = ? WHERE id = ?",
                (name, phone, address, notes, customer_id),
            )
            conn.commit()

    customer = conn.execute(
        "SELECT * FROM customers WHERE id = ?", (customer_id,)
    ).fetchone()
    if customer:
        customer = dict(customer)
        customer["display_id"] = customer_display_id(int(customer["id"]))
    orders = conn.execute(
        """
        SELECT * FROM orders
        WHERE customer_id = ?
           OR customer_display_id = ?
        ORDER BY created_at DESC
        """,
        (customer_id, customer_id),
    ).fetchall()
    order_measure_counts: dict[int, int] = {}
    order_measure_ids: dict[int, list[int]] = {}
    if orders:
        order_ids = [int(row["id"]) for row in orders if row["id"] is not None]
        if order_ids:
            placeholders = ",".join("?" for _ in order_ids)
            measure_rows = conn.execute(
                f"""
                SELECT id, order_id
                FROM measurements
                WHERE order_id IN ({placeholders})
                ORDER BY id ASC
                """,
                tuple(order_ids),
            ).fetchall()
            for row in measure_rows:
                if row["order_id"] is None or row["id"] is None:
                    continue
                oid = int(row["order_id"])
                order_measure_ids.setdefault(oid, []).append(int(row["id"]))
            count_rows = conn.execute(
                f"""
                SELECT order_id, COUNT(*) AS measure_count
                FROM measurements
                WHERE order_id IN ({placeholders})
                GROUP BY order_id
                """,
                tuple(order_ids),
            ).fetchall()
            order_measure_counts = {
                int(row["order_id"]): int(row["measure_count"] or 0)
                for row in count_rows
                if row["order_id"] is not None
            }
    selected_order_id = request.args.get("order_id", "").strip()
    selected_order = None
    if selected_order_id.isdigit():
        selected_id = int(selected_order_id)
        for order in orders:
            if order["id"] == selected_id:
                selected_order = order
                break
    measurements = []
    measurement_by_kind = []
    latest_order = orders[0] if orders else None
    if not selected_order:
        selected_order = latest_order
    latest_measure = None
    if selected_order:
        measurements = fetch_order_measurements(
            conn,
            int(customer_id),
            int(selected_order["id"]),
            selected_order["created_at"],
        )
        latest_measure = measurements[0] if measurements else None
    images = []
    images_by_item = {}
    customer_images = []
    requirement_icons = []
    order_items = []
    material_items = []
    worker_delivery_date = None
    if selected_order:
        if selected_order["notes"]:
            for line in selected_order["notes"].splitlines():
                if line.lower().startswith("worker delivery date:"):
                    worker_delivery_date = date_only(line.split(":", 1)[1].strip())
                    break
        images = conn.execute(
            "SELECT filename, label, item_type FROM order_images WHERE order_id = ?",
            (selected_order["id"],),
        ).fetchall()
        for img in images:
            key = img["item_type"] or "Uncategorized"
            key_norm = (key or "").strip().lower()
            label_norm = str(img["label"] or "").strip().lower()
            if key_norm == "customer" or label_norm == "customer":
                customer_images.append(img)
                continue
            images_by_item.setdefault(key, []).append(img)
        if not customer_images:
            fallback_customer_photo = conn.execute(
                """
                SELECT oi.filename, oi.label, oi.item_type
                FROM order_images oi
                JOIN orders o ON o.id = oi.order_id
                WHERE o.customer_id = ?
                  AND (
                    LOWER(LTRIM(RTRIM(COALESCE(oi.item_type, '')))) = 'customer'
                    OR LOWER(LTRIM(RTRIM(COALESCE(oi.label, '')))) = 'customer'
                  )
                ORDER BY oi.id DESC
                LIMIT 1
                """,
                (int(customer_id),),
            ).fetchall()
            if fallback_customer_photo:
                customer_images = list(fallback_customer_photo)
        material_items = conn.execute(
            """
            SELECT inventory.name AS item_name,
                   order_material_items.qty,
                   uoms.name AS uom_name,
                   order_material_items.unit_price,
                   order_material_items.line_total
            FROM order_material_items
            JOIN inventory ON inventory.id = order_material_items.inventory_id
            LEFT JOIN uoms ON uoms.id = order_material_items.uom_id
            WHERE order_material_items.order_id = ?
            """,
            (selected_order["id"],),
        ).fetchall()
        if selected_order["order_type"] == "Material":
            order_items = conn.execute(
                """
                SELECT inventory.name AS item_type, order_material_items.qty, uoms.name AS uom_name
                FROM order_material_items
                JOIN inventory ON inventory.id = order_material_items.inventory_id
                LEFT JOIN uoms ON uoms.id = order_material_items.uom_id
                WHERE order_material_items.order_id = ?
                """,
                (selected_order["id"],),
            ).fetchall()
        else:
            order_items = conn.execute(
                "SELECT item_type, qty, NULL AS uom_name FROM order_items WHERE order_id = ?",
                (selected_order["id"],),
            ).fetchall()
        def normalize_measure_type(raw_value: str | None) -> str:
            text = (raw_value or "").strip().lower()
            if not text:
                return ""
            base = text.split("-", 1)[0].strip()
            if base in {"s001", "shirt"}:
                return "shirt"
            if base in {"p001", "pant", "trouser", "jean", "jeans"}:
                return "pant"
            if base in {"coat", "blazer", "safari"}:
                return "coat"
            return base or text

        allowed_types = {
            normalize_measure_type(item["item_type"])
            for item in order_items
            if item["item_type"]
        }
        allowed_types = {value for value in allowed_types if value}
        if allowed_types:
            seen_kinds = set()
            matched_types = set()
            for row in measurements:
                kind = row["kind"] or ""
                kind_lower = kind.lower()
                kind_norm = normalize_measure_type(kind)
                if kind_norm not in allowed_types and not any(t in kind_lower for t in allowed_types):
                    continue
                if kind in seen_kinds:
                    continue
                seen_kinds.add(kind)
                measurement_by_kind.append(row)
                if kind_norm:
                    matched_types.add(kind_norm)
        else:
            measurement_by_kind = []
        requirement_icons = conn.execute(
            "SELECT name, filename FROM requirement_icons"
        ).fetchall()
    due_amount = 0
    selected_payment_mode = "Cash"
    measurement_status_summary: list[str] = []
    completed_date_display = None
    delivery_date_display = None
    if selected_order:
        total_amount = float(selected_order["total_amount"] or 0)
        advance_amount = float(selected_order["advance_amount"] or 0)
        paid_amount = float(selected_order["paid_amount"] or 0)
        due_amount = max(total_amount - advance_amount - paid_amount, 0)
        selected_payment_mode = extract_payment_mode(selected_order["notes"])
        if selected_payment_mode not in allowed_payment_methods:
            selected_payment_mode = "Cash"
        completed_date_display = selected_order["completed_at"] if "completed_at" in selected_order.keys() and selected_order["completed_at"] else worker_delivery_date
        delivery_date_display = selected_order["delivered_at"] if "delivered_at" in selected_order.keys() and selected_order["delivered_at"] else selected_order["due_date"]
        seen_status_kinds: set[str] = set()
        display_index = 0
        for mrow in measurement_by_kind:
            kind_text = str(mrow["kind"] or "").strip() or "Item"
            kind_key = kind_text.lower()
            if kind_key in seen_status_kinds:
                continue
            seen_status_kinds.add(kind_key)
            display_index += 1
            status_text = str(mrow["measure_status"] or "").strip() or str(selected_order["status"] or "In-Progress")
            measurement_status_summary.append(f"{display_index}-{status_text}")
        if not measurement_status_summary:
            measurement_status_summary.append(str(selected_order["status"] or "In-Progress"))
    conn.close()
    return render_template(
        "customer_detail.html",
        customer=customer,
        orders=orders,
        order_measure_counts=order_measure_counts,
        order_measure_ids=order_measure_ids,
        latest_order=selected_order,
        selected_order_id=selected_order["id"] if selected_order else None,
        latest_measure=latest_measure,
        measurements=measurement_by_kind,
        images=images,
        images_by_item=images_by_item,
        customer_images=customer_images,
        due_amount=due_amount,
        requirement_icons=requirement_icons,
        order_items=order_items,
        material_items=material_items,
        worker_delivery_date=worker_delivery_date,
        completed_date_display=completed_date_display,
        delivery_date_display=delivery_date_display,
        selected_payment_mode=selected_payment_mode,
        measurement_status_summary=measurement_status_summary,
        auto_print_on_click=get_setting("auto_print_on_click", "0") == "1",
    )


@app.route("/inventory", methods=["GET", "POST"])
def inventory():
    conn = get_db()
    if request.method == "POST":
        if request.form.get("action") == "update":
            try:
                cost_price = max(float(request.form.get("cost_price", "0") or 0), 0.0)
            except (TypeError, ValueError):
                cost_price = 0.0
            try:
                selling_price = max(float(request.form.get("selling_price", "0") or 0), 0.0)
            except (TypeError, ValueError):
                selling_price = 0.0
            conn.execute(
                """
                UPDATE inventory
                SET qty = ?, uom_id = ?, inventory_code = ?, cost_price = ?, selling_price = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    int(request.form.get("qty", "0") or 0),
                    int(request.form.get("uom_id") or 0) or None,
                    request.form.get("inventory_code", "").strip() or None,
                    cost_price,
                    selling_price,
                    now_str(),
                    int(request.form.get("item_id")),
                ),
            )
        conn.commit()

    items = conn.execute(
        """
        SELECT inventory.*, uoms.name AS uom_name
        FROM inventory
        LEFT JOIN uoms ON uoms.id = inventory.uom_id
        ORDER BY inventory.name ASC
        """
    ).fetchall()
    conn.close()
    return render_template("inventory.html", items=items)


@app.route("/inventory/add", methods=["GET", "POST"])
def inventory_add():
    conn = get_db()
    uoms = conn.execute("SELECT * FROM uoms ORDER BY name ASC").fetchall()
    vendors = conn.execute("SELECT * FROM vendors ORDER BY name ASC").fetchall()
    if request.method == "POST":
        names = request.form.getlist("item_name")
        item_codes = request.form.getlist("item_code")
        vendors_in = request.form.getlist("item_vendor")
        qtys = request.form.getlist("item_qty")
        uoms_in = request.form.getlist("item_uom_id")
        costs_in = request.form.getlist("item_cost_price")
        selling_in = request.form.getlist("item_selling_price")

        total_rows = max(
            len(names),
            len(item_codes),
            len(vendors_in),
            len(qtys),
            len(uoms_in),
            len(costs_in),
            len(selling_in),
        )
        if total_rows <= 0:
            conn.close()
            return render_template(
                "inventory_add.html",
                uoms=uoms,
                vendors=vendors,
                error="Please fill all input boxes.",
            )

        def pick(values: list[str], idx: int) -> str:
            return values[idx] if idx < len(values) else ""

        used_codes = set()
        for idx in range(total_rows):
            name = pick(names, idx).strip()
            item_code = pick(item_codes, idx).strip()
            vendor = pick(vendors_in, idx).strip()
            qty = pick(qtys, idx).strip()
            uom_id = pick(uoms_in, idx).strip()
            cost_price = pick(costs_in, idx).strip()
            selling_price = pick(selling_in, idx).strip()

            if not all([name, item_code, vendor, qty, uom_id, cost_price, selling_price]):
                conn.close()
                return render_template(
                    "inventory_add.html",
                    uoms=uoms,
                    vendors=vendors,
                    error=f"Please fill all input boxes for Item {idx + 1}.",
                )

            try:
                qty_value = int(qty)
            except (TypeError, ValueError):
                conn.close()
                return render_template(
                    "inventory_add.html",
                    uoms=uoms,
                    vendors=vendors,
                    error=f"Invalid quantity for Item {idx + 1}.",
                )
            if qty_value < 0:
                conn.close()
                return render_template(
                    "inventory_add.html",
                    uoms=uoms,
                    vendors=vendors,
                    error=f"Quantity cannot be negative for Item {idx + 1}.",
                )
            try:
                cost_value = max(float(cost_price or 0), 0.0)
            except (TypeError, ValueError):
                conn.close()
                return render_template(
                    "inventory_add.html",
                    uoms=uoms,
                    vendors=vendors,
                    error=f"Invalid cost value for Item {idx + 1}.",
                )
            try:
                selling_value = max(float(selling_price or 0), 0.0)
            except (TypeError, ValueError):
                conn.close()
                return render_template(
                    "inventory_add.html",
                    uoms=uoms,
                    vendors=vendors,
                    error=f"Invalid selling value for Item {idx + 1}.",
                )
            inventory_code = item_code.upper()
            if inventory_code in used_codes:
                conn.close()
                return render_template(
                    "inventory_add.html",
                    uoms=uoms,
                    vendors=vendors,
                    error=f"Duplicate inventory code in form: {inventory_code}",
                )
            exists = conn.execute(
                "SELECT id FROM inventory WHERE inventory_code = ?",
                (inventory_code,),
            ).fetchone()
            if exists:
                conn.close()
                return render_template(
                    "inventory_add.html",
                    uoms=uoms,
                    vendors=vendors,
                    error=f"Inventory code already exists: {inventory_code}",
                )
            used_codes.add(inventory_code)
            conn.execute(
                """
                INSERT INTO inventory (inventory_code, name, supplier, qty, uom_id, cost_price, selling_price, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    inventory_code,
                    name,
                    vendor,
                    qty_value,
                    int(uom_id or 0) or None,
                    cost_value,
                    selling_value,
                    now_str(),
                ),
            )

        conn.commit()
        conn.close()
        return redirect(url_for("inventory"))
    conn.close()
    return render_template("inventory_add.html", uoms=uoms, vendors=vendors)


@app.route("/inventory/<int:item_id>/edit", methods=["GET", "POST"])
def inventory_edit(item_id: int):
    view_only = request.args.get("mode", "").strip().lower() == "view"
    conn = get_db()
    item = conn.execute(
        "SELECT * FROM inventory WHERE id = ?",
        (item_id,),
    ).fetchone()
    uoms = conn.execute("SELECT * FROM uoms ORDER BY name ASC").fetchall()
    vendors = conn.execute("SELECT * FROM vendors ORDER BY name ASC").fetchall()
    if not item:
        conn.close()
        return redirect(url_for("inventory"))
    if request.method == "POST":
        if view_only:
            conn.close()
            return redirect(url_for("inventory_edit", item_id=item_id, mode="view"))
        name = request.form.get("name", "").strip()
        if not name:
            conn.close()
            return render_template(
                "inventory_edit.html",
                item=item,
                uoms=uoms,
                vendors=vendors,
                view_only=view_only,
                error="Item name is required.",
            )
        try:
            cost_price = max(float(request.form.get("cost_price", "0") or 0), 0.0)
        except (TypeError, ValueError):
            cost_price = 0.0
        try:
            selling_price = max(float(request.form.get("selling_price", "0") or 0), 0.0)
        except (TypeError, ValueError):
            selling_price = 0.0
        conn.execute(
            """
            UPDATE inventory
            SET name = ?, supplier = ?, qty = ?, uom_id = ?, cost_price = ?, selling_price = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                name,
                request.form.get("supplier", "").strip() or None,
                int(request.form.get("qty", "0") or 0),
                int(request.form.get("uom_id") or 0) or None,
                cost_price,
                selling_price,
                now_str(),
                item_id,
            ),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("inventory"))
    conn.close()
    return render_template("inventory_edit.html", item=item, uoms=uoms, vendors=vendors, view_only=view_only)


@app.route("/inventory/<int:item_id>/delete", methods=["POST"])
def inventory_delete(item_id: int):
    conn = get_db()
    conn.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("inventory"))


@app.route("/vendors")
def vendors():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT v.*,
               (SELECT MAX(purchased_at) FROM vendor_purchase_orders WHERE vendor_id = v.id) AS last_order_at,
               (SELECT COALESCE(SUM(total_amount), 0) FROM vendor_purchase_orders WHERE vendor_id = v.id) AS spent
        FROM vendors v
        ORDER BY v.created_at DESC
        """
    ).fetchall()
    purchases = conn.execute(
        """
        SELECT vpo.*,
               v.vendor_code,
               v.name AS vendor_name
        FROM vendor_purchase_orders vpo
        JOIN vendors v ON v.id = vpo.vendor_id
        ORDER BY vpo.purchased_at DESC
        """
    ).fetchall()
    conn.close()
    return render_template("vendors.html", vendors=rows, purchases=purchases)


@app.route("/vendors/<int:vendor_id>")
def vendors_detail(vendor_id: int):
    conn = get_db()
    vendor = conn.execute(
        "SELECT * FROM vendors WHERE id = ?",
        (vendor_id,),
    ).fetchone()
    if not vendor:
        conn.close()
        return redirect(url_for("vendors"))
    purchases = conn.execute(
        """
        SELECT
            vpo.id,
            vpo.purchase_no,
            vpo.total_amount,
            vpo.paid_amount,
            vpo.status,
            vpo.payment_mode,
            vpo.purchased_at
        FROM vendor_purchase_orders vpo
        WHERE vpo.vendor_id = ?
        ORDER BY vpo.purchased_at DESC, vpo.id DESC
        """,
        (vendor_id,),
    ).fetchall()
    conn.close()
    return render_template(
        "vendors_detail.html",
        vendor=vendor,
        purchases=purchases,
    )


@app.route("/vendors/add", methods=["GET", "POST"])
def vendors_add():
    conn = get_db()
    vendor_code = generate_vendor_code(conn)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        if not name:
            conn.close()
            return render_template(
                "vendors_add.html",
                vendor_code=vendor_code,
                error="Vendor name is required.",
            )
        if not phone:
            conn.close()
            return render_template(
                "vendors_add.html",
                vendor_code=vendor_code,
                error="Phone number is required.",
            )
        if not address:
            conn.close()
            return render_template(
                "vendors_add.html",
                vendor_code=vendor_code,
                error="Address is required.",
            )
        if phone and not is_valid_phone(phone):
            conn.close()
            return render_template(
                "vendors_add.html",
                vendor_code=vendor_code,
                error="Phone number can contain only digits and leading +.",
            )
        conn.execute(
            """
            INSERT INTO vendors (vendor_code, name, phone, email, address, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                vendor_code,
                name,
                phone or None,
                request.form.get("email", "").strip() or None,
                address,
                now_str(),
            ),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("vendors"))
    conn.close()
    return render_template("vendors_add.html", vendor_code=vendor_code)


@app.route("/vendors/<int:vendor_id>/edit", methods=["GET", "POST"])
def vendors_edit(vendor_id: int):
    conn = get_db()
    vendor = conn.execute(
        "SELECT * FROM vendors WHERE id = ?",
        (vendor_id,),
    ).fetchone()
    if not vendor:
        conn.close()
        return redirect(url_for("vendors"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        if not name:
            name = str(vendor["name"] or "").strip()
        if phone and not is_valid_phone(phone):
            conn.close()
            return render_template(
                "vendors_edit.html",
                vendor=vendor,
                error="Phone number can contain only digits and leading +.",
            )
        conn.execute(
            """
            UPDATE vendors
            SET name = ?, phone = ?, email = ?, address = ?
            WHERE id = ?
            """,
            (
                name,
                phone or None,
                request.form.get("email", "").strip() or None,
                request.form.get("address", "").strip() or None,
                vendor_id,
            ),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("vendors"))
    conn.close()
    return render_template("vendors_edit.html", vendor=vendor)


@app.route("/vendors/<int:vendor_id>/delete", methods=["POST"])
def vendors_delete(vendor_id: int):
    conn = get_db()
    purchase_ids = conn.execute(
        "SELECT id FROM vendor_purchase_orders WHERE vendor_id = ?",
        (vendor_id,),
    ).fetchall()
    for row in purchase_ids:
        conn.execute("DELETE FROM vendor_purchase_items WHERE purchase_id = ?", (row["id"],))
        conn.execute("DELETE FROM vendor_purchase_images WHERE purchase_id = ?", (row["id"],))
    conn.execute("DELETE FROM vendor_purchase_orders WHERE vendor_id = ?", (vendor_id,))
    conn.execute("DELETE FROM vendors WHERE id = ?", (vendor_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("vendors"))


@app.route("/vendors/purchase", methods=["GET", "POST"])
def vendors_add_purchase():
    conn = get_db()
    vendors = conn.execute("SELECT * FROM vendors ORDER BY name ASC").fetchall()
    next_purchase_no = generate_purchase_no(conn)
    inventory = conn.execute(
        """
        SELECT inventory.id, inventory.name, inventory.qty, inventory.uom_id,
               uoms.name AS uom_name
        FROM inventory
        LEFT JOIN uoms ON uoms.id = inventory.uom_id
        ORDER BY inventory.name ASC
        """
    ).fetchall()
    if request.method == "POST":
        vendor_id = request.form.get("vendor_id")
        item_ids = request.form.getlist("purchase_item_id")
        qtys = request.form.getlist("purchase_qty")
        prices = request.form.getlist("purchase_unit_price")
        selling_prices = request.form.getlist("purchase_selling_price")
        paid_raw = request.form.get("paid_amount", "").strip()
        paid_amount = float(paid_raw) if paid_raw else 0
        payment_mode = normalize_payment_mode(request.form.get("payment_mode", "Cash"))

        if not vendor_id:
            conn.close()
            return render_template(
                "vendors_purchase_add.html",
                vendors=vendors,
                inventory=inventory,
                next_purchase_no=next_purchase_no,
                error="Vendor is required.",
            )

        has_item = any(item_id.strip() for item_id in item_ids)
        if not has_item:
            conn.close()
            return render_template(
                "vendors_purchase_add.html",
                vendors=vendors,
                inventory=inventory,
                next_purchase_no=next_purchase_no,
                error="At least one material is required.",
            )

        inv_rows = conn.execute("SELECT id, qty, uom_id, name FROM inventory").fetchall()
        inv_map = {str(row["id"]): row for row in inv_rows}

        items = []
        total_amount = 0
        for item_id, qty, price, sell_price in zip(item_ids, qtys, prices, selling_prices, strict=False):
            if not item_id or item_id not in inv_map:
                continue
            try:
                qty_val = float(qty or 0)
                price_val = float(price or 0)
                sell_val = float(sell_price or 0)
            except ValueError:
                continue
            if qty_val <= 0 or price_val < 0:
                continue
            line_total = qty_val * price_val
            total_amount += line_total
            items.append(
                (
                    int(item_id),
                    qty_val,
                    price_val,
                    sell_val,
                    line_total,
                    inv_map[item_id]["uom_id"],
                    (inv_map[item_id]["name"] or "").strip() or None,
                )
            )

        if not items or total_amount <= 0:
            conn.close()
            return render_template(
                "vendors_purchase_add.html",
                vendors=vendors,
                inventory=inventory,
                next_purchase_no=next_purchase_no,
                error="Enter valid items with quantity and unit price.",
            )

        if paid_amount < 0:
            paid_amount = 0
        status = "Unpaid"
        if paid_amount >= total_amount:
            paid_amount = total_amount
            status = "Paid"
        elif paid_amount > 0:
            status = "Partial"

        notes = request.form.get("notes", "").strip() or None
        created_at = now_str()
        cur = conn.cursor()
        purchase_no = generate_purchase_no(conn)
        cur.execute(
            """
            INSERT INTO vendor_purchase_orders
                (purchase_no, vendor_id, total_amount, paid_amount, status, payment_mode, notes, purchased_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                purchase_no,
                int(vendor_id),
                total_amount,
                paid_amount,
                status,
                payment_mode,
                notes,
                created_at,
                created_at,
            ),
        )
        purchase_id = cur.lastrowid
        if purchase_id is None:
            conn.rollback()
            conn.close()
            return render_template(
                "vendors_purchase_add.html",
                vendors=vendors,
                inventory=inventory,
                next_purchase_no=next_purchase_no,
                error="Failed to create purchase order. Please try again.",
            )
        for inventory_id, qty_val, price_val, sell_val, line_total, uom_id, item_name_snapshot in items:
            cur.execute(
                """
                INSERT INTO vendor_purchase_items
                    (purchase_id, inventory_id, uom_id, qty, unit_price, selling_price, line_total, item_name_snapshot)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (purchase_id, inventory_id, uom_id, qty_val, price_val, sell_val, line_total, item_name_snapshot),
            )
            inv_qty = inv_map[str(inventory_id)]["qty"]
            new_qty = float(inv_qty or 0) + qty_val
            cur.execute(
                "UPDATE inventory SET qty = ?, updated_at = ?, cost_price = ?, selling_price = ? WHERE id = ?",
                (new_qty, now_str(), price_val, sell_val, inventory_id),
            )

        files = request.files.getlist("bill_images")
        for file in files:
            if not file or not file.filename:
                continue
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            cur.execute(
                "INSERT INTO vendor_purchase_images (purchase_id, filename) VALUES (?, ?)",
                (purchase_id, filename),
            )

        conn.commit()
        conn.close()
        return redirect(url_for("vendors"))

    conn.close()
    return render_template(
        "vendors_purchase_add.html",
        vendors=vendors,
        inventory=inventory,
        next_purchase_no=next_purchase_no,
    )


@app.route("/vendors/purchase/<int:purchase_id>")
def vendors_purchase_detail(purchase_id: int):
    conn = get_db()
    purchase = conn.execute(
        """
        SELECT vpo.*, v.vendor_code, v.name AS vendor_name
        FROM vendor_purchase_orders vpo
        JOIN vendors v ON v.id = vpo.vendor_id
        WHERE vpo.id = ?
        """,
        (purchase_id,),
    ).fetchone()
    if not purchase:
        conn.close()
        return redirect(url_for("vendors"))
    items = conn.execute(
        """
        SELECT
            vpi.inventory_id,
            COALESCE(vpi.item_name_snapshot, inventory.name) AS item_name,
            CAST(COALESCE(vpi.qty, 0) AS FLOAT) AS qty,
            uoms.name AS uom_name,
            CAST(COALESCE(vpi.unit_price, 0) AS FLOAT) AS unit_price,
            CAST(COALESCE(vpi.line_total, 0) AS FLOAT) AS line_total
        FROM vendor_purchase_items vpi
        LEFT JOIN inventory ON inventory.id = vpi.inventory_id
        LEFT JOIN uoms ON uoms.id = vpi.uom_id
        WHERE vpi.purchase_id = ?
        ORDER BY vpi.id ASC
        """,
        (purchase_id,),
    ).fetchall()
    images = conn.execute(
        "SELECT filename FROM vendor_purchase_images WHERE purchase_id = ?",
        (purchase_id,),
    ).fetchall()
    conn.close()
    return render_template(
        "vendors_purchase_detail.html",
        purchase=purchase,
        items=items,
        images=images,
    )

@app.route("/vendors/purchase/<int:purchase_id>/pay", methods=["POST"])
def vendors_purchase_pay(purchase_id: int):
    amount_raw = request.form.get("pay_amount", "").strip()
    payment_mode = normalize_payment_mode(request.form.get("payment_mode", "Cash"))
    try:
        pay_amount = float(amount_raw)
    except ValueError:
        pay_amount = 0
    if pay_amount <= 0:
        return redirect(url_for("vendors_purchase_detail", purchase_id=purchase_id))
    conn = get_db()
    purchase = conn.execute(
        "SELECT total_amount, paid_amount FROM vendor_purchase_orders WHERE id = ?",
        (purchase_id,),
    ).fetchone()
    if not purchase:
        conn.close()
        return redirect(url_for("vendors"))
    total_amount = float(purchase["total_amount"] or 0)
    paid_amount = float(purchase["paid_amount"] or 0)
    new_paid = min(total_amount, paid_amount + pay_amount)
    status = "Unpaid"
    if new_paid >= total_amount:
        status = "Paid"
    elif new_paid > 0:
        status = "Partial"
    conn.execute(
        "UPDATE vendor_purchase_orders SET paid_amount = ?, status = ?, payment_mode = ? WHERE id = ?",
        (new_paid, status, payment_mode, purchase_id),
    )
    conn.commit()
    conn.close()
    return redirect(url_for("vendors_purchase_detail", purchase_id=purchase_id))


@app.route("/vendors/purchase/<int:purchase_id>/delete", methods=["POST"])
def vendors_purchase_delete(purchase_id: int):
    conn = get_db()
    items = conn.execute(
        "SELECT inventory_id, qty FROM vendor_purchase_items WHERE purchase_id = ?",
        (purchase_id,),
    ).fetchall()
    for item in items:
        inv = conn.execute(
            "SELECT qty FROM inventory WHERE id = ?",
            (item["inventory_id"],),
        ).fetchone()
        current_qty = float(inv["qty"] or 0) if inv else 0
        new_qty = max(current_qty - float(item["qty"] or 0), 0)
        conn.execute(
            "UPDATE inventory SET qty = ?, updated_at = ? WHERE id = ?",
            (new_qty, now_str(), item["inventory_id"]),
        )
    conn.execute("DELETE FROM vendor_purchase_items WHERE purchase_id = ?", (purchase_id,))
    conn.execute("DELETE FROM vendor_purchase_images WHERE purchase_id = ?", (purchase_id,))
    conn.execute("DELETE FROM vendor_purchase_orders WHERE id = ?", (purchase_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("vendors"))


# if __name__ == "__main__":
#     init_db()
#     app.run(debug=True)
@app.route("/fonts/<path:filename>")
def serve_font_file(filename: str):
    return send_from_directory(FONTS_FOLDER, filename)


import threading
import webbrowser

if __name__ == "__main__":

    init_license_db()

    valid, message, warning = validate_license()

    if not valid:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            message,
            "License Error",
            0
        )
        sys.exit()

    if warning:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            warning,
            "License Expiry Warning",
            0
        )

    # â­ ADD THIS PART â†“
    def open_browser():
        webbrowser.open("http://127.0.0.1:5000")

    threading.Timer(1.5, open_browser).start()

    # run flask
    app.run(host="127.0.0.1", port=5000, debug=False)



