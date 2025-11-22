from typing import Optional
from pydantic import BaseModel

class Lead(BaseModel):
    id: str
    name: str
    phone_number: int
    car_model: str
    car_name: str
    car_price_cop: int
    last_call_status: Optional[str] = None
    last_contact_at: Optional[str] = None