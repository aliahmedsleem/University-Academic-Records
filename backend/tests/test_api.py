from io import BytesIO
import openpyxl
import pytest
from app import create_app


@pytest.fixture
def client():
    return create_app().test_client()


def test_health(client):
    assert client.get("/api/health").json["status"] == "ok"


def test_preview_xlsx(client):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Student ID", "Name", "Mark"])
    ws.append(["S001", "Test Student", 85])
    data = BytesIO()
    wb.save(data)
    data.seek(0)
    response = client.post("/api/excel/preview", data={"file": (data, "grades.xlsx")})
    assert response.status_code == 200
    assert response.json["status"] == "preview_only_unverified"
    assert response.json["sheets"][0]["preview"][1][2] == 85


def test_reject_fake_xlsx(client):
    response = client.post("/api/excel/preview", data={"file": (BytesIO(b"not an excel file"), "fake.xlsx")})
    assert response.status_code == 422


def test_reject_unsupported_format(client):
    response = client.post("/api/excel/preview", data={"file": (BytesIO(b"hello"), "grades.csv")})
    assert response.status_code == 422
