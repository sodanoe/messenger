"""
Smoke-тест Step 4: WebSocket + Realtime
Запуск: pytest tests/test_smoke_step4.py -v
Требует:
  - uvicorn app.main:app на localhost:8000
  - pip install websockets pytest-asyncio
"""

import asyncio
import json
import uuid

import httpx
import pytest
import websockets

BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"
RUN = uuid.uuid4().hex[:6]
state: dict = {}

pytestmark = pytest.mark.asyncio


# ────────────────────────────────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────────────────────────────────


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def ws_url(token: str) -> str:
    return f"{WS_BASE}/ws?token={token}"


async def recv_with_timeout(ws, timeout: float = 3.0) -> dict:
    """Receive one JSON message or raise asyncio.TimeoutError."""
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


# ────────────────────────────────────────────────────────────────────────────
#  Setup: admin + 3 пользователя + контакты alice↔bob
# ────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=10) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def setup_users(client):
    """Synchronous setup: login admin, register alice/bob/carol, add contacts."""
    # Admin login
    resp = client.post(
        "/auth/login", json={"username": "admin", "password": "adminpass"}
    )
    assert resp.status_code == 200, f"Admin login: {resp.text}"
    state["admin_token"] = resp.json()["access_token"]

    # Register alice, bob, carol
    for name_key, token_key, uid_key in [
        (f"ws_alice_{RUN}", "token_a", "uid_a"),
        (f"ws_bob_{RUN}", "token_b", "uid_b"),
        (f"ws_carol_{RUN}", "token_c", "uid_c"),
    ]:
        inv = client.post("/auth/invite", headers=auth_headers(state["admin_token"]))
        assert inv.status_code == 200
        code = inv.json()["code"]

        reg = client.post(
            "/auth/register",
            json={
                "username": name_key,
                "password": "password123",
                "invite_code": code,
            },
        )
        assert reg.status_code == 200, f"Register {name_key}: {reg.text}"
        state[token_key] = reg.json()["access_token"]
        me = client.get("/users/me", headers=auth_headers(state[token_key]))
        state[uid_key] = me.json()["id"]

    # Alice adds Bob as contact (creates two-way pair)
    r = client.post(
        "/contacts",
        json={"username": f"ws_bob_{RUN}"},
        headers=auth_headers(state["token_a"]),
    )
    assert r.status_code == 201, f"Add contact: {r.text}"

    print(
        f"\n  RUN={RUN}  alice={state['uid_a']}  bob={state['uid_b']}  carol={state['uid_c']}"
    )


# ────────────────────────────────────────────────────────────────────────────
#  Test 1: базовое подключение и отключение
# ────────────────────────────────────────────────────────────────────────────


async def test_1_connect_and_disconnect():
    """Client can connect and server cleanly accepts."""
    async with websockets.connect(ws_url(state["token_a"])) as ws:
        # Небольшая пауза — убеждаемся что соединение живо
        await asyncio.sleep(0.1)
        # websockets >= 14: ws.open убран, проверяем через ping/pong
        pong = await ws.ping()
        await asyncio.wait_for(pong, timeout=2.0)
    # После выхода из контекст-менеджера соединение закрыто — без ошибок


# ────────────────────────────────────────────────────────────────────────────
#  Test 2: неверный токен → сервер закрывает соединение
# ────────────────────────────────────────────────────────────────────────────


async def test_2_invalid_token_rejected():
    """Bad JWT → server closes with 1008."""
    with pytest.raises(Exception):
        # сервер закрывает соединение с кодом 1008 — любое исключение подходит
        async with websockets.connect(ws_url("bad.token.here")) as ws:
            await ws.recv()


# ────────────────────────────────────────────────────────────────────────────
#  Test 3: online presence — Bob видит alice_online при её подключении
# ────────────────────────────────────────────────────────────────────────────


