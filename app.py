import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, flash
import pandas as pd
from datetime import datetime
from sklearn.linear_model import LinearRegression
import matplotlib
matplotlib.use("Agg")  # Use non-GUI backend
import matplotlib.pyplot as plt

DATA_FILE = "data.csv"
CHART_DIR = "charts"
REPORT_DIR = "reports"

os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "replace-with-a-secure-random-key"

# ------------------ Helper functions ------------------
def ensure_csv():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["Date", "Amount", "Category", "Note"])
        df.to_csv(DATA_FILE, index=False)

def load_df():
    ensure_csv()
    df = pd.read_csv(DATA_FILE)
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    return df

def save_expense(amount, category, note=""):
    ensure_csv()
    
    # Create new row with full datetime format
    row = {
        "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # YYYY-MM-DD HH:MM:SS
        "Amount": float(amount),
        "Category": category,
        "Note": note
    }

    # Append directly to CSV without overwriting old data
    df_new = pd.DataFrame([row])
    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        df_new.to_csv(DATA_FILE, index=False)
    else:
        df_new.to_csv(DATA_FILE, mode='a', header=False, index=False)

    # Regenerate charts using full data
    df_full = load_df()
    generate_charts(df_full)


def generate_charts(df):
    if df.empty:
        return {}

    plt.close('all')  # close old figures

    cat = df.groupby("Category")["Amount"].sum().sort_values(ascending=False)

    # Bar chart
    plt.figure(figsize=(8, 5))
    cat.plot(kind="bar", color="skyblue")
    plt.title("Category-wise Spending")
    plt.xlabel("Category")
    plt.ylabel("Amount (₹)")
    plt.tight_layout()
    bar_path = os.path.join(CHART_DIR, "bar_chart.png")
    plt.savefig(bar_path)
    plt.close()

    # Pie chart
    plt.figure(figsize=(6, 6))
    cat.plot(kind="pie", autopct="%1.1f%%")
    plt.title("Expense Distribution")
    plt.ylabel("")
    plt.tight_layout()
    pie_path = os.path.join(CHART_DIR, "pie_chart.png")
    plt.savefig(pie_path)
    plt.close()

    return {"bar": bar_path, "pie": pie_path}

# ------------------ Routes ------------------
@app.route("/")
def dashboard():
    return render_template("index.html")

@app.route("/add", methods=["GET", "POST"])
def add_expense_route():
    if request.method == "POST":
        amount = request.form.get("amount")
        category = request.form.get("category")
        note = request.form.get("note", "")
        try:
            amt = float(amount)
            if amt <= 0:
                flash("Amount must be positive.", "danger")
                return redirect(url_for("add_expense_route"))
        except Exception:
            flash("Invalid amount.", "danger")
            return redirect(url_for("add_expense_route"))

        save_expense(amt, category, note)
        flash("Expense added!", "success")
        return redirect(url_for("dashboard"))
    return render_template("add.html")

# ------------------ API Endpoints ------------------
@app.route("/api/summary")
def api_summary():
    df = load_df()
    today = pd.Timestamp.today()

    total_today = df.loc[df["Date"].dt.date == today.date(), "Amount"].sum()
    total_week = df.loc[df["Date"] >= today - pd.Timedelta(days=7), "Amount"].sum()
    total_month = df.loc[df["Date"] >= today.replace(day=1), "Amount"].sum()
    cat_totals = df.groupby("Category")["Amount"].sum().sort_values(ascending=False).to_dict()
    charts = generate_charts(df)

    return jsonify({
        "today": float(total_today),
        "week": float(total_week),
        "month": float(total_month),
        "category_totals": cat_totals,
        "charts": {k: os.path.basename(v) for k, v in charts.items()}
    })

@app.route("/api/category-data")
def api_category_data():
    df = load_df()
    cat = df.groupby("Category")["Amount"].sum().sort_values(ascending=False)
    labels = list(cat.index.astype(str))
    values = list(cat.values.astype(float))
    return jsonify({"labels": labels, "values": values})

@app.route("/api/monthly-data")
def api_monthly_data():
    df = load_df()
    if df.empty:
        return jsonify({"labels": [], "values": []})

    monthly = df.groupby(df["Date"].dt.to_period("M"))["Amount"].sum().sort_index()
    monthly = monthly.asfreq('M', fill_value=0)

    labels = [p.strftime("%b %Y") for p in monthly.index.to_timestamp()]
    values = monthly.values.astype(float).tolist()
    return jsonify({"labels": labels, "values": values})

@app.route("/predict")
def predict_next_month():
    df = load_df()
    if df.empty:
        return jsonify({"ok": False, "message": "No data available for prediction."}), 400

    monthly = df.groupby(df["Date"].dt.to_period("M"))["Amount"].sum().sort_index()
    monthly = monthly.asfreq('M', fill_value=0)

    if len(monthly) < 2:
        return jsonify({"ok": False, "message": "Need at least 2 months of data."}), 400

    X = [[i] for i in range(1, len(monthly) + 1)]
    y = monthly.values.astype(float)
    model = LinearRegression().fit(X, y)
    pred = float(max(model.predict([[len(X) + 1]])[0], 0))
    return jsonify({"ok": True, "prediction": round(pred, 2)})

# ------------------ Reports ------------------
@app.route("/export_report")
def export_report():
    df = load_df()
    total_spent = float(df["Amount"].sum())
    cat = df.groupby("Category")["Amount"].sum().sort_values(ascending=False).to_dict()

    pred_val = None
    try:
        resp = predict_next_month()
        if isinstance(resp, tuple):
            resp_obj, status = resp
        else:
            resp_obj = resp
        data = resp_obj.get_json()
        if data.get("ok"):
            pred_val = data["prediction"]
    except Exception:
        pred_val = None

    imgs = generate_charts(df)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_csv = os.path.join(REPORT_DIR, f"report_{timestamp}.csv")
    df.to_csv(report_csv, index=False)

    summary_txt = os.path.join(REPORT_DIR, f"summary_{timestamp}.txt")
    with open(summary_txt, "w", encoding="utf-8") as f:
        f.write("Expense Tracker Summary Report\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write(f"Total Spent (all time): ₹{total_spent}\n\n")
        f.write("Category-wise spending:\n")
        for k, v in cat.items():
            f.write(f" - {k}: ₹{v}\n")
        if pred_val is not None:
            f.write(f"\nPredicted next month: ₹{pred_val}\n")

    result = {
        "csv": os.path.basename(report_csv),
        "summary": os.path.basename(summary_txt),
        "charts": {k: os.path.basename(v) for k, v in imgs.items()} if imgs else {}
    }
    return jsonify({"ok": True, "files": result})

@app.route("/charts/<path:filename>")
def serve_chart(filename):
    return send_from_directory(CHART_DIR, filename)

@app.route("/reports/<path:filename>")
def serve_report(filename):
    return send_from_directory(REPORT_DIR, filename, as_attachment=True)

# ------------------ Main ------------------
if __name__ == "__main__":
    ensure_csv()
    app.run(debug=True)
