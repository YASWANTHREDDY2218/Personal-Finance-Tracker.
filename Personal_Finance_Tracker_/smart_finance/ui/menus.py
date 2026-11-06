"""
menus.py  –  All user interface menus for Personal Finance Tracker.

Key calculations:
-----------------
  Net Balance       = Income − Expenses
  Available Balance = Income − Expenses − Savings
"""

from datetime import date
from config import APPLICATION_NAME, APPLICATION_VERSION
from smart_finance.services import finance_service as service
from smart_finance.ui.helpers import ask, show_transactions, show_budgets, show_goals


# ---------------------------------------------------------------------------
# 1. Income & Expense Management
# ---------------------------------------------------------------------------

def transaction_menu():
    while True:
        print("\n1. Add transaction  2. View transactions  3. Delete transaction  0. Back")
        choice = ask("Choose")
        try:
            if choice == "1":
                kind        = ask("Type (income/expense)").lower()
                amount      = ask("Amount (₹)")
                category    = ask("Category")
                description = ask("Description")
                when        = ask(f"Date YYYY-MM-DD [{date.today().isoformat()}] (Enter for today)")
                row = service.add_transaction(kind, amount, category, description, when)
                print(f"Saved transaction #{row['id']}.")
            elif choice == "2":
                show_transactions(service.user_transactions())
            elif choice == "3":
                rows = service.user_transactions()
                show_transactions(rows)
                if rows:
                    removed = service.delete_transaction(int(ask("Transaction number to delete")))
                    print(f"Deleted {removed['type']} transaction: {removed['category']}.")
            elif choice == "0":
                return
            else:
                print("Invalid choice.")
        except (ValueError, TypeError) as e:
            print(f"Error: {e}")


# ---------------------------------------------------------------------------
# 2. Financial Dashboard
# ---------------------------------------------------------------------------

def dashboard():
    """
    Financial Dashboard displaying:
      - Total Income
      - Total Expenses
      - Total Savings
      - Net Balance (Income − Expenses)
      - Available Balance (Income − Expenses − Savings)
      - Budget Overview for each category (Current Month)
      - Savings Goals Overview (Target, Saved, Remaining, Progress %)
    Automatically checks for pending monthly savings opportunities.
    """
    # Check for completed months with unused savings first
    check_monthly_savings()

    today       = date.today()
    month_label = today.strftime("%B %Y")

    print("\n" + "=" * 65)
    print(f"            FINANCIAL DASHBOARD  —  {month_label}")
    print("=" * 65)

    # --- 1. Overall Totals ---
    income, expenses, savings, net_balance, available = service.totals()

    print("\n  ── Overall Financial Summary ──────────────────────────")
    print(f"  Total Income        : ₹{income:>12,.2f}")
    print(f"  Total Expenses      : ₹{expenses:>12,.2f}")
    print(f"  Total Savings       : ₹{savings:>12,.2f}")
    print(f"  Net Balance         : ₹{net_balance:>12,.2f}   (Income − Expenses)")
    print(f"  Available Balance   : ₹{available:>12,.2f}   (Income − Expenses − Savings)")

    if net_balance > 0:
        status_msg = "You are saving money."
    elif net_balance < 0:
        status_msg = "Expenses exceed income!"
    else:
        status_msg = "Income and expenses are equal."
    print(f"  Financial Status    : {status_msg}")

    # --- 2. Current Month Budget Overview ---
    print(f"\n  ── Budget Overview ({month_label}) ─────────────────────────")
    budget_rows = service.budget_status()
    if not budget_rows:
        print("  No budgets set yet. Go to Budget Management to add one.")
    else:
        show_budgets(budget_rows, month_label)

    # --- 3. Savings Goals Overview ---
    print(f"\n  ── Savings Goals Overview ─────────────────────────────")
    goals = service.savings_goal_overview()
    if not goals:
        print("  No savings goals set yet. Go to Savings Goals to create one.")
    else:
        show_goals(goals)

    print("=" * 65)


# ---------------------------------------------------------------------------
# 3. Budget Management
# ---------------------------------------------------------------------------

