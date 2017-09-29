import csv
import random

from otree.api import models
from django.contrib.contenttypes.models import ContentType
from otree.constants import BaseConstants
from otree.models import BaseGroup, BasePlayer, BaseSubsession

doc = """
This is a bootscats game.
"""


class Constants(BaseConstants):
    name_in_url = 'bootscats'
    players_per_group = 2
    num_rounds = 2


class Subsession(BaseSubsession):

    def before_session_starts(self):
        self.group_randomly()


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    response = models.CharField()

    def set_payoff(self):
        self.payoff = 0