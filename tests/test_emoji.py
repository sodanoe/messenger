"""
Тесты: custom emoji — загрузка, список, дубли, валидация shortcode, удаление.
"""

import io
import uuid

import pytest

try:
    from PIL import Image

    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def make_png_bytes() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGBA", (32, 32), color=(255, 0, 0, 255))
    img.save(buf, format="PNG")
    return buf.getvalue()


def _upload_emoji(client, token, shortcode=None):
    """Хелпер: загрузить emoji, вернуть dict с id и shortcode."""
    if shortcode is None:
        shortcode = f"test_{uuid.uuid4().hex[:6]}"
    png = make_png_bytes()
    resp = client.post(
        "/emojis/",
        data={"shortcode": shortcode},
        files={"file": (f"{shortcode}.png", io.BytesIO(png), "image/png")},
        headers=auth(token),
    )
    return resp, shortcode


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
def test_upload_emoji_success(client, make_user, admin_token):
    alice = make_user()
    resp, shortcode = _upload_emoji(client, alice["token"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["shortcode"] == shortcode
    assert "id" in data

    # Cleanup
    client.delete(f"/emojis/{data['id']}", headers=auth(alice["token"]))


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
def test_emoji_appears_in_list(client, make_user):
    alice = make_user()
    resp, shortcode = _upload_emoji(client, alice["token"])
    assert resp.status_code == 201
    emoji_id = resp.json()["id"]

    emojis = client.get("/emojis/", headers=auth(alice["token"])).json()["emojis"]
    assert any(e["shortcode"] == shortcode for e in emojis)

    # Cleanup
    client.delete(f"/emojis/{emoji_id}", headers=auth(alice["token"]))


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
def test_emoji_duplicate_shortcode(client, make_user):
    """Повторный shortcode → 409 Conflict."""
    alice = make_user()
    resp, shortcode = _upload_emoji(client, alice["token"])
    assert resp.status_code == 201
    emoji_id = resp.json()["id"]

    resp2, _ = _upload_emoji(client, alice["token"], shortcode=shortcode)
    assert resp2.status_code == 409

    # Cleanup
    client.delete(f"/emojis/{emoji_id}", headers=auth(alice["token"]))


def test_emoji_invalid_shortcode_spaces(client, make_user):
    """Shortcode с пробелами → 400."""
    alice = make_user()
    png = b"fake"
    resp = client.post(
        "/emojis/",
        data={"shortcode": "bad emoji"},
        files={"file": ("bad.png", io.BytesIO(png), "image/png")},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 400


def test_emoji_invalid_shortcode_special_chars(client, make_user):
    """Shortcode со спецсимволами → 400."""
    alice = make_user()
    png = b"fake"
    resp = client.post(
        "/emojis/",
        data={"shortcode": "emoji!@#"},
        files={"file": ("bad.png", io.BytesIO(png), "image/png")},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 400


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
def test_delete_emoji_removes_from_list(client, make_user):
    alice = make_user()
    resp, shortcode = _upload_emoji(client, alice["token"])
    assert resp.status_code == 201
    emoji_id = resp.json()["id"]

    del_resp = client.delete(f"/emojis/{emoji_id}", headers=auth(alice["token"]))
    assert del_resp.status_code == 204

    emojis = client.get("/emojis/", headers=auth(alice["token"])).json()["emojis"]
    assert not any(e["shortcode"] == shortcode for e in emojis)


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
def test_delete_emoji_image_returns_404(client, make_user):
    """
    После удаления emoji GET /emojis/{shortcode}.png → 404.
    Проверяем что файл физически недоступен через API.
    """
    alice = make_user()
    resp, shortcode = _upload_emoji(client, alice["token"])
    assert resp.status_code == 201
    emoji_id = resp.json()["id"]

    # Проверяем что файл доступен до удаления
    img_resp = client.get(f"/emojis/{shortcode}.png", headers=auth(alice["token"]))
    assert img_resp.status_code == 200

    # Удаляем
    client.delete(f"/emojis/{emoji_id}", headers=auth(alice["token"]))

    # Теперь должен быть 404
    img_resp2 = client.get(f"/emojis/{shortcode}.png", headers=auth(alice["token"]))
    assert img_resp2.status_code == 404
