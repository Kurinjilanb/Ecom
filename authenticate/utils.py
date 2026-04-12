import logging
import secrets

from django.conf import settings
from django.core import signing
from django.core.cache import cache
import random
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

def verify_signed_token(token, salt="ecom.otp.session"):
    try:
        return signing.loads(token, salt=salt, max_age=300)
    except signing.SignatureExpired:
        print("DEBUG: Token has expired")
        return None
    except signing.BadSignature:
        print("DEBUG: Token signature is invalid (wrong salt or secret)")
        return None


def verify_otp_code(identifier, input_otp):
    print(f"DEBUG: Attempting to fetch key: 'otp_{identifier}'")
    cached_otp = cache.get(f"otp_{identifier}")
    print("-------cached_otp------------>",cached_otp)

    # If Redis returns bytes, decode it to a string first
    if isinstance(cached_otp, bytes):
        cached_otp = cached_otp.decode('utf-8')

    if cached_otp and str(cached_otp).strip()==str(input_otp).strip():
        cache.delete(f"otp_{identifier}")
        print("DEBUG: Token has expired")
        return True
    return False

from django.core import signing


def sign_user_name(email, salt="ecom.otp.session"):
    """
    Step 1: Create the 'Sealed Envelope' during Login.
    This will be sent to the user to hold until they get their OTP.
    """
    # We do NOT use max_age here.
    # We just pack the data into a signed string.
    data = {"email": email}

    # This creates the signature and the internal timestamp automatically.
    signed_token = signing.dumps(data, salt=salt)

    return signed_token


def generate_otp():
    # This generates a truly random 6-digit number every single time
    return f"{secrets.randbelow(1000000):06d}"