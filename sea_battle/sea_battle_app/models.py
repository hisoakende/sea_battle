from typing import Any

from django.contrib.auth.models import User
from django.db import models, IntegrityError

from sea_battle_app.utils import create_battle_address


class Opponent(models.Model):
    """The model of opponent in battle"""

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
    """The sea battle model"""

    address = models.CharField(max_length=127, unique=True)
    first_opponent = models.ForeignKey(Opponent, on_delete=models.SET_NULL, null=True, related_name='first')
    second_opponent = models.ForeignKey(Opponent, on_delete=models.SET_NULL, null=True, related_name='second')
    state = models.JSONField(null=True)
    who_win = models.CharField(max_length=15, choices=(('first', 'first'), ('second', 'second')), null=True)
    datetime = models.DateTimeField(auto_now_add=True)

    objects = BattleInfoManager()
