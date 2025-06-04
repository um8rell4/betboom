from django.urls import path
from . import views

app_name = 'matches'

urlpatterns = [
    path('', views.matches_list, name='matches_list'),
    path('<int:match_id>/', views.match_detail, name='match_detail'),
    path('<int:match_id>/bet/', views.place_bet, name='place_bet'),
]
