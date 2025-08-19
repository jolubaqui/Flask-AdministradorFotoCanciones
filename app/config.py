import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"
UPLOAD_DIR = INSTANCE_DIR / "uploads"
DB_PATH = INSTANCE_DIR / "database.db"

CANCIONES_POR_PAGINA = 5
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
MAX_CONTENT_LENGTH_MB = 16

SECRET_KEY = os.getenv("SECRET_KEY", "56224685ecf563087921ac5eb6e39b9905eddd0d208b661d")
MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH_MB * 1024 * 1024
WTF_CSRF_TIME_LIMIT = None

CLOUD_NAME = os.getenv("dwcomv0hv")
CLOUD_API_KEY = os.getenv("646295341746146")
CLOUD_API_SECRET = os.getenv("0oid-hmmji7Hg8dMG6h-inbKsAw")

# Asegúrate de que los directorios existan
INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)