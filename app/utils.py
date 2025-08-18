import uuid
import bleach
from pathlib import Path
from werkzeug.utils import secure_filename
from PIL import Image

from . import config

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS

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
    dest_path = config.UPLOAD_DIR / final_name
    file_storage.save(dest_path)

    try:
        with Image.open(dest_path) as img:
            img.verify()
    except Exception:
        dest_path.unlink(missing_ok=True)
        raise ValueError("El archivo no es una imagen válida.")

    return final_name