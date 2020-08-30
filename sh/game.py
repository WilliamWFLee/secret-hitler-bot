##!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sh.game

Copyright (c) 2020 William Lee.
Licensed under the MIT License, see LICENSE for details.
"""

import discord
from discord.ext import commands


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
