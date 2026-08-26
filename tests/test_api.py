from app.database import SessionLocal
from app.importer import import_csv

SAMPLE_CSV = """empName,empNameBn,designationName,designationId,subjectName,subjectId,statusName,statusId,eiin,insMpoCode,insBranchId,psID,mpoIndex,id,dob,genderName,genderId,mobileNo,emailId,nid,fatherName,motherName,bankAccNo,payCode,payCodeId,payCodeStepId,basic,remarks,verificationStatus,isSubmit,isUpdated,designationUpdatable,subjectUpdatable
MD ZAMAL HOSSAIN,MD ZAMAL HOSSAIN,HEAD MASTER,76,N/A (NOT APPLICABLE),1,কর্মরত,1,100005,6501101301,15988,100105234,B214451,187041,12-09-1969,Male,1,01733135617,,,,,2456,Pay Code 07,7,105,45040,Validation Completed,Verification Completed,1,1,0,1
ANUKUL CHANDRO SHIL,অনুকুল চন্দ্র শীল,ASSISTANT HEAD MASTER,7,N/A (NOT APPLICABLE),1,কর্মরত,1,100005,6501101301,15988,100105276,B288286,184123,25-06-1972,Female,2,01729785809,,,,,2459,Pay Code 08,8,105,35720,Validation Completed,Verification Completed,1,1,0,1
SAYMALI RANI,SAYMALI RANI,HINDU RELIGION TEACHER,4,N/A (NOT APPLICABLE),1,কর্মরত,1,100005,6501101301,15988,100462434,N1070722,396048,04-02-1986,Female,2,01745581350,,,,,2853,Pay Code 09,9,3,25480,Validation Completed,Verification Completed,1,1,0,1
REHANA AKTER,রেহানা আক্তার,ASSISTANT TEACHER,56,LIBRARY AND INFORMATION SCIENCE,849,কর্মরত,1,200001,6502202202,16000,100500000,M55555,415072,01-01-1983,Female,2,01718239641,,0410979364746,MD. MENHAZ UDDIN,SAKINA BEGUM,2852,Pay Code 09,9,4,22000,Validation Completed,Verification Completed,1,1,0,1
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
    assert client.get("/api/v1/employees").status_code == 401
    assert client.get("/api/v1/institutions").status_code == 401
    assert client.get("/api/v1/stats").status_code == 401


def test_admin_requires_master_key(client):
    assert client.post("/api/v1/admin/keys", json={"name": "x"}).status_code == 403
    assert client.post(
        "/api/v1/admin/keys", json={"name": "x"}, headers={"X-Master-Key": "wrong"}
    ).status_code == 403


def test_full_key_lifecycle(client, master_headers):
    seed()

    resp = client.post("/api/v1/admin/keys", json={"name": "frontend"}, headers=master_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["key"].startswith("sk_")
    assert body["active"] is True

    key = body["key"]
    h = {"X-API-Key": key}

    assert client.get("/api/v1/employees", headers=h).status_code == 200
    assert client.get("/api/v1/institutions", headers=h).status_code == 200
    assert client.get("/api/v1/stats", headers=h).status_code == 200

    keys = client.get("/api/v1/admin/keys", headers=master_headers).json()
    assert len(keys) == 1
    assert keys[0]["key_prefix"] == key[:14]

    kid = body["id"]
    assert client.delete(f"/api/v1/admin/keys/{kid}", headers=master_headers).status_code == 204
    assert client.get("/api/v1/employees", headers=h).status_code == 401

    toggled = client.post(f"/api/v1/admin/keys/{kid}/toggle", headers=master_headers).json()
    assert toggled["active"] is True
    assert client.get("/api/v1/employees", headers=h).status_code == 200


def test_import_mapping(client, api_key):
    seed()
    resp = client.get("/api/v1/employees/1", headers=api_key)
    body = resp.json()
    assert body["name"] == "MD ZAMAL HOSSAIN"
    assert body["designation_name"] == "HEAD MASTER"
    assert body["eiin"] == "100005"
    assert body["date_of_birth"] == "1969-09-12"  # DD-MM-YYYY parsed correctly
    assert body["basic"] == 45040
    assert body["is_submit"] is True
    assert body["designation_updatable"] is False
    assert body["gender"] == "Male"


def test_query_filters_and_pagination(client, api_key):
    seed()

    resp = client.get("/api/v1/employees", headers=api_key)
    assert resp.json()["total"] == 4

    # Filter by institution EIIN
    resp = client.get("/api/v1/employees", params={"eiin": "100005"}, headers=api_key)
    assert resp.json()["total"] == 3

    # Filter by designation
    resp = client.get("/api/v1/employees", params={"designation_name": "HEAD MASTER"}, headers=api_key)
    assert resp.json()["total"] == 1

    # Filter by gender
    resp = client.get("/api/v1/employees", params={"gender": "Female"}, headers=api_key)
    assert resp.json()["total"] == 3

    # Search by name
    resp = client.get("/api/v1/employees", params={"search": "rehana"}, headers=api_key)
    assert resp.json()["total"] == 1

    # Search by Bengali name
    resp = client.get("/api/v1/employees", params={"search": "রেহানা"}, headers=api_key)
    assert resp.json()["total"] == 1

    # Search by NID
    resp = client.get("/api/v1/employees", params={"search": "0410979364746"}, headers=api_key)
    assert resp.json()["total"] == 1

    # Pagination
    resp = client.get("/api/v1/employees", params={"per_page": 2, "page": 2}, headers=api_key)
    body = resp.json()
    assert body["total"] == 4
    assert body["pages"] == 2
    assert len(body["items"]) == 2

    # Sort by name
    resp = client.get("/api/v1/employees", params={"sort": "name", "order": "asc"}, headers=api_key)
    names = [i["name"] for i in resp.json()["items"]]
    assert names == sorted(names)


def test_single_employee(client, api_key):
    seed()
    resp = client.get("/api/v1/employees/2", headers=api_key)
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "ANUKUL CHANDRO SHIL"
    assert body["name_bn"] == "অনুকুল চন্দ্র শীল"

    assert client.get("/api/v1/employees/99999", headers=api_key).status_code == 404


def test_institution_fields_preserved(client, api_key):
    """Regression: institution attrs (mpo code, branch id, ps id) must be set."""
    seed()
    institutions = client.get("/api/v1/institutions", headers=api_key).json()
    by_eiin = {i["eiin"]: i for i in institutions}
    inst = by_eiin["100005"]
    assert inst["ins_mpo_code"] == "6501101301"
    assert inst["ins_branch_id"] == 15988
    assert inst["ps_id"] == 100105234


def test_institution_detail_and_employees(client, api_key):
    seed()
    # Detail by EIIN
    resp = client.get("/api/v1/institutions/100005", headers=api_key)
    assert resp.status_code == 200
    body = resp.json()
    assert body["employee_count"] == 3
    assert body["ins_mpo_code"] == "6501101301"

    # Employees of an institution
    resp = client.get("/api/v1/institutions/100005/employees", headers=api_key)
    assert resp.json()["total"] == 3

    # With a filter
    resp = client.get(
        "/api/v1/institutions/100005/employees",
        params={"designation_name": "HEAD MASTER"},
        headers=api_key,
    )
    assert resp.json()["total"] == 1

    # 404 for unknown institution
    assert client.get("/api/v1/institutions/999999", headers=api_key).status_code == 404
    assert client.get("/api/v1/institutions/999999/employees", headers=api_key).status_code == 404


def test_filters_endpoint(client, api_key):
    seed()
    resp = client.get("/api/v1/filters", headers=api_key)
    assert resp.status_code == 200
    body = resp.json()
    assert "HEAD MASTER" in body["designations"]
    assert "Male" in body["genders"]
    assert "Female" in body["genders"]
    # Bengali status present
    assert "কর্মরত" in body["statuses"]


def test_stats_and_institutions(client, api_key):
    seed()
    stats = client.get("/api/v1/stats", headers=api_key).json()
    assert stats["total_employees"] == 4
    assert stats["total_institutions"] == 2
    assert len(stats["by_gender"]) == 2
    assert stats["by_gender"][0]["gender"] == "Female"

    institutions = client.get("/api/v1/institutions", headers=api_key).json()
    assert len(institutions) == 2
    counts = {i["eiin"]: i["employee_count"] for i in institutions}
    assert counts == {"100005": 3, "200001": 1}

    # Institution search by EIIN
    found = client.get("/api/v1/institutions", params={"search": "200001"}, headers=api_key).json()
    assert len(found) == 1
    assert found[0]["eiin"] == "200001"
