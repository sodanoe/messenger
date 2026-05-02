"""
Тесты CASCADE: после удаления пользователя база остаётся чистой.
Это наш главный smoke-check корректности DELETE /users/me.
"""


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_deleted_user_not_in_search(client, make_user):
    alice = make_user()
    bob = make_user()

    # Bob виден в поиске
    before = client.get(
        f"/users/search?q={bob['username']}", headers=auth(alice["token"])
    ).json()
    assert any(u["username"] == bob["username"] for u in before)

    # Bob удаляет аккаунт
    del_resp = client.delete("/users/me", headers=auth(bob["token"]))
    assert del_resp.status_code == 204

    # Больше не виден
    after = client.get(
        f"/users/search?q={bob['username']}", headers=auth(alice["token"])
    ).json()
    assert not any(u["username"] == bob["username"] for u in after)
    # Примечание: make_user teardown молча проигнорирует повторный DELETE для bob


def test_deleted_user_removed_from_contacts(client, make_user):
    alice = make_user()
    bob = make_user()

    client.post("/contacts", json={"username": bob["username"]}, headers=auth(alice["token"]))

    contacts = client.get("/contacts", headers=auth(alice["token"])).json()
    assert any(c["contact_user_id"] == bob["id"] for c in contacts)

    del_resp = client.delete("/users/me", headers=auth(bob["token"]))
    assert del_resp.status_code == 204
    # Проверяем что контакт исчез у Alice
    contacts_after = client.get("/contacts", headers=auth(alice["token"])).json()
    assert not any(c["contact_user_id"] == bob["id"] for c in contacts_after)


def test_deleted_user_token_invalid(client, make_user):
    """После DELETE /users/me старый токен не должен работать."""
    alice = make_user()

    resp = client.delete("/users/me", headers=auth(alice["token"]))
    assert resp.status_code == 204

    resp2 = client.get("/users/me", headers=auth(alice["token"]))
    assert resp2.status_code in (401, 403)


def test_cascade_chat_access_after_member_deletion(client, make_user):
    """
    Alice и Bob создают чат, Bob удаляет аккаунт.
    Чат по-прежнему доступен Alice — запрос не падает с 500.
    """
    alice = make_user()
    bob = make_user()

    client.post("/contacts", json={"username": bob["username"]}, headers=auth(alice["token"]))
    chat = client.post(
        "/chats/direct", json={"user_id": bob["id"]}, headers=auth(alice["token"])
    ).json()
    chat_id = chat["id"]

    client.post(
        f"/chats/{chat_id}/messages", json={"content": "Hi"}, headers=auth(alice["token"])
    )
    client.post(
        f"/chats/{chat_id}/messages", json={"content": "Hi back"}, headers=auth(bob["token"])
    )

    # Bob удаляет аккаунт
    client.delete("/users/me", headers=auth(bob["token"]))

    # Alice читает историю — не должно быть 500
    resp = client.get(f"/chats/{chat_id}/messages", headers=auth(alice["token"]))
    assert resp.status_code != 500, f"Internal error after cascade delete: {resp.text}"
