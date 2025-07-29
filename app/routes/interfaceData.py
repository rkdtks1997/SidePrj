from fastapi import APIRouter, Request
from app.models.interfaceData import Interface_In
from app.services.salesforce import create_interface, get_salesforce_token

router = APIRouter()

# Bearer 토큰 발급용 엔드포인트
@router.get("/get-bearer-token")
def get_bearer_token():
    token_data = get_salesforce_token()
    print("Token data:", token_data)  # 디버깅용 로그
    # 필요한 경우 토큰 데이터에서 특정 필드만 반환   
    return {
        "access_token": token_data.get("access_token"),
        "instance_url": token_data.get("instance_url"),
        "raw": token_data
    }

@router.post("/create-interfaceData")
def post_interfaceData(data: Interface_In):
    return create_interface(data)


# Salesforce에서 Render로 POST 요청이 오면, 받은 데이터를 다시 Salesforce Lead로 생성
@router.post("/sf-interfaceData-proxy")
async def sf_interface_proxy(request: Request):
    body = await request.json()
    print("Received body:", body)
    # body에서 필요한 필드 추출 (Salesforce에서 오는 데이터 포맷에 맞게 수정 필요)
    first_name = body.get("first_name")
    last_name = body.get("last_name")
    company = body.get("company")
    interface_in = Interface_In(first_name=first_name, last_name=last_name, company=company)
    result = create_interface(interface_in)
    print("Created interface Data:", result)
    
    return {"status": "created", "result": result}
