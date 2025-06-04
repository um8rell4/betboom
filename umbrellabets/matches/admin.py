from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Sport, Match, Bookmaker, Odds, Bet


@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ['title', 'key', 'active', 'matches_count']
    list_filter = ['active']
    search_fields = ['title', 'key']
    list_editable = ['active']

    def matches_count(self, obj):
        count = obj.match_set.count()
        if count > 0:
            url = reverse('admin:matches_match_changelist') + f'?sport__id__exact={obj.id}'
            return format_html('<a href="{}">{} матчей</a>', url, count)
        return count

    matches_count.short_description = 'Количество матчей'


@admin.register(Bookmaker)
class BookmakerAdmin(admin.ModelAdmin):
    list_display = ['title', 'key', 'active', 'odds_count']
    list_filter = ['active']
    search_fields = ['title', 'key']
    list_editable = ['active']

    def odds_count(self, obj):
        count = obj.odds_set.count()
        return count

    odds_count.short_description = 'Количество коэффициентов'


class OddsInline(admin.TabularInline):
    model = Odds
    extra = 0
    fields = ['bookmaker', 'outcome', 'price', 'last_update']
    readonly_fields = ['last_update']


class BetInline(admin.TabularInline):
    model = Bet
    extra = 0
    fields = ['user', 'outcome', 'amount', 'odds', 'potential_win', 'status']
    readonly_fields = ['potential_win']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = [
        'match_title', 'sport', 'commence_time_formatted',
        'status_colored', 'best_odds_display', 'bets_count'
    ]
    list_filter = ['sport', 'status', 'commence_time']
    search_fields = ['home_team', 'away_team', 'api_id']
    date_hierarchy = 'commence_time'
    ordering = ['commence_time']
    inlines = [OddsInline, BetInline]

    fieldsets = (
        ('Основная информация', {
            'fields': ('api_id', 'sport', 'status')
        }),
        ('Команды', {
            'fields': ('home_team', 'away_team')
        }),
        ('Время', {
            'fields': ('commence_time',)
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']

    def match_title(self, obj):
        return f"{obj.home_team} vs {obj.away_team}"

    match_title.short_description = 'Матч'

    def commence_time_formatted(self, obj):
        return obj.commence_time.strftime('%d.%m.%Y %H:%M')

    commence_time_formatted.short_description = 'Время начала'

    def status_colored(self, obj):
        colors = {
            'upcoming': '#10b981',  # зеленый
            'live': '#f59e42',  # оранжевый
            'completed': '#64748b'  # серый
        }
        color = colors.get(obj.status, '#64748b')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_colored.short_description = 'Статус'

    def best_odds_display(self, obj):
        odds = obj.odds.all()
        if odds:
            home_odds = odds.filter(outcome='home').first()
            away_odds = odds.filter(outcome='away').first()

            home_price = home_odds.price if home_odds else 'N/A'
            away_price = away_odds.price if away_odds else 'N/A'

            return format_html(
                '<span style="color: #3b82f6;">{}</span> / <span style="color: #a21caf;">{}</span>',
                home_price, away_price
            )
        return 'Нет коэффициентов'

    best_odds_display.short_description = 'Коэффициенты (Дом/Гости)'

    def bets_count(self, obj):
        count = obj.bets.count()
        if count > 0:
            url = reverse('admin:matches_bet_changelist') + f'?match__id__exact={obj.id}'
            return format_html('<a href="{}">{} ставок</a>', url, count)
        return count

    bets_count.short_description = 'Ставки'


@admin.register(Odds)
class OddsAdmin(admin.ModelAdmin):
    list_display = [
        'match_short', 'bookmaker', 'outcome_colored',
        'price_formatted', 'last_update_formatted'
    ]
    list_filter = ['bookmaker', 'outcome', 'last_update']
    search_fields = ['match__home_team', 'match__away_team', 'bookmaker__title']
    date_hierarchy = 'last_update'
    ordering = ['-last_update']

    def match_short(self, obj):
        return f"{obj.match.home_team} vs {obj.match.away_team}"

    match_short.short_description = 'Матч'

    def outcome_colored(self, obj):
        colors = {
            'home': '#10b981',
            'away': '#f59e42',
            'draw': '#64748b'
        }
        color = colors.get(obj.outcome, '#64748b')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_outcome_display()
        )

    outcome_colored.short_description = 'Исход'

    def price_formatted(self, obj):
        return format_html(
            '<span style="font-weight: bold; font-size: 1.1em;">{}</span>',
            obj.price
        )

    price_formatted.short_description = 'Коэффициент'

    def last_update_formatted(self, obj):
        return obj.last_update.strftime('%d.%m.%Y %H:%M')

    last_update_formatted.short_description = 'Обновлено'


@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'match_short', 'outcome_colored',
        'amount_formatted', 'odds', 'potential_win_formatted',
        'status_colored', 'created_at_formatted'
    ]
    list_filter = ['status', 'outcome', 'created_at', 'match__sport']
    search_fields = [
        'user__username', 'user__email',
        'match__home_team', 'match__away_team'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Ставка', {
            'fields': ('user', 'match', 'outcome')
        }),
        ('Финансы', {
            'fields': ('amount', 'odds', 'potential_win')
        }),
        ('Статус', {
            'fields': ('status',)
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at', 'potential_win']

    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)

    user_link.short_description = 'Пользователь'

    def match_short(self, obj):
        return f"{obj.match.home_team} vs {obj.match.away_team}"

    match_short.short_description = 'Матч'

    def outcome_colored(self, obj):
        colors = {
            'home': '#10b981',
            'away': '#f59e42'
        }
        color = colors.get(obj.outcome, '#64748b')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_outcome_display()
        )

    outcome_colored.short_description = 'Исход'

    def amount_formatted(self, obj):
        return format_html(
            '<span style="font-weight: bold;">{} 🪙</span>',
            obj.amount
        )

    amount_formatted.short_description = 'Сумма ставки'

    def potential_win_formatted(self, obj):
        return format_html(
            '<span style="color: #10b981; font-weight: bold;">{} 🪙</span>',
            obj.potential_win
        )

    potential_win_formatted.short_description = 'Возможный выигрыш'

    def status_colored(self, obj):
        colors = {
            'pending': '#f59e42',
            'won': '#10b981',
            'lost': '#ef4444',
            'cancelled': '#64748b'
        }
        color = colors.get(obj.status, '#64748b')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_colored.short_description = 'Статус'

    def created_at_formatted(self, obj):
        return obj.created_at.strftime('%d.%m.%Y %H:%M')

    created_at_formatted.short_description = 'Дата ставки'


# Настройка заголовков админки
admin.site.site_header = "UmbrellaBet Админ-панель"
admin.site.site_title = "UmbrellaBet"
admin.site.index_title = "Управление платформой"

# Массовые действия
@admin.action(description='Отметить матчи как завершенные')
def mark_completed(modeladmin, request, queryset):
    queryset.update(status='completed')

@admin.action(description='Отметить матчи как предстоящие')
def mark_upcoming(modeladmin, request, queryset):
    queryset.update(status='upcoming')

@admin.action(description='Активировать букмекеров')
def activate_bookmakers(modeladmin, request, queryset):
    queryset.update(active=True)

@admin.action(description='Деактивировать букмекеров')
def deactivate_bookmakers(modeladmin, request, queryset):
    queryset.update(active=False)

# Добавить действия к админкам
MatchAdmin.actions = [mark_completed, mark_upcoming]
BookmakerAdmin.actions = [activate_bookmakers, deactivate_bookmakers]

