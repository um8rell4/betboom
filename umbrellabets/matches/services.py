import requests
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from datetime import datetime
from .models import Sport, Match, Bookmaker, Odds


class OddsAPIService:
    BASE_URL = "https://api.the-odds-api.com/v4"

    def __init__(self):
        self.api_key = settings.ODDS_API_KEY

    def get_sports(self):
        """Получить список доступных видов спорта"""
        url = f"{self.BASE_URL}/sports"
        params = {'apiKey': self.api_key}

        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return []

    def get_odds(self, sport_key='cs2', regions='eu', markets='h2h'):
        """Получить коэффициенты для конкретного спорта"""
        url = f"{self.BASE_URL}/sports/{sport_key}/odds"
        params = {
            'apiKey': self.api_key,
            'regions': regions,
            'markets': markets,
            'oddsFormat': 'decimal',
            'dateFormat': 'iso'
        }

        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return []

    def sync_matches_and_odds(self, sport_key='cs2'):
        """Синхронизация матчей и коэффициентов"""
        data = self.get_odds(sport_key)

        # Получаем или создаем спорт
        sport, created = Sport.objects.get_or_create(
            key=sport_key,
            defaults={'title': sport_key.upper(), 'active': True}
        )

        for match_data in data:
            # Создаем или обновляем матч
            match, created = Match.objects.update_or_create(
                api_id=match_data['id'],
                defaults={
                    'sport': sport,
                    'home_team': match_data['home_team'],
                    'away_team': match_data['away_team'],
                    'commence_time': datetime.fromisoformat(
                        match_data['commence_time'].replace('Z', '+00:00')
                    ),
                    'status': 'upcoming' if datetime.fromisoformat(
                        match_data['commence_time'].replace('Z', '+00:00')
                    ) > timezone.now() else 'live'
                }
            )

            # Обрабатываем коэффициенты
            for bookmaker_data in match_data.get('bookmakers', []):
                # Создаем или получаем букмекера
                bookmaker, created = Bookmaker.objects.get_or_create(
                    key=bookmaker_data['key'],
                    defaults={'title': bookmaker_data['title']}
                )

                # Обрабатываем рынки
                for market in bookmaker_data.get('markets', []):
                    if market['key'] == 'h2h':  # Head to head
                        for outcome in market['outcomes']:
                            Odds.objects.update_or_create(
                                match=match,
                                bookmaker=bookmaker,
                                outcome='home' if outcome['name'] == match.home_team else 'away',
                                defaults={
                                    'price': Decimal(str(outcome['price'])),
                                    'last_update': timezone.now()
                                }
                            )