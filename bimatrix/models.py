import csv
import random

from django.contrib.contenttypes.models import ContentType
from otree.constants import BaseConstants
from otree.models import BasePlayer, BaseSubsession

from otree_redwood.models import Event, DecisionGroup
from otree_redwood.stats import track

doc = """
This is a configurable bimatrix game.
"""


class Constants(BaseConstants):
    name_in_url = 'bimatrix'
    players_per_group = 2
	# Maximum number of rounds, actual number is taken as the max round
	# in the config file.
    num_rounds = 100
    base_points = 0


def parse_config(config_file):
    with open('bimatrix/configs/' + config_file) as f:
        rows = list(csv.DictReader(f))

    rounds = []
    for row in rows:
        rounds.append({
            'shuffle_role': True if row['shuffle_role'] == 'TRUE' else False,
            'period_length': int(row['period_length']),
            'num_subperiods': int(row['num_subperiods']),
            'pure_strategy': True if row['pure_strategy'] == 'TRUE' else False,
            'show_at_worst': True if row['show_at_worst'] == 'TRUE' else False,
            'show_best_response': True if row['show_best_response'] == 'TRUE' else False,
            'rate_limit': int(row['rate_limit']) if row['rate_limit'] else 0,
            'mean_matching': True if row['mean_matching'] == 'TRUE' else False,
            'payoff_matrix': [
                [int(row['payoff1Aa']), int(row['payoff2Aa'])], [int(row['payoff1Ab']), int(row['payoff2Ab'])],
                [int(row['payoff1Ba']), int(row['payoff2Ba'])], [int(row['payoff1Bb']), int(row['payoff2Bb'])]
            ],
        })
    return rounds


class Subsession(BaseSubsession):

    def get_average_strategy(self, row_player):
        id_in_group = 1 if row_player else 2
        players = [p for p in self.get_players() if p.id_in_group == id_in_group]
        sum_strategies = 0
        for p in players:
            sum_strategies += p.get_average_strategy()
        return sum_strategies / len(players)

    def get_average_payoff(self, row_player):
        id_in_group = 1 if row_player else 2
        players = [p for p in self.get_players() if p.id_in_group == id_in_group]
        sum_payoffs = 0
        for p in players:
            if not p.payoff:
                p.set_payoff()
            sum_payoffs += p.payoff
        return sum_payoffs / len(players)

    def set_rows(self):
        for p in self.get_players():
            if p.id_in_group == 1:
                print("row")
                self.session.vars['row_vals'][p.participant.code] = 0
            else:
                print("col")
                self.session.vars['col_vals'][p.participant.code] = 0
        self.session.vars['set_rows'] = True

    def update_mean_vals(self, participant, value):
        play = None
        for p in self.get_players():
            if p.participant.pk == participant.pk:
                play = p
                break
        if play is None:
            return
        if play.id_in_group == 1:
            self.session.vars['row_vals'][participant.code] = value
            self.session.save()
        else:
            self.session.vars['col_vals'][participant.code] = value
            self.session.save()

    def get_mean(self, row_player):
        sum_payoffs = 0
        if row_player == 1:
            for p in self.session.vars['row_vals']:
                sum_payoffs += self.session.vars['row_vals'][p]
            return sum_payoffs/len(self.session.vars['row_vals'])
        else:
            for p in self.session.vars['col_vals']:
                sum_payoffs += self.session.vars['col_vals'][p]
            return sum_payoffs/len(self.session.vars['col_vals'])

    def before_session_starts(self):
        config = parse_config(self.session.config['config_file'])
        if self.round_number > len(config):
            self.group_randomly()
        elif config[self.round_number-1]['shuffle_role']:
            self.group_randomly()
        else:
            self.group_randomly(fixed_id_in_group=True)
        self.session.vars.update({'row_vals':{}, 'col_vals':{}, 'set_rows':False})

        for p in self.get_players():
            if p.id_in_group == 1:
                print("row")
                self.session.vars['row_vals'][p.participant.code] = 0
            else:
                print("col")
                self.session.vars['col_vals'][p.participant.code] = 0


    def payoff_matrix(self):
        return parse_config(self.session.config['config_file'])[self.round_number-1]['payoff_matrix']

    def pure_strategy(self):
        return parse_config(self.session.config['config_file'])[self.round_number-1]['pure_strategy']

    def show_at_worst(self):
        return parse_config(self.session.config['config_file'])[self.round_number-1]['show_at_worst']

    def show_best_response(self):
        return parse_config(self.session.config['config_file'])[self.round_number-1]['show_best_response']

    def rate_limit(self):
        return parse_config(self.session.config['config_file'])[self.round_number-1]['rate_limit']

    def mean_matching(self):
        return parse_config(self.session.config['config_file'])[self.round_number-1]['mean_matching']


