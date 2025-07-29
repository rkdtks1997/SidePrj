from fastapi import APIRouter

router = APIRouter()

@router.api_route("/healthz", methods=["GET", "HEAD"])
async def healthz():
    return {"status": "ok"}
