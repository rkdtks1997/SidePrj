from pydantic import BaseModel

class Interface_In(BaseModel):
    first_name: str
    last_name: str
    company: str = "Unknown Company"