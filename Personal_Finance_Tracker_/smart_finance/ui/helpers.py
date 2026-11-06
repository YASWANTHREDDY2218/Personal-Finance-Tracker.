"""
helpers.py  –  Shared UI helper functions for Personal Finance Tracker.
"""


def ask(label):
    return input(f"{label}: ").strip()


def show_transactions(rows):
    if not rows:
        print("No transactions found.")
        return
    print(f"\n{'No.':<5}{'Type':<10}{'Amount':>12}  {'Category':<18}{'Date':<12} Description")
    print("-" * 85)
    for i, row in enumerate(rows, 1):
        print(
            f"{i:<5}{row['type']:<10}{float(row['amount']):>12,.2f}  "
            f"{row['category']:<18}{row['date']:<12} {row['description']}"
        )


def show_budgets(rows, month_label="Current Month"):
    """Display budget rows with remaining budget and exceeded status."""
    if not rows:
        print("No budgets set.")
        return
    print(f"\n  Budget Overview — {month_label}")
    print(f"  {'Category':<20} {'Budget':>12} {'Spent':>12} {'Remaining':>12}  Status")
    print("  " + "-" * 72)
    for r in rows:
        remaining = r["remaining"]
        exceeded  = r.get("exceeded", remaining < 0)
        status    = "*** BUDGET EXCEEDED ***" if exceeded else "Within budget"
        print(
            f"  {r['name']:<20} ₹{r['budget']:>11,.2f} ₹{r['spent']:>11,.2f} "
            f"₹{remaining:>11,.2f}  {status}"
        )


def show_goals(rows):
    """Display savings goals with target / saved / remaining / progress."""
    if not rows:
        print("No savings goals found.")
        return
    print(f"\n  {'#':<4}{'Goal Name':<22}{'Target':>12}{'Saved':>12}{'Remaining':>12}  Progress")
    print("  " + "-" * 70)
    for i, r in enumerate(rows, 1):
        target    = float(r["target"])
        saved     = float(r["saved"])
        remaining = max(0.0, target - saved)
        percent   = min(100.0, saved / target * 100) if target else 0.0
        bar_filled = int(percent / 5)          # 20-char bar
        bar = "[" + "#" * bar_filled + "-" * (20 - bar_filled) + "]"
        print(
            f"  {i:<4}{r['name']:<22}₹{target:>11,.2f}₹{saved:>11,.2f}"
            f"₹{remaining:>11,.2f}  {percent:5.1f}% {bar}"
        )
