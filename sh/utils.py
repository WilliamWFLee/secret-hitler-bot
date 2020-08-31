##!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sh.utils

Licensed under CC BY-NC-SA 4.0, see LICENSE for details.
"""

from typing import Iterable, Optional

import discord

YES = "✅"
NO = "❌"


async def get_int_from_user(
    client: discord.Client,
    user: discord.User,
    *,
    accept: Optional[Iterable[int]] = None,
    no_accept_msg: str = "You didn't give an integer in the accepted range.",
):
    def check(m):
        return m.content.strip().isnumeric() and m.author == user

    while True:
        msg = await client.wait_for("message", check=check)
        integer = int(msg.content.strip())
        if accept is not None and integer not in accept:
            await user.send(no_accept_msg)
            await user.send("Please try again.")
        else:
            return integer


async def get_vote_from_user(
    client: discord.Client,
    user: discord.User,
    *,
    message: Optional[str] = None,
    yes_text: str = "Yes",
    no_text: str = "No",
):
    def check(reaction, check_user):
        return str(reaction.emoji) in (YES, NO) and check_user == user

    if message is not None:
        await user.send(message)
    msg = await user.send(
        f"React with {YES} for {yes_text} or {NO} for {no_text}"
    )
    await msg.add_reaction(YES)
    await msg.add_reaction(NO)

    reaction, _ = await client.wait_for("reaction_add", check=check)
    if str(reaction.emoji) == YES:
        return True
    return False
