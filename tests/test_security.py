"""
Тесты: безопасность — 401/403, изоляция данных, права доступа.
"""

import pytest


def auth(token):
    return {"Authorization": f"Bearer {token}"}


PROTECTED_ENDPOINTS = [
    ("GET", "/users/me"),
    ("GET", "/contacts"),
    ("GET", "/chats/"),
    ("GET", "/users/search?q=test"),
]


@pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
def test_no_token_returns_401(client, method, path):
    resp = client.request(method, path)
    assert resp.status_code in (401, 403), (
        f"{method} {path}: ожидали 401/403, получили {resp.status_code}"
    )


@pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
def test_bad_token_returns_401(client, method, path):
    resp = client.request(
        method, path, headers={"Authorization": "Bearer bad.token.here"}
    )
    assert resp.status_code in (401, 403), (
        f"{method} {path}: ожидали 401/403, получили {resp.status_code}"
    )


def test_non_admin_cannot_create_invite(client, make_user):
    alice = make_user()
    resp = client.post("/auth/invite", headers=auth(alice["token"]))
    assert resp.status_code == 403


def test_message_isolation(client, make_user):
    """Carol — не участник чата Alice↔Bob — не может читать историю."""
    alice = make_user()
    bob = make_user()
    carol = make_user()

    client.post(
        "/contacts", json={"username": bob["username"]}, headers=auth(alice["token"])
    )
    chat = client.post(
        "/chats/direct", json={"user_id": bob["id"]}, headers=auth(alice["token"])
    ).json()

    resp = client.get(f"/chats/{chat['id']}/messages", headers=auth(carol["token"]))
    assert resp.status_code == 403


def test_blocked_user_cannot_message(client, make_user):
    alice = make_user()
    bob = make_user()

    client.post(
        "/contacts", json={"username": bob["username"]}, headers=auth(alice["token"])
    )
    chat = client.post(
        "/chats/direct", json={"user_id": bob["id"]}, headers=auth(alice["token"])
    ).json()

    # Alice блокирует Bob'а
    client.post(f"/contacts/{bob['id']}/block", headers=auth(alice["token"]))

    # Bob пытается написать — 403
    resp = client.post(
        f"/chats/{chat['id']}/messages",
        json={"content": "unblock me"},
        headers=auth(bob["token"]),
    )
    assert resp.status_code == 403


def test_non_member_cannot_send_to_group(client, make_user):
    alice = make_user()
    bob = make_user()
    carol = make_user()

    group = client.post(
        "/chats/group",
        json={"name": "Exclusive", "member_ids": [bob["id"]]},
        headers=auth(alice["token"]),
    ).json()
    gid = group["id"]

    resp = client.post(
        f"/chats/{gid}/messages",
        json={"content": "intruder"},
        headers=auth(carol["token"]),
    )
    assert resp.status_code == 403

    # Cleanup
    client.delete(f"/chats/{gid}", headers=auth(alice["token"]))
