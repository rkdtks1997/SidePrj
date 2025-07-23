from pydantic import BaseModel

class LeadIn(BaseModel):
    first_name: str
    last_name: str
    company: str = "Unknown Company"
