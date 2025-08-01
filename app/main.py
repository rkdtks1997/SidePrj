from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.interseptor.ratelimiter import RateLimitMiddleware

from app.routes.interfaceData import router as interfaceData
from app.routes.healthCheck import router as healthCheck
from app.routes.publicApiData import router as publicApiData


import os

routers = [interfaceData, healthCheck,publicApiData]

# FastAPI 앱 객체 생성
app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Rate Limiting 인터셉터 등록
app.add_middleware(RateLimitMiddleware, max_requests=30, window_sec=60)

# 디버깅용 루트 엔드포인트
@app.get("/")
def root():
    return {
        "status": "ok",
        "env": {k: os.environ.get(k) for k in [
            "SF_CLIENT_ID", "SF_CLIENT_SECRET", "SF_LOGIN_URL", "SF_API_VERSION", "API_KEY", "SFDC_URL"
        ]}
    }

# 라우터 등록
for router in routers:
    app.include_router(router)
