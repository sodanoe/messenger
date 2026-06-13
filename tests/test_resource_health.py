"""
Smoke-тесты на аномальную фоновую нагрузку.

Цель — поймать "тихие" busy-loop'ы в фоновых задачах (pubsub listener,
presence heartbeat и т.п.), которые не падают и не видны в обычных
функциональных тестах, но жрут CPU 24/7 независимо от активности
пользователей.

Регрессия: pubsub.ping() в idle-ветке get_message(timeout=30) создавал
busy-loop ~96 PING/сек — приложение в простое держало 500% CPU.
"""

import time


def test_idle_redis_ops_per_sec_is_low(redis_client):
    """В простое Redis не должен видеть постоянный поток команд от
    фоновых задач приложения (pubsub listener и т.п.)."""
    samples = []
    for _ in range(3):
        time.sleep(1)
        info = redis_client.info("stats")
        samples.append(info["instantaneous_ops_per_sec"])

    samples.sort()
    median = samples[1]  # медиана сглаживает случайный всплеск от соседних тестов

    assert median < 15, (
        f"instantaneous_ops_per_sec={samples} (медиана={median}) — "
        f"похоже на busy-loop в фоновой задаче. Норма для простоя: "
        f"однозначное число, обычно 0-2."
    )


def test_idle_pubsub_ping_rate_is_near_zero(redis_client):
    """
    Точечный regression-guard конкретно для бага с pubsub.ping():
    PONG приходит как pub/sub-сообщение и "съедается" следующим
    get_message(), что превращает 30-секундный wait в busy-loop.

    Если этот тест когда-нибудь упадёт — проверь app/ws/pubsub.py:
    не появился ли там снова вызов pubsub.ping() / redis.ping()
    внутри idle-ветки слушателя.
    """
    before = redis_client.info("commandstats").get("cmdstat_ping", {}).get("calls", 0)
    time.sleep(5)
    after = redis_client.info("commandstats").get("cmdstat_ping", {}).get("calls", 0)

    rate = (after - before) / 5
    assert rate < 5, (
        f"PING: {rate:.1f}/сек за последние 5 сек (было {before} -> {after}). "
        f"Ожидалось <5/сек в простое — это сигнатура бага с pubsub busy-loop."
    )
