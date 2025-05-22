from django.urls import path
from . import views

app_name = 'accounts'

# Список маршрутов (URL patterns) для данного приложения
urlpatterns = [
    # URL /register/ будет обрабатывать функция register_view из файла views.py
    # Имя маршрута — 'register', можно использовать в шаблонах и redirect'ах
    path('register/', views.register_view, name='register'),

    # URL /login/ — вход в аккаунт
    path('login/', views.login_view, name='login'),

    # URL /logout/ — выход из аккаунта
    path('logout/', views.logout_view, name='logout'),

    # URL /profile/ — отображение страницы профиля, доступно только авторизованным пользователям
    path('profile/', views.profile_view, name='profile'),
]
