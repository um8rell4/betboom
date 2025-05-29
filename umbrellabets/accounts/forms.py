from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from .models import UserProfile
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
import uuid


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

            # Получаем профиль (уже создан сигналом с кодом подтверждения)
            profile = user.profile

            # Обработка реферального кода
            referral_code = self.cleaned_data.get('referral_code')
            if referral_code:
                try:
                    referrer_profile = UserProfile.objects.get(referral_code=referral_code)
                    profile.referred_by = referrer_profile.user
                    # Добавляем бонус рефереру (если метод существует)
                    if hasattr(referrer_profile, 'add_referral_bonus'):
                        referrer_profile.add_referral_bonus(user)
                except UserProfile.DoesNotExist:
                    pass  # Код уже проверен в clean_referral_code

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