"""
Smoke-тест Step 2: Contacts + Direct Messages
Запуск: pytest tests/test_smoke_step2.py -v
Требует: запущенный uvicorn app.main:app на localhost:8000
"""

import uuid
import pytest
import httpx

BASE = "http://localhost:8000"

# Уникальный суффикс на каждый запуск — нет конфликтов с прошлыми прогонами
RUN = uuid.uuid4().hex[:6]
state = {}


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE, timeout=10) as c:
        yield c


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ════════════════════════════════════════════════════════════
#  1. Получить invite-коды под admin
# ════════════════════════════════════════════════════════════

def test_1_admin_login_and_get_invite(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "adminpass"})
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    state["admin_token"] = resp.json()["access_token"]

    for key in ("invite_a", "invite_b"):
        resp = client.post("/auth/invite", headers=auth_headers(state["admin_token"]))
        assert resp.status_code == 200, f"Invite generation failed: {resp.text}"
        state[key] = resp.json()["code"]

    print(f"\n  RUN={RUN}  invite_a={state['invite_a']}  invite_b={state['invite_b']}")


# ════════════════════════════════════════════════════════════
#  2. Регистрация двух пользователей
# ════════════════════════════════════════════════════════════

def test_2_register_two_users(client):
    resp_a = client.post("/auth/register", json={
        "username": f"alice_{RUN}",
        "password": "password123",
        "invite_code": state["invite_a"],
    })
    assert resp_a.status_code == 200, f"Register alice failed: {resp_a.text}"
    state["token_a"] = resp_a.json()["access_token"]

    resp_b = client.post("/auth/register", json={
        "username": f"bob_{RUN}",
        "password": "password123",
        "invite_code": state["invite_b"],
    })
    assert resp_b.status_code == 200, f"Register bob failed: {resp_b.text}"
    state["token_b"] = resp_b.json()["access_token"]

    me_a = client.get("/users/me", headers=auth_headers(state["token_a"]))
    me_b = client.get("/users/me", headers=auth_headers(state["token_b"]))
    assert me_a.status_code == 200
    assert me_b.status_code == 200
    state["user_id_a"] = me_a.json()["id"]
    state["user_id_b"] = me_b.json()["id"]
    print(f"\n  alice id={state['user_id_a']}  bob id={state['user_id_b']}")


# ════════════════════════════════════════════════════════════
#  3. Добавить друг друга в контакты
# ════════════════════════════════════════════════════════════

def test_3_add_contacts(client):
    resp = client.post(
        "/contacts",
        json={"username": f"bob_{RUN}"},
        headers=auth_headers(state["token_a"]),
    )
    assert resp.status_code == 201, f"Add contact failed: {resp.text}"
    assert resp.json()["contact_user_id"] == state["user_id_b"]

    # Повторное добавление → 409
    resp2 = client.post(
        "/contacts",
        json={"username": f"bob_{RUN}"},
        headers=auth_headers(state["token_a"]),
    )
    assert resp2.status_code == 409, "Expected 409 on duplicate contact"

    # Bob проверяет что Alice у него появилась (reverse row)
    contacts_b = client.get("/contacts", headers=auth_headers(state["token_b"]))
    assert contacts_b.status_code == 200
    ids = [c["contact_user_id"] for c in contacts_b.json()]
    assert state["user_id_a"] in ids, "Reverse contact row missing"


# ════════════════════════════════════════════════════════════
#  4. Alice отправляет сообщение Bob'у
# ════════════════════════════════════════════════════════════

def test_4_send_message(client):
    resp = client.post(
        f"/messages/{state['user_id_b']}",
        json={"content": "Привет, Bob! 👋"},
        headers=auth_headers(state["token_a"]),
    )
    assert resp.status_code == 201, f"Send message failed: {resp.text}"
    data = resp.json()
    assert data["content"] == "Привет, Bob! 👋"
    assert data["sender_id"] == state["user_id_a"]
    state["msg_id"] = data["id"]

    # Чужой юзер не может писать (нет контакта)
    resp2 = client.post(
        f"/messages/{state['user_id_a']}",
        json={"content": "hax"},
        headers=auth_headers(state["admin_token"]),
    )
    assert resp2.status_code == 403, "Expected 403 when not in contacts"


