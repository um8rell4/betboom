from django.db import models
from django.contrib.auth.models import User #Импорт встроенных в джанго User'ов
from django.dispatch import receiver
from django.db.models.signals import post_save
import os


def user_avatar_path(instance, filename):
    # Файл будет загружен в MEDIA_ROOT/user_<id>/avatar/<filename>
    return f'user_{instance.user.id}/avatar/{filename}'


class UserProfile(models.Model):
    # Расширяем дефолтных пользователей, представленных Django
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to=user_avatar_path, null=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)  # стартовый баланс
    referral_code = models.CharField(max_length=10, blank=True, unique=True) #Реферальный код каждого пользователя
    is_admin = models.BooleanField(default=False)  # для будущих ролей

    def save(self, *args, **kwargs):
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

    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            UserProfile.objects.create(user=instance)

    @receiver(post_save, sender=User)
    def save_user_profile(sender, instance, **kwargs):
        instance.profile.save()