from fastapi import FastAPI

app = FastAPI(
    title="OpenShelf API",
    description="Backend foundation for the OpenShelf book discovery app.",
    version="0.1.0",
)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "OpenShelf backend is running."}


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "OpenShelf API",
        "message": "The backend foundation is ready for milestone 2.",
    }
