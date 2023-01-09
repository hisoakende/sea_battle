from typing import Any, Union, Optional

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
            self.send_message_to_opponent('give_battle_info', {})
            self.send_message_to_opponent('send_json', {'type': 'info', 'body': 'opponent connected'})
        else:
            self.battle_fields = create_battle()

        self.accept()

    def disconnect(self, code: int) -> None:
        if code != 1000:
            return

        self.player.delete()
        self.battle_model.refresh_from_db()

        if not self.battle_model.first_player and not self.battle_model.second_player:
            self.battle_model.delete()
        else:
            self.send_message_to_opponent('send_json', {'type': 'info', 'body': 'opponent disconnected'})

    def send_json(self, content: dict[str, Any], close: bool = False) -> None:
        super().send_json(content['content'])

    def receive_json(self, content: Union[list, dict[str, Any]], **kwargs: Any) -> None:
        match content:
            case {'type': 'load ships coordinates', 'body': body}:
                self.load_ships_coordinates(body)
            case _:
                self.process_invalid_request(content)

    def load_ships_coordinates(self, ships_coordinates: list[list[list[int]]]) -> None:
        condition, message = validate_ships_coords(ships_coordinates)
        if condition:
            self.battle_fields[self.player_number - 1].ships_coordinates.extend(ships_coordinates)
            self.give_battle_info()
            self.send_json({'content': {'type': 'success', 'body': 'ships successfully placed'}})
        else:
            self.send_json({'content': {'type': 'error', 'body': message}})

    def process_invalid_request(self, body: Union[list, dict[str, Any]]) -> None:
        match body:
            case {'type': _, 'body': _}:
                self.send_json({'content': {'type': 'error', 'body': 'unknown request type'}})
            case {'body': _}:
                self.send_json({'content': {'type': 'error', 'body': 'request must have \'type\' field'}})
            case {'type': _}:
                self.send_json({'content': {'type': 'error', 'body': 'request must have \'body\' field'}})
            case _:
                self.send_json({'content': {'type': 'error', 'body': 'request must have \'type\' and \'body\' fields'}})

    @property
    def opponent(self) -> Optional[Player]:
        if self.player_number == 1:
            return self.battle_model.second_player
        return self.battle_model.first_player

    def send_message_to_opponent(self, func_name: str, content: dict[str, Any]) -> None:
        """
        The function allows you to send messages both opponents consumer
        and opponents client depending on which 'func_name' is received
        """

        if self.opponent is not None:
            async_to_sync(self.channel_layer.send)(
                self.opponent.channel_name, {'type': func_name, 'content': content}
            )

    def set_player(self) -> None:
        self.player = Player.objects.create(channel_name=self.channel_name)

        if self.battle_model.first_player is None:
            self.battle_model.first_player = self.player
            self.player_number = 1
        else:
            self.battle_model.second_player = self.player
            self.player_number = 2

        self.battle_model.save()

    def give_battle_info(self, *args: Any) -> None:
        self.battle_model.refresh_from_db()
        self.send_message_to_opponent('set_battle_info', {'battle_info': self.battle_fields.as_dict()})

    def set_battle_info(self, content: dict[str, Any]) -> None:
        self.battle_fields = BattleInfo.from_dict(content['content']['battle_info'])
