import math
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from atlas.persistent_mvcc import PersistentMVCCStore


class PutRequest(BaseModel):
    value: Any

    @field_validator("value")
    @classmethod
    def validate_finite_numbers(cls, value: Any) -> Any:
        def check(item: Any) -> None:
            if isinstance(item, float) and not math.isfinite(item):
                raise ValueError("Non-finite numbers are not supported")
            if isinstance(item, dict):
                for nested in item.values():
                    check(nested)
            elif isinstance(item, (list, tuple)):
                for nested in item:
                    check(nested)

        check(value)
        return value


def _make_json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {key: _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, Exception):
        return str(value)
    return value


async def _validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": _make_json_safe(exc.errors())},
    )



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

    app.add_exception_handler(
        RequestValidationError, _validation_error_handler
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
