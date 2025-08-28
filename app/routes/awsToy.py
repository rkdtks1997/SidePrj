# awsToy.py
from fastapi import Request, HTTPException, Depends, APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
import httpx, os, base64, json
from datetime import datetime, timezone
from typing import Dict, Any
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

router = APIRouter()

TIMEOUT_SEC = float(os.getenv("TIMEOUT_SEC", "30.0"))   # 여유롭게
RETRY_COUNT = int(os.getenv("RETRY_COUNT", "2"))
UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")          # Render 환경변수로 설정

@router.get("/healthcheck", response_class=PlainTextResponse)
async def healthcheck():
    now = datetime.now(ZoneInfo("Asia/Seoul")) if ZoneInfo else datetime.now(timezone.utc)
    return f"AWS Response : {now.isoformat()}"

async def validate_request(request: Request) -> Dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    if "document" not in payload:
        raise HTTPException(status_code=400, detail="'document' is required.")

    try:
        file_bytes = base64.b64decode(payload["document"], validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 in 'document'.")

    return {
        "payload": payload,
        "file_bytes": file_bytes,
        # 원본 헤더는 여기서도 받긴 하지만, Upstage로는 사용하지 않음
    }

def _build_upstage_headers(client_auth: str | None = None) -> dict:
    """
    Upstage로 보낼 헤더는 Authorization만 허용.
    Content-Type/Length 등은 httpx가 멀티파트로 자동 설정하도록 비워둔다.
    """
    token = client_auth or UPSTAGE_API_KEY
    if not token:
        raise HTTPException(status_code=500, detail="No Upstage API key. Set UPSTAGE_API_KEY or send Authorization.")
    # 'Bearer ' 프리픽스가 빠졌으면 붙여주기
    if not token.lower().startswith("bearer "):
        token = f"Bearer {token}"
    return {"Authorization": token}

@router.post("/api/doc/parse")
async def doc_parse(ctx: Dict[str, Any] = Depends(validate_request)):
    payload   = ctx["payload"]
    file_bytes= ctx["file_bytes"]

    target_url = payload.get("endpointURL", "https://api.upstage.ai/v1/document-digitization")
    mime_type  = payload.get("mime_type") or "application/octet-stream"

    # 파일(멀티파트)
    files = {"document": ("upload.bin", file_bytes, mime_type)}

    # Upstage 샘플과 동일하게: 리스트/딕트/불리언은 JSON 문자열/문자열로
    data: dict[str, str] = {}
    for k, v in payload.items():
        if k in ("document", "endpointURL", "mime_type"):
            continue
        if isinstance(v, (list, dict)):
            data[k] = json.dumps(v)            # ["html"] → '["html"]'
        elif isinstance(v, bool):
            data[k] = "true" if v else "false" # True → 'true'
        else:
            data[k] = str(v)

    # Authorization만 전달 (클라이언트가 보낸 헤더는 절대 그대로 사용 X)
    # 필요 시, 클라이언트 Authorization을 우선 사용하고, 없으면 환경변수 사용
    client_auth = payload.get("authorization")  # 필요 시 바꾸세요
    headers = _build_upstage_headers(client_auth)

    last_exc = None
    for _ in range(RETRY_COUNT + 1):
        try:
            timeout = httpx.Timeout(TIMEOUT_SEC)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    target_url,
                    headers=headers,   # Authorization만
                    files=files,
                    data=data,
                )
            return JSONResponse(
                status_code=resp.status_code,
                content=_try_json(resp.content),
                headers=_filter_response_headers(resp.headers),
            )
        except Exception as e:
            last_exc = e
    raise HTTPException(status_code=502, detail=f"Upstage upstream error: {last_exc}")

def _try_json(content: bytes):
    import json
    try:
        return json.loads(content)
    except Exception:
        return {"raw": content.decode("utf-8", errors="replace")}

def _filter_response_headers(h: httpx.Headers) -> dict:
    drop = {"transfer-encoding", "content-encoding", "connection"}
    return {k: v for k, v in h.items() if k.lower() not in drop}
