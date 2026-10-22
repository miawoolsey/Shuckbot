"""`;game` command: colour, flag, geography and geoguesser games plus stats/leaderboard."""
from __future__ import annotations

from discord.ext import commands

from modules.config import Config
from modules.games import colour, flags, geo
from modules.games.stats import ScoreStore, show_leaderboard, show_stats

MULTIPLAYER_WORDS = ("m", "mp", "multi", "multiplayer")
FLAG_MULTIPLAYER_WORDS = ("m", "multi", "multiplayer")
COLOUR_WORDS = ("color", "colour", "col", "c")
FLAG_WORDS = ("flag", "flags", "f")
GEOGRAPHY_WORDS = ("geography", "geo", "g")
STATS_WORDS = ("stats", "s")
LEADERBOARD_WORDS = ("leaderboard", "leader", "top", "l")
GEOGUESSER_WORDS = ("geoguesser", "geoguessr", "gg")
JAPAN_WORDS = ("japan", "j", "prefectures", "p", "pf")
MAP_WORDS = ("map", "m")


def _any_in(words, args) -> bool:
    return any(word in args for word in words)


def _first_int(args: list[str]) -> int | None:
    return next((int(arg) for arg in args if arg.isdigit()), None)


class Games(commands.Cog):
    def __init__(self, bot: commands.Bot, config: Config) -> None:
        self.bot = bot
        self.config = config
        self.scores = ScoreStore()

    @commands.command(aliases=["g"])
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def game(self, ctx: commands.Context) -> None:
        args = [word.lower() for word in ctx.message.clean_content.split(" ")[1:]]
        if not args:
            await ctx.send("**The list of available games are:**\n\t*;game colour* - guess the hexcode!")
            return
        name, options = args[0], args[1:]

        if name in COLOUR_WORDS:
            letter = "u" if name == "colour" else ""
            if options and options[0] in MULTIPLAYER_WORDS:
                if len(options) > 1 and options[1].isdigit():
                    await colour.colour_guesser_multi(ctx, letter, game_time=int(options[1]))
                else:
                    await colour.colour_guesser_multi(ctx, letter)
            else:
                await colour.colour_guesser(ctx, letter)

        elif name in FLAG_WORDS:
            if not options:
                await flags.flag_guesser(ctx, self.scores)
            elif _any_in(FLAG_MULTIPLAYER_WORDS, options):
                difficulty = max([0] + [flags.difficulty_from_arg(arg) for arg in options])
                points_to_win = _first_int(options)
                if points_to_win is None:
                    await flags.flag_guesser_multi(ctx, self.scores, difficulty=difficulty)
                else:
                    await flags.flag_guesser_multi(ctx, self.scores, difficulty=difficulty,
                                                   points_to_win=points_to_win)
            else:
                await flags.flag_guesser(ctx, self.scores, flags.difficulty_from_arg(options[0]))

        elif name in GEOGRAPHY_WORDS:
            area = "japan" if _any_in(JAPAN_WORDS, args) else ""
            mode = "map" if _any_in(MAP_WORDS, args) else ""
            await geo.geography_game(ctx, self.scores, area, mode)

        elif name in STATS_WORDS:
            user = ctx.message.mentions[0] if ctx.message.mentions else ctx.author
            if _any_in(COLOUR_WORDS, options):
                game = "color"
            elif _any_in(FLAG_WORDS, options):
                game = "flag"
            elif _any_in(GEOGRAPHY_WORDS, options):
                game = "geography"
            else:
                game = "all"
            await show_stats(ctx, self.scores, user, game)

        elif name in LEADERBOARD_WORDS:
            await show_leaderboard(ctx, self.scores)

        elif name in GEOGUESSER_WORDS:
            await geo.geoguesser_game(ctx, self.scores, self.config.mapquest_key, options[0] if options else None)
