"""
Smoke-тест Step 6: Reactions + Replies
Запуск: pytest tests/test_smoke_step6.py -v
Требует: uvicorn app.main:app на localhost:8000 (после применения миграции)
"""

import uuid

import httpx
import pytest

BASE = "http://localhost:8000"
RUN = uuid.uuid4().hex[:6]
state: dict = {}


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=10) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def setup(client):
    """Admin + alice + bob. Alice↔Bob contacts. Alice sends a message."""
    r = client.post("/auth/login", json={"username": "admin", "password": "adminpass"})
    assert r.status_code == 200
    state["admin_token"] = r.json()["access_token"]

    for name_key, tok_key, uid_key in [
        (f"s6_alice_{RUN}", "token_a", "uid_a"),
        (f"s6_bob_{RUN}", "token_b", "uid_b"),
    ]:
        inv = client.post("/auth/invite", headers=auth(state["admin_token"]))
        code = inv.json()["code"]
        reg = client.post(
            "/auth/register",
            json={"username": name_key, "password": "pass123", "invite_code": code},
        )
        assert reg.status_code == 200
        state[tok_key] = reg.json()["access_token"]
        me = client.get("/users/me", headers=auth(state[tok_key]))
        state[uid_key] = me.json()["id"]

    # Alice ↔ Bob contacts
    r = client.post(
        "/contacts", json={"username": f"s6_bob_{RUN}"}, headers=auth(state["token_a"])
    )
    assert r.status_code == 201

    # Alice sends first message
    r = client.post(
        f"/messages/{state['uid_b']}",
        json={"content": "Привет!"},
        headers=auth(state["token_a"]),
    )
    assert r.status_code == 201
    state["msg1_id"] = r.json()["id"]

    print(
        f"\n  RUN={RUN}  alice={state['uid_a']}  bob={state['uid_b']}  msg1={state['msg1_id']}"
    )


# ════════════════════════════════════════════════════════════════════════════
#  1. Реакция на сообщение
# ════════════════════════════════════════════════════════════════════════════


def test_1_add_reaction(client):
    r = client.post(
        f"/messages/{state['msg1_id']}/react",
        json={"emoji": "❤️"},
        headers=auth(state["token_b"]),
    )
    assert r.status_code == 200, f"React failed: {r.text}"
    reactions = r.json()
    assert isinstance(reactions, list)
    assert any(
        rx["emoji"] == "❤️" and rx["user_id"] == state["uid_b"] for rx in reactions
    ), f"Expected ❤️ from bob in {reactions}"


def test_2_reaction_visible_in_history(client):
    r = client.get(f"/messages/{state['uid_b']}", headers=auth(state["token_a"]))
    assert r.status_code == 200
    msgs = r.json()["messages"]
    msg = next((m for m in msgs if m["id"] == state["msg1_id"]), None)
    assert msg is not None, "Сообщение не найдено в истории"
    assert "reactions" in msg, "Поле reactions отсутствует"
    assert any(rx["emoji"] == "❤️" for rx in msg["reactions"]), (
        f"Реакция ❤️ не найдена в {msg['reactions']}"
    )


def test_3_toggle_removes_reaction(client):
    """Повторный POST на тот же эмодзи убирает реакцию."""
    r = client.post(
        f"/messages/{state['msg1_id']}/react",
        json={"emoji": "❤️"},
        headers=auth(state["token_b"]),
    )
    assert r.status_code == 200
    reactions = r.json()
    # Реакция должна исчезнуть
    assert not any(
        rx["emoji"] == "❤️" and rx["user_id"] == state["uid_b"] for rx in reactions
    ), f"Реакция должна была удалиться, но осталась: {reactions}"


def test_4_invalid_emoji_rejected(client):
    r = client.post(
        f"/messages/{state['msg1_id']}/react",
        json={"emoji": "🤡"},
        headers=auth(state["token_b"]),
    )
    assert r.status_code == 422, f"Expected 422 for invalid emoji, got {r.status_code}"


def test_5_outsider_cannot_react(client):
    """Пользователь не в переписке не может реагировать."""
    inv = client.post("/auth/invite", headers=auth(state["admin_token"]))
    code = inv.json()["code"]
    # Изменяем пароль на более сложный
    reg = client.post(
        "/auth/register",
        json={
            "username": f"s6_eve_{RUN}",
            "password": "Password123!",  # Сложный пароль
            "invite_code": code,
        },
    )
    assert reg.status_code == 200

    reg_data = reg.json()

    # Получаем токен
    if "access_token" in reg_data:
        eve_token = reg_data["access_token"]
    else:
        login = client.post(
            "/auth/login",
            json={"username": f"s6_eve_{RUN}", "password": "Password123!"},
        )
        assert login.status_code == 200
        eve_token = login.json()["access_token"]

    # Outsider не может реагировать
    r = client.post(
        f"/messages/{state['msg1_id']}/react",
        json={"emoji": "👍"},
        headers=auth(eve_token),
    )
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"


# ════════════════════════════════════════════════════════════════════════════
#  2. Ответ на сообщение
# ════════════════════════════════════════════════════════════════════════════


def test_6_send_reply(client):
    r = client.post(
        f"/messages/{state['uid_b']}",
        json={"content": "Отвечаю тебе!", "reply_to_id": state["msg1_id"]},
        headers=auth(state["token_a"]),
    )
    assert r.status_code == 201, f"Send reply failed: {r.text}"
    body = r.json()
    assert body["reply_to"] is not None, "reply_to должен быть в ответе"
    assert body["reply_to"]["id"] == state["msg1_id"]
    state["reply_msg_id"] = body["id"]


def test_7_reply_visible_in_history(client):
    r = client.get(f"/messages/{state['uid_b']}", headers=auth(state["token_a"]))
    assert r.status_code == 200
    msgs = r.json()["messages"]
    reply = next((m for m in msgs if m["id"] == state["reply_msg_id"]), None)
    assert reply is not None, "Ответное сообщение не найдено"
    assert reply["reply_to"] is not None
    assert reply["reply_to"]["id"] == state["msg1_id"]
    assert reply["reply_to"]["content"] == "Привет!", (
        f"Неверный текст цитаты: {reply['reply_to']['content']}"
    )


def test_8_invalid_reply_to_ignored(client):
    """reply_to_id из другой переписки → игнорируется (reply_to=None в ответе)."""
    r = client.post(
        f"/messages/{state['uid_b']}",
        json={"content": "Левый reply_to", "reply_to_id": 999999},
        headers=auth(state["token_a"]),
    )
    assert r.status_code == 201
    assert r.json()["reply_to"] is None, (
        "Невалидный reply_to должен быть проигнорирован"
    )


def test_9_multiple_reactions_different_users(client):
    """Несколько пользователей ставят разные реакции."""
    # Добавляем реакцию от alice
    r1 = client.post(
        f"/messages/{state['msg1_id']}/react",
        json={"emoji": "😂"},
        headers=auth(state["token_a"]),
    )
    assert r1.status_code == 200
    # Добавляем реакцию от bob
    r2 = client.post(
        f"/messages/{state['msg1_id']}/react",
        json={"emoji": "👍"},
        headers=auth(state["token_b"]),
    )
    assert r2.status_code == 200

    reactions = r2.json()
    emojis = [rx["emoji"] for rx in reactions]
    assert "😂" in emojis, f"Реакция 😂 от alice не найдена: {reactions}"
    assert "👍" in emojis, f"Реакция 👍 от bob не найдена: {reactions}"
