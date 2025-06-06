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

    RESULT_CHOICES = [
        ('home', 'Победа хозяев'),
        ('away', 'Победа гостей'),
        ('cancelled', 'Отменен'),
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

    # ДОБАВИТЬ ЭТО ПОЛЕ
    result = models.CharField(
        max_length=10,
        choices=RESULT_CHOICES,
        blank=True,
        null=True,
        help_text="Результат матча (заполняется после завершения)"
    )

    # Мета
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['commence_time']

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"

    # ДОБАВИТЬ ЭТИ МЕТОДЫ
    def finish_match(self, winner):
        """Завершить матч и рассчитать ставки"""
        if self.status == 'completed' and self.result:
            return False, "Матч уже завершен"

        self.status = 'completed'
        self.result = winner
        self.save()

        # Рассчитать ставки
        return self.calculate_bets()

    def calculate_bets(self):
        """Рассчитать все ставки на матч"""
        from accounts.models import Transaction

        if not self.result:
            return False, "Результат матча не установлен"

        # Получить все активные ставки
        pending_bets = self.bets.filter(status='pending')

        winners_count = 0
        losers_count = 0
        total_payout = 0

        for bet in pending_bets:
            if self.result == 'cancelled':
                # При отмене матча - вернуть деньги
                bet.status = 'cancelled'
                bet.save()

                # Вернуть сумму ставки на баланс
                bet.user.profile.balance += bet.amount
                bet.user.profile.save()

                # Создать транзакцию возврата
                Transaction.objects.create(
                    user=bet.user,
                    amount=bet.amount,
                    transaction_type='refund',
                    status='completed',
                    comment=f'Возврат за отмененный матч {self.home_team} vs {self.away_team}'
                )

            elif bet.outcome == self.result:
                old_balance = bet.user.profile.balance

                print(f"🔍 Bet ID: {bet.id}")
                print(f"💰 Amount: {bet.amount}")
                print(f"📊 Odds: {bet.odds}")
                print(f"🎯 Potential win: {bet.potential_win}")
                print(f"💳 Balance before: {old_balance}")

                # Выигрышная ставка
                bet.status = 'won'
                bet.save()

                # Перезагрузить из базы для проверки
                bet.user.refresh_from_db()

                print(f"💳 Balance after: {bet.user.profile.balance}")
                print(f"➕ Added: {bet.user.profile.balance - old_balance}")
                print("---")

                # Создать транзакцию выигрыша
                Transaction.objects.create(
                    user=bet.user,
                    amount=bet.potential_win,
                    transaction_type='win',
                    status='completed',
                    comment=f'Выигрыш по ставке на {self.home_team} vs {self.away_team}'
                )

                winners_count += 1
                total_payout += bet.potential_win

            else:
                # Проигрышная ставка
                bet.status = 'lost'
                bet.save()
                losers_count += 1

        if self.result == 'cancelled':
            return True, f"Матч отменен. Возвращены деньги по {pending_bets.count()} ставкам"
        else:
            return True, f"Обработано ставок: {winners_count} выигрышных, {losers_count} проигрышных. Выплачено: {total_payout} 🪙"


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
