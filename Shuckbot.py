import logging
from datetime import datetime
from tinydb import TinyDB, Query

import discord
from discord.ext import commands

from modules import tags, imagesearch, imagefun, help, picturebook, \
    games, parameters, avwx, identify

params = parameters.params

imagesearch.init(params["googleKey"])
logging.basicConfig(level=logging.INFO)

defaultPrefix = ';'

prefixDB = TinyDB('prefixes.json')


def process_prefix(p_bot, message):
    if message.guild is None:
        return ';'
    result = prefixDB.search(Query().id == message.guild.id)
    if not result:
        prefixDB.insert({'id': message.guild.id, 'prefix': ';'})
        return ';'
    else:
        return result[0]['prefix']


bot = commands.Bot(command_prefix=process_prefix, intents=discord.Intents.all())
bot.remove_command("help")  # discord.py ships with a default help command: must remove it


@bot.command(aliases=["shuckbotprefix", "shuckprefix"])
async def prefix(ctx, *args):
    if not (ctx.message.author.guild_permissions.manage_guild or ctx.message.author.guild_permissions.administrator):
        await ctx.channel.send("You need the **Manage Server** permission to do that.")
    elif len(args) > 1 or len(args) == 0 or len(args[0]) > 1:
        await ctx.channel.send("**Format**: ;prefix <single character>")
    elif not args[0].isascii():
        await ctx.channel.send("You must choose an ASCII character!")
    else:
        prefixDB.update({'prefix': args[0]}, Query().id == ctx.message.guild.id)
        await ctx.channel.send("Set server prefix to \"" + args[0] + "\".")


@bot.command()
async def ping(ctx):
    now = datetime.now()
    sent = await ctx.channel.send("Measuring ping...")
    diff = sent.created_at - now
    await sent.edit(content="Pong! Shuckbot's ping is **" + str(int(diff.total_seconds() * 1000)) + "**ms.")


@bot.command(aliases=["help"])
async def page(ctx):
    await help.show_help(ctx.message)


@bot.command(aliases=["i", "im", "image"])
async def img(ctx):
    await imagesearch.google_search(ctx.message)


@bot.command()
async def r34(ctx):
    await imagesearch.r34_search(ctx.message)


@bot.command()
async def invite(ctx):
    await ctx.channel.send(
        params["url"])


@bot.command(aliases=["picturebook", "photobook"])
async def pb(ctx, *args):
    if ' ' not in ctx.message.clean_content:
        await picturebook.get_saved(ctx.message)

    else:
        _arg = args[0]  # the first argument

        if _arg == 'add' or _arg == 'save':
            await picturebook.save(ctx.message)

        elif _arg == 'remove' or _arg == "delete" or _arg == "rm":
            await picturebook.remove(ctx.message, params["ownerID"])


@bot.command(aliases=["t"])
async def tag(ctx):
    args = ctx.message.clean_content.split(' ', 3)
    if len(args) < 2:
        await tags.syntax_error(ctx.message)
    else:
        if args[1] == 'add':
            await tags.add(ctx.message)

        elif args[1] == 'remove' or args[1] == "delete":
            await tags.remove(ctx.message, params["ownerID"])

        elif args[1] == 'edit':
            await tags.edit(ctx.message, params["ownerID"])

        elif args[1] == 'owner':
            if len(args) < 3:
                await tags.syntax_error(ctx.message)
            else:
                owner_id = tags.owner(ctx.message)
                if owner_id == 0:
                    await ctx.channel.send("Tag **" + args[2] + "** does not exist")
                else:
                    tag_owner = await bot.fetch_user(owner_id)
                    await ctx.channel.send("Tag **" + args[2] + "** is owned by `" + str(tag_owner) + "`")

        elif args[1] == 'list':
            await tags.owned(ctx.message)

        elif args[1] == 'random':
            await tags.get_random(ctx.message)

        elif args[1] == 'disable':
            await tags.disable(ctx.message)

        elif args[1] == 'enable':
            await tags.enable(ctx.message)

        else:
            await tags.get(ctx.message)


