import string
import random
from .models import UserProfile


def generate_unique_referral_code(length=8):
    characters = string.ascii_uppercase + string.digits #Все знаки допустимые в рефералке
    while True:
        code = ''.join(random.choices(characters, k=length)) #Рандомно составляет 8-мизначный код
        if not UserProfile.objects.filter(referral_code=code).exists(): #если такого кода не существует
            return code
