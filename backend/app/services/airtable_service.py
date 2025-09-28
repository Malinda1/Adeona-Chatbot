# Airtable API integration

# Airtable API integration - ENHANCED CANCELLATION

# Simple Airtable API integration using requests

import requests
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from backend.app.config.settings import settings
from backend.app.models.customer import Customer
from backend.app.utils.logger import logger, log_error, log_function_call

class AirtableService:
    """Service for managing customer data in Airtable using requests"""
    
    def __init__(self):
        self.base_url = f"https://api.airtable.com/v0/{settings.AIRTABLE_BASE_ID}/{settings.AIRTABLE_TABLE_NAME}"
        self.headers = {
            "Authorization": f"Bearer {settings.AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method: str, url: str, data: Dict = None) -> Optional[Dict]:
        """Make HTTP request to Airtable API"""
        try:
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "PATCH":
                response = requests.patch(url, headers=self.headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                return None
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Airtable API request failed: {e}")
            return None
    
    async def create_customer_record(self, customer: Customer) -> Optional[str]:
        """Create a new customer record in Airtable"""
        try:
            log_function_call("create_customer_record", {"user_id": customer.user_id})
            
            # Prepare data for Airtable
            record_data = {
                "fields": customer.to_dict()
            }
            
            # Create record
            result = self._make_request("POST", self.base_url, record_data)
            
            if result and 'id' in result:
                record_id = result['id']
                logger.info(f"Customer record created with ID: {record_id}")
                return record_id
            else:
                logger.error("Failed to create customer record")
                return None
            
        except Exception as e:
            log_error(e, "create_customer_record")
            return None
    
    async def find_customer_by_user_id(self, user_id: str) -> Optional[Customer]:
        """Find customer record by User ID"""
        try:
            log_function_call("find_customer_by_user_id", {"user_id": user_id})
            
            # Search for the record using formula
            formula = f"{{UserID}} = '{user_id}'"
            url = f"{self.base_url}?filterByFormula={requests.utils.quote(formula)}"
            
            result = self._make_request("GET", url)
            
            if not result or not result.get('records'):
                logger.info(f"No customer found with User ID: {user_id}")
                return None
            
            # Convert first record to Customer object
            record = result['records'][0]
            customer_data = record['fields']
            customer = Customer.from_dict(customer_data)
            
            logger.info(f"Found customer: {customer.user_id}")
            return customer
            
        except Exception as e:
            log_error(e, "find_customer_by_user_id")
            return None
    
    async def delete_customer_record(self, user_id: str) -> bool:
        """Delete customer record by User ID"""
        try:
            log_function_call("delete_customer_record", {"user_id": user_id})
            
            # Find the record first
            formula = f"{{UserID}} = '{user_id}'"
            url = f"{self.base_url}?filterByFormula={requests.utils.quote(formula)}"
            
            result = self._make_request("GET", url)
            
            if not result or not result.get('records'):
                logger.warning(f"No record found to delete with User ID: {user_id}")
                return False
            
            # Delete the record
            record_id = result['records'][0]['id']
            delete_url = f"{self.base_url}/{record_id}"
            
            delete_result = self._make_request("DELETE", delete_url)
            
            if delete_result is not None:
                logger.info(f"Successfully deleted record for User ID: {user_id}")
                return True
            else:
                return False
            
        except Exception as e:
            log_error(e, "delete_customer_record")
            return False
    
    async def update_customer_status(self, user_id: str, status: str) -> bool:
        """Update customer record status"""
        try:
            log_function_call("update_customer_status", {"user_id": user_id, "status": status})
            
            # Find the record first
            formula = f"{{UserID}} = '{user_id}'"
            url = f"{self.base_url}?filterByFormula={requests.utils.quote(formula)}"
            
            result = self._make_request("GET", url)
            
            if not result or not result.get('records'):
                logger.warning(f"No record found to update with User ID: {user_id}")
                return False
            
            # Update the record
            record_id = result['records'][0]['id']
            update_url = f"{self.base_url}/{record_id}"
            update_data = {
                "fields": {"Status": status}
            }
            
            update_result = self._make_request("PATCH", update_url, update_data)
            
            if update_result:
                logger.info(f"Updated status for User ID: {user_id} to {status}")
                return True
            else:
                return False
            
        except Exception as e:
            log_error(e, "update_customer_status")
            return False
    
    async def get_all_active_customers(self) -> List[Customer]:
        """Get all active customer records"""
        try:
            log_function_call("get_all_active_customers")
            
            # Get records with active status
            formula = "{Status} = 'active'"
            url = f"{self.base_url}?filterByFormula={requests.utils.quote(formula)}"
            
            result = self._make_request("GET", url)
            
            customers = []
            if result and result.get('records'):
                for record in result['records']:
                    customer_data = record['fields']
                    customer = Customer.from_dict(customer_data)
                    customers.append(customer)
            
            logger.info(f"Retrieved {len(customers)} active customers")
            return customers
            
        except Exception as e:
            log_error(e, "get_all_active_customers")
            return []
    
    async def check_cancellation_eligibility(self, user_id: str) -> Dict[str, Any]:
        """ENHANCED: Check if a customer is eligible for cancellation within 24-hour window"""
        try:
            log_function_call("check_cancellation_eligibility", {"user_id": user_id})
            
            customer = await self.find_customer_by_user_id(user_id)
            
            if not customer:
                return {
                    "eligible": False,
                    "reason": f"User ID '{user_id}' not found. Please check your User ID and try again.",
                    "customer": None,
                    "time_exceeded": False
                }
            
            if customer.status != "active":
                return {
                    "eligible": False,
                    "reason": "Service request is not active or has already been cancelled.",
                    "customer": customer,
                    "time_exceeded": False
                }
            
            # Check if within 24-hour cancellation window
            # Fixed: Use the correct attribute name and Customer's built-in method
            try:
                # Use the Customer class's built-in method with the correct parameter name
                can_cancel = customer.can_cancel(cancellation_hours=24)
                
            except (ValueError, AttributeError) as e:
                logger.error(f"Error checking cancellation eligibility for customer {user_id}: {e}")
                return {
                    "eligible": False,
                    "reason": "Error processing booking date. Please contact support.",
                    "customer": customer,
                    "time_exceeded": False
                }
            
            if can_cancel:
                return {
                    "eligible": True,
                    "reason": "Within 24-hour cancellation window",
                    "customer": customer,
                    "time_exceeded": False
                }
            else:
                # Calculate when the 24-hour window expired using Customer's method
                deadline = customer.get_cancellation_deadline(cancellation_hours=24)
                
                return {
                    "eligible": False,
                    "reason": f"The 24-hour cancellation window has expired. Deadline was {deadline.strftime('%Y-%m-%d at %H:%M')}.",
                    "customer": customer,
                    "time_exceeded": True,
                    "deadline": deadline.strftime('%Y-%m-%d at %H:%M')
                }
                
        except Exception as e:
            log_error(e, "check_cancellation_eligibility")
            return {
                "eligible": False,
                "reason": "System error occurred while checking eligibility",
                "customer": None,
                "time_exceeded": False
            }
    
    async def process_cancellation(self, user_id: str) -> Dict[str, Any]:
        """ENHANCED: Process service cancellation with comprehensive error handling"""
        try:
            log_function_call("process_cancellation", {"user_id": user_id})
            
            # First, check eligibility
            eligibility = await self.check_cancellation_eligibility(user_id)
            
            if not eligibility["eligible"]:
                # Handle different failure reasons
                if eligibility.get("time_exceeded", False):
                    # 24-hour window exceeded
                    return {
                        "success": False,
                        "message": f"Cannot cancel service request '{user_id}' - the 24-hour cancellation window has expired. {eligibility['reason']}",
                        "requires_contact": True,
                        "time_exceeded": True,
                        "user_found": True
                    }
                
                elif eligibility["customer"] is None:
                    # User ID not found
                    return {
                        "success": False,
                        "message": f"User ID '{user_id}' not found in our records. Please verify your User ID.",
                        "requires_contact": True,
                        "time_exceeded": False,
                        "user_found": False
                    }
                
                else:
                    # Service already cancelled or inactive
                    return {
                        "success": False,
                        "message": eligibility["reason"],
                        "requires_contact": False,
                        "time_exceeded": False,
                        "user_found": True
                    }
            
            # User is eligible - proceed with cancellation
            logger.info(f"Processing eligible cancellation for User ID: {user_id}")
            
            deleted = await self.delete_customer_record(user_id)
            
            if deleted:
                logger.info(f"Successfully cancelled and deleted record for User ID: {user_id}")
                return {
                    "success": True,
                    "message": f"Service request '{user_id}' has been successfully cancelled and removed from our records.",
                    "requires_contact": False,
                    "time_exceeded": False,
                    "user_found": True
                }
            else:
                # Deletion failed
                logger.error(f"Failed to delete record for User ID: {user_id}")
                return {
                    "success": False,
                    "message": f"Failed to complete cancellation for '{user_id}' due to a system error.",
                    "requires_contact": True,
                    "time_exceeded": False,
                    "user_found": True
                }
                
        except Exception as e:
            log_error(e, "process_cancellation")
            return {
                "success": False,
                "message": f"System error occurred while processing cancellation for '{user_id}'",
                "requires_contact": True,
                "time_exceeded": False,
                "user_found": False
            }
    
    async def validate_customer_data(self, customer_data: Dict[str, str]) -> tuple[bool, str]:
        """Validate customer data before creating record"""
        try:
            required_fields = ['name', 'email', 'phone', 'address', 'service_details']
            
            for field in required_fields:
                if not customer_data.get(field, '').strip():
                    return False, f"Please provide {field.replace('_', ' ')}"
            
            # Validate email format
            email = customer_data['email']
            if '@' not in email or '.' not in email.split('@')[-1]:
                return False, "Please provide a valid email address"
            
            # Validate phone number
            phone = customer_data['phone']
            clean_phone = ''.join(filter(str.isdigit, phone))
            if len(clean_phone) < 10:
                return False, "Please provide a valid phone number with at least 10 digits"
            
            # Validate name length
            if len(customer_data['name'].strip()) < 2:
                return False, "Name must be at least 2 characters long"
            
            # Validate address length
            if len(customer_data['address'].strip()) < 5:
                return False, "Please provide a complete address"
            
            # Validate service details length
            if len(customer_data['service_details'].strip()) < 10:
                return False, "Please provide detailed service requirements (at least 10 characters)"
            
            return True, "Valid"
            
        except Exception as e:
            log_error(e, "validate_customer_data")
            return False, "Data validation error occurred"
    
    async def get_customer_stats(self) -> Dict[str, int]:
        """Get customer statistics"""
        try:
            log_function_call("get_customer_stats")
            
            result = self._make_request("GET", self.base_url)
            
            stats = {
                "total_customers": 0,
                "active_customers": 0,
                "cancelled_customers": 0,
                "today_customers": 0
            }
            
            if not result or not result.get('records'):
                return stats
                
            stats["total_customers"] = len(result['records'])
            today = datetime.now().date()
            
            for record in result['records']:
                fields = record.get('fields', {})
                status = fields.get('Status', 'active')
                
                if status == 'active':
                    stats["active_customers"] += 1
                else:
                    stats["cancelled_customers"] += 1
                
                # Check if created today
                date_str = fields.get('Date', '')
                try:
                    record_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").date()
                    if record_date == today:
                        stats["today_customers"] += 1
                except ValueError:
                    pass
            
            logger.info(f"Customer stats: {stats}")
            return stats
            
        except Exception as e:
            log_error(e, "get_customer_stats")
            return {"total_customers": 0, "active_customers": 0, "cancelled_customers": 0, "today_customers": 0}

# Create global instance
airtable_service = AirtableService()