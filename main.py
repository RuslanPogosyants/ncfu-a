# Compatibility entrypoint — actual app lives in app/main.py
# Этот файл сохранён для совместимости с Dockerfile (CMD uvicorn main:app ...)
# и прямым запуском `python main.py`.
from app.main import app  # noqa: F401

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
