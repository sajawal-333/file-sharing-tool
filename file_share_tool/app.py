import os
import sqlite3
from datetime import datetime, timedelta
from uuid import uuid4

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_file,
    abort,
    flash,
)
from werkzeug.utils import secure_filename
import bcrypt


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DATABASE_PATH = os.path.join(BASE_DIR, "database.db")

MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # 1 GB
LINK_TTL_DAYS = 7  # automatic expiration window for links/files


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    init_db()

    register_routes(app)
    return app


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = get_db_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                password_hash BLOB,
                upload_date TEXT NOT NULL
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_file_to_disk(file_storage) -> tuple[str, str]:
    original_filename = secure_filename(file_storage.filename or "")
    if not original_filename:
        raise ValueError("Invalid file name.")

    file_id = uuid4().hex
    stored_filename = f"{file_id}_{original_filename}"
    upload_path = os.path.join(UPLOAD_FOLDER, stored_filename)

    file_storage.save(upload_path)
    return file_id, upload_path


def insert_file_record(file_id: str, filename: str, filepath: str, password_hash: bytes | None) -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO files (file_id, filename, filepath, password_hash, upload_date)
            VALUES (?, ?, ?, ?, ?);
            """,
            (file_id, filename, filepath, password_hash, datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_file_record(file_id: str):
    conn = get_db_connection()
    try:
        cur = conn.execute(
            "SELECT * FROM files WHERE file_id = ?;",
            (file_id,),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    return row


def delete_file_record_and_disk(row) -> None:
    filepath = row["filepath"]
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM files WHERE id = ?;", (row["id"],))
        conn.commit()
    finally:
        conn.close()

    try:
        if os.path.isfile(filepath):
            os.remove(filepath)
    except OSError:
        # Best-effort cleanup; ignore failure to delete files on disk.
        pass


def is_expired(upload_date_str: str) -> bool:
    try:
        uploaded_at = datetime.fromisoformat(upload_date_str)
    except ValueError:
        return False

    return datetime.utcnow() > uploaded_at + timedelta(days=LINK_TTL_DAYS)


def register_routes(app: Flask) -> None:
    @app.route("/", methods=["GET"])
    def index():
        return render_template("upload.html")

    @app.route("/upload", methods=["POST"])
    def upload():
        file = request.files.get("file")
        password = request.form.get("password", "").strip()

        if not file or file.filename == "":
            flash("Please select a file to upload.", "error")
            return redirect(url_for("index"))

        try:
            file_id, filepath = save_file_to_disk(file)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))

        password_hash: bytes | None = None
        if password:
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        insert_file_record(
            file_id=file_id,
            filename=file.filename,
            filepath=filepath,
            password_hash=password_hash,
        )

        download_link = url_for("download", file_id=file_id, _external=True)
        return render_template("success.html", download_link=download_link, has_password=bool(password))

    @app.route("/download/<file_id>", methods=["GET"])
    def download(file_id: str):
        row = get_file_record(file_id)
        if row is None:
            abort(404)

        if is_expired(row["upload_date"]):
            delete_file_record_and_disk(row)
            abort(410)

        if row["password_hash"]:
            return render_template("password.html", file_id=file_id, error=None)

        return send_requested_file(row)

    @app.route("/verify/<file_id>", methods=["POST"])
    def verify(file_id: str):
        row = get_file_record(file_id)
        if row is None:
            abort(404)

        if is_expired(row["upload_date"]):
            delete_file_record_and_disk(row)
            abort(410)

        password = request.form.get("password", "").strip().encode("utf-8")
        stored_hash = row["password_hash"]

        if not stored_hash or not password:
            return render_template(
                "password.html",
                file_id=file_id,
                error="Password is required.",
            )

        if bcrypt.checkpw(password, stored_hash):
            return send_requested_file(row)

        return render_template(
            "password.html",
            file_id=file_id,
            error="Incorrect password. Please try again.",
        )


def send_requested_file(row):
    filepath = row["filepath"]
    filename = row["filename"]

    if not os.path.isfile(filepath):
        delete_file_record_and_disk(row)
        abort(404)

    return send_file(
        filepath,
        as_attachment=True,
        download_name=filename,
    )


app = create_app()


if __name__ == "__main__":
    # Bind to all interfaces so the app can be reached
    # from other machines when the port is exposed.
    host = os.environ.get("FLASK_RUN_HOST", "0.0.0.0")
    # Railway and many PaaS providers expose the port via PORT.
    port_str = os.environ.get("PORT") or os.environ.get("FLASK_RUN_PORT", "5000")
    try:
        port = int(port_str)
    except ValueError:
        port = 5000

    app.run(host=host, port=port, debug=False)

