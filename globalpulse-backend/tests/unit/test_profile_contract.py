import base64
import pytest
from app.schemas.auth import UpdateProfileRequest
from app.core.exceptions import ValidationError

def test_profile_optional_names_and_aliases():
    # Test camelCase alias canonicalization and empty names
    req = UpdateProfileRequest.model_validate({
        "firstName": "",
        "lastName": "",
        "mobileNumber": "9876543210"
    })
    dump = req.model_dump(exclude_unset=True)
    assert "first_name" in dump
    assert dump["first_name"] == ""
    assert dump["last_name"] == ""
    assert dump["mobile_number"] == "9876543210"

def test_profile_image_valid_jpeg():
    # Valid JPEG header \xff\xd8\xff
    jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    b64 = "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes).decode("utf-8")
    req = UpdateProfileRequest.model_validate({"profileImage": b64})
    assert req.profile_image == b64

def test_profile_image_oversized_rejected():
    # 2.5 MB image
    large_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * (2500000)
    b64 = "data:image/jpeg;base64," + base64.b64encode(large_bytes).decode("utf-8")
    with pytest.raises(ValidationError, match="exceeds maximum allowed limit of 2 MB"):
        UpdateProfileRequest.model_validate({"profileImage": b64})

def test_profile_image_invalid_magic_bytes_rejected():
    # Text file fake Data URL
    fake_bytes = b"Hello world this is not an image file"
    b64 = "data:image/jpeg;base64," + base64.b64encode(fake_bytes).decode("utf-8")
    with pytest.raises(ValidationError, match="not a valid JPEG, PNG, or WebP image"):
        UpdateProfileRequest.model_validate({"profile_image": b64})

def test_profile_image_empty_removal():
    req = UpdateProfileRequest.model_validate({"profile_image": ""})
    assert req.profile_image == ""
