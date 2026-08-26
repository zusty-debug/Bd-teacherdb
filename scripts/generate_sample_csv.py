"""Generate a realistic EMIS-style sample CSV for local testing.

Usage:
    python -m scripts.generate_sample_csv --rows 20000 --out sample_emis.csv
"""
import argparse
import csv
import random

NAMES = [
    "MD ZAMAL HOSSAIN", "ANUKUL CHANDRO SHIL", "MOSSAMMAT SHAHNAJ PARVIN",
    "SAYMALI RANI", "SHISHIR KUMAR KIRTTANIA", "REHANA AKTER", "MD ABUL KALAM",
    "FATEMA BEGUM", "MD RAFIQUL ISLAM", "NUSRAT JAHAN", "MD KAMAL HOSSAIN",
    "SHARMIN SULTANA", "MD JAHANGIR ALAM", "TANIA AKTER", "MD SHARIF UDDIN",
]
DESIGNATIONS = [
    ("ASSISTANT TEACHER", 56), ("HEAD MASTER", 76), ("ASSISTANT HEAD MASTER", 7),
    ("LECTURER", 3), ("ASSISTANT PROFESSOR", 4), ("4TH CLASS EMPLOYEE", 2),
    ("OFFICE ASSISTANT (MLSS)", 11), ("AYAH", 9), ("CLEANER", 8),
]
SUBJECTS = [
    ("N/A (NOT APPLICABLE)", 1), ("MATHEMATICS", 101), ("ENGLISH", 102),
    ("BANGLA", 103), ("SCIENCE", 104), ("COMPUTER", 105), ("LIBRARY AND INFORMATION SCIENCE", 849),
]
STATUSES = [("কর্মরত", 1), ("সক্রিয়", 2), ("পদত্যাগকৃত", 3)]
GENDERS = [("Male", 1), ("Female", 2)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=20000)
    parser.add_argument("--out", default="sample_emis.csv")
    args = parser.parse_args()

    fields = [
        "empName", "empNameBn", "designationName", "designationId", "subjectName",
        "subjectId", "statusName", "statusId", "eiin", "insMpoCode", "insBranchId",
        "psID", "mpoIndex", "id", "dob", "genderName", "genderId", "mobileNo",
        "emailId", "nid", "fatherName", "motherName", "bankAccNo", "payCode",
        "payCodeId", "payCodeStepId", "basic", "remarks", "verificationStatus",
        "isSubmit", "isUpdated", "designationUpdatable", "subjectUpdatable",
    ]

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i in range(1, args.rows + 1):
            eiin = str(random.randint(100000, 130000))
            des_name, des_id = random.choice(DESIGNATIONS)
            sub_name, sub_id = random.choice(SUBJECTS)
            status, status_id = random.choice(STATUSES)
            gender, gender_id = random.choice(GENDERS)
            name = random.choice(NAMES)
            w.writerow({
                "empName": name,
                "empNameBn": name,
                "designationName": des_name,
                "designationId": des_id,
                "subjectName": sub_name,
                "subjectId": sub_id,
                "statusName": status,
                "statusId": status_id,
                "eiin": eiin,
                "insMpoCode": str(random.randint(1000000000, 9999999999)),
                "insBranchId": random.randint(10000, 20000),
                "psID": random.randint(100000000, 999999999),
                "mpoIndex": f"{random.choice('BNT')}{random.randint(100000, 9999999)}",
                "id": i,
                "dob": f"{random.randint(1,28):02d}-{random.randint(1,12):02d}-{random.randint(1960,1995)}",
                "genderName": gender,
                "genderId": gender_id,
                "mobileNo": f"01{random.randint(100000000, 999999999)}",
                "emailId": "",
                "nid": str(random.randint(1000000000, 9999999999)),
                "fatherName": random.choice(NAMES),
                "motherName": random.choice(NAMES),
                "bankAccNo": str(random.randint(1000, 99999)),
                "payCode": f"Pay Code {random.randint(1,12):02d}",
                "payCodeId": random.randint(1, 12),
                "payCodeStepId": random.randint(1, 12),
                "basic": random.choice([22000, 25480, 35720, 45040, 52000]),
                "remarks": "",
                "verificationStatus": "Validation Completed",
                "isSubmit": 1,
                "isUpdated": random.choice([0, 1]),
                "designationUpdatable": random.choice([0, 1]),
                "subjectUpdatable": random.choice([0, 1]),
            })

    print(f"Wrote {args.rows} rows to {args.out}")


if __name__ == "__main__":
    main()
