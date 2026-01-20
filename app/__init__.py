from flask import Flask
from .extensions import db, migrate
from .config import Config
from flask_login import LoginManager


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # ==========================
    # Flask Login configuration
    # ==========================
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"  # redirect if not logged in
    login_manager.init_app(app)

    # Import User model
    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))   # REQUIRED

    # Core (root)
    from .models.core import core_bp
    app.register_blueprint(core_bp)

    # Module blueprints
    from .models.construction import construction_bp
    app.register_blueprint(construction_bp, url_prefix="/construction")

    from .models.carenderia import carenderia_bp
    app.register_blueprint(carenderia_bp, url_prefix="/carenderia")

    from .models.catering import catering_bp
    app.register_blueprint(catering_bp, url_prefix="/catering")

    # Auth & Admin
    from .auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    from .auth.admin_routes import admin_bp
    app.register_blueprint(admin_bp, url_prefix="/admin")

    return app
