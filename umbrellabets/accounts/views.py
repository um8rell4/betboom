from django.shortcuts import render, redirect, reverse
from django.contrib.auth import login, authenticate, logout
from .forms import (
    UserRegisterForm, CustomPasswordChangeForm, UserEditForm,
    ProfileEditForm, EmailOrUsernameAuthenticationForm  # Добавить новую форму
)
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import UserProfile, Transaction
from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView, PasswordResetView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import uuid
from django.contrib.auth.models import User
from django.db.models import Q


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
    """
    from .models import Transaction

    try:
        profile = UserProfile.objects.get(
            email_confirmation_code=confirmation_code,
            email_confirmed=False
        )

        # Подтверждаем email и активируем аккаунт
        profile.email_confirmed = True
        profile.save()

        user = profile.user
        user.is_active = True
        user.save()

        print(f"DEBUG: Обрабатываем пользователя {user.username}")
        print(f"DEBUG: Баланс до обновления: {user.profile.balance}")

        # Активируем все pending реферальные бонусы для этого пользователя
        pending_transactions = Transaction.objects.filter(
            user=user,
            status='pending',
            transaction_type='referral_bonus'
        )

        print(f"DEBUG: Найдено pending транзакций: {pending_transactions.count()}")

        for transaction in pending_transactions:
            print(f"DEBUG: Обновляем транзакцию {transaction.transaction_id} с суммой {transaction.amount}")
            old_status = transaction.status
            transaction.status = 'completed'
            transaction.save()
            print(f"DEBUG: Транзакция обновлена с {old_status} на {transaction.status}")

        # Обновляем профиль из базы данных
        user.profile.refresh_from_db()
        print(f"DEBUG: Баланс после обновления: {user.profile.balance}")

        # Если есть реферер, активируем и его бонус
        if profile.referred_by:
            print(f"DEBUG: Обрабатываем реферера {profile.referred_by.username}")
            referrer_transactions = Transaction.objects.filter(
                user=profile.referred_by,
                status='pending',
                transaction_type='referral_bonus',
                comment__contains=user.username
            )

            print(f"DEBUG: Найдено транзакций реферера: {referrer_transactions.count()}")

            for transaction in referrer_transactions:
                print(f"DEBUG: Обновляем транзакцию реферера {transaction.transaction_id}")
                transaction.status = 'completed'
                transaction.save()

        login(request, user, backend='accounts.backends.EmailOrUsernameModelBackend')

        messages.success(
            request,
            "Ваш email успешно подтвержден! Бонусы начислены на ваш счет."
        )
        return redirect('accounts:profile')

    except UserProfile.DoesNotExist:
        messages.error(request, "Неверный код подтверждения.")
        return redirect('accounts:register')


def resend_confirmation_view(request):
    """
    Повторно отправляет письмо с подтверждением email.
    Работает для неавторизованных пользователей.
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            messages.error(request, "Введите email")
            return render(request, 'accounts/resend_confirmation.html')

        try:
            user = User.objects.get(email=email)
            if user.profile.email_confirmed:
                messages.warning(request, "Этот email уже подтвержден")
            else:
                # Генерируем новый код подтверждения
                profile = user.profile
                profile.email_confirmation_code = uuid.uuid4()
                profile.save()

                # Отправляем письмо
                profile.send_confirmation_email(request)
                messages.success(request, f"Письмо с подтверждением отправлено на {email}")

        except User.DoesNotExist:
            messages.error(request, "Пользователь с таким email не найден")
        except Exception as e:
            messages.error(request, f"Ошибка отправки письма: {str(e)}")

        return redirect('accounts:login')

    # GET запрос - показываем форму
    return render(request, 'accounts/resend_confirmation.html')


def login_view(request):
    # Если пользователь отправил данные формы (POST)
    if request.method == 'POST':
        # Используем нашу кастомную форму
        form = EmailOrUsernameAuthenticationForm(data=request.POST, request=request)
        # Если данные корректны (логин и пароль верны)
        if form.is_valid():
            # Получаем объект пользователя
            user = form.get_user()
            # Входим в систему от имени пользователя
            login(request, user)
            # Перенаправляем на профиль
            return redirect('accounts:profile')
        else:
            # Проверяем, есть ли ошибка активации аккаунта
            for error in form.non_field_errors():
                if 'не активирован' in str(error):
                    # Добавляем специальный тег для красивого отображения
                    messages.error(request, str(error), extra_tags='email_not_confirmed')
                    # Очищаем ошибки формы, чтобы не дублировать
                    form._errors.clear()
                    break
    else:
        # Если просто открыли страницу — создаём пустую форму авторизации
        form = EmailOrUsernameAuthenticationForm()

    # Отображаем шаблон входа с формой
    return render(request, 'accounts/login.html', {'form': form})



def logout_view(request):
    # Выходим из текущей сессии пользователя
    logout(request)
    # Перенаправляем на страницу входа
    return redirect('accounts:login')


@login_required  # Декоратор, который запрещает доступ к странице без авторизации
def profile_view(request):
    """Профиль пользователя"""
    # Обновить статистику при каждом просмотре профиля
    request.user.profile.update_betting_stats()

    context = {}
    return render(request, 'accounts/profile.html', context)


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


def leaderboard(request):
    """Рейтинг игроков"""
    from django.db.models import Sum, Count, F

    # Топ игроков по выигрышам
    top_winners = UserProfile.objects.filter(
        user__bets__status='won'
    ).annotate(
        total_winnings=Sum('user__bets__potential_win'),
        total_bets=Count('user__bets'),
        won_bets=Count('user__bets', filter=models.Q(user__bets__status='won'))
    ).order_by('-total_winnings')[:20]

    # Топ по проценту побед
    top_accuracy = UserProfile.objects.filter(
        user__bets__isnull=False
    ).annotate(
        total_bets=Count('user__bets'),
        won_bets=Count('user__bets', filter=models.Q(user__bets__status='won')),
        win_percentage=F('won_bets') * 100.0 / F('total_bets')
    ).filter(total_bets__gte=5).order_by('-win_percentage')[:20]

    context = {
        'top_winners': top_winners,
        'top_accuracy': top_accuracy
    }
    return render(request, 'accounts/leaderboard.html', context)