def budget_menu():
    while True:
        print("\n1. Set/update budget  2. View budgets  3. Delete budget  0. Back")
        choice = ask("Choose")
        try:
            if choice == "1":
                r = service.set_budget(ask("Expense category"), ask("Budget amount (₹)"))
                print(f"Budget saved for '{r['name']}'.")
            elif choice == "2":
                month_label = date.today().strftime("%B %Y")
                print(f"\n  Showing budgets for: {month_label}")
                show_budgets(service.budget_status(), month_label)
            elif choice == "3":
                month_label = date.today().strftime("%B %Y")
                rows = service.budget_status()
                show_budgets(rows, month_label)
                if rows:
                    name = ask("Category name to delete")
                    if not service.delete_budget(name):
                        print("Budget category not found.")
                    else:
                        print("Budget deleted.")
            elif choice == "0":
                return
            else:
                print("Invalid choice.")
        except (ValueError, TypeError) as e:
            print(f"Error: {e}")


# ---------------------------------------------------------------------------
# 4. Savings Goals & Manual Savings
# ---------------------------------------------------------------------------

def savings_menu():
    while True:
        print("\n1. Add goal  2. Add savings to goal  3. View goals  4. Delete goal  0. Back")
        choice = ask("Choose")
        try:
            if choice == "1":
                goal = service.add_goal(ask("Goal name"), ask("Target amount (₹)"))
                print(f"Savings goal '{goal['name']}' saved successfully.")

            elif choice == "2":
                # Manual savings addition
                goals = service.savings_goal_overview()
                if not goals:
                    print("No savings goals found. Please add a goal first.")
                    continue

                show_goals(goals)
                goal_num = int(ask("Enter goal number to add savings to"))
                amount   = ask("Amount to save (₹)")
                when     = ask(f"Date YYYY-MM-DD [{date.today().isoformat()}] (Enter for today)")

                goal = service.add_to_goal(goal_num, amount, when)
                income, expenses, savings, net_balance, available = service.totals()

                print(f"\n  ✓ Successfully saved ₹{float(amount):,.2f} to '{goal['name']}'.")
                print(f"  Total Saved in Goal : ₹{float(goal['saved']):,.2f}")
                print(f"  Available Balance   : ₹{available:,.2f}")

            elif choice == "3":
                goals = service.savings_goal_overview()
                show_goals(goals)

            elif choice == "4":
                goals = service.savings_goal_overview()
                show_goals(goals)
                if goals:
                    removed = service.delete_goal(int(ask("Goal number to delete")))
                    print(f"Deleted goal '{removed['name']}'.")

            elif choice == "0":
                return
            else:
                print("Invalid choice.")
        except (ValueError, TypeError) as e:
            print(f"Error: {e}")


# ---------------------------------------------------------------------------
# Automatic Monthly Savings Transfer
# ---------------------------------------------------------------------------

def check_monthly_savings():
    """
    Checks for completed months where:
      Monthly Unused Money = Monthly Income − Monthly Expenses − Monthly Manual Savings > 0

    Prompts the user for permission:
      - Displays the calculated unused money.
      - Asks if they want to transfer it.
      - Allows them to select an existing savings goal.
      - Asks for final confirmation before transferring.
      - Prevents duplicate transfers using DATA/monthly_transfers.csv.
      - If user declines, nothing is transferred.
    """
    pending = service.detect_pending_transfers()
    if not pending:
        return

    goals = service.savings_goal_overview()

    for entry in pending:
        ym             = entry["year_month"]
        income         = entry["income"]
        expenses       = entry["expenses"]
        manual_savings = entry["manual_savings"]
        unused         = entry["unused"]

        print("\n" + "=" * 65)
        print(f"  💰 Monthly Savings Opportunity Detected: Month {ym}")
        print("=" * 65)
        print(f"  Total Monthly Income         : ₹{income:>12,.2f}")
        print(f"  Total Monthly Expenses       : ₹{expenses:>12,.2f}")
        if manual_savings > 0:
            print(f"  Monthly Manual Savings       : ₹{manual_savings:>12,.2f} (Already saved)")
        print(f"  Remaining Unused Money       : ₹{unused:>12,.2f}")
        print("=" * 65)

        permission = ask("Transfer this unused amount to a savings goal? (yes/no)").strip().lower()
        if permission not in ("yes", "y"):
            print(f"Transfer declined for {ym}. No changes made.")
            continue

        if not goals:
            print("No savings goals found. Please create a goal first (option 4), then visit the Dashboard.")
            continue

        print()
        show_goals(goals)
        try:
            goal_num = int(ask("Enter goal number to receive the transfer"))
        except ValueError:
            print("Invalid input. Transfer cancelled.")
            continue

        if goal_num < 1 or goal_num > len(goals):
            print("Invalid goal number. Transfer cancelled.")
            continue

        chosen_goal = goals[goal_num - 1]
        print(f"\nYou are transferring ₹{unused:,.2f} to '{chosen_goal['name']}'.")
        confirm = ask("Confirm transfer? (yes/no)").strip().lower()
        if confirm not in ("yes", "y"):
            print("Transfer cancelled by user. No changes made.")
            continue

        try:
            updated = service.transfer_to_goal(ym, unused, goal_num)
            print(f"\n  ✓ Successfully transferred ₹{unused:,.2f} to '{updated['name']}'!")
            print(f"  New Saved Amount in Goal: ₹{float(updated['saved']):,.2f}")
            goals = service.savings_goal_overview()
        except ValueError as e:
            print(f"Error: {e}")


