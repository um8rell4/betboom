from django.db import models
from django.contrib.auth.models import User #Импорт встроенных в джанго User'ов


class UserProfile(models.Model):
    # Расширяем дефолтных пользователей, представленных Django
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)  # стартовый баланс
    referral_code = models.CharField(max_length=10, blank=True, unique=True) #Реферальный код каждого пользователя
    is_admin = models.BooleanField(default=False)  # для будущих ролей

    def __str__(self):
        return self.user.username
