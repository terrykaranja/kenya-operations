def test_admin_endpoints_require_authentication(client):
    assert client.get("/api/admin/users").status_code == 401


def test_regular_user_forbidden_from_admin_endpoints(client, regular_user):
    client.post("/api/auth/login", json={"username": "alice", "password": "alicepass123"})
    response = client.get("/api/admin/users")
    assert response.status_code == 403


def test_admin_can_list_users(client, admin_user, regular_user):
    client.post("/api/auth/login", json={"username": "admin", "password": "adminpass123"})
    response = client.get("/api/admin/users")
    assert response.status_code == 200
    usernames = {u["username"] for u in response.json()}
    assert usernames == {"admin", "alice"}


def test_admin_can_create_user(client, admin_user):
    client.post("/api/auth/login", json={"username": "admin", "password": "adminpass123"})
    response = client.post(
        "/api/admin/users",
        json={"username": "bob", "password": "bobpassword1", "is_admin": False},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "bob"
    assert body["is_admin"] is False

    # The new user should be able to log in immediately.
    login_response = client.post(
        "/api/auth/login", json={"username": "bob", "password": "bobpassword1"}
    )
    assert login_response.status_code == 200


def test_admin_cannot_create_duplicate_username(client, admin_user, regular_user):
    client.post("/api/auth/login", json={"username": "admin", "password": "adminpass123"})
    response = client.post(
        "/api/admin/users", json={"username": "alice", "password": "whatever123"}
    )
    assert response.status_code == 409


def test_admin_can_deactivate_user(client, admin_user, regular_user):
    client.post("/api/auth/login", json={"username": "admin", "password": "adminpass123"})
    response = client.put(f"/api/admin/users/{regular_user.id}", json={"is_active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_admin_cannot_delete_self(client, admin_user):
    client.post("/api/auth/login", json={"username": "admin", "password": "adminpass123"})
    response = client.delete(f"/api/admin/users/{admin_user.id}")
    assert response.status_code == 400


def test_admin_can_delete_other_user(client, admin_user, regular_user):
    client.post("/api/auth/login", json={"username": "admin", "password": "adminpass123"})
    response = client.delete(f"/api/admin/users/{regular_user.id}")
    assert response.status_code == 204

    remaining = client.get("/api/admin/users").json()
    assert [u["username"] for u in remaining] == ["admin"]


def test_admin_can_manage_units_and_countries(client, admin_user):
    client.post("/api/auth/login", json={"username": "admin", "password": "adminpass123"})

    unit_response = client.post("/api/admin/units", json={"code": "KG", "description": "Kilograms"})
    assert unit_response.status_code == 201
    assert unit_response.json()["code"] == "KG"

    duplicate_unit = client.post("/api/admin/units", json={"code": "KG", "description": "dupe"})
    assert duplicate_unit.status_code == 409

    country_response = client.post("/api/admin/countries", json={"code": "KE", "name": "Kenya"})
    assert country_response.status_code == 201
    assert country_response.json()["code"] == "KE"

    assert client.get("/api/admin/units").json()[0]["code"] == "KG"
    assert client.get("/api/admin/countries").json()[0]["code"] == "KE"
