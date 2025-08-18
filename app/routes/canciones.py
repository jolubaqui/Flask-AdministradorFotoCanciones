import os
import logging
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.exceptions import Error as CloudinaryError

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort,
    send_from_directory
)
from pathlib import Path
from werkzeug.utils import secure_filename

from ..db import get_db_connection
from ..utils import save_image_safely, sanitize_text
from .. import config

bp = Blueprint('canciones', __name__, url_prefix='/', template_folder='../templates')

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("CLOUD_API_KEY"),
    api_secret=os.getenv("CLOUD_API_SECRET"),
)

@bp.route("/")
def index():
    conn = get_db_connection()
    page = request.args.get("page", 1, type=int)
    query = request.args.get("q", "").strip()
    offset = (page - 1) * config.CANCIONES_POR_PAGINA

    if query:
        search_term = f"%{query}%"
        query_count = "SELECT COUNT(*) FROM canciones WHERE titulo LIKE ? OR letra LIKE ?"
        query_data = "SELECT * FROM canciones WHERE titulo LIKE ? OR letra LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?"
        params_count = (search_term, search_term)
        params_data = (search_term, search_term, config.CANCIONES_POR_PAGINA, offset)
    else:
        query_count = "SELECT COUNT(*) FROM canciones"
        query_data = "SELECT * FROM canciones ORDER BY id DESC LIMIT ? OFFSET ?"
        params_count = ()
        params_data = (config.CANCIONES_POR_PAGINA, offset)
        
    result = conn.execute(query_count, params_count).fetchone()
    total_canciones = result[0] if result and len(result) > 0 else 0
    total_paginas = (total_canciones + config.CANCIONES_POR_PAGINA - 1) // config.CANCIONES_POR_PAGINA
    canciones = conn.execute(query_data, params_data).fetchall()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template(
            "_song_list_partial.html",
            canciones=canciones,
            page=page,
            total_paginas=total_paginas,
            query=query
        )
    
    return render_template(
        "index.html",
        canciones=canciones,
        page=page,
        total_paginas=total_paginas,
        query=query
    )

@bp.route("/agregar", methods=["GET", "POST"])
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
            return redirect(url_for("canciones.index"))
        except ValueError as ve:
            flash(str(ve), "warning")
            return render_template("agregar.html")
        except Exception as e:
            logging.exception("Error en /agregar")
            flash(f"Error al agregar la canción: {e}", "error")
            return render_template("agregar.html")

    return render_template("agregar.html")

@bp.route("/editar/<int:id>", methods=["GET", "POST"])
def editar_cancion(id: int):
    conn = get_db_connection()
    cancion = conn.execute("SELECT * FROM canciones WHERE id = ?", (id,)).fetchone()
    if not cancion:
        flash("Canción no encontrada", "error")
        return redirect(url_for("canciones.index"))

    if request.method == "POST":
        try:
            titulo = sanitize_text(request.form.get("titulo"))
            letra = sanitize_text(request.form.get("letra"))
            ruta_foto_db = cancion["ruta_foto"]
            url_web_foto_db = cancion["url_web_foto"]

            foto_file = request.files.get("foto")
            if foto_file and foto_file.filename:
                if ruta_foto_db:
                    (config.UPLOAD_DIR / ruta_foto_db).unlink(missing_ok=True)
                
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
            return redirect(url_for("canciones.index"))
        except ValueError as ve:
            flash(str(ve), "warning")
            return render_template("editar.html", cancion=cancion)
        except Exception as e:
            logging.exception("Error en /editar")
            flash(f"Error al actualizar: {e}", "error")
            return render_template("editar.html", cancion=cancion)

    return render_template("editar.html", cancion=cancion)

@bp.route("/eliminar/<int:id>", methods=["POST"])
def eliminar_cancion(id: int):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT ruta_foto FROM canciones WHERE id = ?", (id,)).fetchone()
        if row and row["ruta_foto"]:
            try:
                (config.UPLOAD_DIR / row["ruta_foto"]).unlink(missing_ok=True)
            except Exception:
                pass
        conn.execute("DELETE FROM canciones WHERE id = ?", (id,))
        conn.commit()
        flash("Canción eliminada correctamente", "success")
    except Exception as e:
        logging.exception("Error en /eliminar")
        flash(f"Error al eliminar: {e}", "error")
    return redirect(url_for("canciones.index"))

@bp.route("/subir_a_web/<int:id>", methods=["POST"])
def subir_a_web(id: int):
    conn = get_db_connection()
    cancion = conn.execute("SELECT * FROM canciones WHERE id = ?", (id,)).fetchone()
    
    if not cancion or not cancion["ruta_foto"]:
        flash("Canción o foto no encontrada.", "error")
        return redirect(url_for("canciones.index"))

    ruta_local_abs = config.UPLOAD_DIR / cancion["ruta_foto"]
    if not ruta_local_abs.exists():
        flash(f"El archivo local no existe: {ruta_local_abs}", "error")
        return redirect(url_for("canciones.index"))
    
    try:
        public_id = f"canciones/{cancion['id']}_{Path(cancion['ruta_foto']).stem}"
        response = cloudinary.uploader.upload(str(ruta_local_abs), public_id=public_id)
        url_web = response.get("secure_url")

        conn.execute("UPDATE canciones SET url_web_foto = ? WHERE id = ?", (url_web, id))
        conn.commit()
        flash(f"Foto subida con éxito. URL: {url_web}", "success")

    except CloudinaryError as e:
        logging.exception("Cloudinary error")
        flash(f"Error al subir a Cloudinary: {e}", "error")
    except Exception as e:
        logging.exception("Error inesperado en /subir_a_web")
        flash(f"Error inesperado: {e}", "error")

    return redirect(url_for("canciones.index"))

@bp.route("/media/<path:filename>")
def media(filename: str):
    safe_name = secure_filename(filename)
    file_path = config.UPLOAD_DIR / safe_name
    if not file_path.exists():
        abort(404)
    return send_from_directory(config.UPLOAD_DIR, safe_name)