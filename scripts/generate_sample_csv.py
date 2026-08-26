"""Generate a realistic sample student CSV for local testing.

Usage:
    python -m scripts.generate_sample_csv --rows 20000 --out sample_students.csv
"""
import argparse
import csv
import random

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Reyansh", "Krishna", "Ishaan",
    "Shaurya", "Atharv", "Ananya", "Diya", "Aadhya", "Saanvi", "Anika", "Pari",
    "Myra", "Riya", "Ishita", "Sara", "Kabir", "Dev", "Rohan", "Aman", "Rahul",
    "Priya", "Neha", "Kavya", "Meera", "Tanvi", "Zoya", "Aisha", "Nidhi", "Pooja",
]
LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Yadav", "Patel", "Reddy",
    "Nair", "Iyer", "Joshi", "Malhotra", "Mehta", "Chauhan", "Rathore", "Bose",
    "Khan", "Ahmed", "Ali", "Das", "Banerjee", "Chatterjee", "Pillai", "Menon",
]
GRADES = ["Nursery", "KG", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
SECTIONS = ["A", "B", "C", "D"]
GENDERS = ["Male", "Female"]
STATUSES = ["active", "active", "active", "active", "active", "transferred", "graduated"]
CITIES = ["Delhi", "Mumbai", "Bengaluru", "Chennai", "Kolkata", "Hyderabad", "Pune", "Jaipur"]
STATES = ["Delhi", "Maharashtra", "Karnataka", "Tamil Nadu", "West Bengal", "Telangana", "Maharashtra", "Rajasthan"]

SCHOOLS = [
    ("Sunrise Public School", "SUN001", "Delhi", "Delhi"),
    ("Green Valley Academy", "GVA002", "Mumbai", "Maharashtra"),
    ("St. Xavier's High School", "SXS003", "Bengaluru", "Karnataka"),
    ("Lotus International School", "LIS004", "Chennai", "Tamil Nadu"),
]


def random_date(start_year=2004, end_year=2018):
    import datetime

    year = random.randint(start_year, end_year)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return datetime.date(year, month, day)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=20000)
    parser.add_argument("--out", default="sample_students.csv")
    args = parser.parse_args()

    fields = [
        "student_id", "school_name", "school_code", "first_name", "last_name",
        "date_of_birth", "gender", "grade", "section", "admission_date",
        "email", "phone", "address", "guardian_name", "guardian_phone", "status",
    ]

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for i in range(1, args.rows + 1):
            school_name, school_code, city, state = random.choice(SCHOOLS)
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            dob = random_date()
            grade = random.choice(GRADES)
            writer.writerow(
                {
                    "student_id": f"{school_code}-{i:06d}",
                    "school_name": school_name,
                    "school_code": school_code,
                    "first_name": first,
                    "last_name": last,
                    "date_of_birth": dob.isoformat(),
                    "gender": random.choice(GENDERS),
                    "grade": grade,
                    "section": random.choice(SECTIONS),
                    "admission_date": random_date(2015, 2026).isoformat(),
                    "email": f"{first.lower()}.{last.lower()}{i}@example.com",
                    "phone": f"9{random.randint(100000000, 999999999)}",
                    "address": f"{random.randint(1, 999)}, {random.choice(['MG Road', 'Park Street', 'Lake View', 'Sector 12'])}, {city}",
                    "guardian_name": f"{random.choice(FIRST_NAMES)} {last}",
                    "guardian_phone": f"9{random.randint(100000000, 999999999)}",
                    "status": random.choice(STATUSES),
                }
            )

    print(f"Wrote {args.rows} rows to {args.out}")


if __name__ == "__main__":
    main()
