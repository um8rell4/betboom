from django.db import models
from django.contrib.auth.models import User #Импорт встроенных в джанго User'ов
import os
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import uuid
from decimal import Decimal


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
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal(5000.00))  # стартовый баланс
    referred_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals')
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
        Удаляет старый аватар при загрузке нового
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
        from django.urls import reverse

        subject = "Подтвердите ваш email на CyberBet"

        # Создаем полный URL для подтверждения
        confirm_url = request.build_absolute_uri(
            reverse('accounts:confirm-email', kwargs={'confirmation_code': self.email_confirmation_code})
        )

        # Рендер HTML шаблона письма
        html_message = render_to_string('accounts/email_confirmation_email.html', {
            'user': self.user,
            'confirmation_code': self.email_confirmation_code,
            'confirm_url': confirm_url,  # Добавляем эту переменную
            'domain': request.get_host(),
            'protocol': 'https' if request.is_secure() else 'http',
        })

        # Отправка письма (HTML и текстовая версия)
        send_mail(
            subject=subject,
            message=strip_tags(html_message),  # Текстовая версия
            from_email='um8rell4bets@yandex.ru',
            recipient_list=[self.user.email],
            html_message=html_message,  # HTML версия
            fail_silently=False,
        )

    def add_referral_bonus(self, referred_user):
        """Начисляет бонусы за реферала"""
        from decimal import Decimal
        # Бонус приглашенному
        referred_user.profile.balance += Decimal('5000.00')
        referred_user.profile.save()

        # Бонус приглашающему
        self.balance += Decimal('2500.00')
        self.save()

        # Создаем запись о транзакции
        Transaction.objects.create(
            user=self.user,
            amount=Decimal('2500.00'),
            transaction_type='referral_bonus',
            comment=f'Бонус за приглашение {referred_user.username}'
        )

        Transaction.objects.create(
            user=referred_user,
            amount=Decimal('5000.00'),
            transaction_type='referral_bonus',
            comment=f'Реферальный бонус за регистрацию'
        )


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('deposit', 'Пополнение'),
        ('withdrawal', 'Вывод'),
        ('bet', 'Ставка'),
        ('win', 'Выигрыш'),
        ('referral_bonus', 'Реферальный бонус'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.amount} для {self.user.username}"