@bot.command()
async def metar(ctx):
    await avwx.metar(ctx.message, params["avwxKey"])


@bot.command()
async def taf(ctx):
    await avwx.taf(ctx.message, params["avwxKey"])


@bot.command(aliases=["hold"])
async def holding(ctx):
    await imagefun.holding_imagemaker(ctx.message)


@bot.command(aliases=["exmilitary"])
async def exm(ctx):
    await imagefun.exmilitary_imagemaker(ctx.message)


@bot.command(aliases=["fan", "review", "tnd"])
async def fantano(ctx):
    await imagefun.fantano_imagemaker(ctx.message)


@bot.command(aliases=["1bit", "1"])
async def one(ctx):
    await imagefun.one_imagemaker(ctx.message)


@bot.command()
async def kim(ctx):
    await imagefun.kim_imagemaker(ctx.message)


@bot.command(aliases=["e"])
async def emote(ctx):
    await imagefun.get_emoji(ctx.message, bot)


@bot.command(aliases=["pixelsort", "sortpixels"])
async def sort(ctx):
    await imagefun.sort_pixels(ctx.message)


@bot.command(aliases=["pixelshuffle"])
async def shuffle(ctx):
    await imagefun.pixel_shuffle(ctx.message)


@bot.command(aliases=["scale"])
async def resize(ctx):
    await imagefun.resize_img(ctx.message)


@bot.command()
async def size(ctx):
    await imagefun.get_size(ctx.message)


@bot.command(aliases=["mina"])
async def twice(ctx):
    await imagefun.twice_imagemaker(ctx.message)


@bot.command(aliases=["drawing"])
async def draw(ctx):
    await imagefun.drawing_imagemaker(ctx.message)


@bot.command()
async def undo(ctx):
    await imagefun.undo_img(ctx.message)


@bot.command(aliases=["loona"])
async def heejin(ctx):
    await imagefun.heejin_imagemaker(ctx.message)


@bot.command()
async def school(ctx):
    await imagefun.school_imagemaker(ctx.message)


@bot.command(aliases=["lect"])
async def lecture(ctx):
    await imagefun.lecture_imagemaker(ctx.message)


@bot.command()
async def tesla(ctx):
    await imagefun.tesla_imagemaker(ctx.message)


@bot.command()
async def osu(ctx):
    await imagefun.osu_imagemaker(ctx.message)


@bot.command(aliases=["colour", "c"])
async def color(ctx):
    await imagefun.get_colour_from_hex(ctx.message)


@bot.command(aliases=["noisy"])
async def mix(ctx):
    await imagefun.mixer(ctx.message)


@bot.command()
async def noise(ctx):
    await imagefun.noise_imagemaker(ctx.message)


@bot.command(aliases=["gf"])
async def mokou(ctx):
    await imagefun.mokou_imagemaker(ctx.message)


@bot.command()
async def shift(ctx):
    await imagefun.image_shift(ctx.message)


@bot.command(aliases=["megu"])
async def megumin(ctx):
    await imagefun.megumin_imagemaker(ctx.message)


@bot.command()
async def weezer(ctx):
    await imagefun.weezer_imagemaker(ctx.message)


@bot.command(aliases=["g"])
@commands.cooldown(1, 5, commands.BucketType.guild)
async def game(ctx):
    await games.game(ctx.message, bot, params["mapquest"])


@bot.command(aliases=["torgb", "2rgb"])
async def rgb(ctx):
    await imagefun.to_rgb(ctx.message)


@bot.command(aliases=["a"])
async def avatar(ctx):
    await imagefun.get_avatar(ctx.message)


@bot.command()
async def purple(ctx):
    await imagefun.purple(ctx.message)


@bot.command()
async def whatifitwaspurple(ctx):
    await imagefun.whatifitwaspurple(ctx.message)


@bot.command(aliases=["tom"])
async def tomscott(ctx):
    await imagefun.tom_imagemaker(ctx.message)


@bot.command()
async def sickos(ctx):
    await imagefun.sickos_imagemaker(ctx.message)



