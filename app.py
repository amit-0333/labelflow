from flask import Flask, render_template
from flask_login import LoginManager
from core.config import Config
from core.db import db

login_manager = LoginManager()
login_manager.login_view = "auth.login"  # where to send people who aren't logged in


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from core import models
    from auth.routes import auth_bp
    app.register_blueprint(auth_bp)
    from projects.routes import projects_bp
    app.register_blueprint(projects_bp)

    with app.app_context():
        db.create_all()

    @app.route("/")
    def home():
        return render_template("home.html")

    return app


@login_manager.user_loader
def load_user(user_id):
    from core.models import User
    return User.query.get(int(user_id))


app = create_app()

if __name__ == "__main__":
    app.run()