def test_patient_registration_and_login(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "patient@example.com", "password": "secret123", "full_name": "Patient One"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    assert token

    login = client.post("/api/auth/login", json={"email": "patient@example.com", "password": "secret123"})
    assert login.status_code == 200, login.text
    assert login.json()["role"] == "patient"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "patient@example.com"


def test_patient_cannot_access_admin_route(client):
    client.post(
        "/api/auth/register",
        json={"email": "patient2@example.com", "password": "secret123", "full_name": "Patient Two"},
    )
    login = client.post("/api/auth/login", json={"email": "patient2@example.com", "password": "secret123"})
    token = login.json()["access_token"]

    response = client.post("/api/admin/doctors", json={"email": "admin_doctor@example.com", "password": "secret123", "full_name": "Doctor User", "specialization": "General"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
