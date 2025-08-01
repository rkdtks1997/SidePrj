from fastapi import APIRouter, HTTPException
import requests
import os
from app.utils.commonutil import get_salesforce_token
from app.utils.commonutil import sf_post

router = APIRouter()

SUBWAY_API_KEY = os.environ.get("SUBWAY_API_KEY")
SUBWAY_URL = os.environ.get("SUBWAY_URL")

NEWS_CLIENTID = os.environ.get("NEWS_CLIENTID")
NEWS_SECRET = os.environ.get("SUBWAY_URL")
NEWS_URL = os.environ.get("NEWS_URL")



def get_subway_data():
    """서울시 지하철 실시간 도착 정보 조회"""
    try:
        url = f"{SUBWAY_URL}{SUBWAY_API_KEY}/json/realtimeStationArrival/0/5/"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"[Subway API Error] {str(e)}")
    
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
    
@router.post("/sf-subway-proxy")
async def sf_subway_proxy():
    try:
        # 실시간 도착 데이터 조회
        subway_data = get_subway_data()

        if "realtimeArrivalList" not in subway_data:
            raise HTTPException(status_code=400, detail="지하철 도착 정보가 없습니다.")

        # 필요한 데이터 추출 및 반복 전송
        results = []
        for item in subway_data["realtimeArrivalList"]:
            # Salesforce 객체 필드에 맞게 매핑 필요
            payload = {
                "StationName__c": item.get("statnNm"),
                "ArrivalMessage__c": item.get("arvlMsg2"),
                "TrainLine__c": item.get("trainLineNm"),
                "ArrivalTime__c": item.get("recptnDt")
            }
            try:
                result = send_to_salesforce("sobjects/SubwayData__c", payload)
                results.append(result)
            except Exception as single_error:
                results.append({"error": str(single_error), "data": payload})

        return {
            "status": "success",
            "count": len(results),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"[Proxy Error] 처리 중 오류 발생: {str(e)}")

def get_news_data():
    try:
        if not all([NEWS_CLIENTID, NEWS_SECRET, NEWS_URL]):
            raise ValueError("환경변수 설정 누락")

        headers = {
            "X-Naver-Client-Id": NEWS_CLIENTID,
            "X-Naver-Client-Secret": NEWS_SECRET
        }

        response = requests.get(NEWS_URL, headers=headers)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"[News API Error] 요청 실패: {str(e)}")
    except ValueError as ve:
        raise HTTPException(status_code=500, detail=f"[News API Error] {str(ve)}")

def send_to_salesforce(path: str, payload: dict):
    try:
        token_data = get_salesforce_token()
        access_token = token_data["access_token"]
        instance_url = token_data["instance_url"]
        response = sf_post(path, payload, access_token, instance_url)
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"[Salesforce API Error] {str(e)}")

@router.post("/sf-news-proxy")
async def sf_news_proxy():
    try:
        news_data = get_news_data()

        if "items" not in news_data:
            raise HTTPException(status_code=400, detail="뉴스 정보 없음")

        results = []
        for item in news_data["items"]:
            payload = {
                "Title__c": item.get("title", ""),
                "Description__c": item.get("description", ""),
                "Link__c": item.get("link", ""),
                "PubDate__c": item.get("pubDate", "")
            }

            try:
                result = send_to_salesforce("sobjects/NewsData__c", payload)
                results.append({"success": True, "result": result})
            except Exception as single_error:
                results.append({"success": False, "error": str(single_error), "data": payload})

        return {
            "status": "success",
            "count": len(results),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"[Proxy Error] {str(e)}")

