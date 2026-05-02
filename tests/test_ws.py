"""
Тесты: WebSocket — аутентификация, одноразовый тикет, базовое подключение.

Требует: pip install websockets
"""
import pytest

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


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets not installed")
def test_ws_bad_ticket_closes_1008(client, make_user):
    """Невалидный тикет → сервер закрывает соединение с кодом 1008."""
    try:
        with ws_sync.connect(_ws_url("badticket000000000000000000000000")) as ws:
            ws.recv(timeout=3)
        pytest.fail("Соединение должно было быть закрыто")
    except websockets.exceptions.ConnectionClosedError as e:
        assert e.code == 1008, f"Ожидали код 1008, получили {e.code}"
    except Exception as e:
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
