import string
import random
from .models import UserProfile


def generate_unique_referral_code(length=8):
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(characters, k=length))
        if not UserProfile.objects.filter(referral_code=code).exists():
            return code
