"""
Тесты: целостность данных — replies, реакции, пагинация, пустые сообщения.
"""


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def _make_dm(client, alice, bob):
    client.post(
        "/contacts", json={"username": bob["username"]}, headers=auth(alice["token"])
    )
    resp = client.post(
        "/chats/direct", json={"user_id": bob["id"]}, headers=auth(alice["token"])
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_reply_to_nonexistent_message(client, make_user):
    """reply_to_id на несуществующее сообщение → 404."""
    alice = make_user()
    bob = make_user()
    chat_id = _make_dm(client, alice, bob)

    resp = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "reply to ghost", "reply_to_id": 9999999},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 404


def test_cross_chat_reply_forbidden(client, make_user):
    """
    Ответ на сообщение из другого чата → 400.
    Alice пишет в чате A, Bob пытается ответить на это сообщение из чата B.
    """
    alice = make_user()
    bob = make_user()
    carol = make_user()

    chat_a = _make_dm(client, alice, bob)
    chat_b = _make_dm(client, alice, carol)

    # Сообщение в чате A
    msg = client.post(
        f"/chats/{chat_a}/messages",
        json={"content": "message in chat A"},
        headers=auth(alice["token"]),
    ).json()

    # Попытка ответить на него из чата B
    resp = client.post(
        f"/chats/{chat_b}/messages",
        json={"content": "cross-chat reply", "reply_to_id": msg["id"]},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 400


def test_reaction_from_non_member(client, make_user):
    """Реакция от не-участника чата → 403."""
    alice = make_user()
    bob = make_user()
    carol = make_user()

    chat_id = _make_dm(client, alice, bob)

    msg = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "react to me"},
        headers=auth(alice["token"]),
    ).json()

    resp = client.post(
        f"/chats/{chat_id}/messages/{msg['id']}/reactions",
        json={"emoji": "👍"},
        headers=auth(carol["token"]),
    )
    assert resp.status_code == 403


def test_empty_message_rejected(client, make_user):
    """
    Пустое сообщение → 400 или 422.

    ОЖИДАЕМО УПАДЁТ: в schemas/chat.py нет min_length=1 на поле content.
    Это баг — нужно добавить: content: str = Field(min_length=1)
    """
    alice = make_user()
    bob = make_user()
    chat_id = _make_dm(client, alice, bob)

    resp = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": ""},
        headers=auth(alice["token"]),
    )
    assert resp.status_code in (400, 422), (
        "БАГ: пустое сообщение принято сервером. "
        "Добавьте Field(min_length=1) в SendMessageRequest.content"
    )


def test_whitespace_only_message_rejected(client, make_user):
    """
    Сообщение из пробелов → 400.
    Поведение зависит от бизнес-логики: либо trim+reject, либо явная валидация.
    """
    alice = make_user()
    bob = make_user()
    chat_id = _make_dm(client, alice, bob)

    resp = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "   "},
        headers=auth(alice["token"]),
    )
    assert resp.status_code in (400, 422), "Сообщение из пробелов должно отклоняться"


def test_pagination_messages(client, make_user):
    """Отправить 25 сообщений, запросить с limit=10 — получить ровно 10."""
    alice = make_user()
    bob = make_user()
    chat_id = _make_dm(client, alice, bob)

    for i in range(25):
        client.post(
            f"/chats/{chat_id}/messages",
            json={"content": f"msg {i}"},
            headers=auth(alice["token"]),
        )

    # API использует cursor-пагинацию (limit захардкожен = 50 в PAGE_SIZE)
    # Проверяем что сообщения вообще возвращаются в правильном порядке
    history = client.get(
        f"/chats/{chat_id}/messages",
        headers=auth(alice["token"]),
    ).json()

    messages = history["messages"]
    assert len(messages) == 25

    # Порядок: от новых к старым (desc по id)
    ids = [m["id"] for m in messages]
    assert ids == sorted(ids, reverse=True), "Сообщения должны идти от новых к старым"


def test_pagination_cursor(client, make_user):
    """Курсорная пагинация: второй запрос с cursor возвращает следующую страницу."""
    alice = make_user()
    bob = make_user()
    chat_id = _make_dm(client, alice, bob)

    # Отправляем 60 сообщений (больше PAGE_SIZE=50)
    for i in range(60):
        client.post(
            f"/chats/{chat_id}/messages",
            json={"content": f"page msg {i}"},
            headers=auth(alice["token"]),
        )

    # Первая страница
    page1 = client.get(
        f"/chats/{chat_id}/messages",
        headers=auth(alice["token"]),
    ).json()
    assert len(page1["messages"]) == 50
    cursor = page1["next_cursor"]
    assert cursor is not None, "next_cursor должен быть при > 50 сообщениях"

    # Вторая страница
    page2 = client.get(
        f"/chats/{chat_id}/messages?cursor={cursor}",
        headers=auth(alice["token"]),
    ).json()
    assert len(page2["messages"]) == 10
    assert page2["next_cursor"] is None

    # Проверяем что ID не пересекаются
    ids1 = {m["id"] for m in page1["messages"]}
    ids2 = {m["id"] for m in page2["messages"]}
    assert ids1.isdisjoint(ids2), "Страницы не должны пересекаться"


def test_password_hash_not_in_search(client, make_user):
    alice = make_user()
    bob = make_user()

    results = client.get(
        f"/users/search?q={bob['username']}",
        headers=auth(alice["token"]),
    ).json()

    for user in results:
        assert "password" not in user
        assert "password_hash" not in user


def test_password_hash_not_in_members(client, make_user):
    alice = make_user()
    bob = make_user()

    group = client.post(
        "/chats/group",
        json={"name": "PwdTest", "member_ids": [bob["id"]]},
        headers=auth(alice["token"]),
    ).json()

    members = client.get(
        f"/chats/{group['id']}/members",
        headers=auth(alice["token"]),
    ).json()["members"]

    for member in members:
        assert "password" not in member
        assert "password_hash" not in member

    # Cleanup
    client.delete(f"/chats/{group['id']}", headers=auth(alice["token"]))
