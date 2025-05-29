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
        if (not request.user.is_authenticated or
                request.path.startswith('/admin/') or
                request.path.startswith('/api/')):
            return None

        if (hasattr(request.user, 'profile') and
                not request.user.profile.email_confirmed):

            # URL, которые доступны без подтверждения
            exempt_urls = [
                reverse('accounts:logout'),
                reverse('accounts:resend-confirmation'),
                reverse('accounts:profile'),
            ]

            # Проверяем URL confirm-email по паттерну, а не точному совпадению
            if (request.path not in exempt_urls and
                    not request.path.startswith('/accounts/confirm-email/')):
                return HttpResponseRedirect(
                    reverse('accounts:profile') + '?verify_email=1'
                )

        return None
