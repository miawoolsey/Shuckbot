from tinydb import TinyDB, Query
import discord
import random

tagsDB = TinyDB('tags.json')
disableDB = TinyDB('tags_disabled.json')
alldisableDB = TinyDB('tags_servers_disabled.json')


async def syntax_error(message):
    await message.channel.send("Syntax error\n```fix\ntag <tag>\ntag add <tag> <content>"
                               "\ntag edit <tag> <content>\ntag remove <tag>\ntag owner <tag>```")


async def add(message):
    print(message.clean_content)
    args = message.clean_content.split(' ', 3)
    if len(args) < 4:
        await message.channel.send("Syntax error\n`;tag add <tag> <content>`")
    else:
        result = tagsDB.search(Query().tag == args[2].lower())
        if not result:
            tagsDB.insert(
                {'tag': args[2].lower(), 'content': args[3], 'owner': message.author.id})  # inserts as lower case
            await message.channel.send("Added tag **" + args[2] + "**!")
        else:
            await message.channel.send("Tag **" + args[2] + "** already exists!")


async def remove(message, owner_id):
    args = message.clean_content.split(' ', 3)
    if len(args) < 3:
        await message.channel.send("Syntax error\n`;tag remove <tag> (<content>)`")
    else:
        result = tagsDB.search(Query().tag == args[2].lower())
        if not result:  # if result is not found
            await message.channel.send("Tag **" + args[2] + "** not found!")
        else:
            if result[0]['owner'] == message.author.id or message.author.id == int(owner_id):  # the owner can delete tags
                tagsDB.remove(Query().tag == args[2].lower())
                await message.channel.send("Removed tag **" + args[2] + "**!")
            else:
                await message.channel.send("You are not the author of tag **" + args[2] + "**!")


async def edit(message, owner_id):
    args = message.clean_content.split(' ', 3)
    if len(args) < 3:
        await message.channel.send("Syntax error\n`;tag edit <tag> (<content>)`")
    else:
        result = tagsDB.search(Query().tag == args[2].lower())
        if not result:  # if result is not found
            await message.channel.send("Tag **" + args[2] + "** not found!")
        else:
            if result[0]['owner'] == message.author.id or message.author.id == int(owner_id):
                if len(message.clean_content.split(' ')) < 4:
                    await message.channel.send("Syntax error\n`;tag edit <tag> <content>`")
                else:
                    tagsDB.update({'content': args[3]}, Query().tag == args[2].lower())
                    await message.channel.send("Edited tag **" + args[2] + "**!")
            else:
                await message.channel.send("You are not the author of tag **" + args[2] + "**!")


# returns integer owner id, 0 if not found
def owner(message):
    args = message.clean_content.split(' ', 3)
    result = tagsDB.search(Query().tag == args[2].lower())
    if not result:
        return 0
    else:
        return result[0]['owner']


async def owned(message):
    results = None
    if not message.mentions:
        results = tagsDB.search(Query().owner == message.author.id)
    else:
        results = tagsDB.search(Query().owner == message.mentions[0].id)
    if not results and not message.mentions:
        await message.channel.send("You don't own any tags!")
    elif not results:
        await message.channel.send(message.mentions[0].display_name + " doesn't own any tags!")
    else:
        embed = discord.Embed()
        embed.title = "Tag list"
        embed.type = "rich"
        embed.colour = discord.Color.gold()
        to_send = ""
        for i in range(len(results)):
            to_send += str(i + 1) + ". " + results[i]['tag'][:1024] + "\n"
        embed.add_field(name="Tags", value=to_send, inline=False)
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        await message.channel.send(embed=embed)


async def get(message):
    args = message.clean_content.split(' ', 3)
    result = tagsDB.search(Query().tag == args[1].lower())
    if not result:
        await message.channel.send(f"Tag **{args[1]}** not found!")
    else:
        server_number = message.guild.id
        result_d = disableDB.search((Query().tag_name == args[1].lower()) & (Query().server_number == server_number))
        if len(result_d) > 0:
            await message.channel.send(f"Tag **{args[1]}** has been disabled in this server!")
            return
        result_a = alldisableDB.search(Query().server_number == server_number)
        if len(result_a) > 0:
            await message.channel.send(f"Tags have been disabled in this server! An admin can re-enable them with"
                                       f" the command `;t enable all`")
            return
        await message.channel.send(result[0]['content'])


