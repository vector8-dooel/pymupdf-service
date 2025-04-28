from fastapi import APIRouter

# one router, no prefix – we register the exact paths we need
health_router = APIRouter()

@health_router.get(
    "/health",
    description="Status of the service",
)
@health_router.get(
    "/healthz",              # k8s default
    include_in_schema=False  # hide from OpenAPI if you like
)
def get_status():
    """Simple liveness/readiness reply."""
    return {"status": "up"}
