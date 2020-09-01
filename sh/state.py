##!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sh.state

Licensed under CC BY-NC-SA 4.0, see LICENSE for details.
"""

import random
from typing import Callable, List, Optional, Iterable

import discord

PLAYERS_TO_LIB_FASC_COUNT = {
    5: (3, 2),
    6: (4, 2),
    7: (4, 3),
    8: (5, 3),
    9: (5, 4),
    10: (6, 4),
}

POLICY_COUNT = {
    "fascist": 11,
    "liberal": 6,
}

POLICY_TARGET = {
    "fascist": 6,
    "liberal": 5,
}


class GameState:
    def __init__(self):
        """
        Initialises an instance of the state of a Secret Hitler game
        """

        self.players = {}
        self.reset()

    def reset(self):
        """
        Resets state attributes back to default
        """
        self.pres_candidate_index = 0
        self.chancellor = None
        self.president = None
        self.election_tracker = 0
        self.policies = []
        self.discarded_policies = []
        self.policy_counts = {
            "fascist": 0,
            "liberal": 0,
        }

    @property
    def deck_distribution(self):
        counts = {
            "fascist": 0,
            "liberal": 0,
        }
        for policy_type in self.policies:
            counts[policy_type] += 1

        return counts

    def get_players(
        self, predicate: Callable[[discord.User, str], bool] = lambda user, role: True
    ) -> List[discord.User]:
        """
        Retrieves a list of players.

        Optionally, you can specify a predicate that fetched players must satisfied.
        The predicate must be a callable that accepts two positional arguments:
        the player's user as the first and the role as the second

        :param predicate: The predicate, defaults to a function that returns True
        :type predicate: Callable[[discord.User, str], bool], optional
        :return: The list of players
        :rtype: List[discord.User]
        """
        return [user for user, role in self.players.items() if predicate(user, role)]

    def get_fascist_players(
        self, exclude: Optional[Iterable[discord.User]] = None
    ) -> List[discord.User]:
        """
        Retrieves a list of fascist players, excluding Hitler.
        You can optionally exclude players from the list

        :return: The list of fascist players
        :rtype: List[discord.User]
        """

        def fascist_predicate(user, role):
            return role == "fascist" and (
                user in exclude if exclude is not None else True
            )

        return self.get_players(fascist_predicate)

    def get_hitler(self) -> discord.User:
        """
        Gets the player that is Hitler

        :return: The player that is Hitler
        :rtype: discord.User
        """

        def hitler_predicate(_, role):
            return role == "hitler"

        return self.get_players(hitler_predicate)[0]

    def get_presidential_candidate(self) -> discord.User:
        """
        Get the next presidential candidate

        :return: The next presidential candidate
        :rtype: discord.User
        """
        pres_candidate = list(self.players)[self.pres_candidate_index]
        self.pres_candidate_index += 1

        return pres_candidate

    def get_chancellor_candidates(
        self, pres_candidate: discord.User
    ) -> List[discord.User]:
        """
        Get the list of eligible chancellors

        :param pres_candidate: The current presidential candidate
        :type pres_candidate: discord.User
        :return: The list of chancellor candidates
        :rtype: List[discord.User]
        """
        def pres_candidate_check(m):
            return m.author == pres_candidate

        candidates = self.get_players(
            predicate=(
                lambda user, _: (
                    user != self.chancellor
                    if len(self.players) <= 6
                    else user not in (self.president, self.chancellor)
                )
                and user != pres_candidate
            )
        )

        return candidates

    def reset_term_limits(self):
        """
        Resets term limits for the position of Chancellor
        """
        self.president = None
        self.chancellor = None

    def randomise_roles(self):
        """
        Randomises the players of players
        """
        # Get number of liberals and fascists for player count
        num_libs, num_fascs = PLAYERS_TO_LIB_FASC_COUNT[len(self.players)]
        # Produce roles
        roles = ["liberal" for _ in range(num_libs)]
        roles.extend("fascist" for _ in range(num_fascs))
        # Shuffle them
        random.shuffle(roles)
        # Assign roles
        self.players = {user: role for user, role in zip(self.players, roles)}
        # Choose Hitler
        fascists = self.get_players(lambda _, role: role == "fascist")
        hitler = random.choice(fascists)

        self.players[hitler] = "hitler"

    def populate_policies(self):
        """
        Populates the policy deck with the set number of policies
        """
        self.policies = [policy_type for policy_type, count in POLICY_COUNT.items() for _ in range(count)]

    def shuffle_policies(self):
        """
        Shuffles the policy deck
        """
        random.shuffle(self.policies)

    def reshuffle_policies_with_discarded(self):
        """
        Adds the discarded policies to the policy deck, and shuffles them
        """
        self.policies.extend(self.discarded_policies)
        self.discarded_policies = []
        self.shuffle_policies()

    def enact_policy(self, policy_type: str):
        """
        Enacts a policy of the specified type

        :param policy_type: The policy type
        :type policy_type: str
        """
        self.policy_counts[policy_type] += 1

    def enact_top_policy(self) -> str:
        """
        Enacts the policy from the top of the policy deck

        :return: The enacted policy type
        :rtype: str
        """
        policy_type = self.policies.pop()
        self.enact_policy(policy_type)

        return policy_type

    def advance_election_tracker(self):
        """
        Advances the election tracker
        """
        self.election_tracker += 1

    def reset_election_tracker(self):
        """
        Resets the election tracker
        """
        self.election_tracker = 0

    def populace_content(self) -> bool:
        """
        Returns if the populace is content or not.

        The populace is not content when the election tracker has reached 3

        :return: Whether the populace is content
        :rtype: bool
        """
        return self.election_tracker < 3

    def hitler_elected(self) -> bool:
        """
        Returns if Hitler has been elected

        :return: Whether Hitler has been elected
        :rtype: bool
        """
        return self.players[self.chancellor] == "hitler"

    def get_top_three_policies(self) -> List[str]:
        """
        Removes the three policies at the top of the policy deck,
        and returns them

        :return: The policies
        :rtype: List[str]
        """
        self.policies, policies = self.policies[:-3], self.policies[-3:]
        return policies

    def add_to_discard(self, policy_type: str):
        """
        Adds the specified policy type to the discard pile

        :param policy_type: The policy type to add
        :type policy_type: str
        """
        self.discarded_policies.append(policy_type)

    def target_reached(self, policy_type) -> bool:
        """
        Returns whether the target number of policies has been reached

        :param policy_type: The policy type to check
        :type policy_type: stsr
        :return: Whether the target has been reached
        :rtype: bool
        """
        return self.policy_counts[policy_type] >= POLICY_TARGET[policy_type]
