import pytest
from pydantic import ValidationError
from marketharvester.models import CompanyRecord, ContactInfo, Address


def test_valid_company_record():
    record = CompanyRecord(
        name="Apex Plumbing",
        category="Plumbing",
        rating=4.8,
        review_count=100,
        contact=ContactInfo(
            email="info@apex.com",
            phone="(512) 555-0199",
            website="https://apex.com"
        ),
        address=Address(city="Austin", state="TX", postal_code="78701")
    )

    assert record.name == "Apex Plumbing"
    assert record.contact.email == "info@apex.com"
    assert record.contact.phone == "5125550199"
    assert record.hash_fingerprint is not None
    assert record.company_id.startswith("cmp_")


def test_invalid_email_raises_validation_error():
    with pytest.raises(ValidationError) as exc:
        ContactInfo(email="invalid-email-address")
    assert "Invalid email format" in str(exc.value)


def test_invalid_phone_raises_validation_error():
    with pytest.raises(ValidationError) as exc:
        ContactInfo(phone="123")
    assert "Invalid phone number length" in str(exc.value)


def test_rating_out_of_bounds():
    with pytest.raises(ValidationError):
        CompanyRecord(
            name="Super Star Co",
            rating=6.5,
            address=Address(city="Dallas")
        )


def test_deterministic_deduplication_fingerprint():
    r1 = CompanyRecord(
        name="Tech Solutions Inc",
        contact=ContactInfo(website="https://techsolutions.com"),
        address=Address(city="Austin")
    )
    r2 = CompanyRecord(
        name="Tech Solutions Inc.",
        contact=ContactInfo(website="http://techsolutions.com/"),
        address=Address(city="austin")
    )
    # Different string nuances, same business entity
    assert r1.hash_fingerprint == r2.hash_fingerprint
