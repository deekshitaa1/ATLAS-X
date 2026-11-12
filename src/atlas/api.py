from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from atlas.persistent_mvcc import PersistentMVCCStore


class PutRequest(BaseModel):
    value: Any


def create_app(data_dir: str | Path = "data/api_store") -> FastAPI:
    storage_path = Path(data_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.store = PersistentMVCCStore(storage_path)
        try:
            yield
        finally:
            app.state.store.close()

    app = FastAPI(
        title="ATLAS-X Storage API",
        version="0.1.0",
        description="REST API for the ATLAS-X persistent MVCC store.",
        lifespan=lifespan,
    )

    def get_store(request: Request) -> PersistentMVCCStore:
        return request.app.state.store

    @app.get("/health")
    def health(request: Request) -> dict[str, str]:
        get_store(request)
        return {"status": "healthy", "database": "ATLAS-X"}

    @app.put("/kv/{key}")
    def put_value(
        key: str,
        body: PutRequest,
        request: Request,
    ) -> dict[str, Any]:
        store = get_store(request)
        sequence = store.put(key, body.value)
        return {"key": key, "sequence": sequence, "status": "stored"}

    @app.get("/kv/{key}")
    def get_value(key: str, request: Request) -> dict[str, Any]:
        store = get_store(request)
        found, value = store.read_entry(key)
        if not found:
            raise HTTPException(status_code=404, detail="Key not found")
        return {"key": key, "value": value}

    @app.delete("/kv/{key}")
    def delete_value(key: str, request: Request) -> dict[str, str]:
        store = get_store(request)
        if not store.delete_existing(key):
            raise HTTPException(status_code=404, detail="Key not found")
        return {"key": key, "status": "deleted"}

    @app.get("/scan")
    def scan_values(
        request: Request,
        prefix: str = "",
    ) -> dict[str, Any]:
        return get_store(request).scan_prefix(prefix)

    return app


app = create_app()
