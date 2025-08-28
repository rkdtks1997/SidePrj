from fastapi import FastAPI, Request, HTTPException, Depends, APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
import httpx
import os
import base64
import requests
from datetime import datetime, timezone
from typing import Dict, Any
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

router = APIRouter()

# ===== Settings =====
TIMEOUT_SEC = float(os.getenv("TIMEOUT_SEC", "5.0"))
RETRY_COUNT = int(os.getenv("RETRY_COUNT", "2"))

# ===== /healthcheck =====
@router.get("/healthcheck", response_class=PlainTextResponse)
async def healthcheck():
    if ZoneInfo:
        now = datetime.now(ZoneInfo("Asia/Seoul"))
    else:
        now = datetime.now(timezone.utc)
    return f"AWS Response : {now.isoformat()}"

# ===== Validator (앞단 검증) =====
async def validate_request(request: Request) -> Dict[str, Any]:
    # 1) payload try
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    # 2) document not in payload
    if "document" not in payload:
        raise HTTPException(status_code=400, detail="'document' is required.")

    # 3) filebytes try (base64 decode)
    try:
        file_bytes = base64.b64decode(payload["document"], validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 in 'document'.")

    # 헤더는 그대로 bypass
    headers = dict(request.headers)

    return {
        "payload": payload,
        "file_bytes": file_bytes,
        "headers": headers,
    }

# ===== /api/doc/parse =====
@router.post("/api/doc/parse")
async def doc_parse(ctx: Dict[str, Any] = Depends(validate_request)):
    payload = ctx["payload"]
    file_bytes = ctx["file_bytes"]
    headers = ctx["headers"]

    # endpointURL (없으면 기본값)
    target_url = payload.get("endpointURL", "https://api.upstage.ai/v1/document-digitization")
    mime_type = payload.get("mime_type")
#test
    # 파일(멀티파트)
    files = {"document": ("upload.bin", file_bytes, mime_type)}
    data = {
        "model": "document-parse",
        "ocr": "auto",
        "merge_multipage_tables": True,
        "chart_recognition": True,
        "coordinates": True,
        "output_formats": '["html", "markdown"]',
        "base64_encoding": '["table"]',
    }

    response = requests.post(target_url, headers=headers, files=files, data=data)
    
    print(response.json())
    return response.json()

    # # 나머지 파라미터들 (List<String> 포함 → SFDC에서 JSON 직렬화해 오므로 그대로 문자열화)
    # data = {k: str(v) for k, v in payload.items() if k not in ("document", "endpointURL", "mime_type")}

    # # Upstage API 호출 (재시도)
    # last_exc = None
    # for _ in range(RETRY_COUNT + 1):
    #     try:
    #         timeout = httpx.Timeout(TIMEOUT_SEC)
    #         async with httpx.AsyncClient(timeout=timeout) as client:
    #             resp = await client.post(
    #                 target_url,
    #                 headers=headers,   # SFDC가 준 헤더 그대로 전달 (bypass)
    #                 files=files,
    #                 data=data,
    #             )
    #         return JSONResponse(
    #             status_code=resp.status_code,
    #             content=_try_json(resp.content),
    #             headers=_filter_response_headers(resp.headers),
    #         )
    #     except Exception as e:
    #         last_exc = e

    # raise HTTPException(status_code=502, detail=f"Upstage upstream error: {last_exc}")

# ===== Helpers =====
def _try_json(content: bytes):
    import json
    try:
        return json.loads(content)
    except Exception:
        return {"raw": content.decode("utf-8", errors="replace")}

def _filter_response_headers(h: httpx.Headers) -> dict:
    drop = {"transfer-encoding", "content-encoding", "connection"}
    return {k: v for k, v in h.items() if k.lower() not in drop}