class Group(DecisionGroup):

    def num_rounds(self):
        return len(parse_config(self.session.config['config_file']))

    def num_subperiods(self):
        return parse_config(self.session.config['config_file'])[self.round_number-1]['num_subperiods']

    def period_length(self):
        return parse_config(self.session.config['config_file'])[self.round_number-1]['period_length']

    def get_other_player_code(self, player_code):
        for p in self.get_players_in_group():
            if p.participant.code != player_code:
                return p.participant.code

    def _on_decisions_event(self, event=None, **kwargs):
        if self.subsession.mean_matching():
            if not self.ran_ready_function:
                return
            self.subsession.update_mean_vals(event.participant, event.value)
            # find a way to find the decision value because event value is not what we're looking for
            with track('_on_decisions_event'):
                for group in self.subsession.get_groups():
                    for player in group.get_players():
                        group.group_decisions[player.participant.code] = self.subsession.get_mean(player.id_in_group)
                    group.save()
                if not self.num_subperiods():
                    self.send('group_decisions', self.group_decisions)
        else:
            super()._on_decisions_event(self, event, kwargs)

class Player(BasePlayer):

    def get_average_strategy(self):
        decisions = list(Event.objects.filter(
                channel='group_decisions',
                content_type=ContentType.objects.get_for_model(self.group),
                group_pk=self.group.pk).order_by("timestamp"))
        try:
            period_end = Event.objects.get(
                    channel='state',
                    content_type=ContentType.objects.get_for_model(self.group),
                    group_pk=self.group.pk,
                    value='period_end').timestamp
        except Event.DoesNotExist:
            return float('nan')
        # sum of all decisions weighted by the amount of time that decision was held
        weighted_sum_decision = 0
        while decisions:
            cur_decision = decisions.pop(0)
            next_change_time = decisions[0].timestamp if decisions else period_end
            decision_value = cur_decision.value[self.participant.code]
            weighted_sum_decision += decision_value * (next_change_time - cur_decision.timestamp).total_seconds()
        return weighted_sum_decision / self.group.period_length()


    def initial_decision(self):
        if self.subsession.pure_strategy():
            return random.choice([0, 1])
        return random.random()

    def other_player(self):
        return self.get_others_in_group()[0]

    def set_payoff(self):
        decisions = list(Event.objects.filter(
                channel='decisions',
                content_type=ContentType.objects.get_for_model(self.group),
                group_pk=self.group.pk).order_by("timestamp"))

        try:
            period_start = Event.objects.get(
                    channel='state',
                    content_type=ContentType.objects.get_for_model(self.group),
                    group_pk=self.group.pk,
                    value='period_start')
            period_end = Event.objects.get(
                    channel='state',
                    content_type=ContentType.objects.get_for_model(self.group),
                    group_pk=self.group.pk,
                    value='period_end')
        except Event.DoesNotExist:
            return float('nan')

        payoff_matrix = self.subsession.payoff_matrix()

        self.payoff = self.get_payoff(period_start, period_end, decisions, payoff_matrix)


    def get_payoff(self, period_start, period_end, decisions, payoff_matrix):
        period_duration = period_end.timestamp - period_start.timestamp

        payoff = 0

        Aa = payoff_matrix[0][self.id_in_group-1]
        Ab = payoff_matrix[1][self.id_in_group-1]
        Ba = payoff_matrix[2][self.id_in_group-1]
        Bb = payoff_matrix[3][self.id_in_group-1]

        if self.id_in_group == 1:
            row_player = self.participant
            q1, q2 = self.initial_decision(), self.other_player().initial_decision()
        else:
            row_player = self.other_player().participant
            q2, q1 = self.initial_decision(), self.other_player().initial_decision()

        q1, q2 = 0.5, 0.5
        for i, d in enumerate(decisions):
            if d.participant == row_player:
                q1 = d.value
                if self.subsession.mean_matching():
                    q2 = self.subsession.get_mean(self.other_player().id_in_group)
            elif not self.subsession.mean_matching():
                q2 = d.value
            flow_payoff = ((Aa * q1 * q2) +
                           (Ab * q1 * (1 - q2)) +
                           (Ba * (1 - q1) * q2) +
                           (Bb * (1 - q1) * (1 - q2)))

            if i + 1 < len(decisions):
                next_change_time = decisions[i + 1].timestamp
            else:
                next_change_time = period_end.timestamp
            payoff += (next_change_time - d.timestamp).total_seconds() * flow_payoff

        return payoff / period_duration.total_seconds()
