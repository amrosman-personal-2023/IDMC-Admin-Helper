"""
Filename sanitization unit tests.
"""
import pytest
from app.sanitize import sanitize_filename


@pytest.mark.parametrize("raw,expected", [
    ("script.py",               "script.py"),
    ("my_file-v2.csv",          "my_file-v2.csv"),
    ("data.CSV",                "data.CSV"),
    ("  spaced.txt  ",          "spaced.txt"),
    (".hidden",                 "hidden"),          # leading dot stripped
    ("file.tar.gz",             "file.tar.gz"),
])
def test_valid_filenames_pass_through(raw, expected):
    assert sanitize_filename(raw) == expected


@pytest.mark.parametrize("raw", [
    "../etc/passwd",
    "../../secret",
    "subdir/file.py",
    "/absolute/path.py",
    "C:\\Windows\\System32\\cmd.exe",
    "file;rm -rf /",
    "file`whoami`.sh",
    "file$(id).py",
    "file|cat /etc/passwd",
    "file&background.sh",
    "",
    "   ",
    "...",
    "../../",
])
def test_dangerous_inputs_return_none_or_safe(raw):
    result = sanitize_filename(raw)
    # Either None or contains no dangerous characters
    if result is not None:
        assert "/" not in result
        assert "\\" not in result
        assert ".." not in result
        assert ";" not in result
        assert "`" not in result
        assert "$" not in result
        assert "|" not in result
        assert "&" not in result


def test_path_separators_stripped():
    assert sanitize_filename("dir/file.py") == "file.py"
    assert sanitize_filename("dir\\file.py") == "file.py"


def test_dotdot_stripped():
    result = sanitize_filename("../../etc/passwd")
    assert result is None or ".." not in result


def test_empty_after_strip_returns_none():
    assert sanitize_filename("") is None
    assert sanitize_filename("   ") is None
    assert sanitize_filename(";") is None
    assert sanitize_filename("/") is None


def test_unicode_normalization():
    # Fullwidth characters should be normalized
    result = sanitize_filename("ｆｉｌｅ.py")
    assert result is not None
    assert ".py" in result


def test_null_bytes_stripped():
    result = sanitize_filename("file\x00.py")
    assert result is not None
    assert "\x00" not in result
