"""Aviation weather (METAR / TAF) from avwx.rest."""
from __future__ import annotations

import asyncio
from urllib.parse import quote

from discord.ext import commands

from modules import net

AVWX_URL = "https://avwx.rest/api/{report}/{station}"
FLIGHT_RULE_EMOJI = {
    "VFR": ":green_circle:",
    "MVFR": ":blue_circle:",
    "IFR": ":red_circle:",
    "LIFR": "<:pink_circle:702657173980708974>",
}


def _format_line(report: dict) -> str:
    return FLIGHT_RULE_EMOJI.get(report.get("flight_rules"), "") + " `" + report["sanitized"] + "`"


class Aviation(commands.Cog):
    def __init__(self, bot: commands.Bot, token: str | None) -> None:
        self.bot = bot
        self.token = token or ""

    async def _fetch(self, report: str, station: str) -> dict | None:
        """Parsed JSON response, or None if avwx didn't return JSON (unknown station / no report)."""
        url = AVWX_URL.format(report=report, station=quote(station, safe=""))
        try:
            _, data = await net.get_json(url, params={"token": self.token})
        except net.FetchError:
            return None
        return data if isinstance(data, dict) else None

    @commands.command()
    async def metar(self, ctx: commands.Context) -> None:
        args = ctx.message.clean_content.split(" ")
        if len(args) < 2:
            await ctx.send("Syntax error\n```fix\nmetar <station>```")
            return
        result = await self._fetch("metar", args[1])
        if result is None:
            await ctx.send("**Error**: " + args[1].upper() + " is not a valid ICAO station ident.")
        elif "error" in result:
            await ctx.send("**Error**: " + result["error"] + ".")
        else:
            await ctx.send(_format_line(result))

    @commands.command()
    async def taf(self, ctx: commands.Context) -> None:
        args = ctx.message.clean_content.split(" ")
        if len(args) < 2:
            await ctx.send("Syntax error\n```fix\ntaf <station>```")
            return
        metar_result, taf_result = await asyncio.gather(self._fetch("metar", args[1]), self._fetch("taf", args[1]))
        if metar_result is not None and "error" in metar_result:
            await ctx.send("**Error**: " + metar_result["error"] + ".")
        elif metar_result is None or taf_result is None or "forecast" not in taf_result:
            await ctx.send("**Error**: " + args[1].upper() + " does not issue a TAF.")
        else:
            lines = [_format_line(metar_result)] + [_format_line(item) for item in taf_result["forecast"]]
            await ctx.send("\n" + "\n".join(lines))
