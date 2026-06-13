"""
Тесты: отправка сообщений, история, реакции, replies, редактирование, удаление.
"""


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def _dm(client, alice, bob):
    """Добавляет контакт и создаёт direct chat. Возвращает chat_id."""
    client.post(
        "/contacts",
        json={"username": bob["username"]},
        headers=auth(alice["token"]),
    )
    resp = client.post(
        "/chats/direct",
        json={"user_id": bob["id"]},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_send_message(client, make_user):
    alice = make_user()
    bob = make_user()
    chat_id = _dm(client, alice, bob)

    resp = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Привет, Bob!"},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Привет, Bob!"
    assert data["sender_id"] == alice["id"]


def test_message_in_history(client, make_user):
    alice = make_user()
    bob = make_user()
    chat_id = _dm(client, alice, bob)

    client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "History test"},
        headers=auth(alice["token"]),
    )

    history = client.get(
        f"/chats/{chat_id}/messages", headers=auth(bob["token"])
    ).json()
    assert "messages" in history
    assert any(m["content"] == "History test" for m in history["messages"])


def test_dm_requires_contact(client, make_user):
    """Создать чат можно без контакта, но отправить сообщение — нет."""
    alice = make_user()
    bob = make_user()

    chat = client.post(
        "/chats/direct", json={"user_id": bob["id"]}, headers=auth(alice["token"])
    ).json()

    resp = client.post(
        f"/chats/{chat['id']}/messages",
        json={"content": "no contact"},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 403


def test_non_member_cannot_send(client, make_user):
    alice = make_user()
    bob = make_user()
    carol = make_user()
    chat_id = _dm(client, alice, bob)

    resp = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "intruder"},
        headers=auth(carol["token"]),
    )
    assert resp.status_code == 403


def test_add_and_remove_reaction(client, make_user):
    alice = make_user()
    bob = make_user()
    chat_id = _dm(client, alice, bob)

    msg = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "React to me"},
        headers=auth(alice["token"]),
    ).json()
    msg_id = msg["id"]

    add = client.post(
        f"/chats/{chat_id}/messages/{msg_id}/reactions",
        json={"emoji": "❤️"},
        headers=auth(bob["token"]),
    )
    assert add.status_code == 201

    history = client.get(
        f"/chats/{chat_id}/messages", headers=auth(alice["token"])
    ).json()
    found = next(m for m in history["messages"] if m["id"] == msg_id)
    assert any(r["emoji"] == "❤️" for r in found["reactions"])

    remove = client.delete(
        f"/chats/{chat_id}/messages/{msg_id}/reactions/❤️",
        headers=auth(bob["token"]),
    )
    assert remove.status_code == 204


def test_reply_to_message(client, make_user):
    alice = make_user()
    bob = make_user()
    chat_id = _dm(client, alice, bob)

    original = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Оригинал"},
        headers=auth(alice["token"]),
    ).json()

    reply = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Ответ", "reply_to_id": original["id"]},
        headers=auth(bob["token"]),
    ).json()

    assert reply["reply_to"] is not None
    assert reply["reply_to"]["id"] == original["id"]


def test_edit_own_message(client, make_user):
    alice = make_user()
    bob = make_user()
    chat_id = _dm(client, alice, bob)

    msg = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Старый текст"},
        headers=auth(alice["token"]),
    ).json()

    resp = client.put(
        f"/chats/{chat_id}/messages/{msg['id']}",
        json={"new_content": "Новый текст"},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 200


def test_edit_others_message_forbidden(client, make_user):
    alice = make_user()
    bob = make_user()
    chat_id = _dm(client, alice, bob)

    msg = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Alice's message"},
        headers=auth(alice["token"]),
    ).json()

    resp = client.put(
        f"/chats/{chat_id}/messages/{msg['id']}",
        json={"new_content": "Bob's edit attempt"},
        headers=auth(bob["token"]),
    )
    assert resp.status_code == 403


