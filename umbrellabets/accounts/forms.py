from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import UserChangeForm
from .models import UserProfile
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from django.utils.translation import gettext as _


#Форма регистрации пользователя
class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2'] #Поля при регистрации


User = get_user_model()


class UserEditForm(UserChangeForm):
    email = forms.EmailField(label="Email", required=True)
    first_name = forms.CharField(label="Имя", required=False)
    last_name = forms.CharField(label="Фамилия", required=False)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('avatar',)
        widgets = {
            'avatar': forms.FileInput(attrs={'accept': 'image/*'})
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({
            'placeholder': 'Введите текущий пароль',
            'autocomplete': 'current-password'
        })
        self.fields['new_password1'].widget.attrs.update({
            'placeholder': 'Новый пароль',
            'autocomplete': 'new-password'
        })
        self.fields['new_password2'].widget.attrs.update({
            'placeholder': 'Подтвердите новый пароль',
            'autocomplete': 'new-password'
        })

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")
        if not self.user.check_password(old_password):
            raise forms.ValidationError(
                _("Неверный текущий пароль. Пожалуйста, попробуйте снова."),
                code='password_incorrect',
            )
        return old_password
