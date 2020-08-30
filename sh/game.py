##!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sh.game

Licensed under CC BY-NC-SA 4.0, see LICENSE for details.
"""

import asyncio
import random
from typing import Optional

import discord
from discord.ext import commands

MIN_PLAYERS = 5


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

    def _get_players_with_role(self, role: str, exclude: Optional[discord.User] = None):
        return [
            user for user, r in self.players.items() if r == role and user != exclude
        ]

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
        fascists = self._get_players_with_role("fascist")
        hitler = random.choice(fascists)
        self.players[hitler] = "hitler"

    async def _show_role(self, user: discord.User, role: str):
        if role == "hitler":
            await user.send("You are **Hitler**")
            if len(self.players) <= 6:
                other_fascist = self._get_players_with_role("fascist")[0]
                await user.send(f"The other **fascist** is {str(other_fascist)}")
        else:
            await user.send(f"You are a **{role.title()}**")
        if role == "fascist":
            other_fascists = self._get_players_with_role("fascist", exclude=user)
            hitler = self._get_players_with_role("hitler")[0]
            await user.send(f"{str(hitler)} is **Hitler**")
            await user.send(
                "The other **fascists** are: "
                + ", ".join(str(fascist) for fascist in other_fascists)
            )

    async def _show_roles(self):
        await asyncio.gather(
            *(self._show_role(user, role) for user, role in self.players.items())
        )

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
        await self._show_roles()
