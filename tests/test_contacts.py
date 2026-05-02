"""
Тесты: контакты — добавление, список, блокировка, поиск, удаление.
"""


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_add_contact_creates_pair(client, make_user):
    alice = make_user()
    bob = make_user()

    resp = client.post(
        "/contacts",
        json={"username": bob["username"]},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 201
    assert resp.json()["contact_user_id"] == bob["id"]

    # Обратная запись — Bob видит Alice в своих контактах
    contacts_b = client.get("/contacts", headers=auth(bob["token"])).json()
    assert any(c["contact_user_id"] == alice["id"] for c in contacts_b)


def test_add_contact_duplicate(client, make_user):
    alice = make_user()
    bob = make_user()

    client.post(
        "/contacts", json={"username": bob["username"]}, headers=auth(alice["token"])
    )
    resp = client.post(
        "/contacts", json={"username": bob["username"]}, headers=auth(alice["token"])
    )
    assert resp.status_code == 409


def test_add_self_forbidden(client, make_user):
    alice = make_user()
    resp = client.post(
        "/contacts",
        json={"username": alice["username"]},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 400


def test_search_users_found(client, make_user):
    alice = make_user()
    bob = make_user()

    results = client.get(
        f"/users/search?q={bob['username']}", headers=auth(alice["token"])
    ).json()
    assert any(u["username"] == bob["username"] for u in results)


def test_search_requires_token(client, make_user):
    bob = make_user()
    resp = client.get(f"/users/search?q={bob['username']}")
    assert resp.status_code in (401, 403)


def test_block_contact(client, make_user):
    alice = make_user()
    bob = make_user()

    client.post(
        "/contacts", json={"username": bob["username"]}, headers=auth(alice["token"])
    )

    resp = client.post(f"/contacts/{bob['id']}/block", headers=auth(alice["token"]))
    assert resp.status_code == 204


def test_delete_contact(client, make_user):
    alice = make_user()
    bob = make_user()

    client.post(
        "/contacts", json={"username": bob["username"]}, headers=auth(alice["token"])
    )

    resp = client.delete(f"/contacts/{bob['id']}", headers=auth(alice["token"]))
    assert resp.status_code == 204

    contacts = client.get("/contacts", headers=auth(alice["token"])).json()
    assert not any(c["contact_user_id"] == bob["id"] for c in contacts)
