#!/usr/bin/env python3
import argparse
import base64
import secrets
import string

from cryptography.fernet import Fernet


def generate_fernet_key():
    """Generate a valid Fernet key."""
    key = Fernet.generate_key()
    return key.decode()


def generate_password(
    length=16,
    use_uppercase=True,
    use_lowercase=True,
    use_numbers=True,
    use_special=True,
):
    """Generate a secure password with specified characteristics."""
    # Define character sets
    chars = ""
    if use_uppercase:
        chars += string.ascii_uppercase
    if use_lowercase:
        chars += string.ascii_lowercase
    if use_numbers:
        chars += string.digits
    if use_special:
        chars += string.punctuation

    if not chars:
        raise ValueError("At least one character set must be selected")

    # Generate password
    password = "".join(secrets.choice(chars) for _ in range(length))

    # Ensure at least one character from each selected set
    if use_uppercase and not any(c in string.ascii_uppercase for c in password):
        pos = secrets.randbelow(length)
        password = (
            password[:pos]
            + secrets.choice(string.ascii_uppercase)
            + password[pos + 1 :]
        )
    if use_lowercase and not any(c in string.ascii_lowercase for c in password):
        pos = secrets.randbelow(length)
        password = (
            password[:pos]
            + secrets.choice(string.ascii_lowercase)
            + password[pos + 1 :]
        )
    if use_numbers and not any(c in string.digits for c in password):
        pos = secrets.randbelow(length)
        password = password[:pos] + secrets.choice(string.digits) + password[pos + 1 :]
    if use_special and not any(c in string.punctuation for c in password):
        pos = secrets.randbelow(length)
        password = (
            password[:pos] + secrets.choice(string.punctuation) + password[pos + 1 :]
        )

    return password


def main():
    parser = argparse.ArgumentParser(
        description="Generate secure passwords or Fernet keys"
    )
    parser.add_argument(
        "--fernet",
        action="store_true",
        help="Generate a Fernet key instead of a password",
    )
    parser.add_argument(
        "-l", "--length", type=int, default=16, help="Password length (default: 16)"
    )
    parser.add_argument(
        "--no-uppercase", action="store_true", help="Exclude uppercase letters"
    )
    parser.add_argument(
        "--no-lowercase", action="store_true", help="Exclude lowercase letters"
    )
    parser.add_argument("--no-numbers", action="store_true", help="Exclude numbers")
    parser.add_argument(
        "--no-special", action="store_true", help="Exclude special characters"
    )

    args = parser.parse_args()

    try:
        if args.fernet:
            key = generate_fernet_key()
            print("\nGenerated Fernet key:")
            print(f"ENCRYPTION_KEY={key}")
            print("\nAdd this to your .env file")
        else:
            password = generate_password(
                length=args.length,
                use_uppercase=not args.no_uppercase,
                use_lowercase=not args.no_lowercase,
                use_numbers=not args.no_numbers,
                use_special=not args.no_special,
            )
            print(password)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
