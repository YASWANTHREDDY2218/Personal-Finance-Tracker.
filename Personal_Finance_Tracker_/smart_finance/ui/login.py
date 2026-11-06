import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USERS_FILE = ROOT / "DATA" / "users.csv"


def prepare_users_file():
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        with USERS_FILE.open("w", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow(["username", "password"])


def read_users():
    prepare_users_file()
    with USERS_FILE.open("r", newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def register():
    users = read_users()
    print("\n========== CREATE ACCOUNT ==========")
    username = input("Create username: ").strip()
    password = input("Create password (visible): ")
    if not username or not password:
        print("Username and password cannot be empty.")
        return
    if any(u.get("username", "").casefold() == username.casefold() for u in users):
        print("That username already exists. Please choose another.")
        return
    with USERS_FILE.open("a", newline="", encoding="utf-8") as file:
        csv.writer(file).writerow([username, password])
    print("Registration successful! You can now log in.")


def login():
    users = read_users()
    print("\n========== LOGIN ==========")
    for attempt in range(3):
        username = input("Enter username: ").strip()
        password = input("Enter password (visible): ")
        if any(u.get("username", "") == username and u.get("password", "") == password for u in users):
            print("\nLogin successful! Welcome,", username)
            return username
        print("Incorrect username or password.")
        print(f"Attempts remaining: {2 - attempt}")
    print("Too many failed attempts.")
    return None


def start_login():
    while True:
        print("\n===== PERSONAL FINANCE TRACKER =====")
        print("1. Register")
        print("2. Login")
        print("3. Exit")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            register()
        elif choice == "2":
            username = login()
            if username:
                return username
        elif choice == "3":
            print("Thank you!")
            return None
        else:
            print("Invalid choice. Please select 1, 2, or 3.")
