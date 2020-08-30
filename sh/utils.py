##!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sh.utils

Licensed under CC BY-NC-SA 4.0, see LICENSE for details.
"""

from typing import Iterable, Optional

import discord


async def get_int_from_user(
    self,
    client: discord.Client,
    user: discord.User,
    *,
    accept: Optional[Iterable[int]] = None,
    no_accept_msg: str = "You didn't give an integer in the accepted range."
):
    def check(m):
        return m.strip().isnumeric() and m.author == user

    while True:
        msg = await client.wait_for("message", check=check)
        integer = int(msg.strip())
        if accept is not None and integer not in accept:
            await user.send(no_accept_msg)
            await user.send("Please try again.")
        else:
            return integer
