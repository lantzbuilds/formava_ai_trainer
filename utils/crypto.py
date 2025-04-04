import base64
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
        return key
    else:
        # Ensure the key is properly formatted
        try:
            # Try to decode and re-encode to ensure it's valid
            key_bytes = base64.urlsafe_b64decode(key)
            if len(key_bytes) != 32:
                raise ValueError("Key must be 32 bytes")
            # Re-encode the key to ensure it's in the correct format
            return base64.urlsafe_b64encode(key_bytes).decode()
        except Exception as e:
            print(f"Invalid ENCRYPTION_KEY format: {e}")
            # Generate a new key if the existing one is invalid
            new_key = Fernet.generate_key().decode()
            print("Generated a new key. Please update your .env file:")
            print(f"ENCRYPTION_KEY={new_key}")
            return new_key


# Initialize Fernet with the key
fernet = Fernet(get_or_create_key().encode())


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
