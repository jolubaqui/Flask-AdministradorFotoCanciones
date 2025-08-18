import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    if os.environ.get("FLASK_ENV") == "production":
        app.run(host=host, port=port)
    else:
        app.run(host=host, port=port, debug=True)