# Customer data model

from datetime import datetime, timedelta
from typing import Optional
import uuid

class Customer:
    """Customer class for managing customer data and business logic"""
    
    def __init__(self, name: str, email: str, phone: str, address: str, service_details: str):
        self.user_id = str(uuid.uuid4())[:8].upper()  # Short unique ID
        self.name = name.strip()
        self.email = email.lower().strip()
        self.phone = phone.strip()
        self.address = address.strip()
        self.service_details = service_details.strip()
        self.date_created = datetime.now()
        self.status = "active"
    
    def to_dict(self) -> dict:
        """Convert customer object to dictionary for Airtable"""
        return {
            "UserID": self.user_id,
            "Name": self.name,
            "Email": self.email,
            "Phone Number": self.phone,
            "Address": self.address,
            "Services details": self.service_details,
            "Date": self.date_created.strftime("%Y-%m-%d %H:%M:%S"),
            "Status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Customer':
        """Create customer object from dictionary"""
        customer = cls.__new__(cls)
        customer.user_id = data.get("UserID", "")
        customer.name = data.get("Name", "")
        customer.email = data.get("Email", "")
        customer.phone = data.get("Phone Number", "")
        customer.address = data.get("Address", "")
        customer.service_details = data.get("Services details", "")
        
        # Parse date
        date_str = data.get("Date", "")
        try:
            customer.date_created = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            customer.date_created = datetime.now()
        
        customer.status = data.get("Status", "active")
        return customer
    
    def can_cancel(self, cancellation_hours: int = 24) -> bool:
        """Check if customer can cancel within the allowed timeframe"""
        time_diff = datetime.now() - self.date_created
        return time_diff.total_seconds() < (cancellation_hours * 3600)
    
    def get_cancellation_deadline(self, cancellation_hours: int = 24) -> datetime:
        """Get the deadline for cancellation"""
        return self.date_created + timedelta(hours=cancellation_hours)
    
    def validate_data(self) -> tuple[bool, str]:
        """Validate customer data"""
        if not self.name or len(self.name) < 2:
            return False, "Name must be at least 2 characters long"
        
        if not self.email or "@" not in self.email:
            return False, "Please provide a valid email address"
        
        if not self.phone or len(self.phone.replace(" ", "").replace("-", "").replace("+", "")) < 10:
            return False, "Please provide a valid phone number"
        
        if not self.address or len(self.address) < 5:
            return False, "Please provide a complete address"
        
        if not self.service_details or len(self.service_details) < 10:
            return False, "Please provide detailed service requirements"
        
        return True, "Data is valid"
    
    def get_confirmation_message(self) -> str:
        """Get booking confirmation message"""
        return f"""Thank you for choosing Adeona Technologies! Your service request has been submitted successfully.

Details Confirmed:
- User ID: {self.user_id}
- Name: {self.name}
- Email: {self.email}
- Phone: {self.phone}
- Address: {self.address}
- Service: {self.service_details}

IMPORTANT: Please keep your User ID ({self.user_id}) safe. You'll need it if you want to cancel or inquire about your service.

Cancellation Policy: You can cancel your service request within 24 hours. After that, please contact us at (+94) 117 433 3333.

We'll contact you soon to discuss your requirements!"""
    
    def __str__(self) -> str:
        return f"Customer(ID: {self.user_id}, Name: {self.name}, Email: {self.email})"
    
    def __repr__(self) -> str:
        return self.__str__()