from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from .models import Match, Sport, Odds, Bet
from accounts.models import User
from accounts.models import Transaction
import json


def matches_list(request):
    """Список всех матчей"""
    sport_filter = request.GET.get('sport', 'all')

    # Получить live матчи
    live_matches = Match.objects.filter(
        status='live'
    ).select_related('sport').prefetch_related('odds__bookmaker')

    if sport_filter != 'all':
        live_matches = live_matches.filter(sport__key=sport_filter)

    # Получить предстоящие матчи
    upcoming_matches = Match.objects.filter(
        commence_time__gte=timezone.now(),
        status='upcoming'
    ).select_related('sport').prefetch_related('odds__bookmaker')

    if sport_filter != 'all':
        upcoming_matches = upcoming_matches.filter(sport__key=sport_filter)

    sports = Sport.objects.filter(active=True)

    # Группируем предстоящие матчи по спорту
    matches_by_sport = {}
    for match in upcoming_matches:
        sport_key = match.sport.key
        if sport_key not in matches_by_sport:
            matches_by_sport[sport_key] = {
                'sport': match.sport,
                'matches': []
            }
        matches_by_sport[sport_key]['matches'].append(match)

    # Добавить статистику
    total_matches = Match.objects.count()
    total_bets = Bet.objects.count()
    total_users = User.objects.filter(bets__isnull=False).distinct().count()
    upcoming_count = matches_by_sport.values() if matches_by_sport else 0

    context = {
        'live_matches': live_matches,
        'matches_by_sport': matches_by_sport,
        'sports': sports,
        'current_sport': sport_filter,
        'total_matches': total_matches,
        'total_bets': total_bets,
        'total_users': total_users,
        'upcoming_count': sum(
            len(sport_data['matches']) for sport_data in matches_by_sport.values()) if matches_by_sport else 0
    }
    return render(request, 'matches/matches_list.html', context)


def match_detail(request, match_id):
    """Детальная страница матча"""
    match = get_object_or_404(Match, id=match_id)

    # Получить лучшие коэффициенты для каждого исхода
    home_odds = match.odds.filter(outcome='home').order_by('-price').first()
    away_odds = match.odds.filter(outcome='away').order_by('-price').first()

    # Подготовить коэффициенты для JavaScript (без локализации)
    odds_data = {}
    for odds in match.odds.all():
        odds_data[odds.id] = float(odds.price)

    odds_json = json.dumps(odds_data)

    # Получить лучшие коэффициенты для каждого исхода
    home_odds = match.odds.filter(outcome='home').order_by('-price').first()
    away_odds = match.odds.filter(outcome='away').order_by('-price').first()

    # Статистика ставок на этот матч
    total_bets = match.bets.count()
    home_bets_count = match.bets.filter(outcome='home').count()
    away_bets_count = match.bets.filter(outcome='away').count()

    # Проценты ставок
    home_percentage = (home_bets_count / total_bets * 100) if total_bets > 0 else 50
    away_percentage = (away_bets_count / total_bets * 100) if total_bets > 0 else 50

    # Проверить, может ли пользователь делать ставки
    can_bet = match.commence_time > timezone.now() and match.status == 'upcoming'

    context = {
         'match': match,
        'home_odds': home_odds,
        'away_odds': away_odds,
        'odds_json': odds_json,
        'total_bets': total_bets,
        'home_percentage': round(home_percentage, 1),
        'away_percentage': round(away_percentage, 1),
        'can_bet': can_bet,
        'odds': match.odds.select_related('bookmaker').order_by('outcome')
    }
    return render(request, 'matches/match_detail.html', context)


@login_required
def place_bet(request, match_id):
    """Размещение ставки"""
    if request.method == 'POST':
        match = get_object_or_404(Match, id=match_id)

        # Проверяем, что матч еще не начался
        if match.commence_time <= timezone.now() or match.status != 'upcoming':
            messages.error(request, "Ставки на этот матч больше не принимаются")
            return redirect('matches:match_detail', match_id=match_id)

        outcome = request.POST.get('outcome')
        amount = request.POST.get('amount')

        try:
            amount = Decimal(amount)

            # Минимальная ставка
            if amount < 10:
                messages.error(request, "Минимальная ставка: 10 🪙")
                return redirect('matches:match_detail', match_id=match_id)

            # Проверяем баланс
            if request.user.profile.balance < amount:
                messages.error(request, "Недостаточно средств на счете")
                return redirect('matches:match_detail', match_id=match_id)

            # Найти актуальный коэффициент
            odds_obj = match.odds.filter(outcome=outcome).first()
            if not odds_obj:
                messages.error(request, "Коэффициент не найден")
                return redirect('matches:match_detail', match_id=match_id)

            # Создаем ставку
            bet = Bet.objects.create(
                user=request.user,
                match=match,
                outcome=outcome,
                amount=amount,
                odds=odds_obj.price,
                potential_win=amount * odds_obj.price
            )

            # Списываем средства с баланса
            request.user.profile.balance -= amount
            request.user.profile.save()

            # Создаем транзакцию
            from accounts.models import Transaction
            Transaction.objects.create(
                user=request.user,
                amount=-amount,  # Отрицательная сумма для списания
                transaction_type='bet',
                status='completed',
                comment=f'Ставка на матч {match.home_team} vs {match.away_team}'
            )

            messages.success(request, f"✅ Ставка размещена! Возможный выигрыш: {bet.potential_win} 🪙")
            return redirect('accounts:profile')

        except (ValueError, TypeError):
            messages.error(request, "Некорректные данные ставки")

    return redirect('matches:match_detail', match_id=match_id)
