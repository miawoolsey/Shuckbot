"""Image editing, meme template, and emoji commands."""
from __future__ import annotations

import logging
import math
import random
import re
from typing import Callable

import discord
from discord.ext import commands
from PIL import Image

from modules import imaging, net
from modules.config import ASSETS_DIR
from modules.discord_utils import Progress, avatar_url, bytes_to_file, image_to_file
from modules.image_input import (IMAGE_EXTENSIONS, MSG_BROKEN_IMAGE, ImageDecodeError, download_image,
                                 message_image_urls, read_image, run_image_job)

log = logging.getLogger(__name__)

STEPS = ("Processing .", "Processing ..", "Processing ...")
STEPS_NO_SPACE = ("Processing.", "Processing..", "Processing...")
SINGLE_STEP = ("Processing...",)
SLOW_STEPS = tuple("Processing (this might take a while)" + dots for dots in ("", " .", " ..", " ...", " ...."))

CUSTOM_EMOJI_URL = "https://cdn.discordapp.com/emojis/{id}.{ext}"
TWEMOJI_URL = "https://raw.githubusercontent.com/twitter/twemoji/master/assets/svg/{code}.svg"
CUSTOM_EMOJI_ID = re.compile(r"(\d+)>$")
MSG_BAD_EMOJI = "There is a problem with that emoji, sorry :frowning:"
UNDO_HISTORY_LIMIT = 30


def _last_word(message: discord.Message) -> str:
    return message.clean_content.split(" ")[-1]


def _parse_finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(text)
    return value


def _render(transform: Callable[..., Image.Image], img: Image.Image, filename: str, *args) -> discord.File:
    return image_to_file(transform(img, *args), filename)


