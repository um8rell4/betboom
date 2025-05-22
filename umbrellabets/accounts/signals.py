from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile
from .utils import generate_unique_referral_code


#Сигнал, который срабатывает, когда создается User
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        profile = UserProfile.objects.create(user=instance)
        #Генерация уникального реф кода
        profile.referral_code = generate_unique_referral_code()
        profile.save()


#Сигналы для авто-создания профиля при регистрации
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
