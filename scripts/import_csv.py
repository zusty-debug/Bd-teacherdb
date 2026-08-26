"""CLI to import a CSV file into the database.

Usage:
    python -m scripts.import_csv path/to/file.csv [--default-school "My School"]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal  # noqa: E402
from app.importer import import_csv  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", help="Path to the CSV file to import")
    parser.add_argument("--default-school", default="Default School")
    args = parser.parse_args()

    data = Path(args.csv_path).read_bytes()
    db = SessionLocal()
    try:
        summary = import_csv(db, data, default_school_name=args.default_school)
    finally:
        db.close()

    print("Import complete:")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
