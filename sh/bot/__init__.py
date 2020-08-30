#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sh.bot

Copyright (c) 2020 William Lee.
Licensed under the MIT License, see LICENSE for details.
"""

import os
from typing import Optional

from discord.ext import commands

__all__ = ["run"]

bot = commands.Bot(command_prefix="sh-", case_insensitive=True)


@bot.event
async def on_ready():
    print("Secret Hitler Bot is ready")


@bot.event
async def on_command_error(ctx, error):
    ignore = (commands.CommandNotFound,)
    if isinstance(error, ignore):
        return


def run(token: Optional[str] = None):
    """
    Run Secret Hitler Bot with the given token. If token is :data:`None`,
    then attempt to retrieve the token from environment variables
    under the key ``BOT_TOKEN``.

    :param token: The bot token to login into Discord with
    :type token: Optional[str]
    :raises RuntimeError: If token is not specified and was not found in environment
    """
    if token is None:
        token = os.getenv("BOT_TOKEN")
        if token is None:
            raise RuntimeError("Bot token was not found under 'BOT_TOKEN'")
    bot.run(token)
