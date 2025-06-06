from django.db import models
from django.contrib.auth.models import User #Импорт встроенных в джанго User'ов
import os
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import uuid
from decimal import Decimal
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver


def user_avatar_path(instance, filename):
    # Файл будет загружен в MEDIA_ROOT/user_<id>/avatar/<filename>
    return f'user_{instance.user.id}/avatar/{filename}'


class UserProfile(models.Model):
    """
    Модель расширенного профиля пользователя.
    Содержит дополнительные поля к стандартной модели User Django.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name="Пользователь"
    )
    avatar = models.ImageField(
        upload_to=user_avatar_path,
        null=True,
        blank=True,
        verbose_name="Аватар"
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal(5000.00),
        verbose_name="Баланс"
    )
    referred_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='referrals',
        verbose_name="Пригласивший пользователь"
    )
    referral_code = models.CharField(
        max_length=10,
        blank=True,
        unique=True,
        verbose_name="Реферальный код"
    )
    is_admin = models.BooleanField(
        default=False,
        verbose_name="Администратор"
    )
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
    total_bets = models.IntegerField(
        default=0,
        verbose_name="Всего ставок"
    )
    won_bets = models.IntegerField(
        default=0,
        verbose_name="Выиграно ставок"
    )
    total_winnings = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Общая сумма выигрышей"
    )

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self):
        return f"Профиль {self.user.username}"


    @property
    def win_rate(self):
        """Процент выигранных ставок"""
        if self.total_bets == 0:
            return 0
        return round((self.won_bets / self.total_bets) * 100, 2)

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

    def send_confirmation_email(self, request):
        """
        Отправляет email с подтверждением регистрации.
        """
        from django.urls import reverse
        import logging

        logger = logging.getLogger(__name__)

        try:
            subject = "Подтверждение email на CyberBet"

            # Создаем полный URL для подтверждения
            confirm_url = request.build_absolute_uri(
                reverse('accounts:confirm-email', kwargs={'confirmation_code': self.email_confirmation_code})
            )

            # Рендер HTML шаблона письма
            html_message = render_to_string('accounts/email_confirmation_email.html', {
                'user': self.user,
                'confirmation_code': self.email_confirmation_code,
                'confirm_url': confirm_url,
                'domain': request.get_host(),
                'protocol': 'https' if request.is_secure() else 'http',
            })

            logger.info(f"Отправка письма на {self.user.email}")

            # Отправка письма
            send_mail(
                subject=subject,
                message=strip_tags(html_message),
                from_email='um8rell4bets@yandex.ru',
                recipient_list=[self.user.email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(f"Письмо успешно отправлено на {self.user.email}")

        except Exception as e:
            logger.error(f"Ошибка отправки письма: {str(e)}")
            raise e

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

    def update_betting_stats(self):
        """Обновляет статистику ставок пользователя"""
        from matches.models import Bet

        user_bets = Bet.objects.filter(user=self.user)

        self.total_bets = user_bets.count()
        self.won_bets = user_bets.filter(status='won').count()

        # Подсчитать общую сумму выигрышей
        won_bets = user_bets.filter(status='won')
        total_winnings = sum(bet.potential_win for bet in won_bets)
        self.total_winnings = total_winnings

        self.save(update_fields=['total_bets', 'won_bets', 'total_winnings'])


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('deposit', 'Пополнение'),
        ('withdrawal', 'Вывод'),
        ('bet', 'Ставка'),
        ('win', 'Выигрыш'),
        ('referral_bonus', 'Реферальный бонус'),
    )

    STATUS_CHOICES = (
        ('pending', 'В обработке'),
        ('completed', 'Завершена'),
        ('failed', 'Отклонена'),
    )

    # Новое поле UUID
    transaction_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="ID транзакции"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="Пользователь"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Сумма"
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        verbose_name="Тип транзакции"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',  # Изменили default на pending
        verbose_name="Статус"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    comment = models.TextField(
        blank=True,
        verbose_name="Комментарий"
    )

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_id} - {self.get_transaction_type_display()} {self.amount}"

    def update_user_balance(self, old_status=None):
        """
        Обновляет баланс пользователя в зависимости от статуса транзакции
        """
        profile = self.user.profile

        # Если был старый статус, сначала откатываем его влияние
        if old_status == 'completed' and self.status != 'completed':
            if self.transaction_type in ['deposit', 'win', 'referral_bonus']:
                profile.balance -= self.amount
            elif self.transaction_type == 'withdrawal':
                profile.balance += self.amount

        # Применяем новый статус
        if self.status == 'completed':
            if self.transaction_type in ['deposit', 'win', 'referral_bonus']:
                profile.balance += self.amount
            elif self.transaction_type == 'withdrawal':
                profile.balance -= self.amount

        profile.save()

@receiver(pre_save, sender=Transaction)
def transaction_pre_save(sender, instance, **kwargs):
    """Сохраняем старый статус перед изменением"""
    if instance.pk:
        try:
            old_instance = Transaction.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Transaction.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Transaction)
def transaction_post_save(sender, instance, created, **kwargs):
    """Обновляем баланс после сохранения транзакции"""
    old_status = getattr(instance, '_old_status', None)

    if created:
        # Новая транзакция
        if instance.status == 'completed':
            instance.update_user_balance()
    else:
        # Обновление существующей транзакции
        if old_status != instance.status:
            instance.update_user_balance(old_status)


class Notification(models.Model):
    TYPE_CHOICES = [
        ('bet_won', 'Ставка выиграна'),
        ('bet_lost', 'Ставка проиграна'),
        ('match_started', 'Матч начался'),
        ('bonus', 'Бонус получен'),
    ]

    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

