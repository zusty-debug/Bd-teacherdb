"""CLI to import a CSV file into the database.

Usage:
    python -m scripts.import_csv path/to/file.csv
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine, setup_postgres_indexes  # noqa: E402
from app.importer import import_csv  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", help="Path to the CSV file to import")
    args = parser.parse_args()

    # Ensure tables exist (basic indexes only). Trigram indexes are built
    # AFTER import — building them during a bulk load would slow every INSERT.
    Base.metadata.create_all(bind=engine)

    data = Path(args.csv_path).read_bytes()
    db = SessionLocal()
    try:
        summary = import_csv(db, data)
    finally:
        db.close()

    setup_postgres_indexes()

    print("Import complete:")
    for k, v in summary.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
