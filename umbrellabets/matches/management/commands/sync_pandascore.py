from django.core.management.base import BaseCommand
from matches.services.pandascore_service import PandaScoreService


class Command(BaseCommand):
    help = 'Синхронизация матчей из PandaScore API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--game',
            type=str,
            default='cs-go',
            help='Игра для синхронизации (cs-go, dota2, lol, valorant)'
        )
        parser.add_argument(
            '--list-games',
            action='store_true',
            help='Показать список доступных игр'
        )

    def handle(self, *args, **options):
        service = PandaScoreService()

        if options['list_games']:
            self.stdout.write('Получение списка игр...')
            games = service.get_videogames()

            self.stdout.write('\n=== Доступные игры ===')
            for game in games:
                self.stdout.write(f"- {game['slug']}: {game['name']}")
            return

        game = options['game']
        self.stdout.write(f'Синхронизация {game}...')

        try:
            service.sync_matches_from_pandascore(game)
            self.stdout.write(
                self.style.SUCCESS(f'Синхронизация {game} завершена!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка синхронизации: {str(e)}')
            )
