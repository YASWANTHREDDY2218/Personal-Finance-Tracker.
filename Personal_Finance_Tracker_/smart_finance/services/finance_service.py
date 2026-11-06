"""
finance_service.py  –  Core business logic for Personal Finance Tracker.

Key features and rules implemented:
-----------------------------------
1. Transactions:
   - Supports 'income', 'expense', and 'savings' transaction types.
   - User transactions (viewed/deleted in Transaction menu) only show income & expense.
   - Savings are NOT counted as personal expenses.

2. Totals:
   - totals() returns:
       income, expenses, total_savings, net_balance, available_balance
   - Net Balance       = Income − Expenses
   - Available Balance = Income − Expenses − Total Savings

3. Budgets:
   - Calculated for the current calendar month (YYYY-MM).
   - Fresh calculation each month without deleting any past transactions.
   - Category matching is case-insensitive and ignores leading/trailing spaces.
   - Tracks budget, spent, remaining, and exceeded status.

4. Manual Savings:
   - Users can manually add money to any existing savings goal.
   - Updates goal saved amount and progress automatically.
   - Deducts from Available Balance (recorded as a 'savings' transaction).
   - Never counted as an expense.

5. Automatic Monthly Savings:
   - Detects completed months (prior to current month).
   - Monthly Unused = Monthly Income − Monthly Expenses − Monthly Manual Savings.
   - Prompts user with unused money and requests confirmation.
   - Prevents duplicate transfers using DATA/monthly_transfers.csv.
   - If user declines, no transfer occurs.
"""

from datetime import date
from collections import defaultdict
from smart_finance.storage.repositories import (
    transactions, budgets, savings_goals, monthly_transfers
)
from smart_finance.utils.validation import positive_amount, valid_date

CURRENT_USER = ""


def set_user(username):
    global CURRENT_USER
    CURRENT_USER = username


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _mine(store):
    """Return only rows that belong to the current logged-in user."""
    results = []
    prefix = f"{CURRENT_USER.casefold()}|"
    for r in store.get_all():
        u = r.get("username", "")
        if u:
            if u == CURRENT_USER:
                results.append(r)
        else:
            # Fallback for old CSV files where username column wasn't populated
            for k in ("category_key", "goal_key", "transfer_key"):
                val = r.get(k, "")
                if val and val.casefold().startswith(prefix):
                    results.append(r)
                    break
    return results


def _next_txn_id():
    """Return the next unique numeric transaction ID as a string."""
    rows = transactions.get_all()
    return str(max([int(r["id"]) for r in rows if r.get("id", "").isdigit()] or [0]) + 1)


def _record_savings_transaction(amount, goal_name, txn_date):
    """
    Internal: write a transaction of type 'savings'.
    Deducts money from Available Balance without counting as a personal expense.
    """
    record = {
        "id":          _next_txn_id(),
        "username":    CURRENT_USER,
        "type":        "savings",
        "amount":      f"{float(amount):.2f}",
        "category":    "Savings",
        "description": f"Savings Goal: {goal_name}",
        "date":        txn_date
    }
    transactions.add(record)
    return record


def _current_month_str():
    """Return the current year-month string, e.g. '2026-11'."""
    return date.today().strftime("%Y-%m")


def _month_transactions(year_month=None):
    """
    Return all transactions for the given month (default = current month).
    year_month format: 'YYYY-MM'
    """
    if year_month is None:
        year_month = _current_month_str()
    result = []
    for row in all_transactions():
        try:
            if date.fromisoformat(row["date"]).strftime("%Y-%m") == year_month:
                result.append(row)
        except (ValueError, TypeError):
            continue
    return result


# ---------------------------------------------------------------------------
# Transactions (Income & Expense)
# ---------------------------------------------------------------------------

def all_transactions():
    """Return all transactions for current user with amounts as floats."""
    rows = _mine(transactions)
    for row in rows:
        row["amount"] = float(row.get("amount") or 0)
    return rows


def user_transactions():
    """Return only income and expense transactions (for user menu view/delete)."""
    return [r for r in all_transactions() if r["type"] in ("income", "expense")]


def add_transaction(kind, amount, category, description, transaction_date=""):
    """Add an income or expense transaction."""
    kind = kind.strip().lower()
    if kind not in ("income", "expense"):
        raise ValueError("Type must be income or expense.")
    amount = positive_amount(amount)
    category, description = category.strip(), description.strip()
    if not category or not description:
        raise ValueError("Category and description cannot be empty.")
    transaction_date = valid_date(transaction_date.strip() or date.today().isoformat())
    record = {
        "id":          _next_txn_id(),
        "username":    CURRENT_USER,
        "type":        kind,
        "amount":      f"{amount:.2f}",
        "category":    category,
        "description": description,
        "date":        transaction_date
    }
    transactions.add(record)
    return record


