from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.interfaceData import router as interfaceData_router
from app.routes.healthCheck import router as healthCheck
import os


# Render, Heroku 등에서 uvicorn app.main:app --host=0.0.0.0 --port=$PORT 로 실행
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 디버그용 루트 엔드포인트
@app.get("/")
def root():
    return {
        "status": "ok",
        "env": {k: os.environ.get(k) for k in [
            "SF_CLIENT_ID", "SF_CLIENT_SECRET", "SF_LOGIN_URL", "SF_API_VERSION", "API_KEY", "SFDC_URL"
        ]}
    }

app.include_router(interfaceData_router)
app.include_router(healthCheck)
