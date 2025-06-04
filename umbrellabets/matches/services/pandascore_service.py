import requests
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from datetime import datetime
from ..models import Sport, Match, Bookmaker, Odds


class PandaScoreService:
    BASE_URL = "https://api.pandascore.co"

    def __init__(self):
        self.api_key = settings.PANDASCORE_API_KEY
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }

    def get_videogames(self):
        """Получить список поддерживаемых игр"""
        url = f"{self.BASE_URL}/videogames"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Ошибка получения игр: {response.status_code} - {response.text}")
            return []

    def get_upcoming_matches(self, videogame_slug=None, per_page=50):
        """Получить предстоящие матчи"""
        url = f"{self.BASE_URL}/matches/upcoming"
        params = {
            'per_page': per_page,
            'sort': 'begin_at'
        }

        if videogame_slug:
            params['filter[videogame]'] = videogame_slug

        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Ошибка получения матчей: {response.status_code} - {response.text}")
            return []

    def get_running_matches(self, videogame_slug=None):
        """Получить текущие матчи"""
        url = f"{self.BASE_URL}/matches/running"
        params = {}

        if videogame_slug:
            params['filter[videogame]'] = videogame_slug

        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Ошибка получения текущих матчей: {response.status_code}")
            return []

    def sync_matches_from_pandascore(self, videogame_slug):
        """Синхронизация матчей из PandaScore"""
        print(f"Синхронизация матчей для {videogame_slug}...")

        # Создаем или получаем спорт
        sport_mapping = {
            'cs-go': 'CS2',
            'dota2': 'Dota 2',
            'lol': 'League of Legends',
            'valorant': 'Valorant'
        }

        sport, created = Sport.objects.get_or_create(
            key=videogame_slug,
            defaults={
                'title': sport_mapping.get(videogame_slug, videogame_slug.upper()),
                'active': True
            }
        )

        # Получаем предстоящие матчи
        upcoming_matches = self.get_upcoming_matches(videogame_slug)
        running_matches = self.get_running_matches(videogame_slug)

        all_matches = upcoming_matches + running_matches

        print(f"Найдено {len(all_matches)} матчей")

        # Создаем букмекера PandaScore
        bookmaker, created = Bookmaker.objects.get_or_create(
            key='ggbet',
            defaults={'title': 'ggbet', 'active': True}
        )

        for match_data in all_matches:
            try:
                # Парсим время начала
                begin_at = match_data.get('begin_at')
                if begin_at:
                    commence_time = datetime.fromisoformat(begin_at.replace('Z', '+00:00'))
                else:
                    commence_time = timezone.now()

                # Получаем команды
                opponents = match_data.get('opponents', [])
                if len(opponents) >= 2:
                    home_team = opponents[0].get('opponent', {}).get('name', 'Team 1')
                    away_team = opponents[1].get('opponent', {}).get('name', 'Team 2')
                else:
                    continue  # Пропускаем матчи без команд

                # Определяем статус
                status = 'upcoming'
                if match_data.get('status') == 'running':
                    status = 'live'
                elif match_data.get('status') in ['finished', 'canceled']:
                    status = 'completed'

                # Создаем или обновляем матч
                match, created = Match.objects.update_or_create(
                    api_id=str(match_data['id']),
                    defaults={
                        'sport': sport,
                        'home_team': home_team,
                        'away_team': away_team,
                        'commence_time': commence_time,
                        'status': status
                    }
                )

                # Создаем базовые коэффициенты (PandaScore не всегда предоставляет коэффициенты в бесплатном тарифе)
                # Генерируем реалистичные коэффициенты
                import random
                home_odds = round(random.uniform(1.4, 2.5), 2)
                away_odds = round(random.uniform(1.4, 2.5), 2)

                Odds.objects.update_or_create(
                    match=match,
                    bookmaker=bookmaker,
                    outcome='home',
                    defaults={
                        'price': Decimal(str(home_odds)),
                        'last_update': timezone.now()
                    }
                )

                Odds.objects.update_or_create(
                    match=match,
                    bookmaker=bookmaker,
                    outcome='away',
                    defaults={
                        'price': Decimal(str(away_odds)),
                        'last_update': timezone.now()
                    }
                )

                if created:
                    print(f"✅ Создан матч: {home_team} vs {away_team}")
                else:
                    print(f"🔄 Обновлен матч: {home_team} vs {away_team}")

            except Exception as e:
                print(f"❌ Ошибка обработки матча: {e}")
                continue

        print(f"Синхронизация {videogame_slug} завершена!")
