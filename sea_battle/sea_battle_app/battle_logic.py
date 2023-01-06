from copy import deepcopy
from enum import Enum
from typing import NamedTuple, Union

ShipCoordinate = list[tuple[int, int]]

PlayerInfoAsDict = dict[str, Union[list[list[int]], list[ShipCoordinate]]]


class CellState(Enum):
    hit = 1
    missed = 2
    nothing = 3


class PlayerInfo(NamedTuple):
    field: list[list[CellState]]
    ships_coordinates: list[ShipCoordinate]

    def field_as_int(self) -> list[list[int]]:
        return [[cell if isinstance(cell, int) else cell.value for cell in cell_row]
                for cell_row in self.field]

    def as_dict(self) -> PlayerInfoAsDict:
        return {'field': self.field_as_int(), 'ships_coordinates': self.ships_coordinates}


class BattleInfo(NamedTuple):
    first_player: PlayerInfo
    second_player: PlayerInfo

    @staticmethod
    def from_dict(data: dict[str, dict]) -> 'BattleInfo':
        first_player = PlayerInfo(**data['first_player'])
        second_player = PlayerInfo(**data['second_player'])
        return BattleInfo(first_player, second_player)

    def as_dict(self) -> dict[str, PlayerInfoAsDict]:
        return {'first_player': self.first_player.as_dict(), 'second_player': self.second_player.as_dict()}


def create_battle() -> BattleInfo:
    empty_field = [[CellState.nothing for _ in range(10)] for _ in range(10)]
    first_player = PlayerInfo(empty_field, [])
    second_player = PlayerInfo(deepcopy(empty_field), [])
    return BattleInfo(first_player, second_player)
