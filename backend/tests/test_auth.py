def test_login_success_sets_session_cookie(client, regular_user):
    response = client.post(
        "/api/auth/login", json={"username": "alice", "password": "alicepass123"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "alice"
    assert "sez_session" in response.cookies


def test_login_wrong_password_rejected(client, regular_user):
    response = client.post(
        "/api/auth/login", json={"username": "alice", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_login_unknown_user_rejected(client):
    response = client.post(
        "/api/auth/login", json={"username": "ghost", "password": "whatever"}
    )
    assert response.status_code == 401


def test_login_inactive_user_rejected(client, db_session, regular_user):
    regular_user.is_active = False
    db_session.commit()

    response = client.post(
        "/api/auth/login", json={"username": "alice", "password": "alicepass123"}
    )
    assert response.status_code == 401


def test_me_requires_authentication(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client, regular_user):
    client.post("/api/auth/login", json={"username": "alice", "password": "alicepass123"})
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["username"] == "alice"


def test_logout_clears_session(client, regular_user):
    client.post("/api/auth/login", json={"username": "alice", "password": "alicepass123"})
    assert client.get("/api/auth/me").status_code == 200

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 200

    assert client.get("/api/auth/me").status_code == 401