def delete_transaction(number):
    """Delete an income/expense transaction by its display index."""
    rows = user_transactions()
    if number < 1 or number > len(rows):
        raise ValueError("Invalid transaction number.")
    removed = rows[number - 1]
    transactions.save_all([r for r in transactions.get_all() if r.get("id") != removed["id"]])
    return removed


# ---------------------------------------------------------------------------
# Totals (All-Time)
# ---------------------------------------------------------------------------

def totals():
    """
    Return (income, expenses, total_savings, net_balance, available_balance)

    Formulas:
      Net Balance       = Income − Expenses
      Available Balance = Income − Expenses − Total Savings
    """
    rows = all_transactions()
    income   = sum(r["amount"] for r in rows if r["type"] == "income")
    expenses = sum(r["amount"] for r in rows if r["type"] == "expense")
    savings  = sum(float(g["saved"]) for g in _mine(savings_goals))
    net_balance = income - expenses
    available   = income - expenses - savings
    return income, expenses, savings, net_balance, available


# ---------------------------------------------------------------------------
# Budget Management (Current-Month)
# ---------------------------------------------------------------------------

def set_budget(category, amount):
    """Set or update budget for an expense category."""
    category = category.strip()
    if not category:
        raise ValueError("Category cannot be empty.")
    amount = positive_amount(amount, "Budget")
    key = CURRENT_USER.casefold() + "|" + category.casefold()
    record = {
        "category_key": key,
        "username":     CURRENT_USER,
        "name":         category,
        "amount":       f"{amount:.2f}"
    }
    if any(r["category_key"].casefold() == key for r in budgets.get_all()):
        budgets.update(record)
    else:
        budgets.add(record)
    return record


def budget_status(year_month=None):
    """
    Calculate budget status for the given month (default = current month).
    Only 'expense' transactions are counted — savings are excluded.
    Category matching is case-insensitive and trims whitespace.

    Returns list of dicts:
      name, budget, spent, remaining, exceeded
    """
    if year_month is None:
        year_month = _current_month_str()

    month_rows = _month_transactions(year_month)
    output = []
    for b in _mine(budgets):
        cat_key = b["name"].strip().casefold()
        spent = sum(
            r["amount"] for r in month_rows
            if r["type"] == "expense"
            and r["category"].strip().casefold() == cat_key
        )
        budget_amount = float(b["amount"])
        remaining = budget_amount - spent
        output.append({
            "name":      b["name"],
            "budget":    budget_amount,
            "spent":     spent,
            "remaining": remaining,
            "exceeded":  remaining < 0
        })
    return output


monthly_budget_status = budget_status


def delete_budget(category_name):
    """Delete a budget by category name."""
    key = CURRENT_USER.casefold() + "|" + category_name.strip().casefold()
    return budgets.delete(key)


# ---------------------------------------------------------------------------
# Savings Goals & Manual Savings
# ---------------------------------------------------------------------------

def savings_goal_overview():
    """
    Return enriched goal overview for dashboard and menus:
      name, target, saved, remaining, progress_pct, goal_key
    """
    result = []
    for r in _mine(savings_goals):
        target    = float(r["target"])
        saved     = float(r["saved"])
        remaining = max(0.0, target - saved)
        progress  = min(100.0, saved / target * 100) if target > 0 else 0.0
        result.append({
            "name":         r["name"],
            "target":       target,
            "saved":        saved,
            "remaining":    remaining,
            "progress_pct": progress,
            "goal_key":     r["goal_key"]
        })
    return result


def add_goal(name, target):
    """Add a new savings goal."""
    name = name.strip()
    if not name:
        raise ValueError("Goal name cannot be empty.")
    amount = positive_amount(target, "Target")
    rows = _mine(savings_goals)
    if any(r["name"].strip().casefold() == name.casefold() for r in rows):
        raise ValueError("A savings goal with this name already exists.")
    goal_key = CURRENT_USER.casefold() + "|" + name.casefold()
    record = {
        "goal_key": goal_key,
        "username": CURRENT_USER,
        "name":     name,
        "target":   f"{amount:.2f}",
        "saved":    "0.00"
    }
    savings_goals.add(record)
    return record


