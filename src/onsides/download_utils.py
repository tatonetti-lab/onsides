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

    # If name is too long, truncate and add hash to ensure uniqueness.
    # Use byte length since filesystems (ext4) enforce a 255-byte limit,
    # and multi-byte characters (e.g. Japanese) can be 3+ bytes each.
    max_bytes = 240  # leave room for hash suffix and file extension
    if len(clean_name.encode()) > max_bytes:
        name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
        # Truncate by characters until the byte length fits
        truncated = clean_name
        while len(truncated.encode()) > max_bytes - 9:  # 9 = underscore + 8-char hash
            truncated = truncated[:-1]
        clean_name = f"{truncated}_{name_hash}"

    # Ensure we don't have an empty string
    if not clean_name:
        name_hash = hashlib.md5(name.encode()).hexdigest()[:12]
        clean_name = f"medicine_{name_hash}"

    return clean_name
