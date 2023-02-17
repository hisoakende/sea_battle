from django.urls import path

from sea_battle_app.views import CreatingBattleView, WsDocsView

urlpatterns = [
    path('api/create-battle/', CreatingBattleView.as_view()),
    path('api/ws-docs/', WsDocsView.as_view())
]
