from django.db import models
from django.contrib.auth.models import User #Импорт встроенных в джанго User'ов
from django.dispatch import receiver
from django.db.models.signals import post_save
import os
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.utils.html import strip_tags
import uuid


def user_avatar_path(instance, filename):
    # Файл будет загружен в MEDIA_ROOT/user_<id>/avatar/<filename>
    return f'user_{instance.user.id}/avatar/{filename}'


class UserProfile(models.Model):
    """
    Модель расширенного профиля пользователя.
    Содержит дополнительные поля к стандартной модели User Django.
    """
    # Расширяем дефолтных пользователей, представленных Django
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to=user_avatar_path, null=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)  # стартовый баланс
    referral_code = models.CharField(max_length=10, blank=True, unique=True) #Реферальный код каждого пользователя
    is_admin = models.BooleanField(default=False)  # для будущих ролей
    # Поля для подтверждения email
    email_confirmed = models.BooleanField(
        default=False,
        verbose_name="Email подтвержден"
    )
    email_confirmation_code = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        null=True,
        verbose_name="Код подтверждения email"
    )

    def save(self, *args, **kwargs):
        """
        Переопределенный метод save:
        1. Генерирует реферальный код при первом сохранении
        2. Удаляет старый аватар при загрузке нового
        """
        # Удаляем старый аватар при загрузке нового
        try:
            old_avatar = UserProfile.objects.get(pk=self.pk).avatar
            if old_avatar and old_avatar != self.avatar:
                if os.path.isfile(old_avatar.path):
                    os.remove(old_avatar.path)
        except UserProfile.DoesNotExist:
            pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Профиль {self.user.username}"

    def send_confirmation_email(self, request):
        """
        Отправляет email с подтверждением регистрации.

        Args:
            request: HttpRequest объект для получения домена и протокола
        """
        subject = "Подтвердите ваш email на CyberBet"

        # Рендер HTML шаблона письма
        html_message = render_to_string('accounts/email_confirmation_email.html', {
            'user': self.user,
            'confirmation_code': self.email_confirmation_code,
            'domain': request.get_host(),
            'protocol': 'https' if request.is_secure() else 'http',
        })

        # Отправка письма (HTML и текстовая версия)
        send_mail(
            subject=subject,
            message=strip_tags(html_message),  # Текстовая версия
            from_email='noreply@cyberbet.com',
            recipient_list=[self.user.email],
            html_message=html_message,  # HTML версия
            fail_silently=False,
        )

