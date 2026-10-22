import logging

import discord
from discord.ext import commands

from modules import net
from modules.avwx import Aviation
from modules.config import Config
from modules.core import Core, PrefixStore
from modules.games import Games
from modules.help import Help
from modules.identify import Identify
from modules.imagefun import ImageFun
from modules.imagesearch import ImageSearch
from modules.picturebook import Picturebook
from modules.readycheck import ReadyCheck, ReadyCheckView
from modules.tags import Tags

log = logging.getLogger("shuckbot")


class Shuckbot(commands.Bot):
    def __init__(self, config: Config) -> None:
        self.config = config
        self.prefixes = PrefixStore()
        super().__init__(
            command_prefix=lambda bot, message: self.prefixes.get(message.guild.id if message.guild else None),
            intents=discord.Intents.all(),
            help_command=None,  # replaced by our own ;help
        )

    async def setup_hook(self) -> None:
        await net.start()
        for cog in (
            Core(self, self.config, self.prefixes),
            Help(self),
            ImageSearch(self, self.config.google_key),
            Picturebook(self, self.config),
            Tags(self, self.config),
            Aviation(self, self.config.avwx_key),
            ImageFun(self),
            Games(self, self.config),
            Identify(self, self.config),
            ReadyCheck(self),
        ):
            await self.add_cog(cog)
        self.add_view(ReadyCheckView())  # keep ready check buttons working across restarts

    async def close(self) -> None:
        await super().close()
        await net.close()

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("Sorry, this command is on cooldown! Try again in {:.2f} seconds".format(error.retry_after))
        elif isinstance(error, (commands.CommandNotFound, commands.NoPrivateMessage)):
            pass
        elif isinstance(error, commands.UserInputError):
            log.info("Bad input for %s: %s", ctx.command, error)
        else:
            original = getattr(error, "original", error)
            log.error("Error in command %s (message: %r)", ctx.command, ctx.message.content,
                      exc_info=(type(original), original, original.__traceback__))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = Config.load()
    Shuckbot(config).run(config.token, log_handler=None)


if __name__ == "__main__":
    main()
