from fastapi import FastAPI, Request, HTTPException, Depends, Body
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.routing import APIRouter, Request, HTTPException
from typing import Any, Dict, List, Tuple, Union
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
def dl_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()

def normalize_value_text(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip().lower()

def to_str(v: Any) -> str:
    return v if isinstance(v, str) else ("" if v is None else str(v))

def to_float(v: Any, default: float) -> float:
    try:
        return float(v) if not isinstance(v, str) else float(v.strip())
    except Exception:
        return default

def mock_product_options() -> Dict[str, Dict[str, Dict[str, str]]]:
    return {
        "시책": {
            "Promotion2": {
                "P2-CFX-5Y-PT5Y-75MK-OIL2Y": "CFX 5yrs( 동력전달계통5년75만km 보증, 엔진오일및필터2년)",
                # ... 생략 ...
            }
        }
    }

@router.post("/api/similarity")
async def match_value_by_similarity_single_return(
    ctx: Union[Dict[str, Any], str] = Body(...),   # ✅ dict 또는 string 모두 허용
) -> Dict[str, Any]:
    # 0) payload 정규화: dict로 맞춘다
    if isinstance(ctx, str):
        # 바디가 JSON 문자열이면 1회 더 파싱
        try:
            payload = json.loads(ctx)
        except json.JSONDecodeError:
            raise HTTPException(status_code=422, detail="Body is a JSON string but not a valid JSON object")
    elif isinstance(ctx, dict):
        # {"body":"<json>"} 래핑도 지원
        if "body" in ctx and isinstance(ctx["body"], str):
            try:
                payload = json.loads(ctx["body"])
            except json.JSONDecodeError:
                raise HTTPException(status_code=422, detail="Invalid JSON in 'body' field")
        else:
            payload = ctx
    else:
        raise HTTPException(status_code=422, detail="Body must be an object or a JSON string")

    # 입력 파싱
    object_name = to_str(payload.get("objectName")).strip()
    field_name  = to_str(payload.get("fieldName")).strip()
    threshold   = to_float(payload.get("threshold", 0.8), 0.8)

    res: Dict[str, Any] = {
        "success": False,
        "objectName": object_name,
        "fieldName": field_name,
        "sourceValue": None,
        "id": None,
        "message": None,
    }

    # catalog 접근
    catalog = mock_product_options()
    obj_block = catalog.get(object_name)
    field_map = obj_block.get(field_name) if isinstance(obj_block, dict) else None
    if (obj_block is None) or (field_map is None):
        res["message"] = "Invalid objectName or fieldName."
        return res

    # 요청 본문에서 사용자 값 꺼내기: payload[objectName][fieldName]에 문자열
    user_obj_section = payload.get(object_name)
    if not isinstance(user_obj_section, dict):
        res["message"] = f"Request body does not contain source value at payload['{object_name}'][*]."
        return res

    user_value = user_obj_section.get(field_name)
    if not isinstance(user_value, str):
        res["message"] = f"Request body does not contain a string value at payload['{object_name}']['{field_name}']."
        return res

    res["sourceValue"] = user_value

    # 유사도 최상 1건
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