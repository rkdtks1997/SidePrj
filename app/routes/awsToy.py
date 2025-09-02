from fastapi import FastAPI, Request, HTTPException, Depends, Body
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.routing import APIRouter, Request, HTTPException
from typing import Any, Dict, List, Tuple
from datetime import datetime, timezone

import re
import difflib
import sqlite3
import json
import requests
import os

router = APIRouter()

TIMEOUT_SEC = float(os.getenv("TIMEOUT_SEC", "5.0"))


# -------------------------
# Text normalize utils
# -------------------------
TOKEN_SPLIT_REGEX = re.compile(r"[_\-\s]+")
CAMEL_CASE_REGEX = re.compile(r"(?<!^)(?=[A-Z])")
TRAILING_SF_ID_REGEX = re.compile(r"__c$|__r$|__pc$|__pr$", re.IGNORECASE)

@router.get("/healthcheck", response_class=PlainTextResponse)
async def healthcheck():
    now = datetime.now(timezone.utc)
    return f"AWS Response : {now.isoformat()}"

# ---- validate_request가 반드시 여기! (doc_parse보다 먼저) ----
async def validate_request(request: Request) -> Dict[str, Any]:
    try:
        file_bytes = await request.body()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file body.")

    raw = request.headers.get("python-body")
    if not raw:
        raise HTTPException(status_code=400, detail="missing header: python_body")

    try:
        body = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid json in header: python_body")

    payload = {k: _normalize_value(value) for k, value in body.items()}
    payload = prepare_payload_for_headers(payload)

    upstage_headers = {
        "Authorization": request.headers.get("authorization")
    }

    return {
        "payload": payload,
        "file_bytes": file_bytes,
        "headers": upstage_headers,
    }

def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        lower = value.strip().lower()
        if lower == "true":
            return True
        elif lower == "false":
            return False
        if (value.strip().startswith("[") and value.strip().endswith("]")) or \
           (value.strip().startswith("{") and value.strip().endswith("}")):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value
    return value

def prepare_payload_for_headers(payload: Dict[str, Any]) -> Dict[str, str]:
    def to_header_value(v: Any) -> str:
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (list, dict)):
            return json.dumps(v, ensure_ascii=False)
        return str(v)
    return {k: to_header_value(v) for k, v in payload.items()}

# ---- 여기서 validate_request를 참조해도 됨 ----
@router.post("/api/doc/parse")
async def doc_parse(ctx: Dict[str, Any] = Depends(validate_request)):
    payload = ctx["payload"]
    file_bytes = ctx["file_bytes"]
    headers = ctx["headers"]

    target_url = "https://api.upstage.ai/v1/document-digitization"
    files = {"document": file_bytes}

    response = requests.post(target_url, headers=headers, files=files, data=payload)
    return response.json()

# 정확도 검사
# --- 카탈로그: Object → Field → {ID: Value} ---
def mock_product_options() -> Dict[str, Dict[str, Dict[str, str]]]:
    return {
        "시책": {
            "Promotion2": {
                "P2-CFX-5Y-PT5Y-75MK-OIL2Y": "CFX 5yrs( 동력전달계통5년75만km 보증, 엔진오일및필터2년)",
                "P2-CFX-4Y-PT4Y-60MK-OIL2Y": "CFX 4yrs( 동력전달계통4년60만km 보증, 엔진오일및필터2년)",
                "P2-CFX-4Y-PT5Y-60MK-OIL2Y": "CFX 4yrs( 동력전달계통5년60만km 보증, 엔진오일및필터2년)",
                "P2-CFX-4Y-PT4Y-70MK-OIL2Y": "CFX 4yrs( 동력전달계통4년70만km 보증, 엔진오일및필터2년)",
                "P2-CFX-4Y-PT4Y-80MK-OIL2Y": "CFX 4yrs( 동력전달계통4년80만km 보증, 엔진오일및필터2년)",
                "P2-CFX-4Y-PT3Y-60MK-OIL1Y": "CFX 4yrs( 동력전달계통3년60만km 보증, 엔진오일및필터1년)",
                "P2-CFX-5Y-PT4Y-75MK-OIL2Y": "CFX 5yrs( 동력전달계통4년75만km 보증, 엔진오일및필터2년)",
                "P2-CFX-5Y-PT5Y-90MK-OIL2Y": "CFX 5yrs( 동력전달계통5년90만km 보증, 엔진오일및필터2년)",
                "P2-CFX-5Y-PT5Y-100MK-OIL3Y": "CFX 5yrs( 동력전달계통5년100만km 보증, 엔진오일및필터3년)",
                "P2-CFX-5Y-PT6Y-80MK-OIL2Y": "CFX 5yrs( 동력전달계통6년80만km 보증, 엔진오일및필터2년)",
                "P2-CFX-6Y-PT5Y-100MK-OIL3Y": "CFX 6yrs( 동력전달계통5년100만km 보증, 엔진오일및필터3년)",
                "P2-CFX-6Y-PT6Y-100MK-OIL2Y": "CFX 6yrs( 동력전달계통6년100만km 보증, 엔진오일및필터2년)",
                "P2-CFX-6Y-PT5Y-120MK-OIL4Y": "CFX 6yrs( 동력전달계통5년120만km 보증, 엔진오일및필터4년)",
                "P2-CFX-7Y-PT5Y-120MK-OIL3Y": "CFX 7yrs( 동력전달계통5년120만km 보증, 엔진오일및필터3년)",
                "P2-CFX-7Y-PT6Y-150MK-OIL3Y": "CFX 7yrs( 동력전달계통6년150만km 보증, 엔진오일및필터3년)",
                "P2-CFX-3Y-PT3Y-50MK-OIL1Y": "CFX 3yrs( 동력전달계통3년50만km 보증, 엔진오일및필터1년)",
            }
        }
    }

