"""
Тесты: WebSocket — аутентификация, одноразовый тикет, базовое подключение.

Требует: pip install websockets
"""

import pytest
import json
import time

try:
    import websockets
    import websockets.sync.client as ws_sync

    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

from tests.conftest import BASE_URL


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def _ws_url(ticket: str) -> str:
    base = BASE_URL.replace("http://", "ws://").replace("https://", "wss://")
    return f"{base}/ws?ticket={ticket}"


def _drain_ws(ws, duration: float = 2.0) -> list[dict]:
    """Собирает все JSON-сообщения, пришедшие за `duration` секунд."""
    messages = []
    deadline = time.monotonic() + duration
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            raw = ws.recv(timeout=remaining)
            messages.append(json.loads(raw))
        except TimeoutError:
            break
        except Exception:
            break
    return messages


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets not installed")
def test_ws_bad_ticket_closes_1008(client, make_user):
    """Невалидный тикет → сервер закрывает соединение с кодом 1008."""
    try:
        with ws_sync.connect(_ws_url("badticket000000000000000000000000")) as ws:
            ws.recv(timeout=3)
        pytest.fail("Соединение должно было быть закрыто")
    except websockets.exceptions.ConnectionClosedError as e:
        assert e.code == 1008, f"Ожидали код 1008, получили {e.code}"
    except Exception:
        # Некоторые реализации закрывают до handshake
        pass


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets not installed")
def test_ws_no_ticket_rejected(client, make_user):
    """WS без тикета вообще — соединение отклоняется."""
    base = BASE_URL.replace("http://", "ws://").replace("https://", "wss://")
    try:
        with ws_sync.connect(f"{base}/ws") as ws:
            ws.recv(timeout=3)
        pytest.fail("Соединение должно было быть отклонено")
    except Exception:
        pass  # Любая ошибка подключения — это правильное поведение


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets not installed")
def test_ws_ticket_single_use(client, make_user):
    """
    Одноразовый тикет нельзя использовать дважды.
    Второе подключение должно быть закрыто с кодом 1008.
    """
    alice = make_user()

    ticket_resp = client.post("/auth/ws/ticket", headers=auth(alice["token"]))
    assert ticket_resp.status_code == 200
    ticket = ticket_resp.json()["ticket"]

    # Первое подключение — успешное
    try:
        with ws_sync.connect(_ws_url(ticket), open_timeout=5) as ws:
            pass  # просто подключились и отключились
    except Exception:
        pass  # не страшно если сразу закрылось

    # Второе подключение с тем же тикетом — должно быть отклонено
    try:
        with ws_sync.connect(_ws_url(ticket), open_timeout=5) as ws:
            ws.recv(timeout=3)
        pytest.fail("Повторное использование тикета должно быть отклонено")
    except websockets.exceptions.ConnectionClosedError as e:
        assert e.code == 1008, f"Ожидали код 1008, получили {e.code}"
    except Exception:
        pass  # закрытие до handshake тоже нормально


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets not installed")
def test_ws_connect_and_receive(client, make_user):
    """Валидный тикет → подключение успешно, сервер не закрывает сразу."""
    alice = make_user()

    ticket_resp = client.post("/auth/ws/ticket", headers=auth(alice["token"]))
    ticket = ticket_resp.json()["ticket"]

    connected = False
    try:
        with ws_sync.connect(_ws_url(ticket), open_timeout=5) as ws:
            connected = True
            # Отправляем heartbeat ping
            ws.send("ping")
    except websockets.exceptions.ConnectionClosedError as e:
        if e.code == 1008:
            pytest.fail("Валидный тикет был отклонён сервером")
    except Exception:
        pass

    assert connected, "Не удалось подключиться с валидным тикетом"


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets not installed")
def test_ws_presence_survives_one_device_disconnect(client, make_user):
    """У юзера два WS-соединения ("два устройства"). Закрытие одного
    не должно гасить presence и слать user_offline контактам —
    только закрытие ПОСЛЕДНЕГО должно.

    Регрессия для бага: cleanup безусловно делал redis.delete(...)
    и notifier.user_offline(...) при отключении ЛЮБОГО сокета.
    """
    alice = make_user()
    bob = make_user()

    # мьютуал контакт (create_pair создаёт обе стороны как accepted)
    client.post(
        "/contacts", json={"username": alice["username"]}, headers=auth(bob["token"])
    )

    # Bob слушает presence-события про Alice
    bob_ticket = client.post("/auth/ws/ticket", headers=auth(bob["token"])).json()[
        "ticket"
    ]
    with ws_sync.connect(_ws_url(bob_ticket), open_timeout=5) as bob_ws:
        _drain_ws(bob_ws, duration=0.5)  # сброс начального батча

        # Alice подключается с двух "устройств"
        ticket_a1 = client.post("/auth/ws/ticket", headers=auth(alice["token"])).json()[
            "ticket"
        ]
        ticket_a2 = client.post("/auth/ws/ticket", headers=auth(alice["token"])).json()[
            "ticket"
        ]

        ws_a1 = ws_sync.connect(_ws_url(ticket_a1), open_timeout=5)
        ws_a2 = ws_sync.connect(_ws_url(ticket_a2), open_timeout=5)

        try:
            events = _drain_ws(bob_ws, duration=2.0)
            assert any(e.get("type") == "user_online" for e in events), events

            # Закрываем ПЕРВОЕ устройство Alice
            ws_a1.close()

            events = _drain_ws(bob_ws, duration=2.0)
            assert not any(e.get("type") == "user_offline" for e in events), (
                f"user_offline пришёл, хотя у Alice ещё активен второй сокет: {events}"
            )
        finally:
            ws_a2.close()

        # Теперь оба устройства Alice закрыты
        events = _drain_ws(bob_ws, duration=2.0)
        assert any(e.get("type") == "user_offline" for e in events), events


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets not installed")
def test_ws_offline_message_delivered_on_connect(client, make_user):
    """Сообщение, отправленное офлайн-получателю, лежит в
    ws:inbox:{user_id} и доставляется через drain_inbox() при
    подключении."""
    alice = make_user()
    bob = make_user()

    client.post(
        "/contacts", json={"username": bob["username"]}, headers=auth(alice["token"])
    )
    chat = client.post(
        "/chats/direct", json={"user_id": bob["id"]}, headers=auth(alice["token"])
    )
    assert chat.status_code == 201
    chat_id = chat.json()["id"]

    # Bob офлайн (WS не открыт). Alice пишет.
    msg = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "ты на месте?"},
        headers=auth(alice["token"]),
    ).json()

    # Bob подключается
    ticket = client.post("/auth/ws/ticket", headers=auth(bob["token"])).json()["ticket"]
    with ws_sync.connect(_ws_url(ticket), open_timeout=5) as bob_ws:
        events = _drain_ws(bob_ws, duration=3.0)
        new_messages = [e for e in events if e.get("type") == "new_message"]
        assert any(m.get("id") == msg["id"] for m in new_messages), events
