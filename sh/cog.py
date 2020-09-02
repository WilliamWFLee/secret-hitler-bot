#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sh.cog

Licensed under CC BY-NC-SA 4.0, see LICENSE for details.
"""

import asyncio

import discord
from discord.ext import commands

from .game import Game


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
            self.games[ctx.guild] = Game(self.bot, ctx.guild, ctx.author)
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
            self.games[ctx.guild] = Game(self.bot, ctx.guild, ctx.author)
            await ctx.send("Game created!")

    @commands.command()
    @commands.guild_only()
    async def leave(self, ctx):
        if ctx.guild not in self.games:
            return await ctx.send("Game has not been created yet")
        if self.games[ctx.guild] in self.game_tasks:
            return await ctx.send("You can't leave while the game is ongoing!")
        success = self.games[ctx.guild].remove_player(ctx.author)
        if success:
            await ctx.send("You have left the game :cry:")
        else:
            await ctx.send("You weren't in the game!")

    @commands.command()
    @commands.guild_only()
    async def start(self, ctx):
        if ctx.guild not in self.games:
            return await ctx.send("Game has not been created")
        if self.games[ctx.guild].admin != ctx.author:
            return await ctx.send(
                "Only the creator of the game has permission has start the game"
            )
        if ctx.guild in self.game_tasks:
            return await ctx.send("Game has already started")
        task = asyncio.create_task(self.run_game(ctx.guild, ctx.channel))
        self.game_tasks[ctx.guild] = task

    @commands.command()
    @commands.guild_only()
    async def show(self, ctx):
        embed = discord.Embed(title="Secret Hitler")
        status = "Not created"
        if ctx.guild in self.games:
            status = "Created"
        if ctx.guild in self.game_tasks:
            status = "Started"
        embed.add_field(name="Game status", value=status, inline=False)

        if ctx.guild in self.games:
            embed.add_field(name="Admin", value=self.games[ctx.guild].admin.mention)
            players = "\n".join(user.mention for user in self.games[ctx.guild].players)
            embed.add_field(
                name="Players",
                value=players if players else "No players yet",
                inline=False,
            )

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(SetupCog(bot))
