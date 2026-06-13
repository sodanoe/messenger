"""
Тесты: logout (refresh-токен), rate limiting, WS-тикет.
"""


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_logout_clears_cookie(client, make_user):
    alice = make_user()

    login = client.post(
        "/auth/login",
        json={"username": alice["username"], "password": alice["password"]},
    )
    assert login.status_code == 200
    refresh_cookie = login.cookies.get("refresh_token")
    assert refresh_cookie, "refresh_token cookie не установлен после login"

    # Logout — передаём куку через заголовок
    logout = client.post(
        "/auth/logout",
        headers={"Cookie": f"refresh_token={refresh_cookie}"},
    )
    assert logout.status_code == 204

    # Refresh с отозванным токеном → 401
    refresh_resp = client.post(
        "/auth/refresh",
        headers={"Cookie": f"refresh_token={refresh_cookie}"},
    )
    assert refresh_resp.status_code == 401, (
        "Refresh-токен должен быть инвалидирован после logout"
    )


def test_logout_without_cookie_is_graceful(client):
    """Logout без токена не должен падать с 500 — просто 204."""
    resp = client.post("/auth/logout")
    assert resp.status_code == 204


def test_refresh_without_cookie_returns_401(client):
    resp = client.post("/auth/refresh")
    assert resp.status_code == 401


def test_login_rate_limit(client, make_user, redis_client):
    """
    6+ неверных попыток с одного IP → 429 Too Many Requests.
    Лимит: 5 попыток / 60 сек.

    Ключ login:attempts:{ip} чистится в конце теста через redis_client,
    чтобы не блокировать /auth/login для тестов, выполняющихся после.
    """
    alice = make_user()

    last_status = None
    try:
        for i in range(7):
            resp = client.post(
                "/auth/login",
                json={"username": alice["username"], "password": "wrong_password_!!!"},
            )
            last_status = resp.status_code
            if resp.status_code == 429:
                break

        assert last_status == 429, (
            f"Ожидали 429 после 6 попыток, получили {last_status}"
        )
    finally:
        for key in redis_client.scan_iter("login:attempts:*"):
            redis_client.delete(key)


def test_ws_ticket_requires_auth(client):
    """Без access-токена WS-тикет не выдаётся."""
    resp = client.post("/auth/ws/ticket")
    assert resp.status_code in (401, 403)


def test_ws_ticket_issued_to_authed_user(client, make_user):
    """Авторизованный пользователь получает тикет."""
    alice = make_user()
    resp = client.post("/auth/ws/ticket", headers=auth(alice["token"]))
    assert resp.status_code == 200
    data = resp.json()
    assert "ticket" in data
    assert len(data["ticket"]) == 32  # secrets.token_hex(16)


def test_refresh_tokens_independent_per_session(client, make_user):
    """Два логина (две "сессии"/устройства) должны давать разные
    refresh-токены, и logout одной сессии не должен инвалидировать
    refresh-токен другой.

    Регрессия для бага: _redis_refresh_key использовал token[:16],
    который одинаков для любого HS256 JWT (общий заголовок) — все
    refresh-токены юзера попадали в один Redis-ключ, и logout с
    одного устройства "отзывал" сессии всех остальных.
    """
    alice = make_user()

    login1 = client.post(
        "/auth/login",
        json={"username": alice["username"], "password": alice["password"]},
    )
    assert login1.status_code == 200
    refresh1 = login1.cookies.get("refresh_token")

    login2 = client.post(
        "/auth/login",
        json={"username": alice["username"], "password": alice["password"]},
    )
    assert login2.status_code == 200
    refresh2 = login2.cookies.get("refresh_token")

    assert refresh1 and refresh2
    assert refresh1 != refresh2, "Два логина дали одинаковый refresh-токен"

    # Логаут сессии 1
    logout1 = client.post(
        "/auth/logout", headers={"Cookie": f"refresh_token={refresh1}"}
    )
    assert logout1.status_code == 204

    # Сессия 1 теперь невалидна
    r1 = client.post("/auth/refresh", headers={"Cookie": f"refresh_token={refresh1}"})
    assert r1.status_code == 401

    # Сессия 2 должна остаться рабочей
    r2 = client.post("/auth/refresh", headers={"Cookie": f"refresh_token={refresh2}"})
    assert r2.status_code == 200, (
        "Logout одной сессии инвалидировал refresh-токен другой — "
        "вернулась коллизия ключей в Redis"
    )
