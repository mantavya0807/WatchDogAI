"""
Test Code File with PII
This file contains sample code with PII in strings and comments.
"""

# Configuration with PII
API_KEY = "sk-1234567890abcdef"
USER_EMAIL = "john.smith@example.com"
PHONE_NUMBER = "555-123-4567"

# Database connection with credentials
DATABASE_URL = "postgresql://admin:password123@db.example.com:5432/mydb"

# User data
user_data = {
    "name": "Alice Johnson",
    "email": "alice@company.com",
    "ssn": "123-45-6789",
    "address": "123 Main St, Seattle, WA 98101"
}

# Comment with PII: Contact Bob Chen at bob.chen@email.com or (206) 555-8901
# Another comment: SSN is 987-65-4321

def process_user(user):
    """Process user data - contains PII in docstring"""
    # This function processes user data for John Smith
    # Email: john.smith@email.com
    # Phone: 555-987-6543
    return user

# String with credit card
payment_info = "Credit card: 4532-1234-5678-9010"

