from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, Transaction
from .utils import generate_unique_referral_code


#Сигнал, который срабатывает, когда создается User
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        profile = UserProfile.objects.create(user=instance)
        #Генерация уникального реф кода
        profile.referral_code = generate_unique_referral_code()
        profile.save()


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Сохраняет профиль при сохранении пользователя"""
    instance.profile.save()


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