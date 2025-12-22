import json
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request

app = Flask(__name__)

DATA_FILE = "logs.json"

def load_logs():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_logs(logs):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

def filter_logs_by_days(logs, days):
    target_date = date.today() - timedelta(days=days)
    result = []
    for log in logs:
        log_date = datetime.strptime(log["date"], "%Y-%m-%d").date()
        if log_date == target_date:
            result.append(log)
    return result

@app.route("/", methods=["GET", "POST"])
def index():
    logs = load_logs()

    # 保存処理
    if request.method == "POST":
        text = request.form["content"]
        if text.strip():
            logs.append({"date": str(date.today()), "text": text})
            save_logs(logs)

    # 忘却防止データ
    forget_1 = filter_logs_by_days(logs, 1)
    forget_3 = filter_logs_by_days(logs, 3)
    forget_7 = filter_logs_by_days(logs, 7)
    forget_30 = filter_logs_by_days(logs, 30)

    return render_template(
        "index.html",
        logs=logs,
        forget_1=forget_1,
        forget_3=forget_3,
        forget_7=forget_7,
        forget_30=forget_30
    )


from flask import Flask, render_template, request, redirect

# --- 既存の app, load_data, save_data はそのまま ---

@app.route("/search", methods=["GET", "POST"])
def search():
    data = load_logs()
    results = []

    if request.method == "POST":
        date_query = request.form.get("date")
        keyword = request.form.get("keyword", "").lower()

        for entry in data:
            match_date = (date_query == "" or entry["date"] == date_query)
            match_keyword = (keyword == "" or keyword in entry["text"].lower())

            if match_date and match_keyword:
                results.append(entry)

    return render_template("search.html", results=results)

@app.route("/delete/<entry_date>", methods=["POST"])
def delete(entry_date):
    data = load_logs()
    data = [d for d in data if d["date"] != entry_date]
    save_logs(data)
    return redirect("/search")

@app.route("/edit/<entry_date>")
def edit(entry_date):
    data = load_logs()
    entry = next((d for d in data if d["date"] == entry_date), None)
    return render_template("edit.html", entry=entry)

@app.route("/update/<entry_date>", methods=["POST"])
def update(entry_date):
    data = load_logs()
    new_date = request.form.get("date")    # ★追加
    new_task = request.form.get("task")    # ★内容


    for d in data:
        if d["date"] == entry_date:
            d["date"] = new_date
            d["task"] = request.form.get("task")
    save_logs(data)
    return redirect("/search")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

