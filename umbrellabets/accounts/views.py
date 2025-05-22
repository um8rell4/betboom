from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from .forms import UserRegisterForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required



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
