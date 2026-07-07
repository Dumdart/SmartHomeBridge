from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from smart_home_inference.exceptions import (
    ImageTooLargeError,
    InferenceExecutionError,
    InvalidImageError,
    ModelUnavailableError,
)
from smart_home_inference.registry import ModelRegistry, default_model_registry


def create_app(registry: ModelRegistry | None = None) -> Starlette:
    model_registry = registry or default_model_registry()

    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def ready(_request: Request) -> JSONResponse:
        models = {}
        ready_count = 0
        for identifier in model_registry.identifiers():
            model = model_registry.get(identifier)
            is_ready, detail = await run_in_threadpool(model.ready)
            models[identifier] = {"ready": is_ready, "detail": detail}
            if is_ready:
                ready_count += 1

        status_code = 200 if ready_count == len(models) else 503
        return JSONResponse(
            {"ready": ready_count == len(models), "models": models},
            status_code=status_code,
        )

    async def models(_request: Request) -> JSONResponse:
        return JSONResponse({"models": model_registry.identifiers()})

    async def infer_chicken_threat(request: Request) -> JSONResponse:
        return await _infer(request, model_registry, "chicken-threat")

    routes = [
        Route("/health", health, methods=["GET"]),
        Route("/ready", ready, methods=["GET"]),
        Route("/v1/models", models, methods=["GET"]),
        Route("/v1/chicken-threat/infer", infer_chicken_threat, methods=["POST"]),
        Route(
            "/v1/models/chicken-threat/infer",
            infer_chicken_threat,
            methods=["POST"],
        ),
    ]
    return Starlette(routes=routes)


app = create_app()


async def _infer(
    request: Request,
    registry: ModelRegistry,
    identifier: str,
) -> JSONResponse:
    content_type = request.headers.get("content-type", "")
    if content_type.split(";", 1)[0].strip().lower() != "image/jpeg":
        return JSONResponse(
            {"error": "unsupported_content_type", "detail": "Content-Type must be image/jpeg."},
            status_code=415,
        )

    try:
        model = registry.get(identifier)
        image_bytes = await request.body()
        frame = await run_in_threadpool(model.infer, image_bytes)
    except InvalidImageError as exc:
        return JSONResponse(
            {"error": "invalid_image", "detail": str(exc)},
            status_code=400,
        )
    except ImageTooLargeError as exc:
        return JSONResponse(
            {"error": "image_too_large", "detail": str(exc)},
            status_code=413,
        )
    except ModelUnavailableError as exc:
        return JSONResponse(
            {"error": "model_unavailable", "detail": str(exc)},
            status_code=503,
        )
    except InferenceExecutionError as exc:
        return JSONResponse(
            {"error": "inference_failed", "detail": str(exc)},
            status_code=500,
        )

    return JSONResponse(frame.to_dict())
