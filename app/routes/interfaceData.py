import requests
from fastapi import APIRouter, Request, HTTPException
from app.models.interfaceData import Interface_In
from app.services.salesforce import create_interface
from app.utils.commonutil import get_salesforce_token

router = APIRouter()

# ✅ Bearer 토큰 발급용 엔드포인트
@router.get("/get-bearer-token")
def get_bearer_token():
    try:
        token_data = get_salesforce_token()
        return {
            "access_token": token_data.get("access_token"),
            "instance_url": token_data.get("instance_url"),
            "raw": token_data
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"[Token Error] Salesforce 인증 실패: {str(e)}")


@router.post("/create-interfaceData")
def post_interface_data(data: Interface_In):
    try:
        return create_interface(data)
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"[Create Error] InterfaceData 생성 실패: {str(e)}")


@router.post("/sf-interfaceData-proxy")
async def sf_interface_proxy(request: Request):
    try:
        body = await request.json()
        print("Received body:", body)

        # 필수 필드 확인
        if not all(k in body for k in ("first_name", "last_name", "company")):
            raise HTTPException(status_code=400, detail="필수 필드 누락: first_name, last_name, company")

        interface_in = Interface_In(
            first_name=body["first_name"],
            last_name=body["last_name"],
            company=body["company"]
        )

        result = create_interface(interface_in)
        return {"status": "created", "result": result}

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"[Proxy Error] Salesforce API 오류: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"[Proxy Error] 처리 중 오류 발생: {str(e)}")
