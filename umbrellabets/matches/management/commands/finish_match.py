from django.core.management.base import BaseCommand
from matches.models import Match


class Command(BaseCommand):
    help = 'Завершить матч и рассчитать ставки'

    def add_arguments(self, parser):
        parser.add_argument('match_id', type=int, help='ID матча')
        parser.add_argument('winner', type=str, choices=['home', 'away', 'cancelled'], help='Победитель')

    def handle(self, *args, **options):
        match_id = options['match_id']
        winner = options['winner']

        try:
            match = Match.objects.get(id=match_id)
            success, message = match.finish_match(winner)

            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Матч завершен! {message}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Ошибка: {message}')
                )

        except Match.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('❌ Матч не найден')
            )
