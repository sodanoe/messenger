"""
Тесты: создание и удаление чатов (direct + group), доступ участников.
"""


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_create_direct_chat(client, make_user):
    alice = make_user()
    bob = make_user()

    resp = client.post(
        "/chats/direct",
        json={"user_id": bob["id"]},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "direct"
    assert "id" in data


def test_create_direct_chat_idempotent(client, make_user):
    """Повторный запрос возвращает тот же чат, не создаёт новый."""
    alice = make_user()
    bob = make_user()

    r1 = client.post(
        "/chats/direct", json={"user_id": bob["id"]}, headers=auth(alice["token"])
    )
    r2 = client.post(
        "/chats/direct", json={"user_id": bob["id"]}, headers=auth(alice["token"])
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


def test_create_group_chat(client, make_user):
    alice = make_user()
    bob = make_user()

    resp = client.post(
        "/chats/group",
        json={"name": "Test Group", "member_ids": [bob["id"]]},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["type"] == "group"
    assert data["name"] == "Test Group"

    # Cleanup: Alice (admin группы) удаляет её
    client.delete(f"/chats/{data['id']}", headers=auth(alice["token"]))


def test_list_chats_contains_created(client, make_user):
    alice = make_user()
    bob = make_user()

    chat = client.post(
        "/chats/direct", json={"user_id": bob["id"]}, headers=auth(alice["token"])
    ).json()

    chats = client.get("/chats/", headers=auth(alice["token"])).json()["chats"]
    assert any(c["id"] == chat["id"] for c in chats)


def test_delete_group_by_admin(client, make_user):
    alice = make_user()
    bob = make_user()

    group = client.post(
        "/chats/group",
        json={"name": "ToDelete", "member_ids": [bob["id"]]},
        headers=auth(alice["token"]),
    ).json()

    resp = client.delete(f"/chats/{group['id']}", headers=auth(alice["token"]))
    assert resp.status_code == 204

    chats = client.get("/chats/", headers=auth(alice["token"])).json()["chats"]
    assert not any(c["id"] == group["id"] for c in chats)


def test_delete_group_by_member_forbidden(client, make_user):
    alice = make_user()
    bob = make_user()

    group = client.post(
        "/chats/group",
        json={"name": "G", "member_ids": [bob["id"]]},
        headers=auth(alice["token"]),
    ).json()
    gid = group["id"]

    resp = client.delete(f"/chats/{gid}", headers=auth(bob["token"]))
    assert resp.status_code == 403

    # Cleanup
    client.delete(f"/chats/{gid}", headers=auth(alice["token"]))


def test_group_members_list(client, make_user):
    alice = make_user()
    bob = make_user()

    group = client.post(
        "/chats/group",
        json={"name": "MemberTest", "member_ids": [bob["id"]]},
        headers=auth(alice["token"]),
    ).json()
    gid = group["id"]

    members = client.get(f"/chats/{gid}/members", headers=auth(alice["token"])).json()
    ids = [m["id"] for m in members["members"]]
    assert alice["id"] in ids
    assert bob["id"] in ids

    # Alice должна быть admin
    alice_member = next(m for m in members["members"] if m["id"] == alice["id"])
    assert alice_member["role"] == "admin"

    # Cleanup
    client.delete(f"/chats/{gid}", headers=auth(alice["token"]))


def test_non_member_cannot_read_members(client, make_user):
    alice = make_user()
    bob = make_user()
    carol = make_user()

    group = client.post(
        "/chats/group",
        json={"name": "Private", "member_ids": [bob["id"]]},
        headers=auth(alice["token"]),
    ).json()
    gid = group["id"]

    resp = client.get(f"/chats/{gid}/members", headers=auth(carol["token"]))
    assert resp.status_code == 403

    # Cleanup
    client.delete(f"/chats/{gid}", headers=auth(alice["token"]))


def test_add_member_twice_returns_409(client, make_user):
    """Повторное добавление того же юзера в группу — 409, не 500."""
    alice = make_user()
    bob = make_user()
    carol = make_user()

    group = client.post(
        "/chats/group",
        json={"name": "DupMemberTest", "member_ids": [bob["id"]]},
        headers=auth(alice["token"]),
    )
    assert group.status_code == 201
    chat_id = group.json()["id"]

    first = client.post(
        f"/chats/{chat_id}/members",
        json={"user_id": carol["id"]},
        headers=auth(alice["token"]),
    )
    assert first.status_code == 201

    second = client.post(
        f"/chats/{chat_id}/members",
        json={"user_id": carol["id"]},
        headers=auth(alice["token"]),
    )
    assert second.status_code == 409

    client.delete(f"/chats/{chat_id}", headers=auth(alice["token"]))


def test_create_direct_chat_with_self_returns_400(client, make_user):
    """POST /chats/direct с user_id == себе — 400, не 500 и не чужой чат."""
    alice = make_user()

    resp = client.post(
        "/chats/direct",
        json={"user_id": alice["id"]},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 400


def test_create_direct_chat_with_self_returns_400_when_other_chats_exist(
    client, make_user
):
    """Та же проверка, но когда у Alice УЖЕ есть direct-чат с кем-то —
    раньше тривиальный self-join находил этот чужой чат как
    'существующий' и возвращал его id вместо ошибки."""
    alice = make_user()
    bob = make_user()

    client.post(
        "/contacts", json={"username": bob["username"]}, headers=auth(alice["token"])
    )
    existing = client.post(
        "/chats/direct", json={"user_id": bob["id"]}, headers=auth(alice["token"])
    ).json()

    resp = client.post(
        "/chats/direct",
        json={"user_id": alice["id"]},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 400
    if resp.status_code == 201:
        assert resp.json()["id"] != existing["id"], (
            "Вернулся id чужого чата с Bob'ом вместо ошибки 'чат с самим собой'"
        )

    client.delete(f"/chats/{existing['id']}", headers=auth(alice["token"]))


def test_create_direct_chat_with_nonexistent_user_returns_404(client, make_user):
    """POST /chats/direct с несуществующим user_id — 404, не 500."""
    alice = make_user()

    resp = client.post(
        "/chats/direct",
        json={"user_id": 99_999_999},
        headers=auth(alice["token"]),
    )
    assert resp.status_code == 404
