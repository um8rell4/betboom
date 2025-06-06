from django.core.management.base import BaseCommand
from accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Обновить статистику всех пользователей'

    def handle(self, *args, **options):
        profiles = UserProfile.objects.all()

        for profile in profiles:
            profile.update_betting_stats()
            self.stdout.write(f'Обновлена статистика для {profile.user.username}')

        self.stdout.write(
            self.style.SUCCESS(f'Обновлена статистика {profiles.count()} пользователей')
        )