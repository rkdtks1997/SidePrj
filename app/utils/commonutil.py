# app/utils/salesforce_utils.py
from fastapi import APIRouter, HTTPException
import os
import requests

SF_CLIENT_ID = os.environ.get('SF_CLIENT_ID')
SF_CLIENT_SECRET = os.environ.get('SF_CLIENT_SECRET')
SF_LOGIN_URL = os.environ.get('SF_LOGIN_URL')
SF_API_VERSION = os.environ.get('SF_API_VERSION')
API_KEY = os.environ.get('API_KEY')
SFDC_URL = os.environ.get('SFDC_URL')


def get_salesforce_token():
    """Bearer 토큰 또는 OAuth2 방식으로 Salesforce 인증"""

    if API_KEY:
        return {
            "access_token": API_KEY,
            "instance_url": SFDC_URL
        }

    url = f"{SF_LOGIN_URL}/services/oauth2/token"

    payload = {
        "grant_type": "client_credentials",
        "client_id": SF_CLIENT_ID,
        "client_secret": SF_CLIENT_SECRET
    }

    res = requests.post(url, data=payload)
    res.raise_for_status()
    return res.json()


def get_headers(access_token: str):
    return {
        "Authorization": access_token,
        "Content-Type": "application/json"
    }


def sf_get(path: str, access_token: str, instance_url: str):
    """GET 요청"""
    url = f"{instance_url}/services/data/{SF_API_VERSION}/{path.lstrip('/')}"
    print("url", url)

    headers = get_headers(access_token)
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res


def sf_post(path: str, payload: dict, access_token: str, instance_url: str):
    """POST 요청"""
    url = f"{instance_url}/services/data/{SF_API_VERSION}/{path.lstrip('/')}"
    headers = get_headers(access_token)
    res = requests.post(url, json=payload, headers=headers)
    res.raise_for_status()
    return res

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
    