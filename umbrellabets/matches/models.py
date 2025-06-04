from django.db import models
from django.utils import timezone


class Sport(models.Model):
    key = models.CharField(max_length=50, unique=True)  # 'cs2', 'dota2'
    title = models.CharField(max_length=100)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class Match(models.Model):
    STATUS_CHOICES = [
        ('upcoming', 'Предстоящий'),
        ('live', 'В прямом эфире'),
        ('completed', 'Завершен'),
    ]

    # Данные от API
    api_id = models.CharField(max_length=100, unique=True)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE)

    # Команды
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)

    # Время
    commence_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')

    # Мета
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['commence_time']

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"


class Bookmaker(models.Model):
    key = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=100)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class Odds(models.Model):
    OUTCOME_CHOICES = [
        ('home', 'Победа хозяев'),
        ('away', 'Победа гостей'),
        ('draw', 'Ничья'),  # Если применимо
    ]

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='odds')
    bookmaker = models.ForeignKey(Bookmaker, on_delete=models.CASCADE)

    # Коэффициенты
    outcome = models.CharField(max_length=10, choices=OUTCOME_CHOICES)
    price = models.DecimalField(max_digits=6, decimal_places=2)  # Коэффициент

    # Мета
    last_update = models.DateTimeField()

    class Meta:
        unique_together = ['match', 'bookmaker', 'outcome']


class Bet(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('won', 'Выиграна'),
        ('lost', 'Проиграна'),
        ('cancelled', 'Отменена'),
    ]

    OUTCOME_CHOICES = [
        ('home', 'Победа хозяев'),
        ('away', 'Победа гостей'),
    ]

    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='bets')
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='bets')

    outcome = models.CharField(max_length=10, choices=OUTCOME_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    odds = models.DecimalField(max_digits=6, decimal_places=2)
    potential_win = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.match} - {self.amount}"
