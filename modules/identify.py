import re
import requests
from google.cloud import vision
from google.oauth2 import service_account
from modules import parameters
from PIL import Image, ImageDraw
from io import BytesIO
import discord


def is_valid_filetype(str):
    return re.search(r".*(\.png|\.jpg|\.jpeg|\.webp|\.PNG|\.JPG|\.JPEG|\.WEBP).*", str)


async def read_image(message):
    args = message.clean_content.split(' ')

    async def search_previous():
        m = [msg async for msg in message.channel.history(limit=20)]
        for i in range(20):
            if m[i].embeds:
                if m[i].embeds[0].image:
                    if is_valid_filetype(m[i].embeds[0].image.url):
                        return m[i].embeds[0].image.url
                    else:
                        print("invalid embed i = " + str(i))
                        return None
            if m[i].attachments:
                if is_valid_filetype(m[i].attachments[0].url):
                    return m[i].attachments[0].url
                else:
                    print("invalid attachment i = " + str(i))
                    return None

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
            temp = await search_previous()
            if temp is None:
                await message.channel.send("Your URL is not properly formatted! Currently I can only process URL's "
                                           "that end in .png, .jpg, or .webp")
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
                                           "that end in .png, .jpg, or .webp")
                return
            return temp


def pil_image_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        image = Image.open(BytesIO(response.content))
        return image
    except OSError:
        return None


async def vision_init(message):
    image = await read_image(message)
    creds = service_account.Credentials.from_service_account_file(parameters.params["googleJson"])
    client = vision.ImageAnnotatorClient(credentials=creds)
    vision_image = vision.Image()
    vision_image.source.image_uri = image
    return client, vision_image, image


def generate_message(items):
    msg = "I can see "
    for i, label in enumerate(items):
        if i and i < len(items) - 1:
            msg += ", "
        if i == len(items) - 1:
            msg += ", and "
        msg += label.description.lower()
    msg += "."
    return msg


async def identify(message):
    try:
        sent = await message.channel.send("Processing...")
        client, vision_image, image = await vision_init(message)

        if image is None:
            await sent.delete()
            return
        response = client.label_detection(image=vision_image)
        items = response.label_annotations
        if response.error.message:
            await sent.edit(content="I don't like that image! Try another one 🙂")
            return
        else:
            msg = generate_message(items)
            await sent.edit(content=msg)
    except Exception as e:
        print(str(e))


async def landmark(message):
    try:
        sent = await message.channel.send("Processing...")
        client, vision_image, image = await vision_init(message)
        response = client.landmark_detection(image=vision_image)
        items = response.landmark_annotations
        pil_image = pil_image_from_url(image)
        if pil_image is not None:
            draw = ImageDraw.Draw(pil_image)
        if response.error.message:
            print(response.error.message)
            await sent.edit(content="I don't like that image! Try another one 🙂")
            return
        else:
            if len(items) > 0:
                item0 = items[0]
                if pil_image is not None:
                    for item in items:
                        vx = item.bounding_poly.vertices
                        draw.rectangle([vx[0].x, vx[0].y, vx[2].x, vx[3].y], outline="#00ff00", width=3)
                        draw.text([vx[0].x, vx[0].y - 10], item.description, fill="#00ff00", stroke_fill="black", stroke_width=3)
                    pil_image.save("landmark.png")
                    await sent.delete()
                    await message.channel.send(content="I think it's " + item0.description + ".", file=discord.File("landmark.png"))
                else:
                    await sent.edit(content="I think it's " + item0.description + ".")
            else:
                await sent.edit(content="I don't know this place!")
        if pil_image is not None:
            pil_image.close()
    except Exception as e:
        print(str(e))
