import re

import requests

from modules import imagesearch
from tinydb import TinyDB, Query

saved = TinyDB("picturebook.json")


def is_valid_filetype(str):
    return re.search(r".*(\.png|\.jpg|\.gif|\.jpeg|\.webp|\.PNG|\.JPG|\.GIF|\.JPEG|\.WEBP).*", str)


async def read_image(message):
    args = message.clean_content.split(' ')

    async def search_previous():
        m = [msg async for msg in message.channel.history(limit=20)]
        for i in range(20):
            if m[i].attachments:
                if is_valid_filetype(m[i].attachments[0].url):
                    return m[i].attachments[0].url
            if m[i].embeds:
                if m[i].embeds[0].image:
                    if is_valid_filetype(m[i].embeds[0].image.url):
                        return m[i].embeds[0].image.url
            words = m[i].clean_content.split(' ')
            for word in words:
                if is_valid_filetype(word) and word[0:4] == "http":
                    return word
        return None

    if len(args) >= 2:
        if args[1][0:4] == "http" and is_valid_filetype(args[1]):
            try:
                requests.get(args[1], timeout=10)
            except requests.exceptions.ConnectionError:
                await message.channel.send("Your image is invalid!")
                return
            else:
                return args[1]
        else:
            if message.mentions:
                return message.mentions[0].avatar.url
            else:
                temp = await search_previous()
                if temp is None:
                    await message.channel.send("Your URL is not properly formatted! Currently I can only process URL's "
                                               "that end in .png, .jpg, .gif, or .webp")
                    return
                return temp
    else:
        if message.attachments:
            if is_valid_filetype(message.attachments[0].url):
                return message.attachments[0].url
            else:
                await message.channel.send("Your attached image is not a valid file type! (png, jpg, gif)")
                return
        else:
            temp = await search_previous()
            if temp is None:
                await message.channel.send("Your URL is not properly formatted! Currently I can only process URL's "
                                           "that end in .png, .jpg, .gif, or .webp")
                return
            return temp


async def save(message):
    image = await read_image(message)
    if image is None:
        return
    result = saved.table(str(message.guild.id)).search(Query().image == image)
    if len(result):
        await message.channel.send("That image is already in the picturebook!")
        return
    saved.table(str(message.guild.id)).insert({'server': message.guild.id, 'image': str(image),
                                               'owner': message.author.id})
    await message.channel.send("Image saved!")


async def get_saved(message):
    all_saved = saved.table(str(message.guild.id)).all()
    if(len(all_saved)) == 0:
        await message.channel.send("There are no saved images in this server! Use `;save` to save one.")
        return
    images = []
    authors = []
    for item in all_saved:
        images.insert(0, item["image"])
        authors.insert(0, item["owner"])
    await imagesearch.create_viewer(message, images, len(images), "Picturebook", authors=authors)


async def remove(message, owner_id):
    current = imagesearch.get_current_image(message)
    if current is None:
        await message.channel.send("You don't have an image selected in the picturebook!")
        return
    result = saved.table(str(message.guild.id)).search(Query().image == current['images'][current['pg'] - 1])
    if not result:  # if result is not found
        await message.channel.send("Something has gone terribly wrong! Sorry!")
    else:
        if result[0]['owner'] == message.author.id or message.author.id == owner_id:
            saved.table(str(message.guild.id)).remove(Query().image == current['images'][current['pg'] - 1])
            await message.channel.send("Removed the current image!")
        else:
            await message.channel.send("You are not the creator of the current image!")
