from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from .models import Match, Sport, Odds
from accounts.models import Transaction


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

    context = {
        'live_matches': live_matches,
        'matches_by_sport': matches_by_sport,
        'sports': sports,
        'current_sport': sport_filter
    }
    return render(request, 'matches/matches_list.html', context)


def match_detail(request, match_id):
    """Детальная страница матча"""
    match = get_object_or_404(Match, id=match_id)

    # Получаем лучшие коэффициенты
    best_odds = {}
    for odds in match.odds.all():
        if odds.outcome not in best_odds or odds.price > best_odds[odds.outcome].price:
            best_odds[odds.outcome] = odds

    context = {
        'match': match,
        'best_odds': best_odds,
        'all_odds': match.odds.select_related('bookmaker').order_by('outcome', '-price')
    }
    return render(request, 'matches/match_detail.html', context)


@login_required
def place_bet(request, match_id):
    """Размещение ставки"""
    if request.method == 'POST':
        match = get_object_or_404(Match, id=match_id)

        # Проверяем, что матч еще не начался
        if match.commence_time <= timezone.now():
            messages.error(request, "Ставки на этот матч больше не принимаются")
            return redirect('matches:match_detail', match_id=match_id)

        outcome = request.POST.get('outcome')
        amount = request.POST.get('amount')
        odds_value = request.POST.get('odds')

        try:
            amount = Decimal(amount)
            odds_value = Decimal(odds_value)

            # Проверяем баланс
            if request.user.profile.balance < amount:
                messages.error(request, "Недостаточно средств на счете")
                return redirect('matches:match_detail', match_id=match_id)

            # Создаем ставку
            from .models import Bet
            bet = Bet.objects.create(
                user=request.user,
                match=match,
                outcome=outcome,
                amount=amount,
                odds=odds_value,
                potential_win=amount * odds_value
            )

            # Списываем средства
            Transaction.objects.create(
                user=request.user,
                amount=amount,
                transaction_type='bet',
                status='completed',
                comment=f'Ставка на матч {match.home_team} vs {match.away_team}'
            )

            messages.success(request, f"Ставка размещена! Возможный выигрыш: {bet.potential_win}")
            return redirect('accounts:profile')

        except (ValueError, TypeError):
            messages.error(request, "Некорректные данные ставки")

    return redirect('matches:match_detail', match_id=match_id)
