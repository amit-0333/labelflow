from flask import Flask
from core.config import Config
from core.db import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    from core import models  # noqa: F401  (registers the tables)

    with app.app_context():
        db.create_all()  # creates tables that don't exist yet

    @app.route("/")
    def home():
        return "LabelFlow is running"

    return app


app = create_app()

if __name__ == "__main__":
    app.run()