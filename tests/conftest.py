import os
import uuid

import httpx
import pytest

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10) as c:
        yield c


@pytest.fixture(scope="session")
def admin_token(client):
    resp = client.post(
        "/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture
def make_user(client, admin_token):
    """
    Фабричная фикстура — создаёт пользователей и чистит их после теста.

    Использование:
        def test_something(make_user):
            alice = make_user()           # username генерируется автоматически
            bob   = make_user("bob_xyz")  # или явно

        alice / bob — dict с ключами: id, username, password, token

    Teardown: DELETE /users/me для каждого созданного юзера.
    CASCADE в БД подчищает contacts, chat_members, messages, reactions.
    """
    created: list[dict] = []

    def _factory(username: str | None = None, password: str = "Testpass123!") -> dict:
        if username is None:
            username = f"t_{uuid.uuid4().hex[:8]}"

        inv = client.post("/auth/invite", headers=auth(admin_token))
        assert inv.status_code == 200, f"Invite failed: {inv.text}"
        code = inv.json()["code"]

        reg = client.post(
            "/auth/register",
            json={"username": username, "password": password, "invite_code": code},
        )
        assert reg.status_code == 200, f"Register '{username}' failed: {reg.text}"

        token = reg.json()["access_token"]
        me = client.get("/users/me", headers=auth(token))
        assert me.status_code == 200

        user = {
            "id": me.json()["id"],
            "username": username,
            "password": password,
            "token": token,
        }
        created.append(user)
        return user

    yield _factory

    # Teardown — выполняется даже если тест упал
    for user in created:
        try:
            client.delete("/users/me", headers=auth(user["token"]))
        except Exception:
            pass