# Store active readycheck messages
readycheck_messages = {}


class ReadyCheckView(discord.ui.View):
    def __init__(self, message_id):
        super().__init__(timeout=None)
        self.message_id = message_id
    
    @discord.ui.button(label="Ready", style=discord.ButtonStyle.green, custom_id="ready_button")
    async def ready_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_button_click(interaction, "ready")
    
    @discord.ui.button(label="Not Ready", style=discord.ButtonStyle.red, custom_id="not_ready_button")
    async def not_ready_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_button_click(interaction, "not_ready")
    
    async def handle_button_click(self, interaction: discord.Interaction, button_type: str):
        if self.message_id not in readycheck_messages:
            await interaction.response.defer()
            return
        
        data = readycheck_messages[self.message_id]
        username = interaction.user.display_name
        
        if button_type == "ready":
            if username in data['ready']:
                # User clicked ready again, remove them
                data['ready'].discard(username)
            else:
                # Add to ready, remove from not ready
                data['ready'].add(username)
                data['not_ready'].discard(username)
        else:  # not_ready
            if username in data['not_ready']:
                # User clicked not ready again, remove them
                data['not_ready'].discard(username)
            else:
                # Add to not ready, remove from ready
                data['not_ready'].add(username)
                data['ready'].discard(username)
        
        await update_readycheck_message(self.message_id)
        await interaction.response.defer()


@bot.command()
async def readycheck(ctx):
    """Create a ready check poll for Dota 2 Gamers"""
    # Only allow in specific server
    if ctx.guild is None or ctx.guild.id != 149264038017105920:
        return
    
    # Get the Dota 2 Gamers role by ID
    dota_role = ctx.guild.get_role(1240097702864490507)
    
    if dota_role is None:
        await ctx.send("Could not find the @Dota 2 Gamers role!")
        return
    
    # Send initial message with role ping and buttons
    view = ReadyCheckView(None)
    message = await ctx.send(f"READY CHECK {dota_role.mention}\nREADY (0): \nNOT READY (0): ", view=view)
    
    # Update view with message ID and store message info
    view.message_id = message.id
    readycheck_messages[message.id] = {
        'channel_id': message.channel.id,
        'ready': set(),
        'not_ready': set()
    }


async def update_readycheck_message(message_id):
    """Update the readycheck message with current button status"""
    if message_id not in readycheck_messages:
        return
    
    data = readycheck_messages[message_id]
    channel = bot.get_channel(data['channel_id'])
    
    try:
        message = await channel.fetch_message(message_id)
    except Exception:
        # Message was deleted
        del readycheck_messages[message_id]
        return
    
    # Get the Dota 2 Gamers role by ID
    dota_role = message.guild.get_role(1240097702864490507)
    role_mention = dota_role.mention if dota_role else "@Dota 2 Gamers"
    
    # Build the message content
    ready_list = sorted(data['ready'])
    not_ready_list = sorted(data['not_ready'])
    
    content = f"READY CHECK {role_mention}\n"
    
    if ready_list:
        content += f"READY ({len(ready_list)}): {', '.join(ready_list)}\n"
    else:
        content += f"READY (0): \n"
    
    if not_ready_list:
        content += f"NOT READY ({len(not_ready_list)}): {', '.join(not_ready_list)}"
    else:
        content += f"NOT READY (0): "
    
    await message.edit(content=content)


@bot.command(aliases=["identify"])
async def id(ctx):
    await identify.identify(ctx.message)


@bot.command(aliases=["landmarks"])
async def landmark(ctx):
    await identify.landmark(ctx.message)


@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if message.clean_content.lower() == "b" or message.clean_content.lower() == "n":
        await imagesearch.advance(message)

    elif message.clean_content.lower().startswith("p"):
        await imagesearch.jump(message)

    elif message.clean_content.lower() == "s":
        await imagesearch.stop(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send('Sorry, this command is on cooldown! Try again in {:.2f} seconds'.format(error.retry_after))
    elif not isinstance(error, commands.CommandNotFound):
        print(error)

bot.run(params["token"])
