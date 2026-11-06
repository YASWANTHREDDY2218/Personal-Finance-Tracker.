import csv
from pathlib import Path

class CSVStore:
    """Reusable CSV storage matching the Smart Campus project structure."""
    def __init__(self, path, fieldnames, key_field):
        self.path = Path(path).resolve()
        self.fieldnames = fieldnames
        self.key_field = key_field
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save_all([])

    def get_all(self):
        with self.path.open("r", newline="", encoding="utf-8-sig") as file:
            return [dict(row) for row in csv.DictReader(file)
                    if row and row.get(self.key_field)]

    def save_all(self, rows):
        with self.path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=self.fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in self.fieldnames})

    def add(self, row):
        rows = self.get_all()
        rows.append({field: row.get(field, "") for field in self.fieldnames})
        self.save_all(rows)

    def update(self, row):
        target = str(row.get(self.key_field, "")).strip().casefold()
        rows = self.get_all()
        for i, current in enumerate(rows):
            if str(current.get(self.key_field, "")).strip().casefold() == target:
                rows[i] = {field: row.get(field, "") for field in self.fieldnames}
                self.save_all(rows)
                return True
        return False

    def delete(self, key):
        target = str(key).strip().casefold()
        rows = self.get_all()
        kept = [row for row in rows if str(row.get(self.key_field, "")).strip().casefold() != target]
        if len(kept) == len(rows):
            return False
        self.save_all(kept)
        return True
