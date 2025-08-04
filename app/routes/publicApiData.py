from fastapi import APIRouter, HTTPException
import requests
import os
from datetime import datetime
from app.utils.commonutil import send_to_salesforce

router = APIRouter()

SUBWAY_API_KEY = os.environ.get("SUBWAY_API_KEY")
SUBWAY_URL = os.environ.get("SUBWAY_URL")

NEWS_CLIENTID = os.environ.get("NEWS_CLIENTID")
NEWS_SECRET = os.environ.get("NEWS_SECRET")
NEWS_URL = os.environ.get("NEWS_URL")

MOVIE_KEY = os.environ.get("MOVIE_KEY")
MOVIE_URL = os.environ.get("MOVIE_URL")



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
        print("Subway Data:", subway_data)
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
    """뉴스 API 호출"""
    try:
        if not all([NEWS_CLIENTID, NEWS_SECRET, NEWS_URL]):
            raise ValueError("환경변수 설정이 누락되었습니다.")

        query = "AI"  # 혹은 프론트에서 받은 키워드 등으로 동적으로 구성

        headers = {
            "X-Naver-Client-Id": NEWS_CLIENTID,
            "X-Naver-Client-Secret": NEWS_SECRET
        }
        print(f"🔍 요청 헤더: {headers}")

        url = f"{NEWS_URL}?query={query}"
        print(f"🔍 요청 URL: {url}")

        response = requests.get(url, headers=headers)
        print(f"🔍 응답 상태 코드: {response.status_code}")
        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"[News API Error] 요청 실패: {str(e)}")

    except ValueError as ve:
        raise HTTPException(status_code=500, detail=f"[News API Error] 환경변수 오류: {str(ve)}")
    
def get_movie_data():
    """영화 API 호출"""
    try:
        if not all([MOVIE_KEY, MOVIE_URL]):
            raise ValueError("환경변수 설정이 누락되었습니다.")

        targetDt = datetime.now()  # 혹은 프론트에서 받은 키워드 등으로 동적으로 구성

        url = f"{MOVIE_URL}?key={MOVIE_KEY}&targetDt={targetDt}"
        print(f"🔍 요청 URL: {url}")

        response = requests.get(url)
        print(f"🔍 응답 상태 코드: {response.status_code}")
        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"[News API Error] 요청 실패: {str(e)}")

    except ValueError as ve:
        raise HTTPException(status_code=500, detail=f"[News API Error] 환경변수 오류: {str(ve)}")

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
            print('payload',payload)
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

@router.post("/sf-movie-proxy")
async def sf_movie_proxy():
    try:
        movie_data = get_news_data()

        if "items" not in movie_data:
            raise HTTPException(status_code=400, detail="뉴스 정보 없음")

        results = []
        for item in movie_data["items"]:
            payload = {
                "Title__c": item.get("title", ""),
                "Description__c": item.get("description", ""),
                "Link__c": item.get("link", ""),
                "PubDate__c": item.get("pubDate", "")
            }
            print('payload',payload)
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

