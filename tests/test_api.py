import io

from app.database import SessionLocal
from app.importer import import_csv

SAMPLE_CSV = """student_id,school_name,school_code,first_name,last_name,date_of_birth,gender,grade,section,admission_date,email,phone,status
SUN001-000001,Sunrise Public School,SUN001,Aarav,Sharma,2010-05-12,Male,10,A,2021-04-01,aarav.sharma1@example.com,9123456789,active
SUN001-000002,Sunrise Public School,SUN001,Ananya,Verma,2011-03-20,Female,9,B,2021-04-01,ananya.verma2@example.com,9123456780,active
GVA002-000003,Green Valley Academy,GVA002,Rohan,Gupta,2009-11-02,Male,11,A,2020-06-15,rohan.gupta3@example.com,9123456781,active
GVA002-000004,Green Valley Academy,GVA002,Priya,Reddy,2012-07-25,Female,8,C,2021-04-01,priya.reddy4@example.com,9123456782,transferred
"""


def seed():
    db = SessionLocal()
    try:
        import_csv(db, SAMPLE_CSV.encode("utf-8"))
    finally:
        db.close()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_data_requires_api_key(client):
    seed()
    assert client.get("/api/v1/students").status_code == 401
    assert client.get("/api/v1/schools").status_code == 401
    assert client.get("/api/v1/stats").status_code == 401


def test_admin_requires_master_key(client):
    assert client.post("/api/v1/admin/keys", json={"name": "x"}).status_code == 403
    assert client.post(
        "/api/v1/admin/keys", json={"name": "x"}, headers={"X-Master-Key": "wrong"}
    ).status_code == 403


def test_full_key_lifecycle(client, master_headers):
    seed()

    # Create key -> full key returned once
    resp = client.post("/api/v1/admin/keys", json={"name": "frontend"}, headers=master_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["key"].startswith("sk_")
    assert body["active"] is True

    key = body["key"]
    h = {"X-API-Key": key}

    # Key works
    assert client.get("/api/v1/students", headers=h).status_code == 200
    assert client.get("/api/v1/schools", headers=h).status_code == 200
    assert client.get("/api/v1/stats", headers=h).status_code == 200

    # List keys (master)
    keys = client.get("/api/v1/admin/keys", headers=master_headers).json()
    assert len(keys) == 1
    assert keys[0]["key_prefix"] == key[:14]

    # Revoke -> key stops working
    kid = body["id"]
    assert client.delete(f"/api/v1/admin/keys/{kid}", headers=master_headers).status_code == 204
    assert client.get("/api/v1/students", headers=h).status_code == 401

    # Toggle back on
    toggled = client.post(f"/api/v1/admin/keys/{kid}/toggle", headers=master_headers).json()
    assert toggled["active"] is True
    assert client.get("/api/v1/students", headers=h).status_code == 200


def test_query_filters_and_pagination(client, api_key):
    seed()

    # All rows
    resp = client.get("/api/v1/students", headers=api_key)
    assert resp.json()["total"] == 4

    # Filter by school
    resp = client.get("/api/v1/students", params={"school_code": "SUN001"}, headers=api_key)
    assert resp.json()["total"] == 2

    # Filter by grade + status
    resp = client.get("/api/v1/students", params={"grade": "10"}, headers=api_key)
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["first_name"] == "Aarav"

    # Search by last name
    resp = client.get("/api/v1/students", params={"search": "Reddy"}, headers=api_key)
    assert resp.json()["total"] == 1

    # Pagination
    resp = client.get("/api/v1/students", params={"per_page": 2, "page": 2}, headers=api_key)
    body = resp.json()
    assert body["total"] == 4
    assert body["pages"] == 2
    assert len(body["items"]) == 2

    # Sorting
    resp = client.get(
        "/api/v1/students", params={"sort": "first_name", "order": "asc"}, headers=api_key
    )
    names = [i["first_name"] for i in resp.json()["items"]]
    assert names == sorted(names)


def test_single_student(client, api_key):
    seed()
    resp = client.get("/api/v1/students/1", headers=api_key)
    assert resp.status_code == 200
    body = resp.json()
    assert body["school_name"] == "Sunrise Public School"
    assert body["first_name"] == "Aarav"

    assert client.get("/api/v1/students/99999", headers=api_key).status_code == 404


def test_stats_and_schools(client, api_key):
    seed()
    stats = client.get("/api/v1/stats", headers=api_key).json()
    assert stats["total_students"] == 4
    assert stats["total_schools"] == 2
    assert {g["grade"] for g in stats["by_grade"]} == {"8", "9", "10", "11"}

    schools = client.get("/api/v1/schools", headers=api_key).json()
    assert len(schools) == 2
    counts = {s["code"]: s["student_count"] for s in schools}
    assert counts == {"SUN001": 2, "GVA002": 2}


def test_unknown_columns_go_to_extra(client, api_key):
    csv = (
        "student_id,first_name,custom_field_xyz,age\n"
        "ID-1,Test,hello,15\n"
    )
    db = SessionLocal()
    try:
        summary = import_csv(db, csv.encode("utf-8"), default_school_name="Default School")
    finally:
        db.close()
    assert "custom_field_xyz" in summary["unknown_columns"]
    assert "age" in summary["unknown_columns"]

    resp = client.get("/api/v1/students/1", headers=api_key)
    body = resp.json()
    assert body["extra"]["custom_field_xyz"] == "hello"
    assert body["school_name"] == "Default School"
