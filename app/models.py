from pydantic import BaseModel

class Lead(BaseModel):
    """Simple lead model for demo purposes."""
    name: str
    car_model: str
    car_name: str
    car_price_cop: int