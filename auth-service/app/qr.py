"""
Generate a QR code as a base64-encoded PNG data URI from an otpauth:// URI.
Used by the enrollment endpoint so the admin UI can display it directly.
"""
import base64
import io
import urllib.parse


def otpauth_uri(username: str, seed_b32: str, issuer: str = "IDMC Portal") -> str:
    label = urllib.parse.quote(f"{issuer}:{username}")
    params = urllib.parse.urlencode({
        "secret": seed_b32,
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": "6",
        "period": "30",
    })
    return f"otpauth://totp/{label}?{params}"


def qr_data_uri(uri: str) -> str:
    """Return a data:image/png;base64,... string suitable for an <img src>."""
    import qrcode
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"
