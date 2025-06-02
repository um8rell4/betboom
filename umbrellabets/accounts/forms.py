from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm, AuthenticationForm
from .models import UserProfile
from django.utils.translation import gettext as _
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db.models import Q


class UserRegisterForm(UserCreationForm):
    """
    Расширенная форма регистрации с подтверждением email.
    Наследует от UserCreationForm и добавляет:
    - Обязательное поле email
    - Валидацию уникальности email
    - Автоматическую деактивацию пользователя до подтверждения email
    """
    email = forms.EmailField(
        required=True,
        label="Email",
        help_text="На этот адрес будет отправлено письмо с подтверждением"
    )

    referral_code = forms.CharField(
        required=False,
        label='Реферальный код (если есть)',
        widget=forms.TextInput(attrs={'placeholder': 'Необязательно'}),
        help_text="Введите код друга, который вас пригласил"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'referral_code']

    def clean_referral_code(self):
        """Проверяет корректность реферального кода"""
        code = self.cleaned_data.get('referral_code')
        if code:
            if not UserProfile.objects.filter(referral_code=code).exists():
                raise forms.ValidationError("Неверный реферальный код")
        return code

    def clean_email(self):
        """Проверяет, что email уникален и не используется другим пользователем"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Этот email уже используется другим пользователем")
        return email

    def save(self, commit=True):
        """
        Сохраняет пользователя с is_active=False
        """
        user = super().save(commit=False)
        user.is_active = False  # Аккаунт неактивен до подтверждения email

        if commit:
            user.save()

            # Получаем профиль (уже создан сигналом)
            profile = user.profile

            # Обработка реферального кода
            referral_code = self.cleaned_data.get('referral_code')
            if referral_code:
                try:
                    referrer_profile = UserProfile.objects.get(referral_code=referral_code)
                    profile.referred_by = referrer_profile.user

                    # Создаем pending транзакции
                    from .models import Transaction
                    from decimal import Decimal

                    # Транзакция для нового пользователя
                    Transaction.objects.create(
                        user=user,
                        amount=Decimal('5000.00'),
                        transaction_type='referral_bonus',
                        status='pending',
                        comment='Стартовый бонус за регистрацию'
                    )

                    # Транзакция для реферера
                    Transaction.objects.create(
                        user=referrer_profile.user,
                        amount=Decimal('2500.00'),
                        transaction_type='referral_bonus',
                        status='pending',
                        comment=f'Реферальный бонус за приглашение {user.username}'
                    )

                except UserProfile.DoesNotExist:
                    pass
            else:
                # Стартовый бонус без реферера
                from .models import Transaction
                from decimal import Decimal

                Transaction.objects.create(
                    user=user,
                    amount=Decimal('5000.00'),
                    transaction_type='referral_bonus',
                    status='pending',
                    comment='Стартовый бонус за регистрацию'
                )

            profile.save()

        return user


class UserEditForm(UserChangeForm):
    """
    Форма редактирования данных пользователя.
    Позволяет изменять email, имя и фамилию.
    """
    email = forms.EmailField(label="Email", required=True)
    first_name = forms.CharField(label="Имя", required=False)
    last_name = forms.CharField(label="Фамилия", required=False)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')


class ProfileEditForm(forms.ModelForm):
    """
    Форма редактирования профиля пользователя.
    Позволяет изменять аватарку.
    """

    class Meta:
        model = UserProfile
        fields = ('avatar',)
        widgets = {
            'avatar': forms.FileInput(attrs={
                'accept': 'image/*',
                'class': 'form-control-file'
            })
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Кастомная форма смены пароля с улучшенными сообщениями об ошибках
    и кастомизированными placeholder'ами.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Настраиваем атрибуты полей
        self.fields['old_password'].widget.attrs.update({
            'placeholder': 'Введите текущий пароль',
            'autocomplete': 'current-password',
            'class': 'form-control'
        })
        self.fields['new_password1'].widget.attrs.update({
            'placeholder': 'Новый пароль',
            'autocomplete': 'new-password',
            'class': 'form-control'
        })
        self.fields['new_password2'].widget.attrs.update({
            'placeholder': 'Подтвердите новый пароль',
            'autocomplete': 'new-password',
            'class': 'form-control'
        })

    def clean_old_password(self):
        """
        Проверяет, что старый пароль введен правильно.
        Выдает более понятное сообщение об ошибке.
        """
        old_password = self.cleaned_data.get("old_password")
        if not self.user.check_password(old_password):
            raise ValidationError(
                _("Неверный текущий пароль. Пожалуйста, попробуйте снова."),
                code='password_incorrect',
            )
        return old_password


class EmailConfirmationForm(forms.Form):
    """
    Форма для повторной отправки письма подтверждения email.
    """
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'placeholder': 'Введите ваш email',
            'class': 'form-control'
        })
    )

    def clean_email(self):
        """Проверяет, что email существует и не подтвержден"""
        email = self.cleaned_data.get('email')
        try:
            user = User.objects.get(email=email)
            if user.profile.email_confirmed:
                raise ValidationError("Этот email уже подтвержден")
        except User.DoesNotExist:
            raise ValidationError("Пользователь с таким email не найден")
        return email


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    """
    Кастомная форма входа, поддерживающая вход по email или username
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Изменяем label и placeholder для поля username
        self.fields['username'].label = 'Email или имя пользователя'
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Введите email или имя пользователя',
            'class': 'form-control'
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Введите пароль',
            'class': 'form-control'
        })

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            # Сначала проверяем, существует ли пользователь
            try:
                user = User.objects.get(
                    Q(username__iexact=username) | Q(email__iexact=username)
                )

                # Проверяем пароль
                if user.check_password(password):
                    # Пароль верный, но проверяем активацию
                    if not user.is_active:
                        if hasattr(user, 'profile') and not user.profile.email_confirmed:
                            raise ValidationError(
                                "Аккаунт не активирован. Проверьте email для подтверждения регистрации.",
                                code='account_not_activated',
                            )
                        else:
                            raise ValidationError(
                                "Аккаунт заблокирован. Обратитесь в поддержку.",
                                code='account_disabled',
                            )

                    # Все в порядке, аутентифицируем
                    self.user_cache = authenticate(
                        self.request,
                        username=username,
                        password=password
                    )
                    if self.user_cache is None:
                        raise self.get_invalid_login_error()
                    else:
                        self.confirm_login_allowed(self.user_cache)
                else:
                    # Неверный пароль
                    raise self.get_invalid_login_error()

            except User.DoesNotExist:
                # Пользователь не найден
                raise self.get_invalid_login_error()

        return self.cleaned_data

    def get_invalid_login_error(self):
        return ValidationError(
            "Неверный email/имя пользователя или пароль.",
            code='invalid_login',
        )
