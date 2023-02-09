from functools import wraps
from typing import Any, Union, Optional, Callable

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from sea_battle_app.battle_logic import create_battle, BattleInfo, validate_ships_coords, \
    shot_is_valid, process_shot, get_ships_count
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

        self.accept()
        self.set_player()

        if self.battle_model.first_player and self.battle_model.second_player:
            self.send_message_to_opponent('give_battle_info')
            self.send_message_to_opponent('send_json', {'type': 'info', 'body': 'opponent connected'})
        else:
            self.battle_fields = create_battle()

        self.send_json({'content': {'type': 'state', 'body': f'{self.battle_model.state.name}'}})
        self.send_message_to_opponent('request_to_send_data_on_connection')

    def disconnect(self, code: int) -> None:
        if code != 1000:
            return

        self.player.delete()
        self.battle_model.refresh_from_db()

        if self.battle_model.first_player is None and self.battle_model.second_player is None:
            self.battle_model.delete()
        else:
            self.send_message_to_opponent('send_json', {'type': 'info', 'body': 'opponent disconnected'})

    def send_json(self, content: dict[str, Any], close: bool = False) -> None:
        super().send_json(content['content'])

    def receive_json(self, content: Union[list, dict[str, Any]], **kwargs: Any) -> None:
        match content:
            case {'type': 'load ships coordinates', 'body': body}:
                self.load_ships_coordinates(body)
            case {'type': 'take a shot', 'body': body}:
                self.take_shot(body)
            case {'type': 'surrender'}:
                self.surrender()
            case _:
                self.process_invalid_request(content)

    @staticmethod
    def available_at_stage(stage: Battle.State) -> Callable:
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(self, *args: Any) -> Any:
                self.battle_model.refresh_from_db()
                if self.battle_model.state is stage:
                    return func(self, *args)
                self.send_json({'content': {'type': 'error', 'body': 'request is not possible at this stage'}})

            return wrapper

        return decorator

    @available_at_stage(Battle.State.preparation)
    def load_ships_coordinates(self, ships_coordinates: list[list[list[int]]]) -> None:
        condition, message = validate_ships_coords(ships_coordinates)
        if condition:
            self.battle_fields[self.player_number - 1].ships_coordinates = ships_coordinates
            self.give_battle_info()
            if not self.battle_fields[self.opponent_number].ships_coordinates:
                self.send_message_to_opponent('send_json', {'type': 'battle logic', 'body': 'opponent is ready'})

        elif self.battle_fields[self.player_number - 1].ships_coordinates:
            self.send_message_to_opponent('send_json', {'type': 'battle logic', 'body': 'opponent is not ready'})
            self.battle_fields[self.player_number - 1].ships_coordinates = []

        self.send_json({'content': {'type': ['error', 'success'][condition],
                                    'body': message or 'ships successfully placed'}})

        if self.battle_fields[0].ships_coordinates and self.battle_fields[1].ships_coordinates:
            self.start_game()

    @available_at_stage(Battle.State.progress)
    def take_shot(self, shot_coordinates: list[int]) -> None:
        if self.battle_model.whose_move != self.player_number:
            self.send_json({'content': {'type': 'error', 'body': 'not your move'}})
            return

        opponent_info = self.battle_fields[self.opponent_number]

        if not shot_is_valid(shot_coordinates, opponent_info.field):
            self.send_json({'content': {'type': 'error', 'body': 'incorrect shot'}})
            return

        ship_was_hit = process_shot(shot_coordinates, opponent_info)
        self.send_changes_after_shot()

        if ship_was_hit:
            if not any(get_ships_count(opponent_info.ships_coordinates).values()):
                self.end_game()
                return

            self.send_json({'content': {'type': 'battle logic', 'body': 'your move'}})
        else:
            self.send_message_to_opponent('send_json', {'type': 'battle logic', 'body': 'your move'})
            self.battle_model.whose_move = self.opponent_number + 1
            self.battle_model.save()

        self.give_battle_info()

    @available_at_stage(Battle.State.progress)
    def surrender(self) -> None:
        self.send_message_to_opponent('send_json', {'type': 'info', 'body': 'opponent surrendered'})
        self.send_message_to_opponent('end_game')

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

    @property
    def opponent_number(self) -> int:
        """The method that returns opponent number (first player - 0, second player - 1)"""

        return 2 // self.player_number - 1

    def send_message_to_opponent(self, func_name: str, content: Optional[dict[str, Any]] = None) -> None:
        """
        The function allows you to send messages opponent's consumer
        and opponents client depending on which 'func_name' is received
        """

        if self.opponent:
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

    def request_to_send_data_on_connection(self, *args: Any) -> None:
        """
        The method that is needed to request data on connection

        Its use is necessary because in the 'connect' method,
        data from another user came later than the method was completed
        """

        self.send_message_to_opponent('send_data_on_connection')

    def send_data_on_connection(self, *args: Any) -> None:
        if self.battle_model.state == Battle.State.preparation:
            if self.battle_fields[self.opponent_number].ships_coordinates:
                self.send_json({'content': {'type': 'battle logic', 'body': 'opponent is ready'}})
        elif self.battle_model.state == Battle.State.progress:
            self.send_progress_battle_data()
            if self.battle_model.whose_move == self.player_number:
                self.send_json({'content': {'type': 'battle logic', 'body': 'your move'}})

    def start_game(self) -> None:
        self.send_json({'content': {'type': 'state', 'body': self.battle_model.state.progress.name}})
        self.send_message_to_opponent('send_json', {'type': 'state', 'body': self.battle_model.state.progress.name})

        self.send_progress_battle_data()
        self.send_message_to_opponent('send_progress_battle_data')

        self.battle_model.refresh_from_db()
        self.battle_model.whose_move = 1
        self.battle_model.save()

        if self.player_number == 1:
            self.send_json({'content': {'type': 'battle logic', 'body': 'your move'}})
        else:
            self.send_message_to_opponent('send_json', {'type': 'battle logic', 'body': 'your move'})

    def send_changes_after_shot(self) -> None:
        player_info = self.battle_fields[self.opponent_number]
        field = player_info.field_as_int()
        ships_count = get_ships_count(player_info.ships_coordinates)
        self.send_json({'content': {'type': 'changed opponent field',
                                    'body': {'field': field, 'ships count': ships_count}}})
        self.send_message_to_opponent('send_json', {'type': 'changed your field',
                                                    'body': {'field': field, 'ships count': ships_count}})

    def send_progress_battle_data(self, *args: Any) -> None:
        self_info = self.get_all_data_about_player(self.player_number)
        opponents_info = self.get_all_data_about_player(self.opponent_number + 1)
        opponents_info.pop('living ships')
        self.send_json({'content': {'type': 'progress battle data',
                                    'body': {'your info': self_info, 'opponents info': opponents_info}}})

    def end_game(self, *args: Any) -> None:
        """
        The method that processes end of the battle

        Only winner can call it
        """

        self.battle_model.whose_move = None
        self.battle_model.who_win = self.player_number
        self.battle_model.save()

        self.send_json({'content': {'type': 'end game', 'body': 'you are winner'}})
        self.send_message_to_opponent('send_json', {'content': {'type': 'end game', 'body': 'you are loser'}})

        self_info = self.get_all_data_about_player(self.player_number)
        opponents_info = self.get_all_data_about_player(self.opponent_number + 1)

        self.send_json({'content': {'type': 'info after end',
                                    'body': {'your info': self_info, 'opponents info': opponents_info}}})
        self.send_message_to_opponent('send_json', {'type': 'info after end',
                                                    'body': {'your info': opponents_info, 'opponents info': self_info}})

    def get_all_data_about_player(self, player_number: int) -> dict[str, Union[list, dict]]:
        player_info = self.battle_fields[player_number - 1]
        return {'field': player_info.field_as_int(),
                'living ships': player_info.ships_coordinates,
                'ships count': get_ships_count(player_info.ships_coordinates)}
