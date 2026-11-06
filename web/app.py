"""
web/app.py  –  Flask REST API for Personal Finance Tracker
All business logic is delegated to finance_service.py.
CSV storage is shared with the CLI application.
"""

import os
import sys
import csv
import io
from pathlib import Path
from functools import wraps
from datetime import date
from flask import (
    Flask, request, jsonify, session,
    send_file, send_from_directory
)

# ---------------------------------------------------------------------------
# Path setup: point Python at the project root so that existing imports work
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent / "Personal_Finance_Tracker_"
sys.path.insert(0, str(PROJECT_ROOT))

from smart_finance.services import finance_service          # business logic
from smart_finance.ui.login import read_users, USERS_FILE   # auth helpers

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prepare_users_file():
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        with USERS_FILE.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["username", "password"])


def _find_user(username, password=None):
    """Return user dict if found (optionally match password), else None."""
    users = read_users()
    for u in users:
        if u.get("username", "").strip().casefold() == username.strip().casefold():
            if password is None:
                return u
            if u.get("password", "") == password:
                return u
    return None


def _register_user(username, password):
    """Write new user row. Returns (True, msg) or (False, err)."""
    _prepare_users_file()
    users = read_users()
    if any(u.get("username", "").strip().casefold() == username.strip().casefold() for u in users):
        return False, "Username already exists."
    with USERS_FILE.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([username.strip(), password])
    return True, "Account created successfully."


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return jsonify({"error": "Unauthorized. Please log in."}), 401
        finance_service.set_user(session["username"])
        return f(*args, **kwargs)
    return decorated


def _error(msg, code=400):
    return jsonify({"error": str(msg)}), code


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(force=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return _error("Username and password are required.")
    user = _find_user(username, password)
    if not user:
        return _error("Invalid username or password.", 401)
    session.clear()
    session["username"] = user["username"]
    return jsonify({"message": "Login successful", "username": user["username"]})


@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.get_json(force=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return _error("Username and password are required.")
    if len(username) < 3:
        return _error("Username must be at least 3 characters.")
    if len(password) < 4:
        return _error("Password must be at least 4 characters.")
    ok, msg = _register_user(username, password)
    if not ok:
        return _error(msg, 409)
    return jsonify({"message": msg}), 201


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"message": "Logged out successfully."})


@app.route("/api/auth/me", methods=["GET"])
def api_me():
    if "username" in session:
        return jsonify({"username": session["username"]})
    return jsonify({"username": None}), 401


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/api/dashboard", methods=["GET"])
@login_required
def api_dashboard():
    income, expenses, savings, net, available = finance_service.totals()
    savings_rate = round((savings / income * 100), 1) if income > 0 else 0.0

    # Smart financial insights
    insights = []
    if income > 0:
        expense_ratio = expenses / income * 100
        if expense_ratio > 90:
            insights.append({"type": "danger", "text": f"You're spending {expense_ratio:.0f}% of your income. Consider cutting expenses."})
        elif expense_ratio > 70:
            insights.append({"type": "warning", "text": f"Spending is at {expense_ratio:.0f}% of income. Try to save more."})
        else:
            insights.append({"type": "success", "text": f"Great! Your expense ratio is {expense_ratio:.0f}%. Keep it up."})

    if savings_rate >= 20:
        insights.append({"type": "success", "text": f"Excellent savings rate of {savings_rate}%! You're on track."})
    elif savings_rate > 0:
        insights.append({"type": "info", "text": f"Savings rate is {savings_rate}%. Aim for at least 20%."})

    budget_st = finance_service.budget_status()
    exceeded = [b for b in budget_st if b["exceeded"]]
    near_limit = [b for b in budget_st if not b["exceeded"] and b["budget"] > 0 and b["spent"] / b["budget"] >= 0.8]
    if exceeded:
        cats = ", ".join(b["name"] for b in exceeded)
        insights.append({"type": "danger", "text": f"Budget exceeded in: {cats}."})
    if near_limit:
        cats = ", ".join(b["name"] for b in near_limit)
        insights.append({"type": "warning", "text": f"Near budget limit (80%+) in: {cats}."})

    # Category-wise spending (current month)
    txns = finance_service.all_transactions()
    current_month = date.today().strftime("%Y-%m")
    monthly_expense_by_cat = {}
    for t in txns:
        if t["type"] == "expense":
            try:
                if date.fromisoformat(t["date"]).strftime("%Y-%m") == current_month:
                    cat = t["category"].strip()
                    monthly_expense_by_cat[cat] = monthly_expense_by_cat.get(cat, 0) + t["amount"]
            except (ValueError, TypeError):
                pass

    monthly_report = finance_service.monthly_report()

    return jsonify({
        "totals": {
            "income": income,
            "expenses": expenses,
            "savings": savings,
            "net_balance": net,
            "available_balance": available,
            "savings_rate": savings_rate
        },
        "budgets": budget_st,
        "goals": finance_service.savings_goal_overview(),
        "insights": insights,
        "category_spending": [{"category": k, "amount": round(v, 2)} for k, v in sorted(monthly_expense_by_cat.items(), key=lambda x: -x[1])],
        "monthly_report": [
            {"month": r[0], "income": r[1], "expenses": r[2], "balance": r[3]}
            for r in monthly_report
        ]
    })


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@app.route("/api/transactions", methods=["GET"])
@login_required
def api_transactions_get():
    rows = finance_service.user_transactions()

    # Filters from query params
    search = request.args.get("search", "").strip().casefold()
    cat_filter = request.args.get("category", "").strip().casefold()
    type_filter = request.args.get("type", "").strip().casefold()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    sort_by = request.args.get("sort", "date")          # date | amount
    sort_dir = request.args.get("order", "desc")        # asc | desc

    filtered = []
    for r in rows:
        # Search
        if search:
            hay = f"{r.get('description','')} {r.get('category','')}".casefold()
            if search not in hay:
                continue
        # Category filter
        if cat_filter and r.get("category", "").strip().casefold() != cat_filter:
            continue
        # Type filter
        if type_filter and r.get("type", "").strip().casefold() != type_filter:
            continue
        # Date range
        try:
            d = date.fromisoformat(r["date"])
            if date_from and d < date.fromisoformat(date_from):
                continue
            if date_to and d > date.fromisoformat(date_to):
                continue
        except (ValueError, TypeError):
            pass
        filtered.append(r)

    # Sort
    reverse = sort_dir == "desc"
    if sort_by == "amount":
        filtered.sort(key=lambda x: x.get("amount", 0), reverse=reverse)
    else:
        filtered.sort(key=lambda x: x.get("date", ""), reverse=reverse)

    return jsonify({"transactions": filtered})


