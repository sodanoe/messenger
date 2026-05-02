"""
Тесты: бизнес-логика — блокировка, повторное добавление контакта,
двойное удаление аккаунта, выход из группы.
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
    return resp.json()["id"]


def test_block_is_mutual(client, make_user):
    """
    Alice блокирует Bob'а — оба не могут писать друг другу.
    Блокировка симметрична: инициатор тоже теряет возможность писать.
    """
    alice = make_user()
    bob = make_user()
    chat_id = _make_dm(client, alice, bob)

    # Alice блокирует Bob'а
    client.post(f"/contacts/{bob['id']}/block", headers=auth(alice["token"]))

    # Bob пишет Alice — 403
    bob_resp = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "can bob write?"},
        headers=auth(bob["token"]),
    )
    assert bob_resp.status_code == 403, "Bob должен быть заблокирован"

    # Alice пишет Bob'у — тоже 403, блокировка симметрична
    alice_resp = client.post(
        f"/chats/{chat_id}/messages",
        json={"content": "alice tries to write"},
        headers=auth(alice["token"]),
    )
    assert alice_resp.status_code == 403, (
        "После блокировки инициатор тоже не может писать"
    )


def test_readd_contact_after_delete(client, make_user):
    """Удалить контакт → добавить снова → успех (не 409)."""
    alice = make_user()
    bob = make_user()

    # Добавляем
    add = client.post(
        "/contacts", json={"username": bob["username"]}, headers=auth(alice["token"])
    )
    assert add.status_code == 201

    # Удаляем
    delete = client.delete(f"/contacts/{bob['id']}", headers=auth(alice["token"]))
    assert delete.status_code == 204

    # Снова добавляем — не должно быть 409
    readd = client.post(
        "/contacts", json={"username": bob["username"]}, headers=auth(alice["token"])
    )
    assert readd.status_code == 201, f"Повторное добавление провалилось: {readd.text}"


def test_double_delete_account(client, make_user):
    """
    DELETE /users/me дважды.
    Первый — 204.
    Второй — 401 или 404 (токен уже невалиден).
    """
    alice = make_user()

    resp1 = client.delete("/users/me", headers=auth(alice["token"]))
    assert resp1.status_code == 204

    resp2 = client.delete("/users/me", headers=auth(alice["token"]))
    assert resp2.status_code in (401, 404), (
        f"Повторное удаление должно вернуть 401/404, получили {resp2.status_code}"
    )


def test_leave_group(client, make_user):
    """Bob выходит из группы → больше не может читать сообщения."""
    alice = make_user()
    bob = make_user()

    group = client.post(
        "/chats/group",
        json={"name": "LeaveTest", "member_ids": [bob["id"]]},
        headers=auth(alice["token"]),
    ).json()
    gid = group["id"]

    # Bob выходит (удаляет себя из участников)
    leave = client.delete(
        f"/chats/{gid}/members/{bob['id']}",
        headers=auth(bob["token"]),
    )
    assert leave.status_code == 204

    # Bob не может читать историю
    history = client.get(f"/chats/{gid}/messages", headers=auth(bob["token"]))
    assert history.status_code == 403

    # Cleanup
    client.delete(f"/chats/{gid}", headers=auth(alice["token"]))


def test_admin_can_kick_member(client, make_user):
    """Admin (Alice) выкидывает Bob'а из группы."""
    alice = make_user()
    bob = make_user()

    group = client.post(
        "/chats/group",
        json={"name": "KickTest", "member_ids": [bob["id"]]},
        headers=auth(alice["token"]),
    ).json()
    gid = group["id"]

    kick = client.delete(
        f"/chats/{gid}/members/{bob['id']}",
        headers=auth(alice["token"]),
    )
    assert kick.status_code == 204

    members = client.get(f"/chats/{gid}/members", headers=auth(alice["token"])).json()
    ids = [m["id"] for m in members["members"]]
    assert bob["id"] not in ids

    # Cleanup
    client.delete(f"/chats/{gid}", headers=auth(alice["token"]))


def test_member_cannot_kick_other_member(client, make_user):
    """Обычный участник не может выкинуть другого — только admin."""
    alice = make_user()
    bob = make_user()
    carol = make_user()

    group = client.post(
        "/chats/group",
        json={"name": "NoKick", "member_ids": [bob["id"], carol["id"]]},
        headers=auth(alice["token"]),
    ).json()
    gid = group["id"]

    kick = client.delete(
        f"/chats/{gid}/members/{carol['id']}",
        headers=auth(bob["token"]),
    )
    assert kick.status_code == 403

    # Cleanup
    client.delete(f"/chats/{gid}", headers=auth(alice["token"]))


def test_add_member_to_group(client, make_user):
    """Admin добавляет нового участника в группу."""
    alice = make_user()
    bob = make_user()
    carol = make_user()

    group = client.post(
        "/chats/group",
        json={"name": "AddMember", "member_ids": [bob["id"]]},
        headers=auth(alice["token"]),
    ).json()
    gid = group["id"]

    add = client.post(
        f"/chats/{gid}/members",
        json={"user_id": carol["id"]},
        headers=auth(alice["token"]),
    )
    assert add.status_code == 201

    members = client.get(f"/chats/{gid}/members", headers=auth(alice["token"])).json()
    ids = [m["id"] for m in members["members"]]
    assert carol["id"] in ids

    # Cleanup
    client.delete(f"/chats/{gid}", headers=auth(alice["token"]))
