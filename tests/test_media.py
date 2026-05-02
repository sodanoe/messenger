"""
Тесты: загрузка медиафайлов — тип, размер, магические байты.
"""
import io

import pytest

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def make_jpeg_bytes(width: int = 10, height: int = 10) -> bytes:
    """Генерирует минимальный валидный JPEG в памяти."""
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    img.save(buf, format="JPEG")
    return buf.getvalue()


def make_large_bytes(mb: int) -> bytes:
    """Генерирует бинарный мусор заданного размера (не изображение)."""
    return b"\x00" * (mb * 1024 * 1024)


@pytest.mark.skipif(not HAS_PILLOW, reason="Pillow not installed")
def test_upload_valid_jpeg(client, make_user):
    alice = make_user()

    jpeg = make_jpeg_bytes()
    resp = client.post(
        "/media/upload",
        files={"file": ("test.jpg", io.BytesIO(jpeg), "image/jpeg")},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "url" in data


def test_upload_forbidden_mime(client, make_user):
    """Исполняемый файл под видом image/jpeg — должен получить 415."""
    alice = make_user()

    exe_content = b"MZ\x90\x00" + b"\x00" * 100  # PE-заголовок
    resp = client.post(
        "/media/upload",
        files={"file": ("virus.exe", io.BytesIO(exe_content), "application/octet-stream")},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 415


def test_upload_text_as_image(client, make_user):
    """HTML-файл объявлен как image/jpeg — должен получить 415."""
    alice = make_user()

    html = b"<html><body>not an image</body></html>"
    resp = client.post(
        "/media/upload",
        files={"file": ("page.html", io.BytesIO(html), "text/html")},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 415


def test_upload_spoofed_content_type(client, make_user):
    """
    SECURITY TEST: HTML-содержимое, но Content-Type: image/jpeg.
    Сервер должен отклонить по магическим байтам — вернуть 415.

    ОЖИДАЕМО УПАДЁТ до реализации проверки магических байтов.
    Текущее поведение: сервер принимает файл (200) — это баг.
    """
    alice = make_user()

    html = b"<html><body>xss payload</body></html>"
    resp = client.post(
        "/media/upload",
        files={"file": ("evil.jpg", io.BytesIO(html), "image/jpeg")},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 415, (
        "БАГ: сервер принял файл с поддельным content-type. "
        "Нужна проверка по магическим байтам в media_service.py"
    )


def test_upload_too_large(client, make_user):
    """Файл > 20MB должен вернуть 413."""
    alice = make_user()

    big = make_large_bytes(21)
    resp = client.post(
        "/media/upload",
        files={"file": ("big.jpg", io.BytesIO(big), "image/jpeg")},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 413


def test_upload_requires_auth(client):
    resp = client.post(
        "/media/upload",
        files={"file": ("test.jpg", io.BytesIO(b"data"), "image/jpeg")},
    )
    assert resp.status_code in (401, 403)
