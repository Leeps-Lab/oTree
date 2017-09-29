from ._builtin import Page, WaitPage
from . import models

from datetime import timedelta


class GameWaitPage(WaitPage):
    body_text = 'Waiting for all players to be ready'


class Game(Page):
	form_model = models.Player
	form_fields = ['response']
    

class Results(Page):
    timeout_seconds = 30

    def vars_for_template(self):
        self.player.set_payoff()
        return {}


page_sequence = [
    GameWaitPage,
    Game,
    Results
]