##!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sh.game

Licensed under CC BY-NC-SA 4.0, see LICENSE for details.
"""

import asyncio
import itertools
from typing import List, Optional, Tuple, Iterable

import discord
from discord.ext import commands

from . import utils as ut
from .state import GameState

MIN_PLAYERS = 5


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
        self.state = GameState()

    async def _broadcast(self, *args, **kwargs):
        await asyncio.gather(
            *(user.send(*args, **kwargs) for user in self.state.players)
        )

    async def _reveal_top_policy(self):
        policy_type = self.state.enact_top_policy()
        await self._show_enacted_policy(policy_type)

    async def _enact_policy(self, policy_type: str):
        self.state.enact_policy(policy_type)
        await self._show_enacted_policy(policy_type)

    async def _show_enacted_policy(self, policy_type: str):
        await self._broadcast(f"A **{policy_type}** policy has been enacted")
        await self._broadcast(
            "There are now "
            + " and ".join(
                f"**{count} {policy_type}**"
                for policy_type, count in self.state.policy_counts.items()
            )
            + " policies enacted"
        )

    async def _show_role(self, user: discord.User, role: str):
        if role == "hitler":
            await user.send("You are **Hitler**")
            if len(self.state.players) <= 6:
                other_fascist = self.state.get_fascist_players()[0]
                await user.send(f"The other **fascist** is {other_fascist}")
        else:
            await user.send(f"You are a **{role.title()}**")

            if role == "fascist":
                other_fascists = self.state.get_fascist_players(exclude=(user,))
                hitler = self.state.get_hitler()
                await user.send(f"{hitler} is **Hitler**")
                if other_fascists:
                    await user.send(
                        "The other **fascists** are: "
                        + ", ".join(str(fascist) for fascist in other_fascists)
                    )

    async def _pres_choose_chancellor(
        self, pres_candidate: discord.User = None
    ) -> discord.User:
        candidates = self.state.get_chancellor_candidates(pres_candidate)
        cdtes_list = "\n".join(
            f"{i + 1}: {candidate}" for i, candidate in enumerate(candidates)
        )

        candidate_idx = await ut.get_int_choice_from_user(
            self.bot,
            pres_candidate,
            message=(
                "Choose someone to be the next chancellor candidate:\n"
                f"{cdtes_list}\n"
                "React with the number of the player to nominate"
            ),
            min_=1,
            max_=len(candidates),
        )

        return candidates[candidate_idx - 1]

    async def _show_roles(self):
        await asyncio.gather(
            *(self._show_role(user, role) for user, role in self.state.players.items())
        )

    async def _hold_vote(self, chancellor_candidate: discord.User):
        # A dictionary mapping player to vote awaitable
        user_to_aw = {
            user: ut.get_vote_from_user(
                self.bot,
                user,
                message=(
                    "Vote on whether you want "
                    f"**{chancellor_candidate}** to be chancellor"
                ),
                yes_text="Ja!",
                no_text="Nein",
            )
            for user in self.state.players
        }
        # Gathers the votes, order is preserved
        votes = await asyncio.gather(*user_to_aw.values())

        # Maps the player to their vote
        user_to_vote = {user: vote for user, vote in zip(user_to_aw, votes)}
        return user_to_vote

    async def _hold_election(
        self, pres_candidate: Optional[discord.User] = None
    ) -> Optional[Tuple[discord.User, discord.User]]:
        await self._broadcast("**ELECTION**")
        if pres_candidate is None:  # If it's not a special election
            pres_candidate = self.state.get_presidential_candidate()
            await self._broadcast(f"The **presidential** candidate is {pres_candidate}")
        # Have the presidential candidate choose a chancellor
        await self._broadcast(
            "The presidential candidate will now choose a chancellor candidate"
        )
        chancellor_candidate = await self._pres_choose_chancellor(pres_candidate)
        await self._broadcast(
            f"**{pres_candidate}** has nominated "
            f"**{chancellor_candidate}** as **chancellor** candidate"
        )
        # Hold vote
        user_to_vote = await self._hold_vote(chancellor_candidate)
        await self._broadcast("The results of the election:")
        await self._broadcast(
            "\n".join(
                f"{user} voted **{{}}**".format("Ja!" if vote else "Nein")
                for user, vote in user_to_vote.items()
            )
        )

        ja_votes = sum(1 for vote in user_to_vote.values() if vote)
        if ja_votes / len(self.state.players) > 0.5:
            await self._broadcast(
                f"**{pres_candidate}** and **{chancellor_candidate}** "
                "have been elected as **president** and **chancellor**"
            )
            self.state.president = pres_candidate
            self.state.chancellor = chancellor_candidate
            return True
        await self._broadcast(
            f"**{pres_candidate} and {chancellor_candidate}** "
            "have not been elected as **president** and **chancellor**"
        )
        return False

    async def _reset_election_tracker(self):
        self.state.reset_election_tracker()
        await self._broadcast("The election tracker has been reset to 0")

    async def _reveal_deck_distribution(self):
        await self._broadcast(
            "There are "
            + " and ".join(
                f"**{count} {policy_type}**"
                for policy_type, count in self.state.deck_distribution.items()
            )
            + " policies in the deck"
        )

    async def _check_policy_deck(self):
        # Checks whether there are fewer than three policies left
        # adds the discard pile to the deck as appropriate
        if len(self.state.policy_deck) < 3:
            self.state.reshuffle_policies_with_discarded()
            await self._broadcast(
                "Discarded policies have been added to the policy deck"
            )
            await self._broadcast("The deck has been reshuffled")
            await self._broadcast("There are now ")

    async def _chaos(self):
        await self._broadcast(
            "You've failed to elect a government three times in a row"
        )
        await self._broadcast("The country has been thrown into chaos!")
        await self._broadcast(
            "The policy from the top of the deck "
            "will be revealed and enacted immediately."
        )
        await self._reveal_top_policy()
        self.state.reset_term_limits()
        await self._broadcast("Term limits for chancellor have been reset")
        await self._reset_election_tracker()
        await self._reveal_deck_distribution()

    async def _play_election_round(self) -> bool:
        while True:
            success = await self._hold_election()
            if not success:
                self.state.advance_election_tracker()
                await self._broadcast(
                    "The election tracker has been advanced by 1, "
                    f"and is now at **{self.state.election_tracker}**"
                )
                if not self.state.populace_content():
                    await self._chaos()
            else:
                break
        if self.state.hitler_elected() and self.state.policy_counts["fascist"] >= 3:
            await self._broadcast(
                "There are more than three fascist policies enacted "
                "and you have elected Hitler as your chancellor"
            )
            await self._declare_win("fascist")
            return False
        return True

    async def _pres_choose_policies(self) -> List[str]:
        policies = self.state.get_top_three_policies()
        policies_list = "\n".join(
            f"{i + 1}: **{policy.title()}**" for i, policy in enumerate(policies)
        )
        discard_index = await ut.get_int_choice_from_user(
            self.bot,
            self.state.president,
            message=(
                "You must choose a policy to discard:\n"
                f"{policies_list}\n"
                "React with the number of the policy you want to **discard**"
            ),
            min_=1,
            max_=3,
        )

        self.state.add_to_discard(policies.pop(discard_index - 1))
        return policies

    async def _chancellor_choose_policy(self, policies: List[str]) -> str:
        policies_list = "\n".join(
            f"{i + 1}: **{policy.title()}**" for i, policy in enumerate(policies)
        )
        chosen_index = await ut.get_int_choice_from_user(
            self.bot,
            self.state.chancellor,
            message=(
                "You must choose a policy to enact:\n"
                f"{policies_list}\n"
                "React with the number of the policy you want to **enact**"
            ),
            min_=1,
            max_=2,
        )

        return policies[chosen_index - 1]

    async def _get_claim(self, user: discord.User, *, repeat: int) -> Iterable[str]:
        claims = list(
            itertools.combinations_with_replacement(
                self.state.policy_counts.keys(), r=repeat
            )
        )
        claims_list = "\n".join(
            f"{i + 1}: {', '.join(policy.title() for policy in policies)}"
            for i, policies in enumerate(claims)
        )

        claim_index = await ut.get_int_choice_from_user(
            self.bot,
            user,
            message=(
                f"{claims_list}\n"
                "Choose the number of the combination you wish to claim you received"
            ),
            min_=1,
            max_=repeat,
        )
        return claims[claim_index - 1]

    async def _get_wish_to_make_claim(self, user: discord.User):
        return await ut.get_vote_from_user(
            self.bot,
            user,
            message=(
                "Do you wish to claim what policies you received?\n"
                "If you're communicating with other players via voice, "
                "then you may select 'No'"
            ),
        )

    async def _broadcast_claim(
        self, claiming_user: discord.User, policies: Iterable[str]
    ):
        await self._broadcast(
            f"{claiming_user} claims to have received **{{}}**".format(
                ", ".join(policy.title() for policy in policies)
            )
        )

    async def _pres_claim(self):
        wants_claim = await self._get_wish_to_make_claim(self.state.president)
        if not wants_claim:
            return
        claim = await self._get_claim(self.state.president, repeat=3)
        await self._broadcast_claim(self.state.president, claim)

    async def _chancellor_claim(self):
        wants_claim = await self._get_wish_to_make_claim(self.state.chancellor)
        if not wants_claim:
            return
        claim = await self._get_claim(self.state.chancellor, repeat=2)
        await self._broadcast_claim(self.state.chancellor, claim)

    async def _pres_chancellor_claims(self):
        await asyncio.gather(self._pres_claim(), self._chancellor_claim())

    async def _play_legislative_session(self) -> bool:
        await self._broadcast("**LEGISLATIVE SESSION**")
        await self._broadcast(
            "The president will now receive the three policies at the top of the deck "
            "and choose the one they want to discard"
        )
        remaining_policies = await self._pres_choose_policies()
        await self._broadcast(
            "The president has discarded a policy\n"
            "The chancellor will now choose one of the remaining two policies to enact"
        )
        chosen_policy = await self._chancellor_choose_policy(remaining_policies)
        await self._enact_policy(chosen_policy)

        for policy_type in self.state.policy_counts:
            if self.state.target_reached(policy_type):
                self._broadcast(
                    f"The **{policy_type} have reached "
                    "their target number of policies to enact"
                )
                self._declare_win(policy_type)
                return False

        await self._pres_chancellor_claims()
        await self._check_policy_deck()
        return True

    async def _play_round(self) -> bool:
        rounds = (self._play_election_round, self._play_legislative_session)
        for round_ in rounds:
            game_on = await round_()
            if not game_on:
                return False
        return True

    async def _reveal_roles(self):
        await self._broadcast("Everyone's roles:\n")
        await self._broadcast(
            "\n".join("{user}: **{role}**" for user, role in self.state.players.items())
        )

    async def _declare_win(self, role: str):
        await self._broadcast(f"The **{role.title()}s** have won")
        await self._reveal_roles()

    def add_player(self, user: discord.User) -> bool:
        """
        Add a player to this game instance

        :param user: The user to add
        :type user: discord.User
        :return: :data:`True` if the player was added, :data:`False` if the player has already been added
        :rtype: bool
        """
        if user in self.state.players:
            return False
        self.state.players[user] = None
        return True

    def remove_player(self, user: discord.User) -> bool:
        """
        Remove a player from the game instance

        :param user: The user to remove
        :type user: discord.User
        :return: :data:`True` if player was remove, :data:`False` was not in game
        :rtype: bool
        """
        if user not in self.state.players:
            return False
        del self.state.players[user]
        return True

    async def start(self, channel: discord.TextChannel):
        """
        Start the game.

        :param channel: The text channel to bind server-wide game output to
        :type channel: discord.TextChannel
        """
        self.channel = channel
        if len(self.state.players) < MIN_PLAYERS:
            return await channel.send(
                f"Minimum number of players required is {MIN_PLAYERS}: "
                f"{MIN_PLAYERS - len(self.state.players)} more player(s) required"
            )
        self.state.randomise_roles()
        self.state.populate_policies()
        self.state.shuffle_policies()
        await self._show_roles()
        await self._reveal_deck_distribution()
        running = True
        while running:
            game_continue = await self._play_round()
            if not game_continue:
                running = False
        self.state.reset()
