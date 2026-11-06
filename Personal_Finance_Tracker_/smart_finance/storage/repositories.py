from pathlib import Path
from config import DATA_DIR
from smart_finance.storage.csv_store import CSVStore

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / DATA_DIR

TRANSACTION_FIELDS    = ["id", "username", "type", "amount", "category", "description", "date"]
BUDGET_FIELDS         = ["category_key", "username", "name", "amount"]
SAVINGS_FIELDS        = ["goal_key", "username", "name", "target", "saved"]
TRANSFER_FIELDS       = ["transfer_key", "username", "year_month", "amount", "goal_name", "transferred_on"]

transactions    = CSVStore(DATA / "transactions.csv",      TRANSACTION_FIELDS, "id")
budgets         = CSVStore(DATA / "budgets.csv",           BUDGET_FIELDS,      "category_key")
savings_goals   = CSVStore(DATA / "savings_goals.csv",     SAVINGS_FIELDS,     "goal_key")
monthly_transfers = CSVStore(DATA / "monthly_transfers.csv", TRANSFER_FIELDS,  "transfer_key")
