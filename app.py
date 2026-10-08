from flask import Flask
from core.config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    @app.route("/")
    def home():
        return "LabelFlow is running"

    return app


app = create_app()

if __name__ == "__main__":
    app.run()