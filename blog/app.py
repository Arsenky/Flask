from flask import Flask, request, g, render_template, Blueprint, redirect, url_for, current_app
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy

from time import time
from werkzeug.exceptions import BadRequest
from sqlalchemy.exc import IntegrityError


from blog.views.users import users_app
from blog.views.articles import articles_app
from blog.models.database import db
from blog.views.auth import login_manager, auth_app
from blog.security import flask_bcrypt
from blog.models import User
from blog.forms.user import RegistrationForm
from blog.views.authors import authors_app
from blog.admin import admin
from blog.api import init_api

import os

app = Flask(__name__)

flask_bcrypt.init_app(app)

api = init_api(app)

migrate = Migrate(app, db, compare_type=True)

admin.init_app(app)



cfg_name = os.environ.get("CONFIG_NAME") or 'ProductionConfig'
app.config.from_object(f"blog.configs.{cfg_name}")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/blog.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "abcdefg123456"
db.init_app(app)

# для работы авторизации нам обязательно нужен SECRET_KEY в конфигурации, добавляем

app.register_blueprint(auth_app, url_prefix="/auth")
app.register_blueprint(authors_app, url_prefix="/authors")

login_manager.init_app(app)


@app.cli.command("create-admin")
def create_admin():
    """
    Run in your terminal:
    ➜ flask create-admin
    > created admin: <User #1 'admin'>
    """

    from blog.models import User

    admin = User(username="admin", is_staff=True)
    admin.password = os.environ.get("ADMIN_PASSWORD") or "adminpass"
    db.session.add(admin)
    db.session.commit()
    print("created admin:", admin)

# @app.cli.command("del-art")
# def create_admin():
#     from blog.models import Article
#     articles = Article.query.all()
#     print(articles[0])
#     db.session.delete(articles[0])
#     db.session.commit()
#     print("done!")

@app.cli.command("create-tags")
def create_tags():
    """
    Run in your terminal:
    ➜ flask create-tags
    """
    from blog.models import Tag

    for name in [
        "flask",
        "django",
        "python",
        "sqlalchemy",
        "news",
    ]:
        tag = Tag(name=name)
        db.session.add(tag)
        
    db.session.commit()
    print("created tags")


app.register_blueprint(users_app, url_prefix="/users")
app.register_blueprint(articles_app, url_prefix="/articles")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/greet/<name>/")
def greet_name(name: str):
    return f"Hello {name}! "


@app.route("/user/")
def read_user():
    name = request.args.get("name")
    surname = request.args.get("surname")
    return f"User {name or '[no name]'} {surname or '[no surname]'}"


@app.route("/status/", methods=["GET", "POST"])
def custom_status_code():
    if request.method == "GET":
        return """\
        To get response with custom status code
        send request using POST method
        and pass `code` in JSON body / FormData
        """

    print("raw bytes data:", request.data)

    if request.form and "code" in request.form:
        return "code from form", request.form["code"]

    if request.json and "code" in request.json:
        return "code from json", request.json["code"]

    return "", 204

@app.before_request
def process_before_request():
    """
    Sets start_time to `g` object
    """
    g.start_time = time()


@app.after_request
def process_after_request(response):
    """
    adds process time in headers
    """
    if hasattr(g, "start_time"):
        response.headers["process-time"] = time() - g.start_time
    return response


@app.route("/power/")
def power_value():
    x = request.args.get("x") or ""
    y = request.args.get("y") or ""
    if not (x.isdigit() and y.isdigit()):
        app.logger.info("invalid values for power: x=%r and y=%r", x, y)
        raise BadRequest("please pass integers in `x` and `y` query params")

    x = int(x)
    y = int(y)
    result = x ** y
    app.logger.debug("%s ** %s = %s", x, y, result)
    return str(result)


@app.route("/divide-by-zero/")
def do_zero_division():
    return 1 / 0


@app.errorhandler(ZeroDivisionError)
def handle_zero_division_error(error):
    print(error)  # prints str version of error: 'division by zero'
    app.logger.exception("Here's traceback for zero division error")
    return "Never divide by zero!", 400
