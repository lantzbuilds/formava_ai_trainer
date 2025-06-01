"""
Script to generate a favicon from the muscle emoji.
"""

import os

from PIL import Image, ImageDraw, ImageFont


def create_favicon():
    # Create a 32x32 image with a transparent background
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Use a font that supports emoji
    try:
        # Try to use a system font that supports emoji
        font = ImageFont.truetype("Apple Color Emoji", 24)
    except:
        # Fallback to default font
        font = ImageFont.load_default()

    # Draw the muscle emoji
    draw.text((4, 4), "💪", font=font, fill=(0, 0, 0, 255))

    # Ensure the directory exists
    os.makedirs("app/static/images", exist_ok=True)

    # Save as ICO
    img.save("app/static/images/favicon.ico", format="ICO")


if __name__ == "__main__":
    create_favicon()
