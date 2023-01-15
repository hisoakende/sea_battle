from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Union, Optional, Any, Callable

ShipCoordinates = list[list[int]]

PlayerInfoAsDict = dict[str, Union[list[list[int]], Optional[list[ShipCoordinates]]]]


class BattleLogicException(Exception):
    pass


class CellState(Enum):
    hit = 1
    missed = 2
    nothing = 3


@dataclass
class PlayerInfo:
    field: list[list[CellState]]
    ships_coordinates: Optional[list[ShipCoordinates]]

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
    first_player = PlayerInfo(empty_field, None)
    second_player = PlayerInfo(deepcopy(empty_field), None)
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

    if len(set([tuple(cell_coord) for cell_coord in sum(ships_coords, [])])) != 20:
        raise BattleLogicException('incorrect ships coordinates')

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
    process_cells_adjacent_to_ship(ship_coords, add_forbidden_cells, forbidden_cells)


def validate_changing_coord(coord: list[int]) -> None:
    """The function that validates for changing ship coordinates"""

    if max(coord) - min(coord) != len(coord) - 1:
        raise BattleLogicException('incorrect ship coordinates')


def check_if_ship_in_forbidden_cells(ship_coords: ShipCoordinates, forbidden_cells: list[list[int]]) -> None:
    """The function that checks for the presence of a ship in cells adjacent to another ship"""

    for ship_coord in ship_coords:
        if ship_coord in forbidden_cells:
            raise BattleLogicException('ships cant be nearby')


def process_cells_adjacent_to_ship(ship_coords: ShipCoordinates, func: Callable, *args: Any) -> None:
    for x, y in ship_coords:
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                new_x, new_y = x + i, y + j
                if new_x in (-1, 10) or new_y in (-1, 10):
                    continue
                func(ship_coords, [new_x, new_y], *args)


def add_forbidden_cells(ship_coords: ShipCoordinates, new_cell: list[int],
                        forbidden_cells: list[list[int]]) -> None:
    """The function that adds neighboring cell with ship to forbidden cells"""

    if new_cell not in ship_coords and new_cell not in forbidden_cells:
        forbidden_cells.append(new_cell)


def shot_is_valid(shot_coordinates: list[int], field: list[list[CellState]]) -> bool:
    if not isinstance(field, list):
        return False
    if len(shot_coordinates) != 2:
        return False
    if any([type(coord) != int for coord in shot_coordinates]):
        return False
    if any([coord not in range(0, 10) for coord in shot_coordinates]):
        return False
    x, y = shot_coordinates
    if field[x][y] not in (CellState.nothing, 3):
        return False

    return True


def process_shot(shot_coordinates: list[int], player_info: PlayerInfo) -> bool:
    """The method that processes a valid shot. Returns 'true' if ship was hit and 'false' if not"""

    x, y = shot_coordinates
    ship_index = get_affected_ship_index(shot_coordinates, player_info)

    if ship_index is not None:
        player_info.field[x][y] = CellState.hit
        ship = player_info.ships_coordinates[ship_index]

        if did_ship_destroy(ship, player_info.field):
            process_cells_adjacent_to_ship(ship, process_ship_destruction, player_info)

        return True

    player_info.field[x][y] = CellState.missed
    return False


def get_affected_ship_index(shot_coordinates: list[int], player_info: PlayerInfo) -> Optional[int]:
    """The method that processes hitting the ship. Returns the ship index if ship was hit and 'None' if not"""

    for i, ship_coords in enumerate(player_info.ships_coordinates):
        if shot_coordinates in ship_coords:
            return i
    return None


def did_ship_destroy(ship_coords: list[list[int]], field: list[list[CellState]]) -> bool:
    for x, y in ship_coords:
        if field[x][y] != CellState.hit:
            return False
    return True


def process_ship_destruction(ship_coords: ShipCoordinates, new_cell: list[int], player_info: PlayerInfo) -> None:
    """The method that sets neighbours cell with the ship in 'hit'"""

    if new_cell not in ship_coords:
        player_info.field[new_cell[0]][new_cell[1]] = CellState.missed
