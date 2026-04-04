"""
Smoke-тест Step 5: Profile + Hardening
Запуск: pytest tests/test_smoke_step5.py -v
Требует: uvicorn app.main:app на localhost:8000
"""

import uuid

import httpx
import pytest

BASE = "http://localhost:8000"
RUN = uuid.uuid4().hex[:6]
state: dict = {}


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=10) as c:
        yield c


# ════════════════════════════════════════════════════════════════════════════
#  Setup
# ════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module", autouse=True)
def setup(client):
    """Admin + alice + bob + carol. Alice↔Bob contacts. Alice in group."""
    resp = client.post(
        "/auth/login", json={"username": "admin", "password": "adminpass"}
    )
    assert resp.status_code == 200
    state["admin_token"] = resp.json()["access_token"]

    for name_key, token_key, uid_key in [
        (f"s5_alice_{RUN}", "token_a", "uid_a"),
        (f"s5_bob_{RUN}", "token_b", "uid_b"),
        (f"s5_carol_{RUN}", "token_c", "uid_c"),
    ]:
        inv = client.post("/auth/invite", headers=auth_headers(state["admin_token"]))
        code = inv.json()["code"]
        reg = client.post(
            "/auth/register",
            json={
                "username": name_key,
                "password": "password123",
                "invite_code": code,
            },
        )
        assert reg.status_code == 200, f"Register {name_key}: {reg.text}"
        state[token_key] = reg.json()["access_token"]
        me = client.get("/users/me", headers=auth_headers(state[token_key]))
        state[uid_key] = me.json()["id"]

    # Alice ↔ Bob contacts
    r = client.post(
        "/contacts",
        json={"username": f"s5_bob_{RUN}"},
        headers=auth_headers(state["token_a"]),
    )
    assert r.status_code == 201

    # Alice sends Bob a message
    r = client.post(
        f"/messages/{state['uid_b']}",
        json={"content": "test message"},
        headers=auth_headers(state["token_a"]),
    )
    assert r.status_code == 201

    # Alice creates group, invites Bob
    g = client.post(
        "/groups",
        json={"name": f"S5Group_{RUN}"},
        headers=auth_headers(state["token_a"]),
    )
    assert g.status_code == 201
    state["group_id"] = g.json()["id"]
    client.post(
        f"/groups/{state['group_id']}/invite",
        json={"username": f"s5_bob_{RUN}"},
        headers=auth_headers(state["token_a"]),
    )

    print(
        f"\n  RUN={RUN}  alice={state['uid_a']}  bob={state['uid_b']}  carol={state['uid_c']}"
    )


# ════════════════════════════════════════════════════════════════════════════
#  1. GET /users/me — корректный профиль без password_hash
# ════════════════════════════════════════════════════════════════════════════


def test_1_get_me_no_password_hash(client):
    resp = client.get("/users/me", headers=auth_headers(state["token_a"]))
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "username" in data
    assert "last_seen" in data
    assert "password_hash" not in data, "password_hash не должен утекать!"
    assert "password" not in data


# ════════════════════════════════════════════════════════════════════════════
#  2. Изоляция сообщений: Alice не видит чужие переписки
# ════════════════════════════════════════════════════════════════════════════


