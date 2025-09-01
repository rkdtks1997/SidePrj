from fastapi import FastAPI, Request, HTTPException, Depends
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

# similarity_router.py
from typing import Any, Dict, List, Tuple
import re
import difflib
import sqlite3

from fastapi import APIRouter, Request, HTTPException

router = APIRouter()

# -------------------------
# Text normalize utils
# -------------------------
TOKEN_SPLIT_REGEX = re.compile(r"[_\-\s]+")
CAMEL_CASE_REGEX = re.compile(r"(?<!^)(?=[A-Z])")
TRAILING_SF_ID_REGEX = re.compile(r"__c$|__r$|__pc$|__pr$", re.IGNORECASE)

def normalize_identifier(s: str) -> str:
    if not s:
        return ""
    s = TRAILING_SF_ID_REGEX.sub("", s)
    s = CAMEL_CASE_REGEX.sub(" ", s)      # camelCase -> camel Case
    s = TOKEN_SPLIT_REGEX.sub(" ", s)     # snake/kebab -> space
    return re.sub(r"\s+", " ", s).strip().lower()

def dl_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()  # 0~1

# -------------------------
# DB layer (SQLite 예시)
# -------------------------
DB_PATH = "similarity.db"
# 스키마 예시:
# CREATE TABLE IF NOT EXISTS object_fields (
#   id INTEGER PRIMARY KEY,
#   object_name TEXT NOT NULL,
#   field_name  TEXT NOT NULL
# );
# CREATE INDEX IF NOT EXISTS idx_obj ON object_fields(object_name);

def object_exists(object_name: str) -> bool:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT 1 FROM object_fields WHERE object_name=? LIMIT 1", (object_name,))
        return cur.fetchone() is not None

def fetch_object_fields(object_name: str) -> List[str]:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.cursor()
        cur.execute("SELECT field_name FROM object_fields WHERE object_name=?", (object_name,))
        return [r[0] for r in cur.fetchall()]

# -------------------------
# API endpoint
# -------------------------
@router.post("/api/similarity")
async def doc_similarity(request: Request):
    """
    Apex 예시 바디:
    {
      "objectName": "Account",
      "fieldName":  "Name",
      "top_k": 5,            # optional
      "threshold": 0.25      # optional (0~1)
    }
    """
    # 1) 요청 파싱
    try:
        ctx: Dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    object_name = ctx.get("objectName")
    field_name  = ctx.get("fieldName")
    top_k       = int(ctx.get("top_k", 5))
    threshold   = float(ctx.get("threshold", 0.0))  # 0~1

    if not object_name or not field_name:
        raise HTTPException(status_code=400, detail="objectName and fieldName are required")

    # 2) 오브젝트 유효성
    if not object_exists(object_name):
        # 확실: DB에 오브젝트 없음
        return {
            "success": False,
            "objectName": object_name,
            "fieldName": field_name,
            "objectValid": False,
            "fieldValid": False,
            "message": f"Object '{object_name}' not found in DB."
        }

    # 3) 필드 목록 조회
    db_fields = fetch_object_fields(object_name)
    if not db_fields:
        # 확실: 해당 오브젝트의 필드 레코드 없음
        return {
            "success": False,
            "objectName": object_name,
            "fieldName": field_name,
            "objectValid": True,
            "fieldValid": False,
            "message": f"No fields found for object '{object_name}'."
        }

    # 4) 완전일치 판단
    if field_name in db_fields:
        # 확실: 필드 존재 → 즉시 OK
        return {
            "success": True,
            "objectName": object_name,
            "fieldName": field_name,
            "objectValid": True,
            "fieldValid": True,
            "score": 1.0,
            "bestMatch": field_name,
            "candidates": [{"field": field_name, "score": 1.0}]
        }

    # 5) 유사도 후보(difflib)
    src = normalize_identifier(field_name)

    best_field: str = None
    best_score: float = -1.0

    for f in db_fields:
        s = dl_ratio(src, normalize_identifier(f))
        if s > best_score:
            best_field, best_score = f, s

    # threshold 적용: 최상 후보가 하한선 미달이면 매칭 없음으로 처리
    if best_field is None or best_score < float(threshold):
        return {
            "success": True,
            "objectName": object_name,
            "fieldName": field_name,
            "objectValid": True,
            "fieldValid": False,              # 완전일치 아님
            "bestMatch": None,                # 유의미한 후보 없음
            "message": f"No similar field meets threshold {threshold}"
        }

    # 단일 최고 유사도만 반환
    return {
        "success": True,
        "objectName": object_name,
        "fieldName": field_name,
        "objectValid": True,
        "fieldValid": False,                  # 완전일치 아님
        "bestMatch": {
            "field": best_field,
            "score": float(best_score)
        }
    }
