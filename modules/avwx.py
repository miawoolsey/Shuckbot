import requests
from simplejson.scanner import JSONDecodeError
from urllib.parse import quote


async def metar(message, token):
    args = message.clean_content.split(' ')
    if len(args) < 2:
        await message.channel.send("Syntax error\n```fix\nmetar <station>```")
    else:
        resp = requests.get("https://avwx.rest/api/metar/" + quote(args[1]) + "?token=" + token, timeout=10)
        try:
            result = resp.json()
            if "error" in result.keys():
                await message.channel.send("**Error**: " + result['error'] + ".")
            else:
                emoji = ""
                if result['flight_rules'] == "VFR":
                    emoji += ":green_circle:"
                elif result['flight_rules'] == "MVFR":
                    emoji += ":blue_circle:"
                elif result['flight_rules'] == "IFR":
                    emoji += ":red_circle:"
                elif result['flight_rules'] == "LIFR":
                    emoji += "<:pink_circle:702657173980708974>"
                await message.channel.send(emoji + " `" + result['sanitized'] + "`")
        except JSONDecodeError:
            await message.channel.send("**Error**: " + args[1].upper() + " is not a valid ICAO station ident.")


async def taf(message, token):
    args = message.clean_content.split(' ')
    if len(args) < 2:
        await message.channel.send("Syntax error\n```fix\ntaf <station>```")
    else:
        metar_resp = requests.get("https://avwx.rest/api/metar/" + quote(args[1]) + "?token=" + token, timeout=10)
        taf_resp = requests.get("https://avwx.rest/api/taf/" + quote(args[1]) + "?token=" + token, timeout=10)
        try:
            metar_result = metar_resp.json()
            taf_result = taf_resp.json()
            if "error" in metar_result.keys():
                await message.channel.send("**Error**: " + metar_result['error'] + ".")

            else:
                emoji = ""
                to_send = ""
                if metar_result['flight_rules'] == "VFR":
                    emoji += ":green_circle:"
                elif metar_result['flight_rules'] == "MVFR":
                    emoji += ":blue_circle:"
                elif metar_result['flight_rules'] == "IFR":
                    emoji += ":red_circle:"
                elif metar_result['flight_rules'] == "LIFR":
                    emoji += "<:pink_circle:702657173980708974>"
                to_send += "\n" + emoji + " `" + metar_result['sanitized'] + "`"
                for item in taf_result['forecast']:
                    if item['flight_rules'] == "VFR":
                        emoji = ":green_circle:"
                    elif item['flight_rules'] == "MVFR":
                        emoji = ":blue_circle:"
                    elif item['flight_rules'] == "IFR":
                        emoji = ":red_circle:"
                    elif item['flight_rules'] == "LIFR":
                        emoji = "<:pink_circle:702657173980708974>"
                    to_send += "\n" + emoji + " `" + item['sanitized'] + "`"
                await message.channel.send(to_send)
        except JSONDecodeError:
            await message.channel.send("**Error**: " + args[1].upper() + " does not issue a TAF.")
