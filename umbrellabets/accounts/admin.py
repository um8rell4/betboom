from django.contrib import admin
from .models import UserProfile, Transaction


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'balance', 'total_bets', 'won_bets',
        'win_rate_display', 'email_confirmed', 'is_admin'
    ]
    list_filter = ['email_confirmed', 'is_admin', 'referred_by']
    search_fields = ['user__username', 'user__email', 'referral_code']
    readonly_fields = ['referral_code', 'email_confirmation_code', 'win_rate_display']

    def win_rate_display(self, obj):
        return f"{obj.win_rate}%"

    win_rate_display.short_description = "Процент побед"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id_short', 'user', 'transaction_type',
        'amount', 'status', 'created_at'
    ]
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = [
        'user__username', 'comment', 'transaction_id'
    ]
    readonly_fields = ['transaction_id', 'created_at']
    date_hierarchy = 'created_at'

    def transaction_id_short(self, obj):
        """Показываем короткую версию UUID"""
        return str(obj.transaction_id)[:8] + "..."

    transaction_id_short.short_description = "ID транзакции"

    def save_model(self, request, obj, form, change):
        """Переопределяем сохранение для логирования изменений статуса"""
        if change:
            original = Transaction.objects.get(pk=obj.pk)
            if original.status != obj.status:
                self.message_user(
                    request,
                    f"Статус транзакции {obj.transaction_id} изменен с "
                    f"'{original.get_status_display()}' на '{obj.get_status_display()}'. "
                    f"Баланс пользователя обновлен автоматически."
                )
        super().save_model(request, obj, form, change)