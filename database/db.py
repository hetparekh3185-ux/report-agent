import os
import pymysql
import pymysql.cursors
from contextlib import contextmanager
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()  # don't rely on the importer having loaded .env first

# ca.pem lives at the project root; db.py is one level down in database/.
# Resolve an absolute path so it works regardless of the process working
# directory (Render does NOT run the app from the repo root in all setups).
_CA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ca.pem")

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST") or os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT") or os.getenv("DB_PORT", 3306)),
    "user": os.getenv("MYSQL_USER") or os.getenv("DB_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD") or os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE") or os.getenv("DB_NAME", "report_agent"),
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
    "ssl": {"ca": _CA_PATH},
}


@contextmanager
def get_connection():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """
    Tables are created by the SQL script (CREATE DATABASE / CREATE TABLE
    with the users/reports schema you already ran). This just fails fast
    with a clear error if the DB isn't reachable or the schema is missing,
    instead of the Flask app silently 500ing on the first query.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES LIKE 'users'")
            if not cur.fetchone():
                raise RuntimeError(
                    "'users' table not found. Run the CREATE DATABASE/CREATE TABLE "
                    "script against MySQL before starting the app."
                )
            cur.execute("SHOW TABLES LIKE 'reports'")
            if not cur.fetchone():
                raise RuntimeError(
                    "'reports' table not found. Run the CREATE DATABASE/CREATE TABLE "
                    "script against MySQL before starting the app."
                )


def create_user(username: str, email: str, password: str):
    """Returns (True, None) on success, or (False, error_message)."""
    password_hash = generate_password_hash(password)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                    (username, email, password_hash),
                )
        return True, None
    except pymysql.err.IntegrityError:
        return False, "That username or email is already taken."


def verify_user(username: str, password: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
    if row and check_password_hash(row["password_hash"], password):
        return row
    return None


def save_report(user_id: int, topic: str, report_name: str, file_path: str, file_type: str):
    """
    One row per physical file, matching the schema's file_type enum. If a
    generation produces both a .docx and a .pdf, call this twice (see
    save_report_files below for the common case).
    """
    if file_type not in ("docx", "pdf"):
        raise ValueError("file_type must be 'docx' or 'pdf'")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO reports (user_id, topic, report_name, file_path, file_type)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, topic, report_name, file_path, file_type),
            )


def save_report_files(user_id: int, topic: str, docx: dict, pdf: dict = None):
    """
    Convenience wrapper: docx = {"report_name": ..., "file_path": ...},
    pdf (optional) same shape. Inserts both rows in a single transaction
    so a docx row is never saved without its matching pdf row (or vice
    versa) if something fails partway through.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO reports (user_id, topic, report_name, file_path, file_type)
                   VALUES (%s, %s, %s, %s, 'docx')""",
                (user_id, topic, docx["report_name"], docx["file_path"]),
            )
            if pdf:
                cur.execute(
                    """INSERT INTO reports (user_id, topic, report_name, file_path, file_type)
                       VALUES (%s, %s, %s, %s, 'pdf')""",
                    (user_id, topic, pdf["report_name"], pdf["file_path"]),
                )


def user_owns_file(user_id: int, filename: str) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM reports WHERE user_id = %s AND report_name = %s",
                (user_id, filename),
            )
            return cur.fetchone() is not None


def get_reports_for_user(user_id: int):
    """
    Groups the per-file rows back into one entry per (topic, created_at)
    so the dashboard can show one line per generation with both download
    links, instead of two separate list items for the same report.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM reports WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            )
            rows = cur.fetchall()

    grouped = {}
    ordered_keys = []
    for row in rows:
        key = (row["topic"], row["created_at"])
        if key not in grouped:
            grouped[key] = {
                "topic": row["topic"],
                "created_at": row["created_at"],
                "report_name": None,
                "pdf_name": None,
            }
            ordered_keys.append(key)
        if row["file_type"] == "docx":
            grouped[key]["report_name"] = row["report_name"]
        elif row["file_type"] == "pdf":
            grouped[key]["pdf_name"] = row["report_name"]

    return [grouped[k] for k in ordered_keys]
