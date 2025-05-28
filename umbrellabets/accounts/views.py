from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from .forms import UserRegisterForm, CustomPasswordChangeForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import UserEditForm, ProfileEditForm
from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView, PasswordResetView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin



def register_view(request):
    # Если запрос отправлен методом POST (то есть пользователь нажал кнопку "Зарегистрироваться")
    if request.method == 'POST':
        # Создаём форму с данными из запроса
        form = UserRegisterForm(request.POST)
        # Проверяем, валидна ли форма
        if form.is_valid():
            # Сохраняем нового пользователя в базу данных
            user = form.save()
            # Выполняем вход пользователя в систему
            login(request, user)
            # Перенаправляем на страницу профиля
            return redirect('accounts:profile')
    else:
        # Если запрос GET — создаём пустую форму для отображения
        form = UserRegisterForm()

    # Отображаем шаблон регистрации с формой
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    # Если пользователь отправил данные формы (POST)
    if request.method == 'POST':
        # Подставляем данные в стандартную форму авторизации Django
        form = AuthenticationForm(data=request.POST)
        # Если данные корректны (логин и пароль верны)
        if form.is_valid():
            # Получаем объект пользователя
            user = form.get_user()
            # Входим в систему от имени пользователя
            login(request, user)
            # Перенаправляем на профиль
            return redirect('accounts:profile')
    else:
        # Если просто открыли страницу — создаём пустую форму авторизации
        form = AuthenticationForm()

    # Отображаем шаблон входа с формой
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    # Выходим из текущей сессии пользователя
    logout(request)
    # Перенаправляем на страницу входа
    return redirect('accounts:login')


@login_required  # Декоратор, который запрещает доступ к странице без авторизации
def profile_view(request):
    # Отображаем страницу профиля
    return render(request, 'accounts/profile.html')


@login_required
def edit_profile(request):
    if request.method == 'POST':
        user_form = UserEditForm(request.POST, instance=request.user)
        profile_form = ProfileEditForm(
            request.POST,
            request.FILES,
            instance=request.user.profile
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Профиль успешно обновлен')
            return redirect('accounts:profile')
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=request.user.profile)

    return render(request, 'accounts/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


class CustomPasswordChangeView(PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:password_change_done')


class CustomPasswordResetView(SuccessMessageMixin, PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')
    success_message = "Инструкции по сбросу пароля были отправлены на ваш email."

    # Дополнительная валидация email
    def form_valid(self, form):
        # Можно добавить логику проверки, существует ли пользователь с таким email
        return super().form_valid(form)
