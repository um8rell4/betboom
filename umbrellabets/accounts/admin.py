from django.contrib import admin
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import UserProfile, Transaction
import uuid


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'balance', 'total_bets', 'won_bets',
        'win_rate_display', 'email_confirmed', 'user_is_active'
    ]
    list_filter = ['email_confirmed', 'is_admin', 'referred_by']
    search_fields = ['user__username', 'user__email', 'referral_code']
    readonly_fields = ['referral_code', 'email_confirmation_code', 'win_rate_display']
    actions = [
        'confirm_email_and_activate',
        'resend_confirmation_email',
        'deactivate_users'
    ]

    def user_is_active(self, obj):
        return obj.user.is_active

    user_is_active.boolean = True
    user_is_active.short_description = "Активен"

    def win_rate_display(self, obj):
        return f"{obj.win_rate}%"

    win_rate_display.short_description = "Процент побед"

    def confirm_email_and_activate(self, request, queryset):
        """Подтвердить email и активировать пользователей"""
        updated = 0
        for profile in queryset:
            if not profile.email_confirmed:
                profile.email_confirmed = True
                profile.user.is_active = True
                profile.save()
                profile.user.save()
                updated += 1

        self.message_user(
            request,
            f"Email подтвержден и пользователи активированы: {updated}",
            messages.SUCCESS
        )

    confirm_email_and_activate.short_description = "Подтвердить email и активировать"

    def resend_confirmation_email(self, request, queryset):
        """Повторно отправить письмо подтверждения"""
        sent = 0
        errors = 0

        for profile in queryset:
            if not profile.email_confirmed:
                try:
                    # Генерируем новый код подтверждения
                    profile.email_confirmation_code = uuid.uuid4()
                    profile.save()

                    # Отправляем письмо
                    self._send_confirmation_email(profile, request)
                    sent += 1
                except Exception as e:
                    errors += 1
                    self.message_user(
                        request,
                        f"Ошибка отправки письма для {profile.user.username}: {str(e)}",
                        messages.ERROR
                    )

        if sent > 0:
            self.message_user(
                request,
                f"Письма подтверждения отправлены: {sent}",
                messages.SUCCESS
            )
        if errors > 0:
            self.message_user(
                request,
                f"Ошибки при отправке: {errors}",
                messages.ERROR
            )

    resend_confirmation_email.short_description = "Отправить письмо подтверждения"

    def deactivate_users(self, request, queryset):
        """Деактивировать пользователей"""
        updated = 0
        for profile in queryset:
            profile.email_confirmed = False
            profile.user.is_active = False
            profile.save()
            profile.user.save()
            updated += 1

        self.message_user(
            request,
            f"Пользователи деактивированы: {updated}",
            messages.SUCCESS
        )

    deactivate_users.short_description = "Деактивировать пользователей"

    def _send_confirmation_email(self, profile, request):
        """Отправка письма подтверждения из админки"""
        from django.urls import reverse

        # Создаем URL подтверждения
        confirm_url = request.build_absolute_uri(
            reverse('accounts:confirm-email',
                    kwargs={'confirmation_code': profile.email_confirmation_code})
        )

        subject = "Подтверждение email на CyberBet"

        # Рендер HTML шаблона
        html_message = render_to_string('accounts/email_confirmation_email.html', {
            'user': profile.user,
            'confirmation_code': profile.email_confirmation_code,
            'confirm_url': confirm_url,
            'domain': request.get_host(),
            'protocol': 'https' if request.is_secure() else 'http',
        })

        # Отправка письма
        send_mail(
            subject=subject,
            message=strip_tags(html_message),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[profile.user.email],
            html_message=html_message,
            fail_silently=False,
        )


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
        return str(obj.transaction_id)[:8] + "..."

    transaction_id_short.short_description = "ID транзакции"

    def save_model(self, request, obj, form, change):
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