import os
import sys
import sqlite3
from datetime import datetime

from flask import Flask, render_template, request
from cryptography.fernet import Fernet
from machine_id import get_machine_id

app = Flask(__name__)

# ---------------- APP PATH ----------------

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = get_app_dir()
DB_FILE = os.path.join(APP_DIR, "license_db.sqlite")
print(f"Using DB file: {DB_FILE}")

# Global encryption objects
fernet = None


# ---------------- DB INIT ----------------

from dotenv import load_dotenv

def init_system():
    # 1️⃣ Create .env if not exists
    env_path = os.path.join(APP_DIR, ".env1")

    if not os.path.exists(env_path):
        new_key = Fernet.generate_key().decode()
        with open(env_path, "w") as f:
            f.write(f"FERNET_SECRET={new_key}")
        print("Created new .env with secret key.")

    # 2️⃣ Load secret
    load_dotenv(env_path)
    secret = os.getenv("FERNET_SECRET")

    # 3️⃣ Create DB + licenses table
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT,
            license_code TEXT,
            expiry_date TEXT
        )
    """)

    con.commit()
    con.close()

    return secret

# ---------------- LICENSE GENERATE ----------------

def generate_license(machine_id, expiry_date):
    payload = f"{machine_id}|{expiry_date}"
    code = fernet.encrypt(payload.encode()).decode()

    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO licenses(machine_id, license_code, expiry_date) VALUES (?, ?, ?)",
        (machine_id, code, expiry_date)
    )
    con.commit()
    con.close()

    return code


# ---------------- ROUTES ----------------

@app.route("/", methods=["GET", "POST"])
def index():
    license_code = None
    error = None

    # Default: generate for THIS machine
    # machine_id = get_machine_id()
    machine_id = get_machine_id()

    if request.method == "POST":
        machine_id = request.form.get("machine_id")
        expiry_date = request.form.get("expiry_date")

    if request.method == "POST":
        expiry_date = request.form.get("expiry_date")

        if not expiry_date:
            error = "Expiry date is required."

        elif datetime.fromisoformat(expiry_date).date() <= datetime.now().date():
            error = "Expiry date must be in the future."

        else:
            license_code = generate_license(machine_id, expiry_date)

    return render_template(
        "licence_generator.html",
        machine_id=machine_id,
        license_code=license_code,
        error=error
    )


# ---------------- RUN ----------------

if __name__ == "__main__":

    secret_key = init_system()
    fernet = Fernet(secret_key.encode())

    app.run(debug=False)
