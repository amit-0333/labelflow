import os
from flask import Flask, render_template
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix
from core.config import Config
from core.db import db

login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    ## stop the app if production is still using the default secret key
    if app.config["IS_PRODUCTION"] and app.config["SECRET_KEY"] == "dev-secret":
        raise RuntimeError("Set a real SECRET_KEY in the environment")

    ## hosting sites put a proxy in front of the app, this makes https work correctly
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    login_manager.init_app(app)

    from core import models
    from auth.routes import auth_bp
    from projects.routes import projects_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)

    with app.app_context():
        db.create_all()

    ## home page
    @app.route('/')
    def home():
        return render_template('home.html')

    ## hosting sites call this to check the app is alive
    @app.route('/health')
    def health():
        return "ok"

    return app


@login_manager.user_loader
def load_user(user_id):
    from core.models import User
    return User.query.get(int(user_id))


app = create_app()

if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", 5000)))