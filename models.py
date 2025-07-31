from pydantic import BaseModel, Field
from typing import List

class ContactInfo(BaseModel):
    restaurant_name: str = Field(description="Name of the restaurant")
    email: str = Field(description="Contact email address")
    phone: str = Field(description="Phone number if available")
    contact_person: str = Field(description="Name of contact person if available")
    is_signature_contact: bool = Field(description="Whether this contact comes from email signature")
    confidence_score: float = Field(description="Confidence level (0-1) that this is a valid restaurant contact")

class RestaurantContacts(BaseModel):
    contacts: List[ContactInfo] = Field(description="List of restaurant contacts found")