async def get_random(message):
    if not message.channel.is_nsfw():
        await message.channel.send("Sorry, you can only use this command in nsfw channels!")
        return
    server_number = message.guild.id
    result_d = disableDB.search((Query().tag_name == 'random') & (Query().server_number == server_number))
    if len(result_d) > 0:
        await message.channel.send(f"The random tag has been disabled in this server! An admin can re enable this "
                                   f"feature with `;t enable random`")
        return
    result_a = alldisableDB.search(Query().server_number == server_number)
    if len(result_a) > 0:
        await message.channel.send(f"Tags have been disabled in this server! An admin can re-enable them with"
                                   f" the command `;t enable all`")
        return
    result = tagsDB.all()
    length = len(result)
    rand = random.randint(0, length - 1)
    await message.channel.send(result[rand]['content'])


async def disable(message):
    author = message.author
    args = message.clean_content.split(' ', 3)
    if len(args) < 3:
        await message.channel.send("You need to add a tag to disable! If you wish to disable all tags, please write"
                                   " `;t disable all`")
        return
    if author.guild_permissions.administrator or author.guild_permissions.manage_messages:
        result = tagsDB.search(Query().tag == args[2].lower())
        if not result:
            await message.channel.send(f"Tag **{args[2]}** not found!")
        else:  # do the disabling
            tag_name = args[2].lower()
            server_number = message.guild.id

            if tag_name == 'all':  # disabled ALL tags in the server
                res = alldisableDB.search(Query().server_number == server_number)
                if len(res) > 0:
                    await message.channel.send(f'Tags are already disabled, you can reenable tags with the command '
                                               f'`;t enable all`!')
                    return
                alldisableDB.insert({'server_number': server_number})
                await message.channel.send(f'Tags have been disabled serverwide, you can reenable tags with the '
                                           f'command `;t enable all`!')
                return

            res = disableDB.search((Query().tag_name == args[2].lower()) & (Query().server_number == server_number))
            if len(res) > 0:
                await message.channel.send(f'Tag **{tag_name}** is already disabled!')
                return
            disableDB.insert({'tag_name': tag_name, 'server_number': server_number, 'disabled_by': author.id})
            await message.channel.send(f'Tag **{tag_name}** has been disabled in the server!')
    else:
        await message.channel.send("Sorry bud, you don't have the manage message permission! "
                                   "You can't disable tags in the server")


async def enable(message):
    author = message.author
    args = message.clean_content.split(' ', 3)
    if len(args) < 3:
        await message.channel.send("You need to add a tag to enable! If you wish to re-enable tags server-wide use "
                                   "the `;t enable all` command!")
        return
    if author.guild_permissions.administrator or author.guild_permissions.manage_messages:
        result = tagsDB.search(Query().tag == args[2].lower())
        if not result:
            await message.channel.send(f"Tag **{args[2]}** not found!")
        else:  # do the disabling
            tag_name = args[2]
            server_number = message.guild.id

            if tag_name == 'all':  # enable ALL tags in the server
                res = alldisableDB.search(Query().server_number == server_number)
                if len(res) > 0:
                    alldisableDB.remove(Query().server_number == server_number)
                    await message.channel.send(f'Tags have been re-enabled!')
                    return

                await message.channel.send(f'Tags are already enabled!')
                return

            res = disableDB.search((Query().tag_name == args[2].lower()) & (Query().server_number == server_number))
            if len(res) > 0:  # has been disabled here, re enable
                await message.channel.send(f'Tag **{tag_name}** has been enabled!')
                disableDB.remove((Query().tag_name == args[2].lower()) & (Query().server_number == server_number))
                return
            # disableDB.insert({'tag_name': tag_name, 'server_number': server_number, 'disabled_by': author.id})
            await message.channel.send(f'Tag **{tag_name}** is already enabled!')
    else:
        await message.channel.send("Sorry bud, you don't have the manage message permission! "
                                   "You can't enable tags in the server")