# ════════════════════════════════════════════════════════════
#  5. GET история сообщений
# ════════════════════════════════════════════════════════════

def test_5_get_history(client):
    resp = client.get(
        f"/messages/{state['user_id_b']}",
        headers=auth_headers(state["token_a"]),
    )
    assert resp.status_code == 200, f"Get history failed: {resp.text}"
    data = resp.json()
    assert "messages" in data
    assert len(data["messages"]) >= 1
    assert data["messages"][0]["content"] == "Привет, Bob! 👋"
    assert "next_cursor" in data

    resp_b = client.get(
        f"/messages/{state['user_id_a']}",
        headers=auth_headers(state["token_b"]),
    )
    assert resp_b.status_code == 200
    assert len(resp_b.json()["messages"]) >= 1


# ════════════════════════════════════════════════════════════
#  6. GET /contacts — у Bob has_unread=true
# ════════════════════════════════════════════════════════════

def test_6_contacts_has_unread_true(client):
    resp = client.get("/contacts", headers=auth_headers(state["token_b"]))
    assert resp.status_code == 200
    contacts = resp.json()
    alice_contact = next((c for c in contacts if c["contact_user_id"] == state["user_id_a"]), None)
    assert alice_contact is not None, "Alice not found in Bob's contacts"
    assert alice_contact["has_unread"] is True, f"Expected has_unread=True, got {alice_contact}"


# ════════════════════════════════════════════════════════════
#  7. Bob отмечает сообщения как прочитанными
# ════════════════════════════════════════════════════════════

def test_7_mark_read(client):
    resp = client.post(
        f"/messages/{state['user_id_a']}/read",
        headers=auth_headers(state["token_b"]),
    )
    assert resp.status_code == 204, f"Mark read failed: {resp.text}"


# ════════════════════════════════════════════════════════════
#  8. GET /contacts — у Bob has_unread=false
# ════════════════════════════════════════════════════════════

def test_8_contacts_has_unread_false(client):
    resp = client.get("/contacts", headers=auth_headers(state["token_b"]))
    assert resp.status_code == 200
    contacts = resp.json()
    alice_contact = next((c for c in contacts if c["contact_user_id"] == state["user_id_a"]), None)
    assert alice_contact is not None
    assert alice_contact["has_unread"] is False, f"Expected has_unread=False, got {alice_contact}"


# ════════════════════════════════════════════════════════════
#  Бонус: поиск пользователей
# ════════════════════════════════════════════════════════════

def test_bonus_user_search(client):
    resp = client.get(
        f"/users/search?q=bob_{RUN}",
        headers=auth_headers(state["token_a"]),
    )
    assert resp.status_code == 200
    results = resp.json()
    assert any(u["username"] == f"bob_{RUN}" for u in results)

    # Поиск без токена → 401/403
    resp2 = client.get(f"/users/search?q=bob_{RUN}")
    assert resp2.status_code in (401, 403)


# ════════════════════════════════════════════════════════════
#  Бонус: блокировка
# ════════════════════════════════════════════════════════════

def test_bonus_block(client):
    resp = client.post(
        f"/contacts/{state['user_id_b']}/block",
        headers=auth_headers(state["token_a"]),
    )
    assert resp.status_code == 204, f"Block failed: {resp.text}"

    # Bob пытается написать Alice — должен получить 403
    resp2 = client.post(
        f"/messages/{state['user_id_a']}",
        json={"content": "можно?"},
        headers=auth_headers(state["token_b"]),
    )
    assert resp2.status_code == 403, f"Expected 403 after block, got {resp2.status_code}"