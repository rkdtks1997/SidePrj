from fastapi import APIRouter
from app.models.lead import LeadIn
from app.services.salesforce import get_leads, create_lead

router = APIRouter()

@router.get("/leads")
def read_leads():
    return get_leads()

@router.post("/create-lead")
def post_lead(data: LeadIn):
    return create_lead(data)
