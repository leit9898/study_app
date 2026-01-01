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
from flask import Flask, render_template, request, redirect
from sqlalchemy import or_
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect




app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL", "sqlite:///logs.db"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)


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
    tag_type = db.Column(db.String(20), nullable=False) 
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint("name", "tag_type", name="uix_name_tag_type"),
    )


class StudyLog(db.Model):
    __tablename__ = "study_logs"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(100), nullable=False) 
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

#ユーザロード
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#ログイン処理
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

#ログアウト処理
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("logged_out"))

@app.route("/logged_out")
@login_required
def logged_out():
    return render_template("logged_out.html")

# メインページ
@app.route("/", methods=["GET", "POST"])
@login_required
def index():

    # 保存処理
    if request.method == "POST":
        title = request.form.get("title")
        text = request.form["content"]
        tag_ids = request.form.getlist("tags")
        if title and text:
            log = StudyLog(
                date=date.today(),
                title=title,
                text=text
            )

            for tag_id in tag_ids:
                tag = Tag.query.get(int(tag_id))
                if tag:
                    log.tags.append(tag)


            db.session.add(log)
            db.session.commit()


    today = date.today()

    forget_1 = StudyLog.query.filter_by(date=today - timedelta(days=1)).all()
    forget_3 = StudyLog.query.filter_by(date=today - timedelta(days=3)).all()
    forget_7 = StudyLog.query.filter_by(date=today - timedelta(days=7)).all()
    forget_30 = StudyLog.query.filter_by(date=today - timedelta(days=30)).all()        



    return render_template(
        "index.html",
        category_tags=get_tags("category"),
        subject_tags=get_tags("subject"),
        forget_1=forget_1,
        forget_3=forget_3,
        forget_7=forget_7,
        forget_30=forget_30,
    )

# タグ管理

def get_tags(tag_type):
    return (
        Tag.query
        .filter_by(tag_type=tag_type)
        .order_by(Tag.sort_order, Tag.name)
        .all()
    )

@app.route("/tags")
@login_required
def tag_manage():
    category_tags = get_tags("category")
    subject_tags = get_tags("subject")

    return render_template(
        "tags.html",
        category_tags=category_tags,
        subject_tags=subject_tags
    )


@app.route("/tags/add", methods=["POST"])
@login_required
def add_tag():
    name = request.form.get("name").strip()
    tag_type = request.form.get("tag_type")

    if not name or not tag_type:
        flash("タグ名と種類は必須です")
        return redirect(request.referrer)

    existing = Tag.query.filter_by(name=name, tag_type=tag_type).first()
    if existing:
        flash("そのタグは既に存在します")
        return redirect(request.referrer)

    max_order = (
    db.session.query(db.func.max(Tag.sort_order))
    .filter_by(tag_type=tag_type)
    .scalar()
)

    tag = Tag(
    name=name,
    tag_type=tag_type,
    sort_order=(max_order or 0) + 1
)

    db.session.add(tag)
    db.session.commit()
    return redirect(request.referrer)

@app.route("/tags/delete/<int:tag_id>", methods=["POST"])
@login_required
def delete_tag(tag_id):
    tag = Tag.query.get_or_404(tag_id)
    db.session.delete(tag)
    db.session.commit()
    return redirect(request.referrer)

@app.route("/tags/move/<int:tag_id>/<direction>", methods=["POST"])
@login_required
def move_tag(tag_id, direction):
    tag = Tag.query.get_or_404(tag_id)

    if direction == "up":
        target = (
            Tag.query
            .filter(
                Tag.tag_type == tag.tag_type,
                Tag.sort_order < tag.sort_order
            )
            .order_by(Tag.sort_order.desc())
            .first()
        )
    else:
        target = (
            Tag.query
            .filter(
                Tag.tag_type == tag.tag_type,
                Tag.sort_order > tag.sort_order
            )
            .order_by(Tag.sort_order)
            .first()
        )

    if target:
        tag.sort_order, target.sort_order = target.sort_order, tag.sort_order
        db.session.commit()

    return redirect(url_for("tag_manage"))


# 検索機能
@app.route("/search", methods=["GET"])
@login_required
def search():
    date_str = request.args.get("date")
    keyword = request.args.get("keyword", "").strip()
    tag_name = request.args.get("tag", "").strip()
    page = request.args.get("page", 1, type=int)

    query = StudyLog.query

    if date_str:
            query = query.filter(
                StudyLog.date == datetime.strptime(date_str, "%Y-%m-%d").date()
            )
    if keyword:
       query = query.filter(
        or_(
            StudyLog.title.contains(keyword),
            StudyLog.text.contains(keyword)
        )
      )

    if tag_name:
            query = query.join(StudyLog.tags).filter(Tag.name == tag_name)
   
    pagination = query.order_by(StudyLog.date.desc()).paginate(page=page, per_page=10)

    return render_template("search.html", results=pagination.items, pagination=pagination)

# 削除機能
@app.route("/delete/<int:log_id>", methods=["POST"])
@login_required
def delete(log_id):
    log = StudyLog.query.get_or_404(log_id)
    db.session.delete(log)
    db.session.commit()
    return redirect(url_for(
        "search",
        tag=request.args.get("tag"),
        keyword=request.args.get("keyword"),
        date=request.args.get("date"),
    ))

# 編集機能
@app.route("/edit/<int:log_id>")
@login_required
def edit(log_id):
    log = StudyLog.query.get_or_404(log_id)


    return render_template(
    "edit.html",
    entry=log,
    category_tags=get_tags("category"),
    subject_tags=get_tags("subject")
)


# 更新処理
@app.route("/update/<int:log_id>", methods=["POST"])
@login_required
def update(log_id):
    log = StudyLog.query.get_or_404(log_id)

    date_str = request.form.get("date")
    text = request.form.get("text")
    title = request.form.get("title")

    if date_str:
       log.date = datetime.strptime(date_str, "%Y-%m-%d").date()

    if text:   
       log.text = text

    if title:
       log.title = title   

    if not title:
       flash("タイトルは必須です")
       return redirect(request.referrer)

    print(request.form) #あとで消す！！！！！！！


     # タグ更新処理   

    tag_ids = request.form.getlist("tags")
    log.tags.clear()   # ★一度全解除

    for tag_id in tag_ids:
        tag = Tag.query.get(int(tag_id))
        if tag:
            log.tags.append(tag)

    db.session.commit()
    return redirect("/search")





# 初回管理者ユーザ作成
def create_admin_user():
    if User.query.count() == 0:
        username = os.environ.get("ADMIN_USERNAME", "admin")      # デフォルト値を用意
        password = os.environ.get("ADMIN_PASSWORD", "password")   # デフォルト値を用意

        admin = User(username=username)
        admin.password_hash = generate_password_hash(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user '{username}' を作成しました。")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



