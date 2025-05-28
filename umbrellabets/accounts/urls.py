from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'accounts'

# Список маршрутов (URL patterns) для данного приложения
urlpatterns = [
    # URL /register/ будет обрабатывать функция register_view из файла views.py
    # Регистрация и подтверждение email
    path('register/', views.register_view, name='register'),
    path(
        'confirm-email/<uuid:confirmation_code>/',
        views.confirm_email_view,
        name='confirm-email'
    ),
    path(
        'resend-confirmation/',
        views.resend_confirmation_view,
        name='resend-confirmation'
    ),

    # URL /login/ — вход в аккаунт
    path('login/', views.login_view, name='login'),

    # URL /logout/ — выход из аккаунта
    path('logout/', views.logout_view, name='logout'),

    # URL /profile/ — отображение страницы профиля, доступно только авторизованным пользователям
    path('profile/', views.profile_view, name='profile'),

    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path(
        'account/password/',
        views.CustomPasswordChangeView.as_view(),
        name='password_change'
    ),
    path(
        'account/password/done/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='accounts/password_change_done.html'
        ),
        name='password_change_done'
    ),

    path('password-reset/',
         views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.html',  # HTML версия
             html_email_template_name='accounts/password_reset_email.html',  # Явное указание HTML
             subject_template_name='accounts/password_reset_subject.txt',
             success_url='/accounts/password-reset/done/'
         ),
         name='password_reset'),

    # Страница подтверждения отправки письма
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ),
         name='password_reset_done'),

    # Подтверждение сброса пароля (по ссылке из email)
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url='/accounts/password-reset/complete/'
         ),
         name='password_reset_confirm'),

    # Страница успешного сброса пароля
    path('password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ),
         name='password_reset_complete'),
]
