from fastapi import APIRouter

router = APIRouter()

@router.get("/healthz")
async def healthz_proxy():
    return {"commentStr": "health Check Success"}