from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)

app.secret_key = "notes-app-secret-key"

import os
DATABASE = os.path.join(os.getenv("DATA_DIR", "."), "notes.db")


# =========================
# DATABASE CONNECTION
# =========================

def get_db():
    os.makedirs(os.path.dirname(DATABASE) or ".", exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# CREATE DATABASE TABLES
# =========================

def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'Personal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# =========================
# LOGIN
# =========================

@app.route("/", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        email = request.form["email"].strip()
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]

            return redirect("/dashboard")

        error = "Invalid email or password."

    return render_template(
        "login.html",
        error=error
    )


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    error = None

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        if not name or not email or not password:

            error = "Please fill in all fields."

            return render_template(
                "register.html",
                error=error
            )

        hashed_password = generate_password_hash(password)

        try:

            conn = get_db()

            conn.execute(
                """
                INSERT INTO users
                (name, email, password)
                VALUES (?, ?, ?)
                """,
                (
                    name,
                    email,
                    hashed_password
                )
            )

            conn.commit()
            conn.close()

            return redirect("/")

        except sqlite3.IntegrityError:

            error = "An account with this email already exists."

    return render_template(
        "register.html",
        error=error
    )


# =========================
# DASHBOARD / READ NOTES
# =========================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/")

    conn = get_db()

    notes = conn.execute(
        """
        SELECT *
        FROM notes
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (session["user_id"],)
    ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        notes=notes,
        user_name=session["user_name"]
    )


# =========================
# CREATE NOTE
# =========================

@app.route("/add-note", methods=["POST"])
def add_note():

    if "user_id" not in session:
        return redirect("/")

    title = request.form["title"].strip()
    content = request.form["content"].strip()
    category = request.form.get(
        "category",
        "Personal"
    )

    if not title or not content:
        return redirect("/dashboard")

    conn = get_db()

    conn.execute(
        """
        INSERT INTO notes
        (user_id, title, content, category)
        VALUES (?, ?, ?, ?)
        """,
        (
            session["user_id"],
            title,
            content,
            category
        )
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# =========================
# EDIT / UPDATE NOTE
# =========================

@app.route(
    "/edit-note/<int:note_id>",
    methods=["GET", "POST"]
)
def edit_note(note_id):

    if "user_id" not in session:
        return redirect("/")

    conn = get_db()

    note = conn.execute(
        """
        SELECT *
        FROM notes
        WHERE id = ?
        AND user_id = ?
        """,
        (
            note_id,
            session["user_id"]
        )
    ).fetchone()

    if note is None:

        conn.close()

        return redirect("/dashboard")

    # UPDATE
    if request.method == "POST":

        title = request.form["title"].strip()
        content = request.form["content"].strip()
        category = request.form.get(
            "category",
            "Personal"
        )

        conn.execute(
            """
            UPDATE notes
            SET title = ?,
                content = ?,
                category = ?
            WHERE id = ?
            AND user_id = ?
            """,
            (
                title,
                content,
                category,
                note_id,
                session["user_id"]
            )
        )

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    conn.close()

    return render_template(
        "edit_note.html",
        note=note
    )


# =========================
# DELETE NOTE
# =========================

@app.route(
    "/delete-note/<int:note_id>",
    methods=["POST"]
)
def delete_note(note_id):

    if "user_id" not in session:
        return redirect("/")

    conn = get_db()

    conn.execute(
        """
        DELETE FROM notes
        WHERE id = ?
        AND user_id = ?
        """,
        (
            note_id,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    return redirect("/dashboard")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================
# START APPLICATION
# =========================

if __name__ == "__main__":

    init_db()

    app.run(host="0.0.0.0", port=5000, debug=False)

    