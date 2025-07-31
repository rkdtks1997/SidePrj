from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from collections import defaultdict
import time

# 요청 기록 저장소 (IP별)
request_log = defaultdict(list)

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 60, window_sec: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_sec = window_sec
        print('RateLimitMiddleware', self)
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()

        # 해당 IP의 요청 기록 중 유효 시간 내 요청만 필터링
        request_log[client_ip] = [
            ts for ts in request_log[client_ip] if now - ts < self.window_sec
        ]

        if len(request_log[client_ip]) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."}
            )
        
        # 요청 기록 추가 후 다음 미들웨어로 넘김
        request_log[client_ip].append(now)
        return await call_next(request)
