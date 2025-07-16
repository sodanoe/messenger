import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",  # Уровень логирования
        workers=1,  # Количество воркеров
        reload_dirs=["app"],
        access_log=True,  # Включить логи доступа
    )
