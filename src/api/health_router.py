# Initialize the router
from fastapi import APIRouter

health_router = APIRouter(prefix="/health")


@health_router.get(
    path="",
    description="Status of the service",
)
def get_status():
    return {"status": "up"}
