#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sh.cogs.setup

Copyright (c) 2020 William Lee.
Licensed under the MIT License, see LICENSE for details.
"""

import asyncio

import discord
from discord.ext import commands

from ..game import Game


class SetupCog(commands.Cog, name="Setup"):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}
        self.game_tasks = {}

    async def run_game(self, guild: discord.Guild, channel: discord.TextChannel):
        try:
            await self.games[guild].start(channel)
        finally:
            del self.game_tasks[guild]

    @commands.command()
    @commands.guild_only()
    async def join(self, ctx):
        if ctx.guild not in self.games:
            await ctx.send("Creating game...")
            self.games[ctx.guild] = Game(self.bot, ctx.guild)
        success = self.games[ctx.guild].add_player(ctx.author)
        if success:
            await ctx.send("Added you to the game!")
        else:
            await ctx.send("You've already been added to the game!")

    @commands.command()
    @commands.guild_only()
    async def create(self, ctx):
        if ctx.guild in self.games:
            await ctx.send("Game has already been created")
        else:
            self.games[ctx.guild] = Game(self.bot, ctx.guild)
            await ctx.send("Game created!")

    @commands.command()
    @commands.guild_only()
    async def leave(self, ctx):
        if ctx.guild not in self.games:
            await ctx.send("Game has not been created yet")
        success = self.games[ctx.guild].remove_player(ctx.author)
        if success:
            await ctx.send("You have left the game :cry:")
        else:
            await ctx.send("You weren't in the game!")

    @commands.command()
    @commands.guild_only()
    async def start(self, ctx):
        if ctx.guild not in self.games:
            await ctx.send("Game has not been created")
        elif ctx.guild in self.game_tasks:
            await ctx.send("Game has already started")
        else:
            task = asyncio.create_task(self.run_game(ctx.guild, ctx.channel))
            self.game_tasks[ctx.guild] = task


def setup(bot):
    bot.add_cog(SetupCog(bot))
