from fastapi import APIRouter

router = APIRouter()

@router.post("/healthz")
async def healthz_proxy():
    return {"commentStr": "health Check Success"}