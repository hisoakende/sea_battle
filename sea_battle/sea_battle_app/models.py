from typing import Any

from django.contrib.auth.models import User
from django.db import models, IntegrityError

from sea_battle_app.utils import create_battle_address


class Player(models.Model):
    """The model of player in battle"""

    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True)
    channel_name = models.CharField(max_length=127, null=True)


class BattleInfoManager(models.Manager):
    """The sea battle model manager"""

    def create(self, **kwargs: Any) -> 'Battle':
        kwargs['address'] = create_battle_address()
        try:
            return super().create(**kwargs)
        except IntegrityError:
            return self.create(**kwargs)


class Battle(models.Model):
    """
    The sea battle model

    You can define stage of battle by 'who_win' and 'whose move':
    1) if who_win is null and whose_move is null then battle is preparing (players set ships)
    2) if who_win is null but whose_move is not null then game in progress
    3) if who_win is not null and whose_move is null then game is finished
    """

    player_choices = (('first', 'first'), ('second', 'second'))

    address = models.CharField(max_length=127, unique=True)
    first_player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, related_name='first')
    second_player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, related_name='second')
    state = models.JSONField(null=True)
    who_win = models.CharField(max_length=15, choices=player_choices, null=True)
    whose_move = models.CharField(max_length=15, choices=player_choices, null=True)
    datetime = models.DateTimeField(auto_now_add=True)

    objects = BattleInfoManager()
