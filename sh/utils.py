##!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sh.utils

Licensed under CC BY-NC-SA 4.0, see LICENSE for details.
"""

import asyncio
from typing import Optional

import discord

YES = "✅"
NO = "❌"

INT_TO_EMOJI = {
    0: "0️⃣",
    1: "1️⃣",
    2: "2️⃣",
    3: "3️⃣",
    4: "4️⃣",
    5: "5️⃣",
    6: "6️⃣",
    7: "7️⃣",
    8: "8️⃣",
    9: "9️⃣",
    10: "🔟",
}

EMOJI_TO_INT = {v: k for k, v in INT_TO_EMOJI.items()}


async def get_int_choice_from_user(
    client: discord.Client,
    user: discord.User,
    *,
    message: Optional[str] = None,
    min_: int = 0,
    max_: int = 10,
):
    """
    Gets a integer choice from the specified user, with the allowed values
    between a minimum and maximum value.

    :param client: The Discord client to wait for the reaction on
    :type client: discord.Client
    :param user: The user to record the reaction from
    :type user: discord.User
    :param message: The message prompt to send, defaults to None
    :type message: Optional[str]
    :param min_: The minimum value of the choice, defaults to 0
    :type min_: int
    :param max_: The maximum value of the choice, defaults to 10
    :type max_: int
    """

    def check(reaction, check_user):
        return (
            str(reaction.emoji) in emoji
            and reaction.message.id == msg.id
            and check_user == user
        )

    if min_ < 0:
        raise ValueError("Minimum value cannot be less than 0")
    if max_ > 10:
        raise ValueError("Maximum value cannot be more than 10")

    if message is None:
        message = f"Pick a number between {min_} and {max_} inclusive"

    emoji = [INT_TO_EMOJI[v] for v in range(min_, max_ + 1)]
    msg = await user.send(message)
    await asyncio.gather(*(msg.add_reaction(e) for e in emoji))
    reaction, _ = await client.wait_for("reaction_add", check=check)
    await msg.delete()
    return EMOJI_TO_INT[str(reaction.emoji)]


async def get_vote_from_user(
    client: discord.Client,
    user: discord.User,
    *,
    message: Optional[str] = None,
    yes_text: str = "Yes",
    no_text: str = "No",
):
    """
    Gets a yes/no vote from a user

    :param client: The client to use to listen for the vote
    :type client: discord.Client
    :param user: The user to get the vote from
    :type user: discord.User
    :param message: The optional message to give to the user, defaults to None
    :type message: Optional[str]
    :param yes_text: The label to give the 'yes' option, defaults to "Yes"
    :type yes_text: str
    :param no_text: The label to give the 'no' option, defaults to "No"
    :type no_text: str
    """

    def check(reaction, check_user):
        return (
            str(reaction.emoji) in (YES, NO)
            and reaction.message.id == msg.id
            and check_user == user
        )

    if message is None:
        message = ""
    msg = await user.send(
        f"{message}\nReact with {YES} for {yes_text} or {NO} for {no_text}"
    )
    await msg.add_reaction(YES)
    await msg.add_reaction(NO)

    reaction, _ = await client.wait_for("reaction_add", check=check)
    await msg.delete()
    if str(reaction.emoji) == YES:
        return True
    return False
