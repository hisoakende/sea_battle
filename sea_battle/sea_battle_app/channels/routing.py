from django.urls import path

from .consumers import BattleConsumer, SearchOpponentConsumer

websocket_urlpatterns = [
    path('ws/battle/<str:address>/', BattleConsumer.as_asgi()),
    path('ws/search-battle/', SearchOpponentConsumer.as_asgi())
]