class ImageFun(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _edit_image(self, ctx: commands.Context, steps: tuple[str, ...], transform: Callable[..., Image.Image],
                          filename: str, *args) -> bool:
        """Read the user's image, transform it in a worker thread, and post the result."""
        async with Progress(ctx.channel, steps[0]) as progress:
            img = await read_image(ctx.message)
            if img is None:
                return False
            if len(steps) > 1:
                await progress.update(steps[1])
            try:
                file = await run_image_job(_render, transform, img, filename, *args)
            except (ValueError, OSError, MemoryError):
                log.exception("Failed to render %s", filename)
                await progress.finish()
                await ctx.send(MSG_BROKEN_IMAGE)
                return False
            for step in steps[2:]:
                await progress.update(step)
            await progress.finish()
            await ctx.send(file=file)
            return True

    # --- meme templates --------------------------------------------------------------------

    @commands.command(aliases=["hold"])
    async def holding(self, ctx):
        await self._edit_image(ctx, STEPS, imaging.holding, "holding.png")

    @commands.command(aliases=["exmilitary"])
    async def exm(self, ctx):
        await self._edit_image(ctx, STEPS, imaging.exmilitary, "exmilitary.png")

    @commands.command(aliases=["fan", "review", "tnd"])
    async def fantano(self, ctx):
        variant = ctx.message.id % len(imaging.FANTANO_VARIANTS)
        await self._edit_image(ctx, STEPS, imaging.fantano, "fantano.png", variant)

    @commands.command()
    async def kim(self, ctx):
        await self._edit_image(ctx, STEPS, imaging.kim, "kim.png")

    @commands.command(aliases=["mina"])
    async def twice(self, ctx):
        await self._edit_image(ctx, STEPS, imaging.twice, "twice.png")

    @commands.command(aliases=["drawing"])
    async def draw(self, ctx):
        await self._edit_image(ctx, STEPS, imaging.drawing, "drawing.png")

    @commands.command(aliases=["loona"])
    async def heejin(self, ctx):
        await self._edit_image(ctx, STEPS, imaging.heejin, "heejin.png")

    @commands.command()
    async def school(self, ctx):
        await self._edit_image(ctx, STEPS, imaging.school, "school.png")

    @commands.command(aliases=["lect"])
    async def lecture(self, ctx):
        await self._edit_image(ctx, STEPS, imaging.lecture, "school.png")

    @commands.command()
    async def tesla(self, ctx):
        await self._edit_image(ctx, SINGLE_STEP, imaging.tesla, "tesla.png")

    @commands.command()
    async def osu(self, ctx):
        variant = random.randrange(len(imaging.OSU_VARIANTS))
        await self._edit_image(ctx, STEPS, imaging.osu, "osu.png", variant)

    @commands.command(aliases=["gf"])
    async def mokou(self, ctx):
        await self._edit_image(ctx, STEPS_NO_SPACE, imaging.mokou, "mokou.png")

    @commands.command(aliases=["megu"])
    async def megumin(self, ctx):
        await self._edit_image(ctx, SINGLE_STEP, imaging.megumin, "megumin.png")

    @commands.command()
    async def weezer(self, ctx):
        await self._edit_image(ctx, SINGLE_STEP, imaging.weezer, "weezer.png")

    @commands.command()
    async def sickos(self, ctx):
        await self._edit_image(ctx, SINGLE_STEP, imaging.sickos, "sickos.png")

    @commands.command(aliases=["tom"])
    async def tomscott(self, ctx):
        await self._edit_image(ctx, SINGLE_STEP, imaging.tom_scott, "tom.png")

    # --- filters ---------------------------------------------------------------------------

    @commands.command(aliases=["1bit", "1"])
    async def one(self, ctx):
        await self._edit_image(ctx, SINGLE_STEP, imaging.one_bit, "one.png")

    @commands.command(aliases=["torgb", "2rgb"])
    async def rgb(self, ctx):
        await self._edit_image(ctx, SINGLE_STEP, imaging.to_rgb, "rgb.png")

    @commands.command()
    async def purple(self, ctx):
        await self._edit_image(ctx, SINGLE_STEP, imaging.purple, "purple.png")

    @commands.command()
    async def whatifitwaspurple(self, ctx):
        if await self._edit_image(ctx, SINGLE_STEP, imaging.purple, "purple.png"):
            await ctx.send(file=discord.File(ASSETS_DIR / "misc" / "whatifitwaspurple.png"))

    @commands.command(aliases=["noisy"])
    async def mix(self, ctx):
        try:
            amount = abs(int(_last_word(ctx.message))) * 5
        except ValueError:
            amount = 10
        await self._edit_image(ctx, SINGLE_STEP, imaging.mix, "mix.png", min(amount, 100))

    @commands.command(aliases=["pixelsort", "sortpixels"])
    async def sort(self, ctx):
        await self._edit_image(ctx, SLOW_STEPS[:2] + SLOW_STEPS[4:], imaging.sort_pixels, "sorted_pixels.png", _last_word(ctx.message))

    @commands.command()
    async def shift(self, ctx):
        words = ctx.message.clean_content.split(" ")
        axis = None
        try:
            amount = int(words[-1])
        except ValueError:
            axis = {"x": 1, "horizontal": 1, "h": 1, "y": 0, "vertical": 0, "v": 0}.get(words[-1])
            try:
                if axis is None:
                    raise ValueError(words[-1])
                amount = int(words[-2])
            except (ValueError, IndexError):
                await ctx.send("Hey! Those are not valid arguments! It should either look like "
                               ";shift <number> <argument>  or  ;shift <number> !")
                return
        await self._edit_image(ctx, STEPS_NO_SPACE, imaging.shift, "warp.png", amount, axis)

    @commands.command(aliases=["pixelshuffle"])
    async def shuffle(self, ctx):
        async with Progress(ctx.channel, SLOW_STEPS[0]) as progress:
            img = await read_image(ctx.message)
            if img is None:
                return
            max_factor = imaging.shuffle_limit(img.width, img.height)
            await progress.update(SLOW_STEPS[1])
            try:
                swap_factor = _parse_finite_float(_last_word(ctx.message))
            except ValueError:
                swap_factor = max_factor
            if swap_factor > max_factor:
                swap_factor = max_factor
            await progress.update(SLOW_STEPS[2])
            file = await run_image_job(_render, imaging.shuffle_pixels, img, "shuffled_pixels.png", swap_factor)
            await progress.update(SLOW_STEPS[4])
        await ctx.send("Shuffled the image by **" + str(swap_factor) + "** !")
        await ctx.send(file=file)

    @commands.command(aliases=["scale"])
    async def resize(self, ctx):
        try:
            factor = _parse_finite_float(_last_word(ctx.message))
        except ValueError:
            await ctx.send("Hey you need to add a number to the end of the command!")
            return
        async with Progress(ctx.channel, STEPS[0]) as progress:
            img = await read_image(ctx.message)
            if img is None:
                return
            await progress.update(STEPS[1])
            max_factor, min_factor = imaging.resize_limits(img.width, img.height)
            if factor > max_factor:
                factor = max_factor
                await ctx.send("Changing the resize factor to **" + str(factor) + "**")
            if factor < min_factor:
                factor = min_factor
                await ctx.send("Changing the resize factor to **" + str(factor) + "**")
            await progress.update(STEPS[2])
            file = await run_image_job(_render, imaging.resize, img, "resized_img.png", factor)
        await ctx.send(file=file)

    @commands.command()
    async def noise(self, ctx):
        max_width = max_height = 500
        words = ctx.message.clean_content.split(" ")
        try:
            width, height = int(words[1]), int(words[2])
        except ValueError:
            await ctx.send("Hey! You didnt enter valid numbers for height and width!")
            return
        except IndexError:
            await ctx.send("Hey! You need to enter two values with your command for height and width!")
            return

        async with Progress(ctx.channel, "Processing") as progress:
            clamped_width = min(max(width, 1), max_width)
            clamped_height = min(max(height, 1), max_height)
            text = "Processing"
            if (clamped_width, clamped_height) != (width, height):
                text = "Resizing to (" + str(clamped_width) + ", " + str(clamped_height) + "), " + text
            await progress.update(text + ".")
            file = await run_image_job(
                lambda: image_to_file(imaging.noise(clamped_width, clamped_height), "noise.png"))
        await ctx.send(file=file)

    # --- image info ------------------------------------------------------------------------

    @commands.command()
    async def size(self, ctx):
        img = await read_image(ctx.message)
        if img is not None:
            await ctx.send("The images dimensions are: " + str(img.size) + " !")

    @commands.command(aliases=["a"])
    async def avatar(self, ctx):
        mentions = ctx.message.mentions if len(ctx.message.clean_content.split(" ")) > 1 else []
        if mentions:
            await ctx.send("".join(avatar_url(member) + "\n" for member in mentions))
        else:
            await ctx.send(avatar_url(ctx.author))

    @commands.command(aliases=["colour", "c"])
    async def color(self, ctx):
        colour = ctx.message.clean_content.split(" ")[1:]
        if not colour:
            await ctx.send("Hey you need to add a hex code or rgb values to the end of the command!")
            return
        if len(colour) != 1:
            return
        value = colour[0] if colour[0].startswith("#") else "#" + colour[0]
        try:
            img = imaging.solid_colour(value)
        except ValueError:
            await ctx.send("Hey you need to add a valid hex code to the end of the command!")
            return
        await ctx.send(file=image_to_file(img, "colour.png"))

    @commands.command()
    async def undo(self, ctx):
        """Re-post the image from before the bot's most recent image edit."""
        async with Progress(ctx.channel, STEPS[0]) as progress:
            seen_bot_image = False
            target = None
            async for message in ctx.channel.history(limit=UNDO_HISTORY_LIMIT):
                for url in message_image_urls(message, IMAGE_EXTENSIONS):
                    if seen_bot_image:
                        target = url
                        break
                    if message.author.bot:
                        seen_bot_image = True
                        await progress.update(STEPS[1])
                if target:
                    break
            if target is None:
                await progress.update(STEPS[2])
                await progress.finish()
                await ctx.send("There's nothing to undo!")
                return
            await progress.update(STEPS[2])
            try:
                img = await download_image(target)
                file = await run_image_job(image_to_file, img, "undo.png")
            except (net.FetchError, ImageDecodeError, OSError):
                await progress.finish()
                await ctx.send(MSG_BROKEN_IMAGE)
                return
        await ctx.send(file=file)

    # --- emoji -----------------------------------------------------------------------------

    @commands.command(aliases=["e"])
    async def emote(self, ctx):
        words = ctx.message.content.split(" ")
        async with Progress(ctx.channel, STEPS[0]) as progress:
            if len(words) < 2 or not words[1]:
                await ctx.send(MSG_BAD_EMOJI)
            elif words[1].endswith(">"):
                await self._custom_emoji(ctx, progress, words)
            else:
                await self._unicode_emoji(ctx, progress, words)

    async def _custom_emoji(self, ctx, progress: Progress, words: list[str]) -> None:
        match = CUSTOM_EMOJI_ID.search(words[1])
        if match is None:
            await ctx.send(MSG_BAD_EMOJI)
            return
        animated = words[1].startswith("<a:")
        ext, max_scale = ("gif", 10) if animated else ("png", 12)
        try:
            data = await net.get_bytes(CUSTOM_EMOJI_URL.format(id=match.group(1), ext=ext))
        except net.FetchError:
            await ctx.send(MSG_BAD_EMOJI)
            return
        if len(words) > 2:
            await progress.update(STEPS[1])
            try:
                scale = _parse_finite_float(words[2])
            except ValueError:
                await ctx.send("Invalid scale!")
            else:
                if scale > max_scale:
                    scale = max_scale
                    await ctx.send(f"That scale's too large! resizing to {max_scale}")
                if scale > 0:
                    resize = imaging.scale_animation if animated else imaging.scale_image
                    try:
                        data = await run_image_job(resize, data, scale)
                    except (OSError, ValueError):
                        await ctx.send(MSG_BAD_EMOJI)
                        return
        await ctx.send(file=bytes_to_file(data, "emoji." + ext))

    async def _unicode_emoji(self, ctx, progress: Progress, words: list[str]) -> None:
        url = TWEMOJI_URL.format(code=imaging.twemoji_code(words[1]))
        default_scale = 20
        try:
            scale = _parse_finite_float(words[2]) if len(words) > 2 else default_scale
        except ValueError:
            scale = default_scale
        if scale <= 0:
            scale = default_scale
        try:
            svg = await net.get_bytes(url)
        except net.FetchError:
            await ctx.send(MSG_BAD_EMOJI)
            return
        await progress.update(STEPS[1])
        too_big_notice = None
        if scale * imaging.TWEMOJI_SVG_SIZE > imaging.MAX_EMOJI_RENDER_PX:
            too_big_notice = await ctx.send("That scale's too big! Resizing to 20...")
            scale = default_scale
        try:
            png = await run_image_job(imaging.render_svg, svg, scale)
        except MemoryError:
            too_big_notice = too_big_notice or await ctx.send("That scale's too big! Resizing to 20...")
            png = await run_image_job(imaging.render_svg, svg, default_scale)
        except Exception:
            log.exception("Failed to render twemoji %s", url)
            await ctx.send(MSG_BAD_EMOJI)
            return
        if too_big_notice is not None:
            await too_big_notice.delete()
        await progress.update(STEPS[2])
        await ctx.send(file=bytes_to_file(png, "emoji.png"))
