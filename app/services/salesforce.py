import os
import requests
from app.models.interfaceData import Interface_In

SF_CLIENT_ID = os.environ.get('SF_CLIENT_ID')
SF_CLIENT_SECRET = os.environ.get('SF_CLIENT_SECRET')

SF_LOGIN_URL = os.environ.get('SF_LOGIN_URL')
SF_API_VERSION = os.environ.get('SF_API_VERSION', 'v58.0')
API_KEY = os.environ.get('API_KEY')
SFDC_URL = os.environ.get('SFDC_URL')

# Salesforce 인증

def get_salesforce_token():
    # API_KEY를 Bearer 토큰으로 직접 사용하는 방식
    if API_KEY:
        return {
            "access_token": API_KEY,
            "instance_url": SFDC_URL  # 실제 인스턴스 URL 사용
        }
    # (추가) 필요시 기존 OAuth2 방식도 fallback으로 남겨둘 수 있음
    url = f"{SF_LOGIN_URL}/services/oauth2/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": SF_CLIENT_ID,
        "client_secret": SF_CLIENT_SECRET
    }
    res = requests.post(url, data=payload)
    res.raise_for_status()
    return res.json()

def create_interface(data: Interface_In):
    token_data = get_salesforce_token()
    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }
    instance_url = token_data["instance_url"]

    interfaceData_url = f"{instance_url}/services/data/{SF_API_VERSION}/sobjects/InterfaceData__c/"
    print("payload:", data)
    payload = {
        "FirstName": data.first_name,
        "LastName": data.last_name,
        "Company": data.company
    }

    test_url = f"{instance_url}/services/data/{SF_API_VERSION}/sobjects/InterfaceData__c/describe"
    test_res = requests.get(test_url, headers=headers)
    print("Test response:", test_res.status_code, test_res.text)

    print("Payload for lead creation:", payload)    
    print("lead_url:: ", interfaceData_url)    
    response = requests.post(interfaceData_url, json=payload, headers=headers)
    return response.json()