@app.route("/api/transactions", methods=["POST"])
@login_required
def api_transactions_post():
    data = request.get_json(force=True) or {}
    try:
        record = finance_service.add_transaction(
            kind=data.get("type", ""),
            amount=data.get("amount"),
            category=data.get("category", ""),
            description=data.get("description", ""),
            transaction_date=data.get("date", "")
        )
        return jsonify({"message": "Transaction added.", "transaction": record}), 201
    except ValueError as e:
        return _error(e)


@app.route("/api/transactions/<txn_id>", methods=["DELETE"])
@login_required
def api_transactions_delete(txn_id):
    rows = finance_service.user_transactions()
    idx = next((i for i, r in enumerate(rows) if str(r.get("id")) == txn_id), None)
    if idx is None:
        return _error("Transaction not found.", 404)
    try:
        removed = finance_service.delete_transaction(idx + 1)
        return jsonify({"message": "Transaction deleted.", "transaction": removed})
    except ValueError as e:
        return _error(e)


@app.route("/api/transactions/export", methods=["GET"])
@login_required
def api_transactions_export():
    rows = finance_service.user_transactions()
    output = io.StringIO()
    fields = ["id", "type", "amount", "category", "description", "date"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    filename = f"transactions_{session['username']}_{date.today().isoformat()}.csv"
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename
    )


# ---------------------------------------------------------------------------
# Budgets
# ---------------------------------------------------------------------------

@app.route("/api/budgets", methods=["GET"])
@login_required
def api_budgets_get():
    return jsonify({"budgets": finance_service.budget_status()})


@app.route("/api/budgets", methods=["POST"])
@login_required
def api_budgets_post():
    data = request.get_json(force=True) or {}
    try:
        record = finance_service.set_budget(
            category=data.get("category", ""),
            amount=data.get("amount")
        )
        return jsonify({"message": "Budget saved.", "budget": record}), 201
    except ValueError as e:
        return _error(e)


@app.route("/api/budgets/<path:category>", methods=["DELETE"])
@login_required
def api_budgets_delete(category):
    ok = finance_service.delete_budget(category)
    if not ok:
        return _error("Budget not found.", 404)
    return jsonify({"message": "Budget deleted."})


# ---------------------------------------------------------------------------
# Savings Goals
# ---------------------------------------------------------------------------

@app.route("/api/goals", methods=["GET"])
@login_required
def api_goals_get():
    return jsonify({"goals": finance_service.savings_goal_overview()})


@app.route("/api/goals", methods=["POST"])
@login_required
def api_goals_post():
    data = request.get_json(force=True) or {}
    try:
        record = finance_service.add_goal(
            name=data.get("name", ""),
            target=data.get("target")
        )
        return jsonify({"message": "Savings goal created.", "goal": record}), 201
    except ValueError as e:
        return _error(e)


@app.route("/api/goals/<int:goal_n>/add", methods=["POST"])
@login_required
def api_goals_add(goal_n):
    data = request.get_json(force=True) or {}
    try:
        goal = finance_service.add_to_goal(
            number=goal_n,
            amount=data.get("amount"),
            savings_date=data.get("date", "")
        )
        return jsonify({"message": "Savings added.", "goal": goal})
    except ValueError as e:
        return _error(e)


@app.route("/api/goals/<int:goal_n>", methods=["DELETE"])
@login_required
def api_goals_delete(goal_n):
    try:
        removed = finance_service.delete_goal(goal_n)
        return jsonify({"message": "Savings goal deleted.", "goal": removed})
    except ValueError as e:
        return _error(e)


# ---------------------------------------------------------------------------
# Monthly report
# ---------------------------------------------------------------------------

@app.route("/api/report", methods=["GET"])
@login_required
def api_report():
    data = finance_service.monthly_report()
    return jsonify({
        "report": [
            {"month": r[0], "income": r[1], "expenses": r[2], "balance": r[3]}
            for r in data
        ]
    })


# ---------------------------------------------------------------------------
# Serve SPA
# ---------------------------------------------------------------------------

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def spa(path):
    return send_from_directory(str(STATIC_DIR), "index.html")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5000)