def test_2_message_isolation(client):
    # Carol пытается прочитать переписку Alice↔Bob — нет контакта → 403
    resp = client.get(
        f"/messages/{state['uid_b']}", headers=auth_headers(state["token_c"])
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


# ════════════════════════════════════════════════════════════════════════════
#  3. Блокировка: Bob пишет Alice после блока → 403
# ════════════════════════════════════════════════════════════════════════════


def test_3_blocked_user_cannot_message(client):
    # Alice блокирует Bob
    resp = client.post(
        f"/contacts/{state['uid_b']}/block", headers=auth_headers(state["token_a"])
    )
    assert resp.status_code == 204

    # Bob пытается написать Alice
    resp2 = client.post(
        f"/messages/{state['uid_a']}",
        json={"content": "unblock me"},
        headers=auth_headers(state["token_b"]),
    )
    assert (
        resp2.status_code == 403
    ), f"Expected 403 after block, got {resp2.status_code}"


# ════════════════════════════════════════════════════════════════════════════
#  4. Non-member не может читать group messages
# ════════════════════════════════════════════════════════════════════════════


def test_4_non_member_group_access_denied(client):
    resp = client.get(
        f"/groups/{state['group_id']}/messages", headers=auth_headers(state["token_c"])
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    resp2 = client.get(
        f"/groups/{state['group_id']}/members", headers=auth_headers(state["token_c"])
    )
    assert resp2.status_code == 403


# ════════════════════════════════════════════════════════════════════════════
#  5. Истёкший / невалидный JWT → 401/403 на любом эндпойнте
# ════════════════════════════════════════════════════════════════════════════


def test_5_invalid_jwt_rejected(client):
    bad = {"Authorization": "Bearer totally.invalid.token"}
    endpoints = [
        ("GET", "/users/me"),
        ("GET", "/contacts"),
        ("GET", f"/messages/{state['uid_b']}"),
        ("GET", "/groups"),
    ]
    for method, path in endpoints:
        resp = client.request(method, path, headers=bad)
        assert resp.status_code in (
            401,
            403,
        ), f"{method} {path}: Expected 401/403, got {resp.status_code}"


# ════════════════════════════════════════════════════════════════════════════
#  6. Unauthenticated access → 401/403 (без токена вообще)
# ════════════════════════════════════════════════════════════════════════════


def test_6_no_token_rejected(client):
    endpoints = [
        ("GET", "/users/me"),
        ("GET", "/contacts"),
        ("GET", "/groups"),
        ("GET", f"/messages/{state['uid_b']}"),
        ("GET", f"/users/search?q=test"),
    ]
    for method, path in endpoints:
        resp = client.request(method, path)
        assert resp.status_code in (
            401,
            403,
        ), f"{method} {path}: Expected 401/403 without token, got {resp.status_code}"


# ════════════════════════════════════════════════════════════════════════════
#  7. Admin endpoint без admin прав → 403
# ════════════════════════════════════════════════════════════════════════════


def test_7_non_admin_cannot_generate_invite(client):
    resp = client.post("/auth/invite", headers=auth_headers(state["token_a"]))
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"


# ════════════════════════════════════════════════════════════════════════════
#  8. DELETE /users/me — полное удаление аккаунта
# ════════════════════════════════════════════════════════════════════════════


def test_8_delete_account(client):
    # Регистрируем временного пользователя
    inv = client.post("/auth/invite", headers=auth_headers(state["admin_token"]))
    code = inv.json()["code"]
    reg = client.post(
        "/auth/register",
        json={
            "username": f"s5_doomed_{RUN}",
            "password": "password123",
            "invite_code": code,
        },
    )
    assert reg.status_code == 200
    doomed_token = reg.json()["access_token"]
    doomed_id_resp = client.get("/users/me", headers=auth_headers(doomed_token))
    doomed_id = doomed_id_resp.json()["id"]

    # Добавляем контакт к Alice чтобы создать данные
    inv2 = client.post("/auth/invite", headers=auth_headers(state["admin_token"]))
    code2 = inv2.json()["code"]
    reg2 = client.post(
        "/auth/register",
        json={
            "username": f"s5_friend_{RUN}",
            "password": "password123",
            "invite_code": code2,
        },
    )
    friend_token = reg2.json()["access_token"]
    client.post(
        "/contacts",
        json={"username": f"s5_friend_{RUN}"},
        headers=auth_headers(doomed_token),
    )
    client.post(
        f"/messages/{reg2.json().get('id', doomed_id)}",
        json={"content": "bye"},
        headers=auth_headers(doomed_token),
    )

    # Удаляем аккаунт
    resp = client.delete("/users/me", headers=auth_headers(doomed_token))
    assert resp.status_code == 204, f"Delete account failed: {resp.text}"

    # Старый токен больше не работает
    resp2 = client.get("/users/me", headers=auth_headers(doomed_token))
    assert resp2.status_code in (
        401,
        403,
    ), f"Token should be invalid after deletion, got {resp2.status_code}"


# ════════════════════════════════════════════════════════════════════════════
#  9. CASCADE: контакты и сообщения удалённого юзера исчезают
# ════════════════════════════════════════════════════════════════════════════


def test_9_cascade_wipe(client):
    """
    Carol регистрируется, добавляет Bob в контакты, шлёт сообщение,
    потом удаляет аккаунт.
    Bob не должен видеть Carol в контактах.
    """
    # Регистрируем Carol2
    inv = client.post("/auth/invite", headers=auth_headers(state["admin_token"]))
    code = inv.json()["code"]
    reg = client.post(
        "/auth/register",
        json={
            "username": f"s5_carol2_{RUN}",
            "password": "password123",
            "invite_code": code,
        },
    )
    assert reg.status_code == 200
    carol2_token = reg.json()["access_token"]

    # Carol2 добавляет Bob в контакты
    # Сначала Bob должен добавить Carol2 (нет — используем другой подход:
    # создаём пару через add_contact от carol2)
    r = client.post(
        "/contacts",
        json={"username": f"s5_bob_{RUN}"},
        headers=auth_headers(carol2_token),
    )
    # Может быть 201 или 409 если уже есть
    assert r.status_code in (201, 409)

    # Получаем carol2_id до удаления
    carol2_id_resp = client.get("/users/me", headers=auth_headers(carol2_token))
    assert carol2_id_resp.status_code == 200
    carol2_id = carol2_id_resp.json()["id"]

    # Carol2 удаляет аккаунт
    resp = client.delete("/users/me", headers=auth_headers(carol2_token))
    assert resp.status_code == 204

    # Bob не должен видеть Carol2 в контактах
    contacts_after = client.get(
        "/contacts", headers=auth_headers(state["token_b"])
    ).json()
    after_ids = [c["contact_user_id"] for c in contacts_after]
    assert (
        carol2_id not in after_ids
    ), f"Carol2 (id={carol2_id}) всё ещё в контактах Bob после удаления"


# ════════════════════════════════════════════════════════════════════════════
#  10. Поиск не возвращает удалённых пользователей
# ════════════════════════════════════════════════════════════════════════════


def test_10_deleted_user_not_in_search(client):
    # Регистрируем временного пользователя с уникальным именем
    inv = client.post("/auth/invite", headers=auth_headers(state["admin_token"]))
    code = inv.json()["code"]
    ghost_name = f"s5_ghost_{RUN}"
    reg = client.post(
        "/auth/register",
        json={
            "username": ghost_name,
            "password": "password123",
            "invite_code": code,
        },
    )
    ghost_token = reg.json()["access_token"]

    # Убеждаемся что юзер находится
    search_before = client.get(
        f"/users/search?q={ghost_name}", headers=auth_headers(state["token_a"])
    ).json()
    assert any(
        u["username"] == ghost_name for u in search_before
    ), "Ghost должен находиться до удаления"

    # Удаляем
    client.delete("/users/me", headers=auth_headers(ghost_token))

    # Теперь не должен находиться
    search_after = client.get(
        f"/users/search?q={ghost_name}", headers=auth_headers(state["token_a"])
    ).json()
    assert not any(
        u["username"] == ghost_name for u in search_after
    ), f"Ghost всё ещё в поиске после удаления: {search_after}"
