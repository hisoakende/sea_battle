from django.urls import path

from sea_battle_app.views import CreatingBattleView

urlpatterns = [
    path('api/create-battle/', CreatingBattleView.as_view())
]
