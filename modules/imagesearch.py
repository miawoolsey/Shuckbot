import random
import discord
import untangle
from asyncio import sleep
from googleapiclient.discovery import build
from googleapiclient import errors

searchService = None
searches = [{}]


def init(google_key):
    global searchService
    try:
        searchService = build('customsearch', 'v1', developerKey=google_key)
    except errors.HttpError:  # sometimes this happens for some reason
        print("Daily quota exceeded!")


async def google_search(message):
    try:
        query = message.clean_content.split(' ', 1)[1]  # splits the img and the rest of the command
        res = searchService.cse().list(q=query,
                                       cx="017178301722928584583:yi4kptiqtbq",
                                       searchType="image").execute()
        images = []
        length = len(res['items'])
        for item in res['items']:
            images.append(item['link'])
        await create_viewer(message, images, length, "Google search for " + query)
    except errors.HttpError:  # google returns a 403 when you're out of quota
        await message.channel.send("The daily quota for Google searches has been exceeded.")
    except NameError:  # sometimes build() fails when you're over quota instead of returning the 403 here
        await message.channel.send("The daily quota for Google searches has been exceeded.")
    except ConnectionResetError:
        print("Connection reset by google!")
        await message.channel.send("Connection error. Please try again.")
    except Exception as e:
        print("Error in google search: ", e)


async def r34_search(message):
    if not message.channel.is_nsfw():
        await message.channel.send("Hey! This isn't an nsfw channel! You can't use that here!")
        return
    tags = message.clean_content.split(' ', 1)[1]
    urltags = tags.replace(" ", "%20")
    print(tags, flush=True)
    resp = untangle.parse("https://rule34.xxx/index.php?page=dapi&s=post&q=index&limit=1000&tags=" + urltags)
    print("hello", flush=True)
    print(resp.posts.children, flush=True)
    length = len(resp.posts.children)
    print(length, flush=True)
    if length == 0:
        await message.channel.send("No results found!")
        return
    images = []
    for item in resp.posts.children:
        images.append(item['file_url'])
    random.shuffle(images)
    await create_viewer(message, images, length, "r34 search for " + tags)


async def create_viewer(message, images_array, length, title, **kwargs):
    authors = []
    if "authors" in kwargs.keys():
        for item in kwargs["authors"]:
            authors.append(item)
    embed = discord.Embed()
    embed.title = title
    embed.set_image(url=images_array[0]).set_footer(text="Page 1 of " + str(length)) \
        .set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
    if len(authors):
        embed.description = "By `" + str(message.guild.get_member(authors[0])) + "`"
    sent = await message.channel.send(embed=embed)  # save the message
    # store the message channel, the message to edit, the query results, the page we're on, and the author
    meta = {'chan': message.channel.id, 'msg': sent, 'images': images_array, 'pg': 1, 'length': length,
            'author': message.author.id, 'authors': authors}
    found = False  # is there a previous search in this channel
    if not searches[0]:
        searches[0] = meta  # if there are no previous searches anywhere, make this one the first one
        found = True
    else:
        for i in range(len(searches)):
            if searches[i]['chan'] == message.channel.id:
                searches[i] = meta  # replace this channel's previous search with the new one
                found = True
    if not found:
        searches.append(meta)  # if there isn't a search in this channel, append it to the list


async def stop(message):
    if not searches[0]:
        return
    for item in searches:
        if item['chan'] == message.channel.id and item['pg']:
            if item['author'] != message.author.id:
                break
            await item['msg'].delete()
            await message.delete()
            break


async def advance(message):
    if not searches[0]:
        return
    for item in searches:
        if item['chan'] == message.channel.id and item['pg']:
            if item['author'] != message.author.id:
                break
            embed = item['msg'].embeds[0]
            if message.clean_content.lower() == "b":  # reverse page unless it's page 10 in which case loop around
                if item['pg'] > 1:
                    item['pg'] -= 1
                else:
                    item['pg'] = item['length']
            else:  # same as b except go forwards
                if item['pg'] < item['length']:
                    item['pg'] += 1
                else:
                    item['pg'] = 1
            await edit_embed(item, embed, message)
            break


async def jump(message):
    if not searches[0]:
        return
    try:
        page = int(message.clean_content[1:])
    except ValueError:
        return
    for item in searches:
        if item['chan'] == message.channel.id and item['pg']:
            if item['author'] != message.author.id:
                break
            if 1 <= page <= item['length']:
                embed = item['msg'].embeds[0]
                item['pg'] = page
                await edit_embed(item, embed, message)
            break


def get_current_image(message):
    if not searches[0]:
        return
    for item in searches:
        if item['chan'] == message.channel.id:
            return item


async def edit_embed(results, embed, message):
    embed.set_image(url=results['images'][results['pg'] - 1]) \
        .set_footer(text="Page " + str(results['pg']) + " of " + str(results['length']))
    if len(results['authors']):
        embed.description = "By `" + str(message.guild.get_member(results['authors'][results['pg'] - 1])) + "`"
    await results['msg'].edit(embed=embed)
    await message.delete()
