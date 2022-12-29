from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from sea_battle_app.models import Battle, Player


class BattleConsumer(JsonWebsocketConsumer):
    """Consumer for sea battle processing """

    def connect(self) -> None:
        address = self.scope['url_route']['kwargs']['address']
        try:
            self.battle = Battle.objects.get(address=address)
        except Battle.DoesNotExist:
            self.close()
            return

        if self.battle.first_player and self.battle.second_player:
            self.close()
            return

        self.set_player()

        if self.battle.first_player and self.battle.second_player:
            self.send_message_to_opponent({'type': 'info', 'message': 'opponent connected'})

        self.accept()

    def disconnect(self, code: int) -> None:
        if code != 1000:
            return

        self.player.delete()
        self.battle.refresh_from_db()

        if not self.battle.first_player and not self.battle.second_player:
            self.battle.delete()
        else:
            self.send_message_to_opponent({'type': 'info', 'message': 'opponent disconnected'})

    def send_json(self, content: dict, close=False) -> None:
        super().send_json(content['content'])

    def send_message_to_opponent(self, content: dict) -> None:
        if self.battle.first_player == self.player:
            opponent = self.battle.second_player
        else:
            opponent = self.battle.first_player

        async_to_sync(self.channel_layer.send)(
            opponent.channel_name, {'type': 'send_json', 'content': content}
        )

    def set_player(self):
        self.player = Player.objects.create(channel_name=self.channel_name)

        if self.battle.first_player is None:
            self.battle.first_player = self.player
        else:
            self.battle.second_player = self.player

        self.battle.save()
