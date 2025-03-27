import hashlib
import re


def sanitize_filename(name):
    """
    Convert a medicine name into a safe filename by:
    - Replacing spaces with underscores
    - Removing slashes, quotes, and other problematic characters
    - Converting to lowercase for consistency
    - Limiting length and ensuring uniqueness with a hash if needed
    """

    # Convert to lowercase and replace spaces with underscores
    clean_name = name.lower().replace(" ", "_")

    # Remove any characters that aren't alphanumeric, underscore, or hyphen
    clean_name = re.sub(r"[^\w\-]", "", clean_name)

    # If name is too long (over 100 chars), truncate and add hash to ensure uniqueness
    if len(clean_name) > 100:
        name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
        clean_name = f"{clean_name[:90]}_{name_hash}"

    # Ensure we don't have an empty string
    if not clean_name:
        name_hash = hashlib.md5(name.encode()).hexdigest()[:12]
        clean_name = f"medicine_{name_hash}"

    return clean_name