def dl_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()  # 0~1

# --- 값 정규화 & 유사도 ---
def normalize_value_text(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip().lower()

# ---- 어떤 포맷으로 와도 payload를 뽑아내는 추출기 ----
async def extract_payload(request: Request) -> Dict[str, Any]:
    ctype = request.headers.get("content-type", "").lower()

    # 1) 순수 JSON 본문
    if "application/json" in ctype:
        try:
            return await request.json()
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid JSON body")

    # 2) form-data 또는 x-www-form-urlencoded
    if "multipart/form-data" in ctype or "application/x-www-form-urlencoded" in ctype:
        form = await request.form()
        # (1) body 필드가 문자열 JSON일 수 있음
        if "body" in form:
            body_val = form["body"]
            if isinstance(body_val, (bytes, bytearray)):
                body_val = body_val.decode("utf-8", errors="ignore")
            try:
                return json.loads(body_val)
            except json.JSONDecodeError:
                raise HTTPException(status_code=422, detail="Invalid JSON in form field 'body'")
        # (2) 그렇지 않으면 form을 dict로 반환 (필요시 확장)
        return dict(form)

    # 3) 헤더에 body가 담긴 경우 (예: 'body' 또는 'python-body')
    for hdr in ("body", "python-body"):
        raw = request.headers.get(hdr)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                raise HTTPException(status_code=422, detail=f"Invalid JSON in header '{hdr}'")

    # 4) 마지막으로 raw 바이트를 JSON으로 시도
    raw_bytes = await request.body()
    if raw_bytes:
        try:
            return json.loads(raw_bytes.decode("utf-8", errors="ignore"))
        except json.JSONDecodeError:
            raise HTTPException(status_code=422, detail="Invalid raw body (not JSON)")

    raise HTTPException(status_code=422, detail="No payload found")

# ---- 엔드포인트 ----
@router.post("/api/similarity")
async def match_value_by_similarity_single_return(request: Request) -> Dict[str, Any]:
    # 어떤 방식이든 payload를 추출
    payload: Dict[str, Any] = await extract_payload(request)

    # 파라미터 파싱
    object_name = payload.get("objectName")
    field_name  = payload.get("fieldName")
    threshold   = payload.get("threshold", 0.8), 0.8  # 기본 0.8

    res: Dict[str, Any] = { 
        "success": False,
        "objectName": object_name,
        "fieldName": field_name,
        "sourceValue": None,
        "id": None,
        "message": None,
    }

    # object/field 존재 체크
    catalog = mock_product_options()
    obj_block = catalog.get(object_name)
    field_map = obj_block.get(field_name) if isinstance(obj_block, dict) else None
    if (obj_block is None) or (field_map is None):
        res["message"] = "Invalid objectName or fieldName."
        return res

    # 요청 본문에서 사용자 값 추출: payload[objectName][fieldName] (문자열이어야 함)
    user_obj_section = payload.get(object_name)
    if not isinstance(user_obj_section, dict):
        res["message"] = f"Request body does not contain source value at payload['{object_name}'][*]."
        return res

    user_value = user_obj_section.get(field_name)
    if not isinstance(user_value, str):
        res["message"] = f"Request body does not contain a string value at payload['{object_name}']['{field_name}']."
        return res

    res["sourceValue"] = user_value

    # 유사도 최상 1건만
    src = normalize_value_text(user_value)
    best_id, best_val, best_score = None, None, -1.0
    for id_, val in field_map.items():
        s = dl_ratio(src, normalize_value_text(val))
        if s > best_score:
            best_id, best_val, best_score = id_, val, s

    if best_id is not None and best_score >= threshold:
        res["success"] = True
        res["id"] = {"id": best_id, "value": best_val, "score": float(best_score)}
    else:
        res["message"] = f"No value meets threshold {threshold}"

    return res