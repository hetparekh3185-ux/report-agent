import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash, jsonify
from dotenv import load_dotenv

load_dotenv()

from database import db
from services import report_generator, word_generator, pdf_generator
from utils.helpers import slugify

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

GENERATED_REPORTS_DIR = os.path.join(os.path.dirname(__file__), "generated_reports")
os.makedirs(GENERATED_REPORTS_DIR, exist_ok=True)


def login_required(view):
    """Decorator: redirect to /login if there's no active session."""
    from functools import wraps

    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.before_request
def ensure_db():
    db.init_db()


# ---------------------------------------------------------------- routes ---

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    user = db.verify_user(username, password)
    if not user:
        flash("Invalid username or password.")
        return redirect(url_for("login"))

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return redirect(url_for("dashboard"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not username or not email or not password:
        flash("All fields are required.")
        return redirect(url_for("register"))

    if len(password) < 8:
        flash("Password must be at least 8 characters.")
        return redirect(url_for("register"))

    ok, error = db.create_user(username, email, password)
    if not ok:
        flash(error)
        return redirect(url_for("register"))

    flash("Account created. Please log in.")
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/dashboard-data")
@login_required
def dashboard_data():
    reports = db.get_reports_for_user(session["user_id"])
    return jsonify(username=session.get("username", "User"), reports=reports)


@app.route("/generate", methods=["POST"])
@login_required
def generate():
    """
    Body (JSON or form): { "topic": "..." }
    Runs Groq -> formats text -> writes .docx (and .pdf if requested) ->
    saves a row in the reports table -> returns the report id + filenames.
    """
    payload = request.get_json(silent=True) or request.form
    topic = (payload.get("topic") or "").strip()
    want_pdf = str(payload.get("want_pdf", "false")).lower() == "true"

    try:
        num_pages = int(payload.get("num_pages", 3))
        if num_pages <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "num_pages must be a positive integer."}), 400

    if not topic:
        return jsonify({"error": "Topic is required."}), 400

    try:
        report_text = report_generator.generate_report_text(topic, num_pages)
    except Exception as exc:  # GroqConfigError / GroqRequestError / network errors etc.
        return jsonify({"error": str(exc)}), 502

    report_id = str(uuid.uuid4())[:8]
    safe_topic = slugify(topic)
    docx_filename = f"{safe_topic}_{report_id}.docx"
    docx_path = os.path.join(GENERATED_REPORTS_DIR, docx_filename)
    word_generator.build_docx(topic=topic, body_text=report_text, output_path=docx_path)

    pdf_filename = None
    if want_pdf:
        pdf_filename = f"{safe_topic}_{report_id}.pdf"
        pdf_path = os.path.join(GENERATED_REPORTS_DIR, pdf_filename)
        pdf_generator.build_pdf(topic=topic, body_text=report_text, output_path=pdf_path)

    db.save_report_files(
        user_id=session["user_id"],
        topic=topic,
        docx={"report_name": docx_filename, "file_path": docx_path},
        pdf={"report_name": pdf_filename, "file_path": pdf_path} if want_pdf else None,
    )

    return jsonify(
        {
            "report_id": report_id,
            "docx_filename": docx_filename,
            "pdf_filename": pdf_filename,
            "preview": report_text[:600],
        }
    )


@app.route("/download/<filename>")
@login_required
def download(filename):
    # send_from_directory guards against path traversal (../) on its own,
    # but double-check the file actually lives in generated_reports.
    safe_path = os.path.join(GENERATED_REPORTS_DIR, filename)
    if not os.path.abspath(safe_path).startswith(os.path.abspath(GENERATED_REPORTS_DIR)):
        return jsonify({"error": "Invalid filename."}), 400
    if not os.path.isfile(safe_path):
        return jsonify({"error": "File not found."}), 404

    # Ownership check: being logged in isn't enough — this file has to be
    # one of *this* user's reports, or user A could download user B's
    # report just by knowing/guessing the filename.
    if not db.user_owns_file(session["user_id"], filename):
        return jsonify({"error": "You don't have access to this file."}), 403

    return send_from_directory(GENERATED_REPORTS_DIR, filename, as_attachment=True)


@app.route("/history")
@login_required
def history():
    reports = db.get_reports_for_user(session["user_id"])
    return render_template("history.html", reports=reports)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
