import os

from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Get encryption key from environment or generate a new one
def get_or_create_key():
    """Get the encryption key from environment or generate a new one."""
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        # Generate a new key
        key = Fernet.generate_key().decode()
        print("WARNING: No ENCRYPTION_KEY found in .env. Generated a new one.")
        print("Please add this to your .env file:")
        print(f"ENCRYPTION_KEY={key}")
    return key.encode()


# Initialize Fernet with the key
fernet = Fernet(get_or_create_key())


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key."""
    if not api_key:
        return None
    return fernet.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key."""
    if not encrypted_key:
        return None
    return fernet.decrypt(encrypted_key.encode()).decode()
