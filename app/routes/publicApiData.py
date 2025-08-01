from fastapi import APIRouter, HTTPException
import requests
import os
from app.utils.commonutil import get_salesforce_token
from app.services.salesforce import send_to_salesforce
router = APIRouter()

SUBWAY_API_KEY = os.environ.get("SUBWAY_API_KEY")
SUBWAY_URL = os.environ.get("SUBWAY_URL")

def get_subway_data():
    """서울시 지하철 실시간 도착 정보 조회"""
    try:
        url = f"{SUBWAY_URL}{SUBWAY_API_KEY}/json/realtimeStationArrival/0/5/"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"[Subway API Error] {str(e)}")

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
