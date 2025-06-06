import base64
import logging
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Path to store the encryption key if not in .env
KEY_FILE = Path(".encryption_key")


def get_or_create_key():
    """Get the encryption key from environment or generate a new one."""
    # First try to get from environment
    key = os.getenv("ENCRYPTION_KEY")
    logger.info(f"Got key from environment: {bool(key)}")
    if key:
        logger.debug(f"Key from environment: {key[:10]}...")

    # If not in environment, try to read from file
    if not key and KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()
        logger.info("Got key from file")
        logger.debug(f"Key from file: {key[:10]}...")

    # If still no key, generate a new one
    if not key:
        key = Fernet.generate_key().decode()
        # Save to file
        KEY_FILE.write_text(key)
        logger.warning(
            "WARNING: No ENCRYPTION_KEY found. Generated a new one and saved to .encryption_key"
        )
        logger.warning("For production use, please add this to your .env file:")
        logger.warning(f"ENCRYPTION_KEY={key}")

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
            logger.info(
                "Note: Encryption key has been reformatted to ensure proper encoding"
            )

        return formatted_key
    except Exception as e:
        logger.error(f"Invalid ENCRYPTION_KEY format: {e}")
        # Generate a new key if the existing one is invalid
        new_key = Fernet.generate_key().decode()
        if not os.getenv("ENCRYPTION_KEY"):
            KEY_FILE.write_text(new_key)
        logger.warning(
            "Generated a new key. For production use, please add to your .env file:"
        )
        logger.warning(f"ENCRYPTION_KEY={new_key}")
        return new_key


def get_fernet():
    """Get a fresh Fernet instance with the current key."""
    key = get_or_create_key()
    logger.debug(f"Using encryption key: {key[:10]}...")
    return Fernet(key.encode())


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key."""
    if not api_key:
        return None
    try:
        logger.debug(f"Encrypting API key: {api_key[:5]}...")
        encrypted = get_fernet().encrypt(api_key.encode()).decode()
        logger.debug(f"Encrypted result: {encrypted[:20]}...")
        return encrypted
    except Exception as e:
        logger.error(f"Error encrypting API key: {str(e)}")
        raise


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key."""
    if not encrypted_key:
        return None
    try:
        logger.debug(f"Attempting to decrypt key: {encrypted_key[:20]}...")
        decrypted = get_fernet().decrypt(encrypted_key.encode()).decode()
        logger.debug(f"Successfully decrypted key: {decrypted[:5]}...")
        return decrypted
    except Exception as e:
        logger.error(f"Error decrypting API key: {str(e)}")
        logger.error(f"Encrypted key length: {len(encrypted_key)}")
        logger.error(
            f"Encrypted key format: {encrypted_key[:50] if len(encrypted_key) > 50 else encrypted_key}"
        )
        raise
