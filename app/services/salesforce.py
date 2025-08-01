# app/services/interface_service.py

from app.models.interfaceData import Interface_In
from app.utils.commonutil import get_salesforce_token, sf_get, sf_post

def create_interface(data: Interface_In):
    print("스타트!!")
    token_data = get_salesforce_token()
    print("token_data",token_data)
    access_token = token_data["access_token"]
    instance_url = token_data["instance_url"]
    print("access_token",access_token)
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
