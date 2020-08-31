##!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sh.game

Licensed under CC BY-NC-SA 4.0, see LICENSE for details.
"""

import asyncio
import random
from typing import List, Optional

import discord
from discord.ext import commands

from . import utils as ut

MIN_PLAYERS = 5
FASCIST_POLICY_COUNT = 11
LIBERAL_POLICY_COUNT = 6

PLAYERS_TO_LIB_FASC_COUNT = {
    5: (3, 2),
    6: (4, 2),
    7: (4, 3),
    8: (5, 3),
    9: (5, 4),
    10: (6, 4),
}


class Game:
    """
    Class for managing a game of Secret Hitler
    """

    def __init__(self, bot: commands.Bot, guild: discord.Guild):
        """
        Initialises an instance of a Secret Hitler game

        :param bot: The discord.py bot instance tied to this game
        :type bot: commands.Bot
        :param guild: The guild this game is running in
        :type guild: discord.Guild
        """
        self.bot = bot
        self.guild = guild
        self.players = {}
        self.pres_candidate_index = 0
        self.last_chancellor = None
        self.last_president = None
        self.election_tracker = 0
        self.policies = []

    async def _broadcast(self, *args, **kwargs):
        await asyncio.gather(user.send(*args, **kwargs) for user in self.players)

    def _get_players(self, predicate=lambda user, role: True) -> List[discord.User]:
        return [user for user, role in self.players.items() if predicate(user, role)]

    def _randomise_roles(self):
        # Get number of liberals and fascists for player count
        num_libs, num_fascs = PLAYERS_TO_LIB_FASC_COUNT[len(self.players)]
        # Produce roles
        roles = ["liberal" for _ in range(num_libs)]
        roles.extend("fascist" for _ in range(num_fascs))
        # Shuffle them
        random.shufle(roles)
        # Assign roles
        self.players = {user: role for user, role in zip(self.players, roles)}
        # Choose Hitler
        fascists = self._get_players(lambda _, role: role == "fascist")
        hitler = random.choice(fascists)
        self.players[hitler] = "hitler"

    def _populate_policies(self):
        self.policies = ["Fascist" for _ in range(FASCIST_POLICY_COUNT)]
        self.policies.extend("Liberal" for _ in range(LIBERAL_POLICY_COUNT))

    def _shuffle_policies(self):
        random.shuffle(self.policies)

    async def _show_role(self, user: discord.User, role: str):
        if role == "hitler":
            await user.send("You are **Hitler**")
            if len(self.players) <= 6:
                other_fascist = self._get_players(lambda _, role: role == "fascist")[0]
                await user.send(f"The other **fascist** is {other_fascist}")
        else:
            await user.send(f"You are a **{role.title()}**")
        if role == "fascist":
            other_fascists = self._get_players(
                lambda check_user, role: role == "fascist" and check_user != user
            )
            hitler = self._get_players(lambda _, role: role == "hitler")[0]
            await user.send(f"{hitler} is **Hitler**")
            await user.send(
                "The other **fascists** are: "
                + ", ".join(str(fascist) for fascist in other_fascists)
            )

    async def _pres_choose_chancellor(
        self, pres_candidate: discord.User = None
    ) -> discord.User:
        def pres_candidate_check(m):
            return m.author == pres_candidate

        candidates = self._get_players(
            predicate=(
                lambda user, _: user != self.last_chancellor
                if len(self.players) <= 6
                else user not in (self.last_president, self.last_chancellor)
            )
        )
        cdtes_list = "\n".join(
            "{i}: {candidate}" for i, candidate in enumerate(candidates)
        )
        await pres_candidate.send("Choose someone to be the next chancellor candidate:")
        await pres_candidate.send(cdtes_list)
        await pres_candidate.send("Send the number of the player to nominate:")

        candidate_idx = await ut.get_int_from_user(
            self.bot,
            pres_candidate,
            accept=range(1, len(candidates + 1)),
            no_accept_msg="The number you selected does not correspond to a candidate",
        )

        return candidates[candidate_idx]

    async def _show_roles(self):
        await asyncio.gather(
            *(self._show_role(user, role) for user, role in self.players.items())
        )

    async def _hold_vote(self, chancellor_candidate: discord.User):
        # A dictionary mapping player to vote awaitable
        user_to_aw = {
            user: ut.get_vote_from_user(
                self.bot,
                user,
                message=(
                    "Vote on whether you want "
                    f"{chancellor_candidate} to be chancellor"
                ),
                yes_text="Ja!",
                no_text="Nein",
            )
            for user in self.players
        }
        # Gathers the votes, order is preserved
        await self._broadcast("Waiting for players to cast votes...")
        votes = await asyncio.gather(*user_to_aw.values())

        # Maps the player to their vote
        user_to_vote = {user: vote for user, vote in zip(user_to_aw, votes)}
        return user_to_vote

    async def _hold_election(
        self, pres_candidate: Optional[discord.User] = None
    ) -> Optional[discord.User]:
        if pres_candidate is None:  # If it's not a special election
            pres_candidate = list(self.players)[self.pres_candidate_index]
            self.pres_candidate_index += 1

        await self._broadcast(f"The ***presidential** candidate is {pres_candidate}")
        # Have the presidential candidate choose a chancellor
        chancellor_candidate = self._pres_choose_chancellor(pres_candidate)
        await self._broadcast(
            f"{pres_candidate} has nominated "
            f"{chancellor_candidate} as **chancellor** candidate"
        )
        # Hold vote
        user_to_vote = self._hold_vote(chancellor_candidate)
        await self._broadcast("The results of the election:")
        await self._broadcast(
            "\n".join(
                f"{user} voted " + ("Ja!" if vote else "Nein")
                for user, vote in user_to_vote.items()
            )
        )

        ja_votes = sum(1 for vote in user_to_vote.values() if vote)
        if ja_votes / len(self.players) > 0.5:
            await self._broadcast(
                f"{chancellor_candidate} has been elected as chancellor"
            )
            return chancellor_candidate
        await self._broadcast(f"{chancellor_candidate} did not get a majority vote")
        return None

    def add_player(self, user: discord.User) -> bool:
        """
        Add a player to this game instance

        :param user: The user to add
        :type user: discord.User
        :return: :data:`True` if the player was added, :data:`False` if the player has already been added
        :rtype: bool
        """
        if user in self.players:
            return False
        self.players[user] = None
        return True

    def remove_player(self, user: discord.User) -> bool:
        """
        Remove a player from the game instance

        :param user: The user to remove
        :type user: discord.User
        :return: :data:`True` if player was remove, :data:`False` was not in game
        :rtype: bool
        """
        if user not in self.players:
            return False
        del self.players[user]
        return True

    async def start(self, channel: discord.TextChannel):
        """
        Start the game.

        :param channel: The text channel to bind server-wide game output to
        :type channel: discord.TextChannel
        """
        self.channel = channel
        if len(self.players) < MIN_PLAYERS:
            return await channel.send(
                f"Minimum number of players required is {MIN_PLAYERS}: "
                f"{MIN_PLAYERS - len(self.players)} more player(s) required"
            )
        self._randomise_roles()
        self._populate_policies()
        self._shuffle_policies()
        await self._show_roles()
        while self.election_tracker < 3:
            self.chancellor = await self._hold_election()
            if self.chancellor is None:
                self.election_tracker += 1
                self._broadcast(
                    "The election tracker has been advanced by 1, "
                    f"and is now at {self.election_tracker}"
                )
            else:
                break
        else:
            pass
