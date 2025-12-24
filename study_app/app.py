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
from werkzeug.security import (check_password_hash, generate_password_hash)



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
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
# 中間テーブル（多対多）    
studylog_tags = db.Table(
    "studylog_tags",
    db.Column("studylog_id", db.Integer, db.ForeignKey("study_logs.id")),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id")),
)

class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)

class StudyLog(db.Model):
    __tablename__ = "study_logs"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    text = db.Column(db.Text, nullable=False)
    tags = db.relationship(
        "Tag",
        secondary=studylog_tags,
        backref="logs"
    )


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# 中間テーブル（多対多）



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
    return redirect(url_for("logged_out"))

@app.route("/logged_out")
@login_required
def logged_out():
    return render_template("logged_out.html")





@app.route("/", methods=["GET", "POST"])
@login_required
def index():

    # 保存処理
    if request.method == "POST":
        text = request.form["content"]
        tag_str = request.form.get("tags", "")
        if text.strip():
            log = StudyLog(date=date.today(), text=text)
            tag_names = [t.strip() for t in tag_str.split(",") if t.strip()]
            for name in tag_names:
                tag = Tag.query.filter_by(name=name).first()
                if not tag:
                    tag = Tag(name=name)
                    db.session.add(tag)
                log.tags.append(tag)

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
        tag_name = request.form.get("tag", "").strip()

        query = StudyLog.query

        if date_str:
            query = query.filter(
                StudyLog.date == datetime.strptime(date_str, "%Y-%m-%d").date()
            )
        if keyword:
            query = query.filter(StudyLog.text.contains(keyword))

        if tag_name:
            query = query.join(StudyLog.tags).filter(Tag.name == tag_name)
   


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
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



