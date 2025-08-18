import os
import uuid
import logging
import sqlite3
from pathlib import Path

from flask import (
    Flask, render_template, request, redirect, url_for, flash, g, jsonify,
    send_from_directory, abort
)
from werkzeug.utils import secure_filename

import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.exceptions import Error as CloudinaryError

from dotenv import load_dotenv

from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf

import bleach
from PIL import Image
from flask_talisman import Talisman

# -----------------------------
# Configuración y constantes
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
UPLOAD_DIR = INSTANCE_DIR / "uploads"
DB_PATH = INSTANCE_DIR / "database.db"

CANCIONES_POR_PAGINA = 5
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
MAX_CONTENT_LENGTH_MB = 16

INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv()

# -----------------------------
# Crear app y extensiones
# -----------------------------
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "dev_secret_key"),
    MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH_MB * 1024 * 1024,
    WTF_CSRF_TIME_LIMIT=None,
)

csrf = CSRFProtect(app)

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)

if os.environ.get("FLASK_ENV") == "production":
    Talisman(
        app,
        content_security_policy=None,
        force_https=True,
        strict_transport_security=True,
        session_cookie_secure=True,
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("CLOUD_API_KEY"),
    api_secret=os.getenv("CLOUD_API_SECRET"),
)

# -----------------------------
# DB helpers
# -----------------------------
def get_db_connection():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
        g.db.execute("PRAGMA journal_mode = WAL;")
        g.db.execute("PRAGMA synchronous = NORMAL;")
    return g.db

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS canciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            letra TEXT NOT NULL,
            ruta_foto TEXT,
            url_web_foto TEXT
        );
        """
    )
    conn.commit()
    app.logger.info("DB lista y tabla 'canciones' creada si no existía.")

with app.app_context():
    if not DB_PATH.exists():
        init_db()
    else:
        app.logger.info("DB existente. Saltando init.")

# -----------------------------
# Utilidades
# -----------------------------
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def sanitize_text(text: str) -> str:
    allowed_tags = ["b", "i", "u", "em", "strong", "br", "p", "ul", "ol", "li"]
    return bleach.clean(text or "", tags=allowed_tags, strip=True)

def save_image_safely(file_storage) -> str:
    if not file_storage or file_storage.filename == "":
        raise ValueError("No se seleccionó archivo.")

    if not allowed_file(file_storage.filename):
        raise ValueError("Extensión no permitida.")

    safe_name = secure_filename(file_storage.filename)
    final_name = f"{uuid.uuid4().hex}_{safe_name}"
    dest_path = UPLOAD_DIR / final_name
    file_storage.save(dest_path)

    try:
        with Image.open(dest_path) as img:
            img.verify()
    except Exception:
        dest_path.unlink(missing_ok=True)
        raise ValueError("El archivo no es una imagen válida.")

    return final_name

# -----------------------------
# Rutas
# -----------------------------
@app.route("/")
def index():
    conn = get_db_connection()
    page = request.args.get("page", 1, type=int)
    query = request.args.get("q", "").strip()
    offset = (page - 1) * CANCIONES_POR_PAGINA

    if query:
        search_term = f"%{query}%"
        query_count = "SELECT COUNT(*) FROM canciones WHERE titulo LIKE ? OR letra LIKE ?"
        query_data = "SELECT * FROM canciones WHERE titulo LIKE ? OR letra LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?"
        params_count = (search_term, search_term)
        params_data = (search_term, search_term, CANCIONES_POR_PAGINA, offset)
    else:
        query_count = "SELECT COUNT(*) FROM canciones"
        query_data = "SELECT * FROM canciones ORDER BY id DESC LIMIT ? OFFSET ?"
        params_count = ()
        params_data = (CANCIONES_POR_PAGINA, offset)
        
    total_canciones = conn.execute(query_count, params_count).fetchone()[0]
    total_paginas = (total_canciones + CANCIONES_POR_PAGINA - 1) // CANCIONES_POR_PAGINA

    canciones = conn.execute(query_data, params_data).fetchall()

    return render_template(
        "index.html",
        canciones=canciones,
        page=page,
        total_paginas=total_paginas,
    )

@app.route("/agregar", methods=["GET", "POST"])
def agregar_cancion():
    if request.method == "POST":
        try:
            titulo = sanitize_text(request.form.get("titulo"))
            letra = sanitize_text(request.form.get("letra"))

            ruta_foto = None
            foto_file = request.files.get("foto")
            if foto_file and foto_file.filename:
                final_name = save_image_safely(foto_file)
                ruta_foto = final_name

            conn = get_db_connection()
            conn.execute(
                "INSERT INTO canciones (titulo, ruta_foto, letra) VALUES (?, ?, ?)",
                (titulo, ruta_foto, letra),
            )
            conn.commit()
            flash("Canción agregada exitosamente!", "success")
            return redirect(url_for("index"))
        except ValueError as ve:
            flash(str(ve), "warning")
            return render_template("agregar.html")
        except Exception as e:
            app.logger.exception("Error en /agregar")
            flash(f"Error al agregar la canción: {e}", "error")
            return render_template("agregar.html")

    return render_template("agregar.html")

@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar_cancion(id: int):
    conn = get_db_connection()
    cancion = conn.execute("SELECT * FROM canciones WHERE id = ?", (id,)).fetchone()
    if not cancion:
        flash("Canción no encontrada", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        try:
            titulo = sanitize_text(request.form.get("titulo"))
            letra = sanitize_text(request.form.get("letra"))
            ruta_foto_db = cancion["ruta_foto"]
            url_web_foto_db = cancion["url_web_foto"]

            foto_file = request.files.get("foto")
            if foto_file and foto_file.filename:
                # Si se sube una nueva foto, reemplaza la anterior
                if ruta_foto_db:
                    (UPLOAD_DIR / ruta_foto_db).unlink(missing_ok=True)
                
                final_name = save_image_safely(foto_file)
                ruta_foto_db = final_name
                url_web_foto_db = None
                flash("Foto de canción actualizada!", "success")

            conn.execute(
                "UPDATE canciones SET titulo = ?, letra = ?, ruta_foto = ?, url_web_foto = ? WHERE id = ?",
                (titulo, letra, ruta_foto_db, url_web_foto_db, id),
            )
            conn.commit()
            flash("Canción actualizada correctamente", "success")
            return redirect(url_for("index"))
        except ValueError as ve:
            flash(str(ve), "warning")
            return render_template("editar.html", cancion=cancion)
        except Exception as e:
            app.logger.exception("Error en /editar")
            flash(f"Error al actualizar: {e}", "error")
            return render_template("editar.html", cancion=cancion)

    return render_template("editar.html", cancion=cancion)

@app.route("/eliminar/<int:id>", methods=["POST"])
def eliminar_cancion(id: int):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT ruta_foto FROM canciones WHERE id = ?", (id,)).fetchone()
        if row and row["ruta_foto"]:
            try:
                (UPLOAD_DIR / row["ruta_foto"]).unlink(missing_ok=True)
            except Exception:
                pass
        conn.execute("DELETE FROM canciones WHERE id = ?", (id,))
        conn.commit()
        flash("Canción eliminada correctamente", "success")
    except Exception as e:
        app.logger.exception("Error en /eliminar")
        flash(f"Error al eliminar: {e}", "error")
    return redirect(url_for("index"))

@app.route("/subir_a_web/<int:id>", methods=["POST"])
def subir_a_web(id: int):
    conn = get_db_connection()
    cancion = conn.execute("SELECT * FROM canciones WHERE id = ?", (id,)).fetchone()
    
    if not cancion or not cancion["ruta_foto"]:
        flash("Canción o foto no encontrada.", "error")
        return redirect(url_for("index"))

    ruta_local_abs = UPLOAD_DIR / cancion["ruta_foto"]
    if not ruta_local_abs.exists():
        flash(f"El archivo local no existe: {ruta_local_abs}", "error")
        return redirect(url_for("index"))
    
    try:
        public_id = f"canciones/{cancion['id']}_{Path(cancion['ruta_foto']).stem}"
        response = cloudinary.uploader.upload(str(ruta_local_abs), public_id=public_id)
        url_web = response.get("secure_url")

        conn.execute("UPDATE canciones SET url_web_foto = ? WHERE id = ?", (url_web, id))
        conn.commit()
        flash(f"Foto subida con éxito. URL: {url_web}", "success")

    except CloudinaryError as e:
        app.logger.exception("Cloudinary error")
        flash(f"Error al subir a Cloudinary: {e}", "error")
    except Exception as e:
        app.logger.exception("Error inesperado en /subir_a_web")
        flash(f"Error inesperado: {e}", "error")

    return redirect(url_for("index"))

@app.route("/media/<path:filename>")
def media(filename: str):
    safe_name = Path(secure_filename(filename)).name
    file_path = UPLOAD_DIR / safe_name
    if not file_path.exists():
        abort(404)
    return send_from_directory(UPLOAD_DIR, safe_name)

# -----------------------------
# Arranque
# -----------------------------
if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    if os.environ.get("FLASK_ENV") == "production":
        app.run(host=host, port=port)
    else:
        app.run(host=host, port=port, debug=True)