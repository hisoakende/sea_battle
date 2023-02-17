from django.views.generic import TemplateView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from sea_battle_app.models import Battle


class CreatingBattleView(APIView):
    """The view that processes the creation of the battle"""

    @staticmethod
    def get(request: Request) -> Response:
        battle = Battle.objects.create()
        return Response({'ws_address': battle.address})


class WsDocsView(TemplateView):
    """The view that processes showing of the documentation"""

    template_name = 'index.html'
