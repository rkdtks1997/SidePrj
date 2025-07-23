# Salesforce FastAPI Heroku Example

이 프로젝트는 FastAPI와 Heroku, Salesforce API 연동 예제입니다.

## 폴더 구조
```
SidePrj/
├── app/
│   ├── main.py
│   ├── models/
│   ├── routes/
│   └── services/
├── init.py
├── Procfile
├── requirements.txt
├── README.md
└── .gitignore
```

## 환경 변수 (Heroku Config Vars)
- SF_CLIENT_ID
- SF_CLIENT_SECRET
- SF_LOGIN_URL
- SF_API_VERSION
- API_KEY
- SFDC_URL

## 실행 방법
1. Heroku에 환경 변수 등록
2. `heroku local` 또는 Heroku에 배포
3. API 엔드포인트:
   - GET `/leads`
   - POST `/create-lead`

## 주의사항
- 환경 변수 값은 절대 깃허브에 올리지 마세요!
- 필요시 `.env` 파일로 로컬 테스트 가능