async def test_3_online_presence_notification():
    """
    Bob connects first.
    Alice connects → Bob receives {type: user_online, user_id: alice_id}.
    Alice disconnects → Bob receives {type: user_offline, user_id: alice_id}.
    """
    async with websockets.connect(ws_url(state["token_b"])) as ws_bob:
        await asyncio.sleep(0.1)

        # Alice подключается — Bob должен получить уведомление
        async with websockets.connect(ws_url(state["token_a"])):
            msg = await recv_with_timeout(ws_bob, timeout=3.0)
            assert msg["type"] == "user_online", f"Expected user_online, got {msg}"
            assert msg["user_id"] == state["uid_a"]

        # Alice отключилась — Bob получает user_offline
        msg = await recv_with_timeout(ws_bob, timeout=3.0)
        assert msg["type"] == "user_offline", f"Expected user_offline, got {msg}"
        assert msg["user_id"] == state["uid_a"]


# ────────────────────────────────────────────────────────────────────────────
#  Test 4: DM через WS — Alice шлёт Bob'у, Bob получает мгновенно
# ────────────────────────────────────────────────────────────────────────────


async def test_4_dm_realtime_delivery(client):
    """POST /messages/:bob_id while Bob is connected → Bob's WS receives it."""
    async with websockets.connect(ws_url(state["token_b"])) as ws_bob:
        # Ждём возможный user_online (Alice может прийти позже — не важно)
        await asyncio.sleep(0.1)

        # Alice отправляет DM через REST
        resp = client.post(
            f"/messages/{state['uid_b']}",
            json={"content": "Привет через WS! 🚀"},
            headers=auth_headers(state["token_a"]),
        )
        assert resp.status_code == 201, f"Send DM: {resp.text}"

        # Bob должен получить сообщение по WS
        msg = await recv_with_timeout(ws_bob, timeout=3.0)

        # Пропускаем возможный user_online от Alice
        if msg.get("type") in ("user_online", "user_offline"):
            msg = await recv_with_timeout(ws_bob, timeout=3.0)

        assert msg["type"] == "new_message", f"Expected new_message, got {msg}"
        assert msg["from"] == state["uid_a"]
        assert msg["content"] == "Привет через WS! 🚀"
        assert "created_at" in msg


# ────────────────────────────────────────────────────────────────────────────
#  Test 5: offline receiver — сообщение сохраняется в БД без ошибок
# ────────────────────────────────────────────────────────────────────────────


async def test_5_dm_to_offline_user_no_error(client):
    """Sending DM to user with no WS connection must still return 201."""
    # Bob не подключён по WS
    resp = client.post(
        f"/messages/{state['uid_b']}",
        json={"content": "offline message"},
        headers=auth_headers(state["token_a"]),
    )
    assert resp.status_code == 201, f"DM to offline: {resp.text}"


# ────────────────────────────────────────────────────────────────────────────
#  Test 6: heartbeat продлевает TTL
# ────────────────────────────────────────────────────────────────────────────


async def test_6_heartbeat(client):
    """Client sends ping text → server resets Redis TTL, no disconnect."""
    async with websockets.connect(ws_url(state["token_a"])) as ws:
        await asyncio.sleep(0.1)
        # Шлём heartbeat
        await ws.send("ping")
        # Соединение должно остаться живым (websockets >= 14: ws.open убран)
        await asyncio.sleep(0.2)
        pong = await ws.ping()
        await asyncio.wait_for(pong, timeout=2.0)

        # Redis online key должен существовать (через GET /contacts)
        resp = client.get("/contacts", headers=auth_headers(state["token_b"]))
        assert resp.status_code == 200
        contacts = resp.json()
        alice_contact = next(
            (c for c in contacts if c["contact_user_id"] == state["uid_a"]), None
        )
        assert alice_contact is not None
        assert alice_contact.get("is_online") is True, (
            f"Expected is_online=True while WS open, got {alice_contact}"
        )


# ────────────────────────────────────────────────────────────────────────────
#  Test 7: группа — fan-out group_message
# ────────────────────────────────────────────────────────────────────────────


