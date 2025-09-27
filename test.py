import pytest
from datetime import datetime, timedelta
from backend.app.models.customer import Customer


def test_customer_creation():
    customer = Customer(
        name="John Doe",
        email="john@example.com",
        phone="+94 771234567",
        address="123 Main Street",
        service_details="Website development and hosting"
    )

    assert customer.name == "John Doe"
    assert customer.email == "john@example.com"
    assert len(customer.user_id) == 8
    assert customer.status == "active"
    assert isinstance(customer.date_created, datetime)


def test_to_dict_and_from_dict():
    customer = Customer(
        name="Alice",
        email="alice@example.com",
        phone="0712345678",
        address="456 Park Avenue",
        service_details="Mobile App Development"
    )

    data_dict = customer.to_dict()
    new_customer = Customer.from_dict(data_dict)

    assert new_customer.name == "Alice"
    assert new_customer.email == "alice@example.com"
    assert new_customer.service_details == "Mobile App Development"
    assert isinstance(new_customer.date_created, datetime)


def test_validate_data():
    valid_customer = Customer(
        name="Valid User",
        email="valid@example.com",
        phone="0712345678",
        address="Valid Address",
        service_details="This is a detailed service request"
    )
    assert valid_customer.validate_data()[0] is True

    invalid_customer = Customer(
        name="A",
        email="invalidemail",
        phone="123",
        address="abc",
        service_details="short"
    )
    assert invalid_customer.validate_data()[0] is False


def test_cancellation_policy():
    customer = Customer(
        name="Cancel Test",
        email="cancel@example.com",
        phone="0777777777",
        address="Test Address",
        service_details="Service request for cancellation test"
    )
    # Created now, should allow cancellation
    assert customer.can_cancel(cancellation_hours=24) is True

    # Simulate old booking
    customer.date_created = datetime.now() - timedelta(hours=30)
    assert customer.can_cancel(cancellation_hours=24) is False


def test_get_confirmation_message():
    customer = Customer(
        name="Sam Smith",
        email="sam@example.com",
        phone="0778888888",
        address="Colombo, Sri Lanka",
        service_details="Cloud migration service"
    )
    message = customer.get_confirmation_message()
    assert "Sam Smith" in message
    assert customer.user_id in message
    assert "Adeona Technologies" in message


if __name__ == "__main__":
    pytest.main([__file__])