# ---------------------------------------------------------------------------
# 5. Smart Spending Analysis
# ---------------------------------------------------------------------------

def spending_analysis():
    rows  = [r for r in service.all_transactions() if r["type"] == "expense"]
    total = sum(r["amount"] for r in rows)
    if not rows:
        print("No expenses available for analysis.")
        return
    categories = {}
    for r in rows:
        categories[r["category"]] = categories.get(r["category"], 0) + r["amount"]
    print(f"\n  Total spending: ₹{total:,.2f}")
    for name, amount in sorted(categories.items(), key=lambda item: item[1], reverse=True):
        print(f"  {name}: ₹{amount:,.2f} ({amount / total * 100:.1f}%)")
    print(f"\n  Highest spending category: {max(categories, key=categories.get)}")
    print(f"  Average daily spending (30-day estimate): ₹{total / 30:,.2f}")


# ---------------------------------------------------------------------------
# 6. Can I Afford It?
# ---------------------------------------------------------------------------

def affordability():
    income, expenses, savings, net_balance, available = service.totals()
    print(f"\n  Net Balance       : ₹{net_balance:,.2f}  (Income − Expenses)")
    print(f"  Total Savings     : ₹{savings:,.2f}")
    print(f"  Available Balance : ₹{available:,.2f}  (Income − Expenses − Savings)")
    try:
        amount = float(ask("Planned purchase amount (₹)"))
        if amount <= 0:
            raise ValueError("Amount must be greater than ₹0.")
        if amount <= available:
            print(f"  ✓ Affordable! Balance after purchase: ₹{available - amount:,.2f}")
        else:
            print(f"  ✗ Not affordable from available balance. Short by ₹{amount - available:,.2f}")
    except ValueError as e:
        print(f"  Error: {e}")


# ---------------------------------------------------------------------------
# 7. Monthly Comparison Report
# ---------------------------------------------------------------------------

def monthly_report():
    rows = service.monthly_report()
    if not rows:
        print("No dated transactions available for monthly comparison.")
        return
    print(f"\n  {'Month':<12}{'Income':>14}{'Expenses':>14}{'Balance':>14}")
    print("  " + "-" * 56)
    for month, income, expenses, balance in rows:
        print(f"  {month:<12}₹{income:>12,.2f}₹{expenses:>12,.2f}₹{balance:>12,.2f}")


# ---------------------------------------------------------------------------
# Main Menu
# ---------------------------------------------------------------------------

def run_main_menu():
    # Detect completed months with unused savings upon login
    check_monthly_savings()

    actions = {
        "1": transaction_menu,
        "2": dashboard,
        "3": budget_menu,
        "4": savings_menu,
        "5": spending_analysis,
        "6": affordability,
        "7": monthly_report,
    }
    while True:
        print(f"\n{'=' * 48}\n{APPLICATION_NAME} v{APPLICATION_VERSION}\n{'=' * 48}")
        print("1. Income & Expense Management")
        print("2. Financial Dashboard")
        print("3. Budget Management")
        print("4. Savings Goals")
        print("5. Smart Spending Analysis")
        print("6. Can I Afford It?")
        print("7. Monthly Comparison Report")
        print("8. Exit")
        choice = ask("Enter your choice")
        if choice == "8":
            print("Thank you for using Personal Finance Tracker!")
            break
        action = actions.get(choice)
        if action:
            action()
        else:
            print("Invalid choice. Select 1 to 8.")
