from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    UserMixin
)
from werkzeug.security import check_password_hash



app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL", "sqlite:///logs.db"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

class StudyLog(db.Model):
    __tablename__ = "study_logs"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    text = db.Column(db.Text, nullable=False)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("ユーザー名とパスワードを入力してください")
            return render_template("login.html")
    
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))
        else:
            flash("ユーザー名かパスワードが間違っています")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))





@app.route("/", methods=["GET", "POST"])
@login_required
def index():

    # 保存処理
    if request.method == "POST":
        text = request.form["content"]
        if text.strip():
            log = StudyLog(date=date.today(), text=text)
            db.session.add(log)
            db.session.commit()

    today = date.today()

    forget_1 = StudyLog.query.filter_by(date=today - timedelta(days=1)).all()
    forget_3 = StudyLog.query.filter_by(date=today - timedelta(days=3)).all()
    forget_7 = StudyLog.query.filter_by(date=today - timedelta(days=7)).all()
    forget_30 = StudyLog.query.filter_by(date=today - timedelta(days=30)).all()        

    logs = StudyLog.query.order_by(StudyLog.date.desc()).all()

    return render_template(
        "index.html",
        logs=logs,
        forget_1=forget_1,
        forget_3=forget_3,
        forget_7=forget_7,
        forget_30=forget_30,
    )


from flask import Flask, render_template, request, redirect

# --- 既存の app, load_data, save_data はそのまま ---

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    results = []

    if request.method == "POST":
        date_str = request.form.get("date")
        keyword = request.form.get("keyword", "").strip()

        query = StudyLog.query

        if date_str:
            query = query.filter(
                StudyLog.date == datetime.strptime(date_str, "%Y-%m-%d").date()
            )
        if keyword:
            query = query.filter(StudyLog.text.contains(keyword))


        results = query.order_by(StudyLog.date.desc()).all()

    return render_template("search.html", results=results)

@app.route("/delete/<int:log_id>", methods=["POST"])
@login_required
def delete(log_id):
    log = StudyLog.query.get_or_404(log_id)
    db.session.delete(log)
    db.session.commit()
    return redirect("/search")

@app.route("/edit/<int:log_id>")
@login_required
def edit(log_id):
    log = StudyLog.query.get_or_404(log_id)
    return render_template("edit.html", entry=log)

@app.route("/update/<int:log_id>", methods=["POST"])
@login_required
def update(log_id):
    log = StudyLog.query.get_or_404(log_id)

    date_str = request.form.get("date")
    text = request.form.get("text")

    if date_str:
       log.date = datetime.strptime(date_str, "%Y-%m-%d").date()
    if text:   
       log.text = text

    
    db.session.commit()
    return redirect("/search")

from werkzeug.security import generate_password_hash

def create_admin_user():
    if User.query.count() == 0:
        username = os.environ.get("ADMIN_USERNAME", "admin")      # デフォルト値を用意
        password = os.environ.get("ADMIN_PASSWORD", "password")   # デフォルト値を用意

        admin = User(username=username)
        admin.password_hash = generate_password_hash(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user '{username}' を作成しました。")

with app.app_context():
    db.create_all()
    create_admin_user()


if __name__ == "__main__":
    app.run()



