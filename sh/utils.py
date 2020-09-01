##!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sh.utils

Licensed under CC BY-NC-SA 4.0, see LICENSE for details.
"""

import asyncio
from typing import Any, Iterable, Optional

import discord

YES = "✅"
NO = "❌"

NUMBER_EMOJI = [
    "1️⃣",
    "2️⃣",
    "3️⃣",
    "4️⃣",
    "5️⃣",
    "6️⃣",
    "7️⃣",
    "8️⃣",
    "9️⃣",
    "🔟",
]


async def get_choice_from_user(
    client: discord.Client,
    user: discord.User,
    *,
    message: Optional[str] = None,
    choices: Iterable[Any] = (),
):
    """
    Gets a choice from a user. The number of choices must not exceed 10.

    :param client: The Discord client to wait for the reaction on
    :type client: discord.Client
    :param user: The user to record the reaction from
    :type user: discord.User
    :param message: The message prompt to send, defaults to None
    :type message: Optional[str]
    :param max_: The maximum value of the choice, defaults to 10
    :type max_: int
    :raises ValueError: If the number of choices is more than 10 or empty
    """

    def check(reaction, check_user):
        return (
            str(reaction.emoji) in emoji_to_choice
            and reaction.message.id == msg.id
            and check_user == user
        )

    choices = tuple(choices)
    if not choices:
        raise ValueError("Choices cannot be empty")
    if len(choices) > 10:
        raise ValueError("Number of choices cannot be more than 10")

    if message is None:
        message = ""
    else:
        message += "\n"
    emoji_to_choice = {emoji: choice for emoji, choice in zip(NUMBER_EMOJI, choices)}
    message += (
        "\n".join(f"{emoji} {choice}" for emoji, choice in emoji_to_choice.items())
        + "\n"
    )
    message += "Choose by reacting with the number of your choice"
    msg = await user.send(message)
    await asyncio.gather(*(msg.add_reaction(emoji) for emoji in emoji_to_choice))
    reaction, _ = await client.wait_for("reaction_add", check=check)
    await msg.delete()
    return emoji_to_choice[str(reaction.emoji)]


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
