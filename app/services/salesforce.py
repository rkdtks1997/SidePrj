# app/services/interface_service.py

from app.models.interfaceData import Interface_In
from app.utils.commonutil import get_salesforce_token, sf_get, sf_post

def create_interface(data: Interface_In):

    token_data = get_salesforce_token()

    access_token = token_data["access_token"]
    instance_url = token_data["instance_url"]
    # payload 구성
    payload = {
        "FirstName__c": data.first_name,
        "LastName__c": data.last_name,
        "Company__c": data.company
    }

    # describe 테스트 (optional)
    try:
        res = sf_get("sobjects/InterfaceData__c/describe", access_token, instance_url)
        print("Describe:", res.status_code)
    except Exception as e:
        print("Describe failed:", e)

    # POST 데이터 생성
    res = sf_post("sobjects/InterfaceData__c", payload, access_token, instance_url)
    print("res",res)
    return res.json()

def send_to_salesforce(path: str, payload: dict):
    """Salesforce에 POST 요청을 보내는 공통 함수"""
    try:
        token_data = get_salesforce_token()
        access_token = token_data["access_token"]
        instance_url = token_data["instance_url"]

        # 내부 Salesforce POST 유틸 사용
        response = sf_post(path, payload, access_token, instance_url)
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"[Salesforce API Error] {str(e)}")