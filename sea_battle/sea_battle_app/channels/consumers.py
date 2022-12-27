from channels.generic.websocket import JsonWebsocketConsumer

from sea_battle_app.models import Battle, Opponent


class BattleConsumer(JsonWebsocketConsumer):
    """Consumer for sea battle processing """

    def connect(self) -> None:
        address = self.scope['url_route']['kwargs']['address']
        try:
            self.battle = Battle.objects.get(address=address)
        except Battle.DoesNotExist:
            self.close()
            return

        if self.battle.first_opponent and self.battle.second_opponent:
            self.close()
            return

        self.player = Opponent.objects.create(channel_name=self.channel_name)
        if self.battle.first_opponent is None:
            self.battle.first_opponent = self.player
        else:
            self.battle.second_opponent = self.player

        self.battle.save()
        self.accept()

    def disconnect(self, code: int) -> None:
        if code != 1000:
            return

        if bool(self.battle.first_opponent) + bool(self.battle.second_opponent) == 1:
            self.battle.delete()
        self.player.delete()
