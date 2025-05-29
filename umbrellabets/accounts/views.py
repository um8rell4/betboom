from django.shortcuts import render, redirect, reverse
from django.contrib.auth import login, authenticate, logout
from .forms import UserRegisterForm, CustomPasswordChangeForm, UserEditForm, ProfileEditForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView, PasswordResetView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import uuid


def register_view(request):
    """
    Обработка регистрации нового пользователя с подтверждением email и реферальной системой.
    Сохраняет пользователя с is_active=False, отправляет письмо с подтверждением,
    обрабатывает реферальные коды и начисляет бонусы.
    """
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            # Сохраняем пользователя через форму (форма уже обрабатывает реферальную систему)
            user = form.save()

            try:
                # Отправка письма с подтверждением
                user.profile.send_confirmation_email(request)

                # Определяем тип бонуса для сообщения
                bonus_message = ""
                if hasattr(user, 'profile') and user.profile.referred_by:
                    bonus_message = "Вам начислен реферальный бонус: 5000"
                else:
                    bonus_message = "Вам начислен стартовый бонус: 5000"

                # Информируем пользователя о регистрации и бонусе
                messages.success(
                    request,
                    f"Регистрация почти завершена! "
                    f"Пожалуйста, проверьте ваш email и перейдите по ссылке для подтверждения. "
                    f"{bonus_message}"
                )
                return redirect('accounts:login')  # Перенаправляем на страницу входа

            except Exception as e:
                # В случае ошибки отправки - удаляем пользователя и сообщаем об ошибке
                user.delete()
                messages.error(
                    request,
                    f"Ошибка при отправке письма подтверждения: {str(e)}. "
                    "Пожалуйста, попробуйте еще раз."
                )
                return redirect('accounts:register')
    else:
        # Автозаполнение реферального кода из GET-параметра
        initial = {}
        if 'ref' in request.GET:
            initial['referral_code'] = request.GET['ref']
        form = UserRegisterForm(initial=initial)

    return render(request, 'accounts/register.html', {'form': form})


def send_confirmation_email(request, user):
    """
    Отправляет письмо с подтверждением email новому пользователю.
    """
    profile = user.profile
    subject = "Подтвердите ваш email на UmbrellaBet"

    # Используем правильное имя URL с учетом пространства имен
    confirm_url = request.build_absolute_uri(
        reverse('accounts:confirm-email', kwargs={'confirmation_code': profile.email_confirmation_code})
    )

    context = {
        'user': user,
        'confirm_url': confirm_url,  # Теперь передаем полный URL
        'domain': request.get_host(),
        'protocol': 'https' if request.is_secure() else 'http',
    }

    html_message = render_to_string('accounts/email_confirmation_email.html', context)
    plain_message = strip_tags(html_message)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def confirm_email_view(request, confirmation_code):
    """
    Обрабатывает подтверждение email по ссылке из письма.
    Активирует аккаунт пользователя при успешном подтверждении.
    """
    print(f"Received confirmation_code: {confirmation_code}")
    print(f"Type of confirmation_code: {type(confirmation_code)}")

    # Проверим, есть ли вообще профили с неподтвержденным email
    unconfirmed_profiles = UserProfile.objects.filter(email_confirmed=False)
    print(f"Unconfirmed profiles count: {unconfirmed_profiles.count()}")

    for profile in unconfirmed_profiles:
        print(
            f"Profile {profile.user.username}: code={profile.email_confirmation_code}, type={type(profile.email_confirmation_code)}")

    try:
        # Ищем профиль с неподтвержденным email и совпадающим кодом
        profile = UserProfile.objects.get(
            email_confirmation_code=confirmation_code,
            email_confirmed=False
        )

        print(f"Found matching profile: {profile.user.username}")

        # Подтверждаем email и активируем аккаунт
        profile.email_confirmed = True
        profile.save()

        user = profile.user
        user.is_active = True  # Активируем аккаунт
        user.save()

        # Автоматически входим пользователя после подтверждения
        login(request, user)

        messages.success(
            request,
            "Ваш email успешно подтвержден! Добро пожаловать на UmbrellaBet."
        )
        return redirect('accounts:profile')

    except UserProfile.DoesNotExist:
        print("Profile not found with given confirmation code")
        messages.error(
            request,
            "Неверный или устаревший код подтверждения. "
            "Пожалуйста, зарегистрируйтесь снова."
        )
        return redirect('accounts:register')


@login_required
def resend_confirmation_view(request):
    """
    Повторно отправляет письмо с подтверждением email.
    Доступно только для аутентифицированных пользователей.
    """
    if request.user.profile.email_confirmed:
        messages.warning(request, "Ваш email уже подтвержден")
        return redirect('accounts:profile')

    # Генерируем новый код подтверждения
    profile = request.user.profile
    profile.email_confirmation_code = uuid.uuid4()
    profile.save()

    try:
        send_confirmation_email(request, request.user)
        messages.info(request, "Письмо с подтверждением отправлено повторно")
    except Exception as e:
        messages.error(
            request,
            f"Ошибка отправки письма: {str(e)}. Пожалуйста, попробуйте позже."
        )

    return redirect('accounts:profile')


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
