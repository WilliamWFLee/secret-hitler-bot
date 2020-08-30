#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from discord.ext import commands

from ..game import Game


class SetupCog(commands.Cog, name="Setup"):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

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


def setup(bot):
    bot.add_cog(SetupCog(bot))
