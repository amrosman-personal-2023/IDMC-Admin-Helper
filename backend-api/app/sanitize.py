"""
Filename sanitization.  Strips all path components and shell metacharacters.
Returns None if nothing safe remains after stripping.
"""
import re
import unicodedata
from pathlib import PurePosixPath, PureWindowsPath
from typing import Optional

# Characters that must never appear in a filename sent to the filesystem
_DANGEROUS = re.compile(r'[/\\<>:"|?*\x00-\x1f;`$&\'()\[\]{}^~!#%]')
_DOTDOT = re.compile(r'\.\.+')


def sanitize_filename(raw: str) -> Optional[str]:
    """
    Strip path separators, directory traversal sequences, and shell
    metacharacters from a filename.  Returns None if the result is empty.
    """
    if not raw:
        return None

    # Normalize unicode (NFKC) to collapse homoglyphs
    name = unicodedata.normalize("NFKC", raw)

    # Take only the final component — strip any directory prefix
    name = PurePosixPath(name).name
    name = PureWindowsPath(name).name

    # Remove dangerous characters
    name = _DANGEROUS.sub("", name)

    # Collapse or remove .. sequences
    name = _DOTDOT.sub("", name)

    # Strip leading dots and whitespace
    name = name.lstrip(". \t")

    name = name.strip()
    return name if name else None
