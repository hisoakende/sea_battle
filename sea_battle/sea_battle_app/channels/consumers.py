from typing import Any, Union

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from sea_battle_app.battle_logic import create_battle, BattleInfo, validate_ships_coords
from sea_battle_app.models import Battle, Player


class BattleConsumer(JsonWebsocketConsumer):
    """Consumer for sea battle processing """

    def connect(self) -> None:
        address = self.scope['url_route']['kwargs']['address']
        try:
            self.battle_model = Battle.objects.get(address=address)
        except Battle.DoesNotExist:
            self.close()
            return

        if self.battle_model.first_player and self.battle_model.second_player:
            self.close()
            return

        self.set_player()

        if self.battle_model.first_player and self.battle_model.second_player:
            self.request_battle_info()
            self.send_message_to_opponent({'type': 'info', 'message': 'opponent connected'})
        else:
            self.battle_info = create_battle()

        self.accept()

    def disconnect(self, code: int) -> None:
        if code != 1000:
            return

        self.player.delete()
        self.battle_model.refresh_from_db()

        if not self.battle_model.first_player and not self.battle_model.second_player:
            self.battle_model.delete()
        else:
            self.send_message_to_opponent({'type': 'info', 'message': 'opponent disconnected'})

    def send_json(self, content: dict[str, Any], close: bool = False) -> None:
        super().send_json(content['content'])

    @property
    def opponent(self) -> Player:
        if self.battle_model.first_player == self.player or self.battle_model.first_player is None:
            return self.battle_model.second_player
        return self.battle_model.first_player

    def send_message_to_opponent(self, content: dict[str, Any]) -> None:
        async_to_sync(self.channel_layer.send)(
            self.opponent.channel_name, {'type': 'send_json', 'content': content}
        )

    def set_player(self) -> None:
        self.player = Player.objects.create(channel_name=self.channel_name)

        if self.battle_model.first_player is None:
            self.battle_model.first_player = self.player
        else:
            self.battle_model.second_player = self.player

        self.battle_model.save()

    def request_battle_info(self) -> None:
        async_to_sync(self.channel_layer.send)(
            self.opponent.channel_name, {'type': 'give_battle_info'}
        )

    def give_battle_info(self, content: dict[str, Any]) -> None:
        self.battle_model.refresh_from_db()
        async_to_sync(self.channel_layer.send)(
            self.opponent.channel_name, {'type': 'set_battle_info', 'battle_info': self.battle_info.as_dict()}
        )

    def set_battle_info(self, content: dict[str, Any]) -> None:
        self.battle_info = BattleInfo.from_dict(content['battle_info'])
