from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Кастомный бэкенд аутентификации, позволяющий входить
    как по username, так и по email
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get('username')

        if username is None or password is None:
            return None

        try:
            # Ищем пользователя по username или email
            user = User.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
        except User.DoesNotExist:
            # Запускаем хэширование пароля для защиты от timing атак
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            # Если найдено несколько пользователей (что не должно происходить)
            return None

        # Проверяем пароль и активность пользователя
        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
