"""
Smoke-тест Step 3: Group Chats
Запуск: pytest tests/test_smoke_step3.py -v
Требует: запущенный uvicorn app.main:app на localhost:8000
         и уже зарегистрированного admin
"""

import uuid
import pytest
import httpx

BASE = "http://localhost:8000"

# Уникальный суффикс на каждый запуск
RUN = uuid.uuid4().hex[:6]
state = {}


@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE, timeout=10) as c:
        yield c


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ════════════════════════════════════════════════════════════
#  Подготовка: логин admin + регистрация двух юзеров
# ════════════════════════════════════════════════════════════


def test_0_setup(client):
    resp = client.post(
        "/auth/login", json={"username": "admin", "password": "adminpass"}
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    state["admin_token"] = resp.json()["access_token"]

    for key in ("invite_a", "invite_b"):
        resp = client.post("/auth/invite", headers=auth_headers(state["admin_token"]))
        assert resp.status_code == 200
        state[key] = resp.json()["code"]

    for name, invite_key, token_key, uid_key in [
        (f"alice_g_{RUN}", "invite_a", "token_a", "uid_a"),
        (f"bob_g_{RUN}", "invite_b", "token_b", "uid_b"),
    ]:
        resp = client.post(
            "/auth/register",
            json={
                "username": name,
                "password": "password123",
                "invite_code": state[invite_key],
            },
        )
        assert resp.status_code == 200, f"Register {name} failed: {resp.text}"
        state[token_key] = resp.json()["access_token"]
        me = client.get("/users/me", headers=auth_headers(state[token_key]))
        state[uid_key] = me.json()["id"]

    print(f"\n  RUN={RUN}  uid_a={state['uid_a']}  uid_b={state['uid_b']}")


# ════════════════════════════════════════════════════════════
#  1. Alice создаёт группу
# ════════════════════════════════════════════════════════════


def test_1_create_group(client):
    resp = client.post(
        "/groups",
        json={"name": f"Test Group {RUN}"},
        headers=auth_headers(state["token_a"]),
    )
    assert resp.status_code == 201, f"Create group failed: {resp.text}"
    data = resp.json()
    assert data["name"] == f"Test Group {RUN}"
    assert data["created_by"] == state["uid_a"]
    state["group_id"] = data["id"]


# ════════════════════════════════════════════════════════════
#  2. GET /groups — Alice видит свою группу
# ════════════════════════════════════════════════════════════


def test_2_list_groups(client):
    resp = client.get("/groups", headers=auth_headers(state["token_a"]))
    assert resp.status_code == 200
    assert any(g["id"] == state["group_id"] for g in resp.json())

    # Bob не видит группу — он ещё не участник
    resp_b = client.get("/groups", headers=auth_headers(state["token_b"]))
    assert resp_b.status_code == 200
    assert not any(g["id"] == state["group_id"] for g in resp_b.json())


# ════════════════════════════════════════════════════════════
#  3. Bob не может зайти в группу (не участник)
# ════════════════════════════════════════════════════════════


def test_3_non_member_gets_403(client):
    resp = client.get(
        f"/groups/{state['group_id']}/messages",
        headers=auth_headers(state["token_b"]),
    )
    assert resp.status_code == 403, (
        f"Expected 403 for non-member, got {resp.status_code}"
    )

    resp2 = client.get(
        f"/groups/{state['group_id']}/members",
        headers=auth_headers(state["token_b"]),
    )
    assert resp2.status_code == 403


# ════════════════════════════════════════════════════════════
#  4. Alice (admin) приглашает Bob
# ════════════════════════════════════════════════════════════


def test_4_invite_member(client):
    resp = client.post(
        f"/groups/{state['group_id']}/invite",
        json={"username": f"bob_g_{RUN}"},
        headers=auth_headers(state["token_a"]),
    )
    assert resp.status_code == 201, f"Invite failed: {resp.text}"
    data = resp.json()
    assert data["user_id"] == state["uid_b"]
    assert data["role"] == "member"

    # Повторное приглашение → 409
    resp2 = client.post(
        f"/groups/{state['group_id']}/invite",
        json={"username": f"bob_g_{RUN}"},
        headers=auth_headers(state["token_a"]),
    )
    assert resp2.status_code == 409


# ════════════════════════════════════════════════════════════
#  5. GET /groups/:id/members — оба видны
# ════════════════════════════════════════════════════════════


def test_5_list_members(client):
    resp = client.get(
        f"/groups/{state['group_id']}/members",
        headers=auth_headers(state["token_a"]),
    )
    assert resp.status_code == 200
    members = resp.json()
    user_ids = [m["user_id"] for m in members]
    assert state["uid_a"] in user_ids
    assert state["uid_b"] in user_ids

    alice_member = next(m for m in members if m["user_id"] == state["uid_a"])
    bob_member = next(m for m in members if m["user_id"] == state["uid_b"])
    assert alice_member["role"] == "admin"
    assert bob_member["role"] == "member"


# ════════════════════════════════════════════════════════════
#  6. Bob (member) не может приглашать — 403
# ════════════════════════════════════════════════════════════


def test_6_member_cannot_invite(client):
    invite = client.post("/auth/invite", headers=auth_headers(state["admin_token"]))
    code = invite.json()["code"]
    client.post(
        "/auth/register",
        json={
            "username": f"charlie_g_{RUN}",
            "password": "password123",
            "invite_code": code,
        },
    )

    resp = client.post(
        f"/groups/{state['group_id']}/invite",
        json={"username": f"charlie_g_{RUN}"},
        headers=auth_headers(state["token_b"]),  # Bob — member, не admin
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


# ════════════════════════════════════════════════════════════
#  7. Alice отправляет сообщение в группу
# ════════════════════════════════════════════════════════════


def test_7_send_group_message(client):
    resp = client.post(
        f"/groups/{state['group_id']}/messages",
        json={"content": "Привет всем в группе! 🎉"},
        headers=auth_headers(state["token_a"]),
    )
    assert resp.status_code == 201, f"Send group message failed: {resp.text}"
    data = resp.json()
    assert data["content"] == "Привет всем в группе! 🎉"
    assert data["sender_id"] == state["uid_a"]
    assert data["group_id"] == state["group_id"]
    state["msg_id"] = data["id"]


# ════════════════════════════════════════════════════════════
#  8. Bob читает историю группы
# ════════════════════════════════════════════════════════════


def test_8_get_group_messages(client):
    resp = client.get(
        f"/groups/{state['group_id']}/messages",
        headers=auth_headers(state["token_b"]),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "messages" in data
    assert "next_cursor" in data
    assert len(data["messages"]) >= 1
    assert data["messages"][0]["content"] == "Привет всем в группе! 🎉"


# ════════════════════════════════════════════════════════════
#  9. Cursor pagination
# ════════════════════════════════════════════════════════════


def test_9_cursor_pagination(client):
    for i in range(2):
        client.post(
            f"/groups/{state['group_id']}/messages",
            json={"content": f"Сообщение {i + 2}"},
            headers=auth_headers(state["token_b"]),
        )

    resp = client.get(
        f"/groups/{state['group_id']}/messages",
        headers=auth_headers(state["token_a"]),
    )
    msgs = resp.json()["messages"]
    assert len(msgs) >= 3

    last_id = msgs[-1]["id"]
    resp2 = client.get(
        f"/groups/{state['group_id']}/messages?cursor={last_id}",
        headers=auth_headers(state["token_a"]),
    )
    assert resp2.status_code == 200
    for m in resp2.json()["messages"]:
        assert m["id"] < last_id


# ════════════════════════════════════════════════════════════
#  10. Bob (member) выходит из группы сам
# ════════════════════════════════════════════════════════════


def test_10_self_leave(client):
    resp = client.delete(
        f"/groups/{state['group_id']}/members/{state['uid_b']}",
        headers=auth_headers(state["token_b"]),
    )
    assert resp.status_code == 204, f"Self-leave failed: {resp.text}"

    resp2 = client.get("/groups", headers=auth_headers(state["token_b"]))
    assert not any(g["id"] == state["group_id"] for g in resp2.json())


# ════════════════════════════════════════════════════════════
#  11. Alice (admin) удаляет группу
# ════════════════════════════════════════════════════════════


def test_11_delete_group(client):
    resp = client.delete(
        f"/groups/{state['group_id']}",
        headers=auth_headers(state["token_a"]),
    )
    assert resp.status_code == 204, f"Delete group failed: {resp.text}"

    resp2 = client.get("/groups", headers=auth_headers(state["token_a"]))
    assert not any(g["id"] == state["group_id"] for g in resp2.json())


# ════════════════════════════════════════════════════════════
#  12. Не-admin не может удалить группу
# ════════════════════════════════════════════════════════════


def test_12_member_cannot_delete_group(client):
    invite = client.post("/auth/invite", headers=auth_headers(state["admin_token"]))
    code = invite.json()["code"]
    reg = client.post(
        "/auth/register",
        json={
            "username": f"dave_g_{RUN}",
            "password": "password123",
            "invite_code": code,
        },
    )
    assert reg.status_code == 200, f"Register dave failed: {reg.text}"
    token_d = reg.json()["access_token"]

    g = client.post(
        "/groups", json={"name": f"G2_{RUN}"}, headers=auth_headers(state["token_a"])
    )
    gid = g.json()["id"]
    client.post(
        f"/groups/{gid}/invite",
        json={"username": f"dave_g_{RUN}"},
        headers=auth_headers(state["token_a"]),
    )

    # Dave (member) пытается удалить → 403
    resp = client.delete(f"/groups/{gid}", headers=auth_headers(token_d))
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    # Чистим за собой
    client.delete(f"/groups/{gid}", headers=auth_headers(state["token_a"]))