def test_delete_own_message(client, make_user):
    alice = make_user()
    bob = make_user()
    chat_id = _dm(client, alice, bob)

    msg = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Delete me"},
        headers=auth(alice["token"]),
    ).json()

    resp = client.delete(
        f"/chats/{chat_id}/messages/{msg['id']}",
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 204

    history = client.get(
        f"/chats/{chat_id}/messages", headers=auth(alice["token"])
    ).json()
    assert not any(m["id"] == msg["id"] for m in history["messages"])


def test_group_message_flow(client, make_user):
    alice = make_user()
    bob = make_user()

    group = client.post(
        "/chats/group",
        json={"name": "TestGroup", "member_ids": [bob["id"]]},
        headers=auth(alice["token"]),
    ).json()
    gid = group["id"]

    msg = client.post(
        f"/chats/{gid}/messages",
        json={"content": "Всем привет!"},
        headers=auth(alice["token"]),
    ).json()
    assert msg["content"] == "Всем привет!"

    history = client.get(f"/chats/{gid}/messages", headers=auth(bob["token"])).json()
    assert any(m["content"] == "Всем привет!" for m in history["messages"])

    # Cleanup
    client.delete(f"/chats/{gid}", headers=auth(alice["token"]))


def test_edit_deleted_message_returns_404(client, make_user):
    """После удаления сообщение нельзя отредактировать — 404.

    Регрессия для фикса: get_by_id не фильтровал is_deleted, поэтому
    edit_message мог менять content уже "удалённого" сообщения.
    """
    alice = make_user()
    bob = make_user()
    chat_id = _dm(client, alice, bob)

    msg = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "будет удалено"},
        headers=auth(alice["token"]),
    ).json()

    deleted = client.delete(
        f"/chats/{chat_id}/messages/{msg['id']}", headers=auth(alice["token"])
    )
    assert deleted.status_code == 204

    edited = client.put(
        f"/chats/{chat_id}/messages/{msg['id']}",
        json={"new_content": "правка после удаления"},
        headers=auth(alice["token"]),
    )
    assert edited.status_code == 404


def test_delete_message_twice_is_idempotent(client, make_user):
    """Повторное удаление уже удалённого сообщения — не ошибка (204)."""
    alice = make_user()
    bob = make_user()
    chat_id = _dm(client, alice, bob)

    msg = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "удалю дважды"},
        headers=auth(alice["token"]),
    ).json()

    first = client.delete(
        f"/chats/{chat_id}/messages/{msg['id']}", headers=auth(alice["token"])
    )
    assert first.status_code == 204

    second = client.delete(
        f"/chats/{chat_id}/messages/{msg['id']}", headers=auth(alice["token"])
    )
    assert second.status_code == 204


def test_reply_to_message_with_media_includes_media_url(client, make_user):
    """Reply на сообщение с картинкой должен содержать media_url
    оригинала в reply_to (regression для рефакторинга send_message:
    _load_media_map + _build_reply_payload)."""
    import io

    try:
        from PIL import Image
    except ImportError:
        import pytest

        pytest.skip("Pillow not installed")

    alice = make_user()
    bob = make_user()
    chat_id = _dm(client, alice, bob)

    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color=(0, 255, 0)).save(buf, format="JPEG")
    buf.seek(0)

    upload = client.post(
        "/media/upload",
        files={"file": ("photo.jpg", buf, "image/jpeg")},
        headers=auth(alice["token"]),
    )
    assert upload.status_code == 200
    media = upload.json()

    original = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Глянь фото", "media_id": media["id"]},
        headers=auth(alice["token"]),
    ).json()
    assert original["media_url"] == media["url"]

    reply = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "Красота!", "reply_to_id": original["id"]},
        headers=auth(bob["token"]),
    ).json()

    assert reply["reply_to"] is not None
    assert reply["reply_to"]["id"] == original["id"]
    assert reply["reply_to"]["media_url"] == media["url"]
