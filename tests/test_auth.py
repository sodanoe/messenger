"""
Тесты: аутентификация, инвайты, регистрация.
"""

import uuid


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_admin_login(client, admin_token):
    """Успешный логин — токен получен."""
    assert admin_token  # фикстура сама проверяет статус 200


def test_login_bad_password(client):
    resp = client.post(
        "/auth/login", json={"username": "admin", "password": "totally_wrong"}
    )
    assert resp.status_code == 401


def test_register_and_me(client, make_user):
    user = make_user()

    me = client.get("/users/me", headers=auth(user["token"]))
    assert me.status_code == 200

    data = me.json()
    assert data["id"] == user["id"]
    assert data["username"] == user["username"]
    assert "password_hash" not in data, "password_hash не должен утекать в API!"
    assert "password" not in data


def test_register_duplicate_username(client, make_user, admin_token):
    user = make_user()

    # Новый инвайт, то же имя
    inv = client.post("/auth/invite", headers=auth(admin_token))
    code = inv.json()["code"]
    resp = client.post(
        "/auth/register",
        json={
            "username": user["username"],
            "password": "pass123!",
            "invite_code": code,
        },
    )
    assert resp.status_code == 409


def test_register_invalid_invite(client):
    resp = client.post(
        "/auth/register",
        json={"username": "nobody", "password": "pass123!", "invite_code": "BADCODE1"},
    )
    assert resp.status_code == 400


def test_invite_single_use(client, admin_token):
    """Один инвайт-код нельзя использовать дважды."""
    inv = client.post("/auth/invite", headers=auth(admin_token))
    code = inv.json()["code"]

    name1 = f"u1_{uuid.uuid4().hex[:6]}"
    reg1 = client.post(
        "/auth/register",
        json={"username": name1, "password": "Testpass123!", "invite_code": code},
    )
    assert reg1.status_code == 200
    token1 = reg1.json()["access_token"]

    name2 = f"u2_{uuid.uuid4().hex[:6]}"
    reg2 = client.post(
        "/auth/register",
        json={"username": name2, "password": "Testpass123!", "invite_code": code},
    )
    assert reg2.status_code == 400, "Повторный инвайт должен вернуть 400"

    # Cleanup
    client.delete("/users/me", headers=auth(token1))
