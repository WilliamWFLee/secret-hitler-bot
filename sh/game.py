##!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sh.game

Licensed under CC BY-NC-SA 4.0, see LICENSE for details.
"""

import asyncio
import itertools
from typing import Iterable, List, Optional, Tuple

import discord
from discord.ext import commands

from . import utils as ut
from .state import GameState

MIN_PLAYERS = 5
INACTIVITY_LIMIT = 300


class Game:
    """
    Class for managing a game of Secret Hitler
    """

    def __init__(
        self, bot: commands.Bot, channel: discord.TextChannel, admin: discord.User
    ):
        """
        Initialises an instance of a Secret Hitler game.
        Automatically adds the admin to the game.

        :param bot: The discord.py bot instance tied to this game
        :type bot: commands.Bot
        :param channel: The channel to use for server-wide output
        :type channel: discord.Channel
        :param admin: The admin of this game
        :type admin: discord.User
        """
        self.bot = bot
        self.channel = channel
        self.admin = admin
        self.state = GameState()
        self.inactivity_timer = 0
        self.add_player(admin)

    @property
    def guild(self):
        """
        Shortcut for Game.channel.guild
        """
        return self.channel.guild

    @property
    def players(self):
        """
        Shortcut for Game.state.players
        """
        return self.state.players

    def with_section_divider(coro):  # noqa
        async def inner(self, *args, **kwargs):
            await self._broadcast(25 * "-")
            return await coro(self, *args, **kwargs)

        return inner

    def with_inactivity_timer_reset(coro_or_func):  # noqa
        async def coro_inner(self, *args, **kwargs):
            self.inactivity_timer = 0
            return await coro_or_func(self, *args, **kwargs)

        def func_inner(self, *args, **kwargs):
            self.inactivity_timer = 0
            return coro_or_func(self, *args, **kwargs)

        if asyncio.iscoroutinefunction(coro_or_func):
            return coro_inner
        return func_inner

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
        candidate = await ut.get_choice_from_user(
            self.bot,
            pres_candidate,
            message="Choose someone to be the next chancellor candidate",
            choices=candidates,
        )
        return candidate

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
            for user in self.state.get_alive_players()
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
        if ja_votes / len(self.state.get_alive_players()) > 0.5:
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
            await self._reveal_deck_distribution()

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

    @with_section_divider
    @with_inactivity_timer_reset
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
        discard_policy = await ut.get_choice_from_user(
            self.bot,
            self.state.president,
            message="You must choose a policy to discard",
            choices=policies,
        )

        policies.remove(discard_policy)
        self.state.add_to_discard(discard_policy)
        return policies

    async def _chancellor_choose_policy(
        self, policies: List[str], can_veto: bool = False
    ) -> Optional[str]:
        if can_veto:
            policies = policies.copy() + ["I wish to veto this agenda"]
        chosen_policy = await ut.get_choice_from_user(
            self.bot,
            self.state.chancellor,
            message="You must choose a policy to enact",
            choices=policies,
        )
        if can_veto and chosen_policy == "I wish to veto this agenda":
            return None
        return chosen_policy

    async def _get_claim(self, user: discord.User, *, repeat: int) -> Iterable[str]:
        claims = (
            ", ".join(combo)
            for combo in itertools.combinations_with_replacement(
                self.state.policy_counts.keys(), r=repeat
            )
        )
        claim = await ut.get_choice_from_user(
            self.bot,
            user,
            message=(
                "Choose the number of the combination you wish to claim you received"
            ),
            choices=claims,
        )
        return claim.split(", ")

    async def _get_wish_to_make_claim(self, user: discord.User):
        return await ut.get_vote_from_user(
            self.bot,
            user,
            message=(
                "Do you wish to claim what policies you received/saw?\n"
                "If you're communicating with other players via voice, "
                "then you may select 'No'"
            ),
        )

    async def _broadcast_claim(
        self, claiming_user: discord.User, policies: Iterable[str]
    ):
        await self._broadcast(
            f"{claiming_user} claims to have received/seen **{{}}**".format(
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

    async def _begin_veto(self, remaining_policies: List[str]) -> bool:
        await self._broadcast("The chancellor wishes to veto the current agenda")
        await self._broadcast(
            "The president will now choose whether or not they consent to the veto"
        )
        pres_agrees = await ut.get_vote_from_user(
            self.bot, self.state.president, message="Do you agree to veto this agenda?"
        )
        if pres_agrees:
            await self._broadcast("The president agrees to veto the agenda")
            for policy in remaining_policies:
                self.state.add_to_discard(policy)
        else:
            await self._broadcast("The president does not agree to veto the agenda")
            await self._broadcast("The chancellor will enact a policy as normal")
            chosen_policy = await self._chancellor_choose_policy(remaining_policies)
            await self._enact_policy(chosen_policy)

    @with_section_divider
    @with_inactivity_timer_reset
    async def _play_legislative_session(self) -> Optional[str]:
        await self._broadcast("**LEGISLATIVE SESSION**")
        if self.state.can_veto():
            await self._broadcast(
                "The executive branch have the power to veto the agenda in this session"
            )
        await self._broadcast(
            "The president will now receive the three policies at the top of the deck "
            "and choose the one they want to discard"
        )
        remaining_policies = await self._pres_choose_policies()
        await self._broadcast("The president has discarded a policy")
        await self._broadcast(
            "The chancellor will now choose one of the remaining two policies to enact"
        )
        chosen_policy = await self._chancellor_choose_policy(
            remaining_policies, can_veto=self.state.can_veto()
        )
        if chosen_policy is None:
            await self._begin_veto(remaining_policies)
        else:
            await self._enact_policy(chosen_policy)

        for policy_type in self.state.policy_counts:
            if self.state.target_reached(policy_type):
                self._broadcast(
                    f"The **{policy_type} have reached "
                    "their target number of policies to enact"
                )
                self._declare_win(policy_type)
                return None

        await self._pres_chancellor_claims()
        await self._check_policy_deck()
        return chosen_policy

    async def _policy_peek(self):
        await self._broadcast(
            "The president may now peek at the three policies "
            "on the top of the policy deck"
        )
        policies = self.state.peek_top_three_policies()
        await self.state.president.send(
            "The three policies are (from top to bottom) **{}**".format(
                ", ".join(policy.title() for policy in policies)
            )
        )
        await self._pres_claim()

    async def _execution(self) -> bool:
        await self._broadcast("The president must now choose a player to kill")
        alive_players = self.state.get_alive_players(exclude=(self.state.president,))
        selected_player = await ut.get_choice_from_user(
            self.bot,
            self.state.president,
            message="Choose the player you want to kill",
            choices=alive_players,
        )
        await self._broadcast(
            f"{self.state.president} formally executes {selected_player}"
        )
        self.state.kill_player(selected_player)
        await self._broadcast(f"{selected_player} is now dead")
        if self.state.hitler_dead():
            await self._broadcast("Hitler has been killed!")
            await self._declare_win("liberal")
            return False
        return True

    async def _investigate_loyalty(self):
        await self._broadcast(
            "The president has the power to investigate the loyalty of one person"
        )
        player_to_investigate = await ut.get_choice_from_user(
            self.bot,
            self.state.president,
            message="Choose a player to investigate",
            choices=self.state.get_alive_players(exclude=(self.state.president,)),
        )
        await self._broadcast(
            f"The president has chosen to investigate **{player_to_investigate}**"
        )
        membership = self.state.get_party_membership(player_to_investigate)
        await self.state.president.send(
            f"{player_to_investigate} is a **{membership}**"
        )
        wants_to_share = await ut.get_vote_from_user(
            self.bot,
            self.state.president,
            message="Do you want to share your findings?",
        )
        if wants_to_share:
            claim_membership = await ut.get_choice_from_user(
                self.bot,
                self.state.president,
                message="Choose what you want to claim your findings are",
                choices=("fascist", "liberal"),
            )
            await self._broadcast(
                f"{self.state.president} claims that {player_to_investigate} "
                f"is a {claim_membership}"
            )

    async def _special_election(self):
        await self._broadcast("The president is calling a special election")
        next_pres_candidate = await ut.get_choice_from_user(
            self.bot,
            self.state.president,
            message="Choose the next presidential candidate",
            choices=self.state.get_alive_players(exclude=(self.state.president,)),
        )
        await self._broadcast(
            f"The president has chosen {next_pres_candidate} "
            "to be the next presidential candidate"
        )
        self.state.next_presidential_candidate = next_pres_candidate

    @with_section_divider
    @with_inactivity_timer_reset
    async def _play_executive_action(self, policy_enacted: str) -> bool:
        if policy_enacted != "fascist":
            return True
        executive_action = self.state.get_executive_action()
        if executive_action:
            await self._broadcast("**EXECUTIVE ACTION**")
            executive_action_to_coro = {
                "policy_peek": self._policy_peek,
                "execute": self._execution,
                "loyalty": self._investigate_loyalty,
                "special_election": self._special_election,
            }
            result = await executive_action_to_coro[executive_action]()
            if result is not None and not result:
                return False
        return True

    async def _play_round(self) -> bool:
        game_on = await self._play_election_round()
        if not game_on:
            return False
        policy_enacted = await self._play_legislative_session()
        if policy_enacted is None:
            return False
        game_on = await self._play_executive_action(policy_enacted)
        if not game_on:
            return False
        return True

    async def _reveal_roles(self):
        await self._broadcast("Everyone's roles:\n")
        await self._broadcast(
            "\n".join(
                f"{user}: **{role}**" for user, role in self.state.players.items()
            )
        )

    async def _declare_win(self, role: str):
        await self._broadcast(f"The **{role.title()}s** have won")
        await self._reveal_roles()

    def increment_inactivity_timer(self, seconds: float) -> bool:
        """
        Increments the activity timer,
        and returns whether the inactivity limit has been reached

        :param seconds: The number of seconds to increment the timer by
        :type seconds: float
        :return: Whether the inactivity has been reached
        :rtype: bool
        """
        self.inactivity_timer += seconds
        return self.inactivity_timer >= INACTIVITY_LIMIT

    @with_inactivity_timer_reset
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

    @with_inactivity_timer_reset
    def remove_player(self, user: discord.User) -> Optional[bool]:
        """
        Remove a player from the game instance

        :param user: The user to remove
        :type user: discord.User
        :return: :data:`True` if player was removed,
                 :data:`False` if player was not in game,
                 and :data:`None` if no players remain in the game
        :rtype: bool
        """
        if user not in self.state.players:
            return False
        del self.state.players[user]
        if self.admin == user:
            self.admin = None
            if not self.state.players:
                return None
            self.admin = list(self.state.players)[0]
        return True

    @with_inactivity_timer_reset
    async def start(self):
        """
        Start the game.
        """
        if len(self.state.players) < MIN_PLAYERS:
            return await self.channel.send(
                f"Minimum number of players required is {MIN_PLAYERS}: "
                f"{MIN_PLAYERS - len(self.state.players)} more player(s) required"
            )
        await self.channel.send("Game of Secret Hitler has started!")
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
