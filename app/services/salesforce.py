import os
import requests
from app.models.lead import LeadIn


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

# Lead 조회

def get_leads():
    token_data = get_salesforce_token()
    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }

    instance_url = token_data["instance_url"]
    query = "SELECT Id, FirstName, LastName, Company FROM Lead LIMIT 10"
    response = requests.get(
        f"{instance_url}/services/data/{SF_API_VERSION}/query",
        headers=headers,
        params={"q": query}
    )
    return response.json()

# Lead 생성

def create_lead(data: LeadIn):
    token_data = get_salesforce_token()
    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }
    instance_url = token_data["instance_url"]
    print("Token data:", token_data)  # 디버깅용 로그
    print("Headers for lead query:", headers)  # 디버깅용 로그 
    # Salesforce Lead 생성 API 호출

    lead_url = f"{instance_url}/services/data/{SF_API_VERSION}/sobjects/Lead/"
    payload = {
        "FirstName": data.first_name,
        "LastName": data.last_name,
        "Company": data.company
    }
    print("Payload for lead creation:", payload)    
    response = requests.post(lead_url, json=payload, headers=headers)
    return response.json()
