from django.http import HttpResponseRedirect
from django.urls import reverse


class EmailConfirmationMiddleware:
    """
    Middleware для проверки подтверждения email.
    Перенаправляет пользователей с неподтвержденным email на страницу с уведомлением.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Пропускаем следующие случаи:
        # 1. Неаутентифицированные пользователи
        # 2. Запросы к API или админке
        # 3. URL, которые должны быть доступны без подтверждения
        if (not request.user.is_authenticated or
                request.path.startswith('/admin/') or
                request.path.startswith('/api/')):
            return None

        # Проверяем подтверждение email
        if (hasattr(request.user, 'profile') and
                not request.user.profile.email_confirmed):

            # URL, которые доступны без подтверждения
            exempt_urls = [
                reverse('accounts:logout'),
                reverse('accounts:resend-confirmation'),
                reverse('accounts:confirm-email', args=['00000000-0000-0000-0000-000000000000']),
                reverse('accounts:profile'),
            ]

            if request.path not in exempt_urls:
                # Перенаправляем на страницу аккаунта с флагом
                return HttpResponseRedirect(
                    reverse('accounts:profile') + '?verify_email=1'
                )

        return None