import os
import logging

from flask import Flask, g
from flask_wtf import CSRFProtect
from flask_talisman import Talisman

from . import config
from .db import close_connection, init_db
from .routes.canciones import bp as canciones_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    app.secret_key = "super_secret_key"
    
    CSRFProtect(app)
    
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

    app.teardown_appcontext(close_connection)
    
    with app.app_context():
        init_db()

    app.register_blueprint(canciones_bp)

    return app