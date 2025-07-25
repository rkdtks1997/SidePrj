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
        "Authorization": f"Bearer {token_data['access_token']}",
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
        "Authorization": f"Bearer {token_data['access_token']}",
        "Content-Type": "application/json"
    }
    instance_url = token_data["instance_url"]
    lead_url = f"{instance_url}/services/data/{SF_API_VERSION}/sobjects/Lead/"
    payload = {
        "FirstName": data.first_name,
        "LastName": data.last_name,
        "Company": data.company
    }
    response = requests.post(lead_url, json=payload, headers=headers)
    return response.json()