async def test_7_group_message_fanout(client):
    """
    Alice создаёт группу, приглашает Bob.
    Bob подключён по WS.
    Alice шлёт POST /groups/:id/messages → Bob получает {type: group_message}.
    """
    # Создаём группу
    g = client.post(
        "/groups",
        json={"name": f"WS Group {RUN}"},
        headers=auth_headers(state["token_a"]),
    )
    assert g.status_code == 201, f"Create group: {g.text}"
    group_id = g.json()["id"]
    state["group_id"] = group_id

    # Приглашаем Bob
    inv = client.post(
        f"/groups/{group_id}/invite",
        json={"username": f"ws_bob_{RUN}"},
        headers=auth_headers(state["token_a"]),
    )
    assert inv.status_code == 201, f"Invite bob: {inv.text}"

    # Bob подключается
    async with websockets.connect(ws_url(state["token_b"])) as ws_bob:
        await asyncio.sleep(0.1)

        # Alice шлёт сообщение в группу
        resp = client.post(
            f"/groups/{group_id}/messages",
            json={"content": "Привет группа! 🎉"},
            headers=auth_headers(state["token_a"]),
        )
        assert resp.status_code == 201, f"Group message: {resp.text}"

        # Bob получает по WS
        msg = await recv_with_timeout(ws_bob, timeout=3.0)

        # Пропускаем user_online если пришёл
        if msg.get("type") in ("user_online", "user_offline"):
            msg = await recv_with_timeout(ws_bob, timeout=3.0)

        assert msg["type"] == "group_message", f"Expected group_message, got {msg}"
        assert msg["group_id"] == group_id
        assert msg["from"] == state["uid_a"]
        assert msg["content"] == "Привет группа! 🎉"
        assert "created_at" in msg


# ────────────────────────────────────────────────────────────────────────────
#  Test 8: Alice не получает собственный group message
# ────────────────────────────────────────────────────────────────────────────


async def test_8_sender_excluded_from_fanout(client):
    """Sender should NOT receive their own group message via WS."""
    group_id = state["group_id"]

    async with websockets.connect(ws_url(state["token_a"])) as ws_alice:
        await asyncio.sleep(0.1)

        resp = client.post(
            f"/groups/{group_id}/messages",
            json={"content": "Alice's own message"},
            headers=auth_headers(state["token_a"]),
        )
        assert resp.status_code == 201

        # Alice не должна получить свой message обратно
        with pytest.raises(asyncio.TimeoutError):
            msg = await recv_with_timeout(ws_alice, timeout=1.5)
            # Если что-то пришло — убеждаемся что это НЕ group_message
            assert msg.get("type") != "group_message", (
                f"Sender should not receive own group_message, got {msg}"
            )


# ────────────────────────────────────────────────────────────────────────────
#  Test 9: Carol не получает group_message (не участник)
# ────────────────────────────────────────────────────────────────────────────


async def test_9_non_member_no_message(client):
    """Carol is not in the group → must not receive group_message."""
    group_id = state["group_id"]

    async with websockets.connect(ws_url(state["token_c"])) as ws_carol:
        await asyncio.sleep(0.1)

        client.post(
            f"/groups/{group_id}/messages",
            json={"content": "Private group stuff"},
            headers=auth_headers(state["token_a"]),
        )

        with pytest.raises(asyncio.TimeoutError):
            await recv_with_timeout(ws_carol, timeout=1.5)


# ────────────────────────────────────────────────────────────────────────────
#  Test 10: is_online в /contacts обновляется live
# ────────────────────────────────────────────────────────────────────────────


async def test_10_contacts_is_online_live(client):
    """
    GET /contacts for Bob:
      - Alice offline → is_online=False
      - Alice connects → is_online=True
    """
    # Убеждаемся что Alice НЕ подключена
    await asyncio.sleep(0.2)

    resp_before = client.get("/contacts", headers=auth_headers(state["token_b"]))
    contacts_before = resp_before.json()
    alice_before = next(
        (c for c in contacts_before if c["contact_user_id"] == state["uid_a"]), None
    )
    assert alice_before is not None
    assert alice_before.get("is_online") is False, (
        f"Expected is_online=False before connect, got {alice_before}"
    )

    # Alice подключается
    async with websockets.connect(ws_url(state["token_a"])):
        await asyncio.sleep(0.2)  # Redis TTL должен проставиться

        resp_after = client.get("/contacts", headers=auth_headers(state["token_b"]))
        contacts_after = resp_after.json()
        alice_after = next(
            (c for c in contacts_after if c["contact_user_id"] == state["uid_a"]), None
        )
        assert alice_after is not None
        assert alice_after.get("is_online") is True, (
            f"Expected is_online=True after connect, got {alice_after}"
        )
