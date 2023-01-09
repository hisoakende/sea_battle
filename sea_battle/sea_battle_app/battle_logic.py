from copy import deepcopy
from enum import Enum
from typing import NamedTuple, Union

ShipCoordinates = list[list[int]]

PlayerInfoAsDict = dict[str, Union[list[list[int]], list[ShipCoordinates]]]


class BattleLogicException(Exception):
    pass


class CellState(Enum):
    hit = 1
    missed = 2
    nothing = 3


class PlayerInfo(NamedTuple):
    field: list[list[CellState]]
    ships_coordinates: list[ShipCoordinates]

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


def validate_ships_coords(ships_coords: list[ShipCoordinates]) -> tuple[bool, str]:
    try:
        _validate_ships_coords(ships_coords)
    except BattleLogicException as e:
        return False, str(e)
    except Exception:
        return False, 'incorrect input data'
    return True, ''


def _validate_ships_coords(ships_coords: list[ShipCoordinates]) -> None:
    if not isinstance(ships_coords, list):
        raise TypeError

    if len(ships_coords) != 10:
        raise BattleLogicException('incorrect ships count')

    forbidden_cells, ships_count_by_size = [], [0, 0, 0, 0]
    for ship_coords in ships_coords:
        validate_ship_coords(ship_coords, forbidden_cells, ships_count_by_size)

    if ships_count_by_size[0] != 4 or ships_count_by_size[1] != 3 \
            or ships_count_by_size[2] != 2 or ships_count_by_size[3] != 1:
        raise BattleLogicException('incorrect ratio of ships')


def validate_ship_coords(ship_coords: ShipCoordinates, forbidden_cells: list[list[int]],
                         ships_count_by_size: list[int]) -> None:
    if len(ship_coords) == 0 or len(ship_coords) > 4:
        raise BattleLogicException('incorrect ship size')
    ships_count_by_size[len(ship_coords) - 1] += 1

    coords_x, coords_y = [], []
    for x, y in ship_coords:
        if x > 9 or x < 0 or y > 9 or y < 0:
            raise BattleLogicException('incorrect ship coordinates')
        coords_x.append(x)
        coords_y.append(y)

    if len(set(coords_x)) == 1:
        validate_changing_coord(coords_y)
    elif len(set(coords_y)) == 1:
        validate_changing_coord(coords_x)
    else:
        raise BattleLogicException('incorrect ship coordinates')

    check_if_ship_in_forbidden_cells(ship_coords, forbidden_cells)
    add_forbidden_cells(ship_coords, forbidden_cells)


def validate_changing_coord(coord: list[int]) -> None:
    """The function that validates for changing ship coordinates"""

    if max(coord) - min(coord) != len(coord) - 1:
        raise BattleLogicException('incorrect ship coordinates')


def check_if_ship_in_forbidden_cells(ship_coords: ShipCoordinates, forbidden_cells: list[list[int]]) -> None:
    """The function that checks for the presence of a ship in cells adjacent to another ship"""

    for ship_coord in ship_coords:
        if ship_coord in forbidden_cells:
            raise BattleLogicException('ships cant be nearby')


def add_forbidden_cells(ship_coords: ShipCoordinates, forbidden_cells: list[list[int]]) -> None:
    """The function that adds neighboring cells with ship to forbidden cells"""

    for x, y in ship_coords:
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                new_cell = [x + i, y + j]
                if new_cell in ship_coords or new_cell in forbidden_cells:
                    continue
                forbidden_cells.append(new_cell)
