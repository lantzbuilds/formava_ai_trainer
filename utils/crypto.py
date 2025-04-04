import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Path to store the encryption key if not in .env
KEY_FILE = Path(".encryption_key")


def get_or_create_key():
    """Get the encryption key from environment or generate a new one."""
    # First try to get from environment
    key = os.getenv("ENCRYPTION_KEY")

    # If not in environment, try to read from file
    if not key and KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()

    # If still no key, generate a new one
    if not key:
        key = Fernet.generate_key().decode()
        # Save to file
        KEY_FILE.write_text(key)
        print(
            "WARNING: No ENCRYPTION_KEY found. Generated a new one and saved to .encryption_key"
        )
        print("For production use, please add this to your .env file:")
        print(f"ENCRYPTION_KEY={key}")

    # Validate and format the key
    try:
        # Try to decode and re-encode to ensure it's valid
        key_bytes = base64.urlsafe_b64decode(key)
        if len(key_bytes) != 32:
            raise ValueError("Key must be 32 bytes")
        # Re-encode the key to ensure it's in the correct format
        formatted_key = base64.urlsafe_b64encode(key_bytes).decode()

        # If the key was different from what we have, update it
        if formatted_key != key:
            if not os.getenv("ENCRYPTION_KEY"):
                KEY_FILE.write_text(formatted_key)
            print("Note: Encryption key has been reformatted to ensure proper encoding")

        return formatted_key
    except Exception as e:
        print(f"Invalid ENCRYPTION_KEY format: {e}")
        # Generate a new key if the existing one is invalid
        new_key = Fernet.generate_key().decode()
        if not os.getenv("ENCRYPTION_KEY"):
            KEY_FILE.write_text(new_key)
        print("Generated a new key. For production use, please add to your .env file:")
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
