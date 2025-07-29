
from fastapi import APIRouter, Request
from app.models.lead import LeadIn
from app.services.salesforce import get_leads, create_lead, get_salesforce_token
# Bearer 토큰 발급용 엔드포인트
@router.get("/get-bearer-token")
def get_bearer_token():
    token_data = get_salesforce_token()
    return {
        "access_token": token_data.get("access_token"),
        "instance_url": token_data.get("instance_url"),
        "raw": token_data
    }

router = APIRouter()

@router.get("/leads")
def read_leads():
    return get_leads()

@router.post("/create-lead")
def post_lead(data: LeadIn):
    return create_lead(data)


# Salesforce에서 Render로 POST 요청이 오면, 받은 데이터를 다시 Salesforce Lead로 생성
@router.post("/sf-lead-proxy")
async def sf_lead_proxy(request: Request):
    body = await request.json()
    # body에서 필요한 필드 추출 (Salesforce에서 오는 데이터 포맷에 맞게 수정 필요)
    first_name = body.get("first_name") or body.get("FirstName")
    last_name = body.get("last_name") or body.get("LastName")
    company = body.get("company") or body.get("Company", "Unknown Company")
    lead_in = LeadIn(first_name=first_name, last_name=last_name, company=company)
    result = create_lead(lead_in)
    return {"status": "created", "result": result}
