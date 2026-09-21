import uvicorn
from app.config import settings

def main() -> None:
    host = settings.HOST
    port = settings.PORT
    docs_url = f"http://localhost:{port}/docs" if host in ("0.0.0.0", "127.0.0.1") else f"http://{host}:{port}/docs"
    print(f"Starting server on {host}:{port}")
    print(f"Test the APIs using the interactive Swagger UI at: {docs_url}")
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
    )

if __name__ == "__main__":
    main()
