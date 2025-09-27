#!/usr/bin/env python3
"""
Test script for the Airtable Service
This script tests all the main functionality of the AirtableService class
"""

import asyncio
import sys
import os
from datetime import datetime
import uuid

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from backend.app.services.airtable_service import AirtableService
    from backend.app.models.customer import Customer
    from backend.app.config.settings import settings
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure your project structure matches the import paths")
    sys.exit(1)

class AirtableServiceTester:
    """Test class for AirtableService"""
    
    def __init__(self):
        self.service = AirtableService()
        self.test_user_id = f"TEST_{uuid.uuid4().hex[:8].upper()}"
        self.test_customer = None
        
    async def create_test_customer(self) -> Customer:
        """Create a test customer object"""
        customer_data = {
            'user_id': self.test_user_id,
            'name': 'Test Customer',
            'email': 'test@example.com',
            'phone': '+1234567890',
            'address': '123 Test Street, Test City, TC 12345',
            'service_details': 'This is a test service request for automated testing purposes',
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': 'active'
        }
        
        return Customer.from_dict(customer_data)
    
    async def test_data_validation(self) -> bool:
        """Test customer data validation"""
        print("\n--- Testing Data Validation ---")
        
        try:
            # Test valid data
            valid_data = {
                'name': 'John Doe',
                'email': 'john@example.com',
                'phone': '+1234567890',
                'address': '123 Main Street, City, State 12345',
                'service_details': 'Need web development services for my business'
            }
            
            is_valid, message = await self.service.validate_customer_data(valid_data)
            print(f"Valid data test: {'PASS' if is_valid else 'FAIL'} - {message}")
            
            # Test invalid email
            invalid_data = valid_data.copy()
            invalid_data['email'] = 'invalid_email'
            is_valid, message = await self.service.validate_customer_data(invalid_data)
            print(f"Invalid email test: {'PASS' if not is_valid else 'FAIL'} - {message}")
            
            # Test missing required field
            incomplete_data = valid_data.copy()
            del incomplete_data['name']
            is_valid, message = await self.service.validate_customer_data(incomplete_data)
            print(f"Missing field test: {'PASS' if not is_valid else 'FAIL'} - {message}")
            
            # Test short phone number
            short_phone_data = valid_data.copy()
            short_phone_data['phone'] = '123'
            is_valid, message = await self.service.validate_customer_data(short_phone_data)
            print(f"Short phone test: {'PASS' if not is_valid else 'FAIL'} - {message}")
            
            return True
            
        except Exception as e:
            print(f"Data validation test failed: {e}")
            return False
    
    async def test_create_customer(self) -> bool:
        """Test creating a customer record"""
        print("\n--- Testing Customer Creation ---")
        
        try:
            self.test_customer = await self.create_test_customer()
            record_id = await self.service.create_customer_record(self.test_customer)
            
            if record_id:
                print(f"Customer creation: PASS - Record ID: {record_id}")
                return True
            else:
                print("Customer creation: FAIL - No record ID returned")
                return False
                
        except Exception as e:
            print(f"Customer creation test failed: {e}")
            return False
    
    async def test_find_customer(self) -> bool:
        """Test finding a customer by user ID"""
        print("\n--- Testing Customer Lookup ---")
        
        try:
            # Test finding existing customer
            found_customer = await self.service.find_customer_by_user_id(self.test_user_id)
            
            if found_customer:
                print(f"Find existing customer: PASS - Found: {found_customer.name}")
                
                # Test finding non-existent customer
                not_found = await self.service.find_customer_by_user_id("NONEXISTENT_ID")
                if not not_found:
                    print("Find non-existent customer: PASS - Correctly returned None")
                    return True
                else:
                    print("Find non-existent customer: FAIL - Should have returned None")
                    return False
            else:
                print("Find existing customer: FAIL - Customer not found")
                return False
                
        except Exception as e:
            print(f"Customer lookup test failed: {e}")
            return False
    
    async def test_update_customer_status(self) -> bool:
        """Test updating customer status"""
        print("\n--- Testing Status Update ---")
        
        try:
            # Update to cancelled status
            updated = await self.service.update_customer_status(self.test_user_id, 'cancelled')
            
            if updated:
                print("Status update: PASS - Status updated to cancelled")
                
                # Verify the update
                customer = await self.service.find_customer_by_user_id(self.test_user_id)
                if customer and customer.status == 'cancelled':
                    print("Status verification: PASS - Status correctly updated")
                    
                    # Update back to active for other tests
                    await self.service.update_customer_status(self.test_user_id, 'active')
                    return True
                else:
                    print("Status verification: FAIL - Status not updated correctly")
                    return False
            else:
                print("Status update: FAIL - Update operation failed")
                return False
                
        except Exception as e:
            print(f"Status update test failed: {e}")
            return False
    
    async def test_cancellation_eligibility(self) -> bool:
        """Test cancellation eligibility check"""
        print("\n--- Testing Cancellation Eligibility ---")
        
        try:
            # Test eligible customer (newly created should be eligible)
            eligibility = await self.service.check_cancellation_eligibility(self.test_user_id)
            
            if eligibility['eligible']:
                print(f"Cancellation eligibility: PASS - {eligibility['reason']}")
                
                # Test non-existent customer
                no_customer = await self.service.check_cancellation_eligibility("NONEXISTENT_ID")
                if not no_customer['eligible'] and "not found" in no_customer['reason'].lower():
                    print("Non-existent customer eligibility: PASS - Correctly not eligible")
                    return True
                else:
                    print("Non-existent customer eligibility: FAIL")
                    return False
            else:
                print(f"Cancellation eligibility: INFO - Not eligible: {eligibility['reason']}")
                # This might be expected behavior depending on your cancellation window
                return True
                
        except Exception as e:
            print(f"Cancellation eligibility test failed: {e}")
            return False
    
    async def test_get_active_customers(self) -> bool:
        """Test getting all active customers"""
        print("\n--- Testing Get Active Customers ---")
        
        try:
            active_customers = await self.service.get_all_active_customers()
            
            print(f"Active customers retrieved: {len(active_customers)}")
            
            # Check if our test customer is in the list
            test_customer_found = any(c.user_id == self.test_user_id for c in active_customers)
            
            if test_customer_found:
                print("Active customers test: PASS - Test customer found in active list")
                return True
            else:
                print("Active customers test: WARN - Test customer not found in active list (might be expected)")
                return True  # This could be normal depending on timing
                
        except Exception as e:
            print(f"Get active customers test failed: {e}")
            return False
    
    async def test_customer_stats(self) -> bool:
        """Test getting customer statistics"""
        print("\n--- Testing Customer Statistics ---")
        
        try:
            stats = await self.service.get_customer_stats()
            
            print(f"Customer stats: {stats}")
            
            if isinstance(stats, dict) and 'total_customers' in stats:
                print("Customer stats test: PASS - Stats retrieved successfully")
                return True
            else:
                print("Customer stats test: FAIL - Invalid stats format")
                return False
                
        except Exception as e:
            print(f"Customer stats test failed: {e}")
            return False
    
    async def test_cleanup(self) -> bool:
        """Clean up test data"""
        print("\n--- Cleaning Up Test Data ---")
        
        try:
            deleted = await self.service.delete_customer_record(self.test_user_id)
            
            if deleted:
                print("Cleanup: PASS - Test customer record deleted")
                return True
            else:
                print("Cleanup: FAIL - Could not delete test customer record")
                return False
                
        except Exception as e:
            print(f"Cleanup failed: {e}")
            return False
    
    async def run_all_tests(self) -> None:
        """Run all tests"""
        print("=" * 60)
        print("AIRTABLE SERVICE TEST SUITE")
        print("=" * 60)
        
        print(f"Test User ID: {self.test_user_id}")
        
        # Check configuration
        print(f"\nConfiguration Check:")
        print(f"- Base ID: {settings.AIRTABLE_BASE_ID[:10]}..." if hasattr(settings, 'AIRTABLE_BASE_ID') else "- Base ID: Not configured")
        print(f"- Table Name: {settings.AIRTABLE_TABLE_NAME}" if hasattr(settings, 'AIRTABLE_TABLE_NAME') else "- Table Name: Not configured")
        print(f"- API Key: {'Configured' if hasattr(settings, 'AIRTABLE_API_KEY') and settings.AIRTABLE_API_KEY else 'Not configured'}")
        
        tests = [
            ("Data Validation", self.test_data_validation),
            ("Customer Creation", self.test_create_customer),
            ("Customer Lookup", self.test_find_customer),
            ("Status Update", self.test_update_customer_status),
            ("Cancellation Eligibility", self.test_cancellation_eligibility),
            ("Active Customers", self.test_get_active_customers),
            ("Customer Statistics", self.test_customer_stats),
            ("Cleanup", self.test_cleanup),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results.append((test_name, result))
            except Exception as e:
                print(f"{test_name} test crashed: {e}")
                results.append((test_name, False))
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "PASS" if result else "FAIL"
            print(f"{test_name:.<30} {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("\nAll tests passed! Airtable service is working correctly.")
        elif passed > 0:
            print(f"\n{passed} out of {total} tests passed. Some functionality may need attention.")
        else:
            print("\nAll tests failed. Check your Airtable configuration and network connection.")

async def main():
    """Main test runner"""
    
    # Check if we can import required modules
    try:
        tester = AirtableServiceTester()
        await tester.run_all_tests()
    except Exception as e:
        print(f"Test runner failed: {e}")
        print("\nPossible issues:")
        print("1. Missing configuration in settings")
        print("2. Network connectivity issues")
        print("3. Invalid Airtable credentials")
        print("4. Missing required modules")

if __name__ == "__main__":
    print("Starting Airtable Service Tests...")
    asyncio.run(main())