def add_to_goal(number, amount, savings_date=""):
    """
    Manually add money to an existing savings goal.

    - Updates goal saved amount and progress automatically.
    - Deducts amount from Available Balance (records 'savings' transaction).
    - Does NOT count savings as a personal expense.
    - Tracks savings_date so it can be subtracted from month-end unused calculation.
    """
    rows = _mine(savings_goals)
    if number < 1 or number > len(rows):
        raise ValueError("Invalid savings goal number.")
    amount = positive_amount(amount, "Savings amount")
    goal = rows[number - 1]

    # Update goal saved amount
    goal["saved"] = f"{float(goal['saved']) + amount:.2f}"
    savings_goals.update(goal)

    # Record manual savings transaction (type = 'savings')
    txn_date = date.today().isoformat()
    if savings_date and str(savings_date).strip():
        txn_date = valid_date(str(savings_date).strip())
    _record_savings_transaction(amount, goal["name"], txn_date)

    return goal


def delete_goal(number):
    """Delete a savings goal."""
    rows = _mine(savings_goals)
    if number < 1 or number > len(rows):
        raise ValueError("Invalid savings goal number.")
    goal = rows[number - 1]
    savings_goals.delete(goal["goal_key"])
    return goal


# ---------------------------------------------------------------------------
# Automatic Monthly Savings
# ---------------------------------------------------------------------------

def _completed_months():
    """
    Return sorted list of 'YYYY-MM' months that are strictly before the
    current calendar month and have at least one income or expense transaction.
    """
    current = _current_month_str()
    seen = set()
    for row in all_transactions():
        if row["type"] not in ("income", "expense"):
            continue
        try:
            m = date.fromisoformat(row["date"]).strftime("%Y-%m")
        except (ValueError, TypeError):
            continue
        if m < current:
            seen.add(m)
    return sorted(seen)


def already_transferred(year_month):
    """Check if an automatic monthly transfer was already recorded for this month."""
    key = CURRENT_USER.casefold() + "|" + year_month
    return any(
        r.get("transfer_key", "").casefold() == key
        for r in monthly_transfers.get_all()
    )


def detect_pending_transfers():
    """
    Detect completed months with remaining unused money:

      Unused Money = Monthly Income − Monthly Personal Expenses − Monthly Manual Savings

    Only months where unused > 0 and not yet transferred are returned.
    """
    pending = []
    for year_month in _completed_months():
        if already_transferred(year_month):
            continue
        month_rows = _month_transactions(year_month)
        income         = sum(r["amount"] for r in month_rows if r["type"] == "income")
        expenses       = sum(r["amount"] for r in month_rows if r["type"] == "expense")
        manual_savings = sum(r["amount"] for r in month_rows if r["type"] == "savings")
        unused = income - expenses - manual_savings
        if unused > 0:
            pending.append({
                "year_month":     year_month,
                "income":         income,
                "expenses":       expenses,
                "manual_savings": manual_savings,
                "unused":         unused
            })
    return pending


def transfer_to_goal(year_month, amount, goal_number):
    """
    Transfer monthly unused money to a selected savings goal:
      - Validates that month was not already transferred.
      - Credits the savings goal.
      - Records transfer history in monthly_transfers.csv to prevent duplicates.
      - Does NOT modify original income/expense transactions.
    """
    if already_transferred(year_month):
        raise ValueError(f"Month {year_month} has already been transferred.")

    rows = _mine(savings_goals)
    if goal_number < 1 or goal_number > len(rows):
        raise ValueError("Invalid savings goal number.")

    goal = rows[goal_number - 1]
    new_saved = float(goal["saved"]) + float(amount)
    goal["saved"] = f"{new_saved:.2f}"
    savings_goals.update(goal)

    # Record transfer in monthly_transfers.csv
    key = CURRENT_USER.casefold() + "|" + year_month
    record = {
        "transfer_key":   key,
        "username":       CURRENT_USER,
        "year_month":     year_month,
        "amount":         f"{float(amount):.2f}",
        "goal_name":      goal["name"],
        "transferred_on": date.today().isoformat()
    }
    monthly_transfers.add(record)
    return goal


# ---------------------------------------------------------------------------
# Monthly Report
# ---------------------------------------------------------------------------

def monthly_report():
    """
    Per-month summary of income and personal expenses (savings excluded).
    Returns list of (month, income, expenses, balance) tuples.
    """
    monthly = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
    for row in all_transactions():
        if row["type"] not in ("income", "expense"):
            continue
        try:
            month = date.fromisoformat(row["date"]).strftime("%Y-%m")
        except (ValueError, TypeError):
            continue
        monthly[month]["income" if row["type"] == "income" else "expenses"] += row["amount"]
    return [
        (month, v["income"], v["expenses"], v["income"] - v["expenses"])
        for month, v in sorted(monthly.items())
    ]
