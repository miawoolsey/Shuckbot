import discord
from PIL import Image, ImageChops, ImageColor
import requests
from io import BytesIO
import re
import numpy as np
from numpy import linalg
import cairosvg
import random


def is_valid_filetype(str):
    return re.search(r".*(\.png|\.jpg|\.gif|\.jpeg|\.webp|\.PNG|\.JPG|\.GIF|\.JPEG|\.WEBP).*", str)


# or re.search(r".*https://tenor.com/view/.*", str) ?


# reads an image in from the sent message
# can be from one of the following:
# 	an image URL located next to the command
# 	an attached image
# 	the profile picture of a mentioned user
# 	any image posted in the last 20 messages (attached, embedded, or a URL in text)
async def read_image(message):
    args = message.clean_content.split(' ')

    async def search_previous():
        async for m in message.channel.history(limit=20):
            if m.attachments and is_valid_filetype(m.attachments[0].url):
                readURL = m.attachments[0].url
                response = requests.get(readURL, timeout=10)
                image = Image.open(BytesIO(response.content))
                return image
            if m.embeds and m.embeds[0].image and is_valid_filetype(m.embeds[0].image.url):
                readURL = m.embeds[0].image.url
                response = requests.get(readURL, timeout=10)
                image = Image.open(BytesIO(response.content))
                return image
            words = m.clean_content.split(' ')
            for word in words:
                if is_valid_filetype(word) and word[0:4] == "http":
                    try:
                        response = requests.get(word, timeout=10)
                        image = Image.open(BytesIO(response.content))
                        return image
                    except OSError:
                        continue
        return None

    if len(args) >= 2:
        if args[1][0:4] == "http" and is_valid_filetype(args[1]):
            try:
                response = requests.get(args[1], timeout=10)
            except requests.exceptions.ConnectionError:
                await message.channel.send("Your image is invalid!")
                return
            else:
                image = Image.open(BytesIO(response.content))
                return image
        else:
            if message.mentions:
                readURL = message.mentions[0].display_avatar.url
                response = requests.get(readURL, timeout=10)
                image = Image.open(BytesIO(response.content))
                return image
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
                readURL = message.attachments[0].url
                response = requests.get(readURL, timeout=10)
                image = Image.open(BytesIO(response.content))
                return image
            else:
                await message.channel.send("Your attached image is not a valid file type! (png, jpg, gif)")
                return
        else:
            temp = await search_previous()
            if temp is None:
                await message.channel.send("Your URL is not properly formatted or I couldn't find an image!")
                return
            return temp


# taken from https://hhsprings.bitbucket.io/docs/programming/examples/python/PIL/Image__class_Image.html
# used for perspective transform
def _create_coeff(
        xyA1, xyA2, xyA3, xyA4,
        xyB1, xyB2, xyB3, xyB4):
    A = np.array([
        [xyA1[0], xyA1[1], 1, 0, 0, 0, -xyB1[0] * xyA1[0], -xyB1[0] * xyA1[1]],
        [0, 0, 0, xyA1[0], xyA1[1], 1, -xyB1[1] * xyA1[0], -xyB1[1] * xyA1[1]],
        [xyA2[0], xyA2[1], 1, 0, 0, 0, -xyB2[0] * xyA2[0], -xyB2[0] * xyA2[1]],
        [0, 0, 0, xyA2[0], xyA2[1], 1, -xyB2[1] * xyA2[0], -xyB2[1] * xyA2[1]],
        [xyA3[0], xyA3[1], 1, 0, 0, 0, -xyB3[0] * xyA3[0], -xyB3[0] * xyA3[1]],
        [0, 0, 0, xyA3[0], xyA3[1], 1, -xyB3[1] * xyA3[0], -xyB3[1] * xyA3[1]],
        [xyA4[0], xyA4[1], 1, 0, 0, 0, -xyB4[0] * xyA4[0], -xyB4[0] * xyA4[1]],
        [0, 0, 0, xyA4[0], xyA4[1], 1, -xyB4[1] * xyA4[0], -xyB4[1] * xyA4[1]],
    ], dtype=np.float32)
    B = np.array([
        xyB1[0],
        xyB1[1],
        xyB2[0],
        xyB2[1],
        xyB3[0],
        xyB3[1],
        xyB4[0],
        xyB4[1],
    ], dtype=np.float32)
    return linalg.solve(A, B)


# crops the image to be a square of size size
def square_image_crop(img, size):
    if img.size[0] == img.size[1]:
        img = img.resize((size, size), resample=Image.BICUBIC)
    elif img.size[0] > img.size[1]:
        img = img.resize((int(size * img.size[0] / img.size[1]), size), resample=Image.BICUBIC)
        img = img.crop((((img.size[0] - size) / 2) // 1,
                        0,
                        ((img.size[0] + size) / 2) // 1,
                        img.size[1]))
    else:
        img = img.resize((size, int(size * img.size[1] / img.size[0])), resample=Image.BICUBIC)
        img = img.crop((0,
                        ((img.size[1] - size) / 2) // 1,
                        img.size[0],
                        ((img.size[1] + size) / 2) // 1))
    return img


def rectangle_image_crop(input_img, size):
    if input_img.width * size[1] > input_img.height * size[0]:
        input_img = input_img.resize((int(size[1] * input_img.width / input_img.height), size[1]), Image.BILINEAR)
        input_img = input_img.crop((int((input_img.width - (input_img.height * size[0] / size[1])) / 2),
                                    0,
                                    int(input_img.width - (
                                            (input_img.width - (input_img.height * size[0] / size[1])) / 2)),
                                    input_img.height))
    # elif input_img.width * size[1] <= input_img.height * size[0]:
    else:
        input_img = input_img.resize((size[0], int(size[0] * input_img.height / input_img.width)), Image.BILINEAR)
        input_img = input_img.crop((0,
                                    int((input_img.height - (input_img.width * size[1] / size[0])) / 2),
                                    input_img.width,
                                    int(input_img.height - (
                                            (input_img.height - (input_img.width * size[1] / size[0])) / 2))))
    return input_img


async def holding_imagemaker(message):
    sent = await message.channel.send("Processing .")
    # holding_input_image = "https://rimgo.pussthecat.org/uYkGfzu.png"
    holding_base_image = "https://rimgo.pussthecat.org/0mr6e6p.jpg"
    holding_mask = "https://rimgo.pussthecat.org/DimDfNH.png"

    inner = await read_image(message)
    if inner is None:
        await sent.delete()
        return

    await sent.edit(content="Processing ..")

    inner = inner.convert("RGBA")
    response = requests.get(holding_base_image, timeout=10)
    im = Image.open(BytesIO(response.content))

    response = requests.get(holding_mask, timeout=10)
    im_mask = Image.open(BytesIO(response.content))

    # ratio of width/height, but multiplied by 1000 and floored
    # if its over 1000, the width is larger than the height
    # used for the scaling, honestly could probably be removed
    xyratio = (inner.size[0] / inner.size[1]) * 1000 // 1

    # the resized dimension of the inner image in pixels
    IM_SIZE = 260
    # creates the square image to be placed inside by resizing, cropping, and rotating the input image
    inside_img = inner.copy()
    if xyratio > 1000:
        inside_img = inside_img.resize((int(xyratio * IM_SIZE / 1000) // 1, IM_SIZE), Image.BILINEAR)
    else:
        inside_img = inside_img.resize((IM_SIZE, int(IM_SIZE * 1000 / xyratio) // 1), Image.BILINEAR)
    inside_img = inside_img.crop(((inside_img.size[0] - IM_SIZE) / 2, (inside_img.size[1] - IM_SIZE) / 2,
                                  (inside_img.size[0] + IM_SIZE) / 2, (inside_img.size[1] + IM_SIZE) / 2))
    inside_img_prerotate = inside_img.copy()
    inside_img = inside_img.rotate(17, Image.BILINEAR, expand=True)
    inside_img.putalpha(Image.new("L", inside_img_prerotate.size, "white").rotate(17, expand=True))

    await sent.edit(content="Processing ...")

    # the pixel position of the placed image on the background image
    P1, P2 = 123, 232

    # creates the image the same size as the template and places the inside image in the correct location
    bg = Image.new("RGBA", im.size, "rgba(0,0,0,255)")
    bg.paste(inside_img, box=(P1, P2, inside_img.size[0] + P1, inside_img.size[1] + P2),
             mask=Image.new("L", inside_img_prerotate.size, "white").rotate(17, expand=True))

    # the final version of the image
    im_final = bg.copy()
    im_final.paste(im, mask=im_mask)
    im_final.save("holding.png")

    await sent.delete()
    await message.channel.send(file=discord.File("holding.png"))


async def exmilitary_imagemaker(message):
    sent = await message.channel.send("Processing .")

    exmilitary_base_image = "https://images.genius.com/6cb70d371c813611099de5c517fc60f7.1000x1000x1.png"
    exmilitary_mask_image = "https://rimgo.pussthecat.org/crHKd8m.png"
    exmilitary_texture = "https://rimgo.pussthecat.org/dDF8G3z.png"

    IM_SIZE = 500  # pixel size of output, same for height and width

    # try loading each image
    inner = await read_image(message)
    if inner is None:
        await sent.delete()
        return

    await sent.edit(content="Processing ..")

    response = requests.get(exmilitary_base_image, timeout=10)
    try:
        im = Image.open(BytesIO(response.content))
    except Exception as e:
        print(e)
        return
    response = requests.get(exmilitary_mask_image, timeout=10)
    im_mask = Image.open(BytesIO(response.content))
    response = requests.get(exmilitary_texture, timeout=10)
    texture = Image.open(BytesIO(response.content))

    print("Images loaded")
    im = im.resize((IM_SIZE, IM_SIZE), Image.BILINEAR)
    im_mask = im_mask.resize((IM_SIZE, IM_SIZE), Image.BILINEAR)
    inside_img = inner.copy().convert("RGBA")
    if inner.size[0] > inner.size[1]:
        inside_img = inside_img.resize(((int(IM_SIZE * inner.size[0] / inner.size[1]) // 1), IM_SIZE), Image.BILINEAR)
    else:
        inside_img = inside_img.resize((IM_SIZE, int(IM_SIZE * inner.size[1] / inner.size[0]) // 1), Image.BILINEAR)
    inside_img = inside_img.crop(((inside_img.size[0] - IM_SIZE) / 2, (inside_img.size[1] - IM_SIZE) / 2,
                                  (inside_img.size[0] + IM_SIZE) / 2, (inside_img.size[1] + IM_SIZE) / 2))

    print("Input image processed")
    texture = texture.resize((IM_SIZE, IM_SIZE)).convert("RGBA")

    print("Applying texture...")
    masko = Image.new("L", (IM_SIZE, IM_SIZE), 110)
    inside_img.paste(texture, mask=masko)

    await sent.edit(content="Processing ...")

    im_final = im_mask.copy()
    im_final.paste(inside_img, mask=im)
    im_final = im_final.resize((IM_SIZE, IM_SIZE), Image.BILINEAR)

    bg = Image.new("RGBA", im.size, "rgba(1,1,1,255)")
    bg.paste(im_final)

    im_final = im_final.convert("RGB")

    im_final.save("exmilitary.png")

    await sent.delete()
    await message.channel.send(file=discord.File("exmilitary.png"))


async def fantano_imagemaker(message):
    sent = await message.channel.send("Processing .")
    image_group = [("https://rimgo.pussthecat.org/iitXl6v.png", "https://rimgo.pussthecat.org/2uil9xz.png", (49, 28), 500, -20, 30, -30),
                   ("https://rimgo.pussthecat.org/EQSNZS4.png", "https://rimgo.pussthecat.org/z2RfZkp.png", (22, 20), 475, -20, 5, -5),
                   ("https://rimgo.pussthecat.org/IlyaYTT.png", "https://rimgo.pussthecat.org/gHWQJiu.png", (26, 24), 495, -30, 20,
                    -25)]  # (base image, cutout image)

    number = message.id % 3

    response = requests.get(image_group[number][0], timeout=10)
    img = Image.open(BytesIO(response.content))

    response = requests.get(image_group[number][1], timeout=10)
    cutout = Image.open(BytesIO(response.content))

    await sent.edit(content="Processing ..")

    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return

    SIZE = image_group[number][3]

    input_img = square_image_crop(input_img, SIZE).convert("RGBA")

    coeff = _create_coeff(
        (0, 0),
        (input_img.width, 0),
        (input_img.width, input_img.height),
        (0, input_img.height),
        # =>
        (0, 0),
        (input_img.width, image_group[number][4]),
        (input_img.width, input_img.height + image_group[number][5]),
        (image_group[number][6], input_img.height),
    )

    await sent.edit(content="Processing ...")

    input_img = input_img.transform((SIZE, SIZE), Image.PERSPECTIVE, coeff, Image.BICUBIC)

    blank = Image.new("RGBA", (1280, 720), "rgba(220,220,220,255)")
    blank.paste(input_img, image_group[number][2], mask=input_img)

    img_final = ImageChops.composite(img, blank, cutout)
    img_final.save("fantano.png")

    await sent.delete()
    await message.channel.send(file=discord.File("fantano.png"))


async def one_imagemaker(message):
    sent = await message.channel.send("Processing...")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return
    input_img = input_img.convert("RGBA").convert("1")
    input_img.save("one.png")
    await sent.delete()
    await message.channel.send(file=discord.File("one.png"))


async def kim_imagemaker(message):
    kim_base_url = "https://rimgo.pussthecat.org/5UIezWU.png"
    kim_cutout_url = "https://rimgo.pussthecat.org/1JlEG9R.png"

    sent = await message.channel.send("Processing .")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return

    await sent.edit(content="Processing ..")

    response = requests.get(kim_base_url, timeout=10)
    img = Image.open(BytesIO(response.content))

    response = requests.get(kim_cutout_url, timeout=10)
    cutout = Image.open(BytesIO(response.content))

    size = 260, 155
    input_img = rectangle_image_crop(input_img, size)

    coeff = _create_coeff(
        (0, 0),
        (input_img.width, 0),
        (input_img.width, input_img.height),
        (0, input_img.height),
        # =>
        (-3, 0),
        (input_img.width, - 19),
        (input_img.width + 5, input_img.height - 60),
        (0, input_img.height + 12),
    )

    input_img = input_img.transform((268, 235), Image.PERSPECTIVE, coeff, Image.BICUBIC).convert("RGBA")

    await sent.edit(content="Processing ...")

    blank = Image.new("RGBA", img.size, "rgba(20,20,20,255)")
    blank.paste(input_img, (753, 202), mask=input_img)

    img_final = ImageChops.composite(img, blank, cutout)
    img_final.save("kim.png")

    await sent.delete()
    await message.channel.send(file=discord.File("kim.png"))


async def get_emoji(message, client):
    sent = await message.channel.send("Processing .")
    message2 = message.content.split(' ')
    if message2[1][-1:] == '>':
        url = "https://cdn.discordapp.com/emojis/" + str(message2[1][-19:-1]) + ".gif"
        try:
            response = requests.get(url, timeout=10)
            img = Image.open(BytesIO(response.content))
            if (len(message2) > 2):
                try:
                    await sent.edit(content="Processing ..")
                    size = float(message2[2])
                    if (size > 10):
                        size = 10
                        await message.channel.send("That scale's too large! resizing to 10")
                except ValueError:
                    await message.channel.send("Invalid scale!")
                else:
                    img = img.resize((int(img.width * size), int(img.height * size)), Image.BICUBIC)
            img.save("emoji.gif")
            await message.channel.send(file=discord.File("emoji.gif"))
        except OSError:
            url = "https://cdn.discordapp.com/emojis/" + str(message2[1][-19:-1]) + ".png"
            response = requests.get(url, timeout=10)
            img = Image.open(BytesIO(response.content))
            if (len(message2) > 2):
                try:
                    await sent.edit(content="Processing ..")
                    size = float(message2[2])
                    if (size > 12):
                        size = 12
                        await message.channel.send("That scale's too large! resizing to 12")
                except ValueError:
                    await message.channel.send("Invalid scale!")
                else:
                    img = img.resize((int(img.width * size), int(img.height * size)), Image.BICUBIC)
            await sent.edit(content="Processing ..")
            img.save("emoji.png")
            await message.channel.send(file=discord.File("emoji.png"))
    else:
        try:
            emoji = "https://raw.githubusercontent.com/twitter/twemoji/master/assets/svg/" + \
                    message.content[3].lower().encode("unicode_escape").decode()[-5:] + \
                    ".svg"
            try:
                await sent.edit(content="Processing ..")
                cairosvg.svg2png(url=emoji, write_to="emoji.png", scale=float(message.content[5:]))
            except IndexError:
                cairosvg.svg2png(url=emoji, write_to="emoji.png", scale=int(20))
            except MemoryError:
                sent2 = await message.channel.send("That scale's too big! Resizing to 20...")
                cairosvg.svg2png(url=emoji, write_to="emoji.png", scale=int(20))
                await sent2.delete()

            except Exception:
                cairosvg.svg2png(url=emoji, write_to="emoji.png", scale=int(20))
        except OSError:
            await message.channel.send("There is a problem with that emoji, sorry :frowning:")
        else:
            await sent.edit(content="Processing ...")
            await message.channel.send(file=discord.File("emoji.png"))
            await sent.delete()
    try:
        await sent.delete()
    except Exception:
        pass


async def resize_img(message):
    message_split = message.clean_content.split(' ')
    try:
        resize_factor = float(message_split[-1])
    except ValueError:
        await message.channel.send("Hey you need to add a number to the end of the command!")
        return

    sent = await message.channel.send("Processing .")

    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return

    await sent.edit(content="Processing ..")

    x = input_img.width * input_img.height
    if x > 1000000:
        max_factor = 1
    elif x > 1:
        # max_factor = int(50*(200000/(x+550000)))
        # max_factor = min(int(1 + (0.0000001 * ((x - 2000000) * (x - 2000000)))), 10)
        max_factor = int((1000000) / (x + 90000))
    elif x == 1:
        max_factor = 250
    else:
        max_factor = 1

    min_factor = max((1 / input_img.width), (1 / input_img.height))

    if resize_factor > max_factor:
        resize_factor = max_factor
        await message.channel.send("Changing the resize factor to **" + str(resize_factor) + "**")

    if resize_factor < min_factor:
        resize_factor = min_factor
        await message.channel.send("Changing the resize factor to **" + str(resize_factor) + "**")

    await sent.edit(content="Processing ...")

    input_img = input_img.convert("RGBA").resize(
        (int(input_img.width * resize_factor), int(input_img.height * resize_factor)),
        Image.BICUBIC)

    input_img.save("resized_img.png")
    await sent.delete()
    await message.channel.send(file=discord.File("resized_img.png"))


async def sort_pixels(message):
    sent = await message.channel.send("Processing (this might take a while)")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return
    input_img = input_img.convert("RGBA")

    await sent.edit(content="Processing (this might take a while) .")

    MAX_SIZE = 500

    def pixel_brightness(px):
        r, g, b, a = px
        return r + g + b

    if input_img.height >= input_img.width:
        if input_img.height > MAX_SIZE:
            input_img = input_img.resize((int(input_img.width * MAX_SIZE / input_img.height), MAX_SIZE), Image.BICUBIC)
    else:
        if input_img.width > MAX_SIZE:
            input_img = input_img.resize((MAX_SIZE, int(input_img.height * MAX_SIZE / input_img.width)), Image.BICUBIC)

    pixels = []
    message_split = message.clean_content.split(' ')

    if message_split[-1] in {"vert", "vertical", "y", "columns", "cols", "col"}:  # sort the vertical columns
        for x in range(input_img.width):
            for y in range(input_img.height):
                temp_px = input_img.getpixel((x, y))
                temp = temp_px[0], temp_px[1], temp_px[2], temp_px[3], pixel_brightness(temp_px)
                pixels.append(temp)
            pixels.sort(key=lambda tup: tup[4])  # sort pixels[]
            for y in range(input_img.height):
                input_img.putpixel((x, y), pixels[y][0:4])
            pixels.clear()

            if x == input_img.width // 3:
                await sent.edit(content="Processing (this might take a while) ..")
            elif x == 2 * input_img.width // 3:
                await sent.edit(content="Processing (this might take a while) ...")

    elif message_split[-1] in {"hor", "horizontal", "x", "row", "rows"}:  # sort the vertical columns
        for y in range(0, input_img.height, 1):
            for x in range(input_img.width):
                temp_px = input_img.getpixel((x, y))
                temp = temp_px[0], temp_px[1], temp_px[2], temp_px[3], pixel_brightness(temp_px)
                pixels.append(temp)
            pixels.sort(key=lambda tup: tup[4])  # sort pixels[]
            for x in range(input_img.width):
                input_img.putpixel((x, y), pixels[x][0:4])
            pixels.clear()

            if y == input_img.height // 3:
                await sent.edit(content="Processing (this might take a while) ..")
            elif y == 2 * input_img.height // 3:
                await sent.edit(content="Processing (this might take a while) ...")

    else:
        for y in range(input_img.height):  # put all pixels in pixels[]
            for x in range(input_img.width):
                temp_px = input_img.getpixel((x, y))
                temp = temp_px[0], temp_px[1], temp_px[2], temp_px[3], pixel_brightness(temp_px)
                pixels.append(temp)

        await sent.edit(content="Processing (this might take a while) ..")

        pixels.sort(key=lambda tup: tup[4])  # sort pixels[]


        await sent.edit(content="Processing (this might take a while) ...")

        counter = 0
        for y in range(input_img.height):  # put all pixels[] on the image
            for x in range(input_img.width):
                input_img.putpixel((x, y), pixels[counter][0:4])
                counter = counter + 1

    await sent.edit(content="Processing (this might take a while) ....")
    input_img.save("sorted_pixels.png")
    await sent.delete()
    await message.channel.send(file=discord.File("sorted_pixels.png"))


async def pixel_shuffle(message):
    message_split = message.clean_content.split(' ')

    sent = await message.channel.send("Processing (this might take a while)")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return

    max_factor = int(
        3314233 / (input_img.width * input_img.height + 100000))  # function to limit the user entered value

    await sent.edit(content="Processing (this might take a while) .")

    try:
        swap_factor = float(message_split[-1])
    except ValueError:
        swap_factor = max_factor

    if swap_factor > max_factor:
        swap_factor = max_factor

    input_img = input_img.convert("RGBA")

    for i in range(int(swap_factor * input_img.width * input_img.height // 20)):
        if i == int(int(swap_factor * input_img.width * input_img.height // 20) / 3):
            await sent.edit(content="Processing (this might take a while) ..")
        if i == 2 * int(int(swap_factor * input_img.width * input_img.height // 20) / 3):
            await sent.edit(content="Processing (this might take a while) ...")
        # get two random pixels
        pos1 = random.randint(0, input_img.width - 1), random.randint(0, input_img.height - 1)
        pos2 = random.randint(0, input_img.width - 1), random.randint(0, input_img.height - 1)

        # swap the two pixels
        temp = input_img.getpixel(pos1)
        input_img.putpixel(pos1, input_img.getpixel(pos2))
        input_img.putpixel(pos2, temp)

    await sent.edit(content="Processing (this might take a while) ....")
    input_img.save("shuffled_pixels.png")
    await sent.delete()
    await message.channel.send("Shuffled the image by **" + str(swap_factor) + "** !")
    await message.channel.send(file=discord.File("shuffled_pixels.png"))


async def get_size(message):
    input_img = await read_image(message)
    if input_img is None:
        return
    input_img = input_img.convert("RGBA")
    await message.channel.send("The images dimensions are: " + str(input_img.size) + " !")


async def twice_imagemaker(message):
    naeyon_base_url = "https://rimgo.pussthecat.org/jl3Lv0U.png"
    naeyon_cutout_url = "https://rimgo.pussthecat.org/OsQvrXh.png"

    sent = await message.channel.send("Processing .")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return
    await sent.edit(content="Processing ..")

    input_img = input_img.convert("RGBA")

    response = requests.get(naeyon_base_url, timeout=10)
    img = Image.open(BytesIO(response.content))

    response = requests.get(naeyon_cutout_url, timeout=10)
    cutout = Image.open(BytesIO(response.content))

    size = 372, 272
    input_img = rectangle_image_crop(input_img, size)

    blank = Image.new("RGBA", img.size, "rgba(230,230,230,255)")
    blank.paste(input_img, (116, 221), mask=input_img)

    await sent.edit(content="Processing ...")

    img_final = ImageChops.composite(img, blank, cutout)
    img_final.save("twice.png")

    await sent.delete()
    await message.channel.send(file=discord.File("twice.png"))


async def drawing_imagemaker(message):
    drawing_base_url = "https://rimgo.pussthecat.org/9XayuIf.png"
    drawing_cutout_url = "https://rimgo.pussthecat.org/NCTZJgG.png"  # "https://rimgo.pussthecat.org/nRhholX.png"

    sent = await message.channel.send("Processing .")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return
    await sent.edit(content="Processing ..")
    input_img = input_img.convert("RGBA")

    response = requests.get(drawing_base_url, timeout=10)
    img = Image.open(BytesIO(response.content))

    response = requests.get(drawing_cutout_url, timeout=10)
    cutout = Image.open(BytesIO(response.content))

    size = 1089, 961

    input_img = rectangle_image_crop(input_img, size)

    bigger_img = Image.new("RGBA", (1400, 1280), (0, 0, 0, 255))
    bigger_img.paste(img, (572, 0))

    cutout_2 = Image.new("RGBA", (1400, 1280), (0, 0, 0, 0))
    cutout_2.paste(cutout, (300, 0))

    coeff = _create_coeff(
        (0, 0),
        (input_img.width, 0),
        (input_img.width, input_img.height),
        (0, input_img.height),
        # =>
        (-176, 200),
        (input_img.width - 180, -840),
        (input_img.width + 183, input_img.height),
        (0, input_img.height),
    )

    input_img = input_img.transform((1400, 1280), Image.PERSPECTIVE, coeff, Image.BICUBIC)
    await sent.edit(content="Processing ...")

    blank = Image.new("RGBA", bigger_img.size, "rgba(189,177,166,255)")
    blank.paste(input_img, (243, 33), mask=input_img)

    img_final= ImageChops.composite(bigger_img, blank, cutout_2).crop((572, 0, 1400, 1280))
    img_final.save("drawing.png")
    await sent.delete()
    await message.channel.send(file=discord.File("drawing.png"))


async def undo_img(message):
    sent = await message.channel.send("Processing .")
    m = [msg async for msg in message.channel.history(limit=30)]
    counter = 0
    for i in range(30):
        if m[i].attachments:
            if is_valid_filetype(m[i].attachments[0].url):
                readURL = m[i].attachments[0].url
                response = requests.get(readURL, timeout=10)
                image = Image.open(BytesIO(response.content))
                if m[i].author.bot or counter == 1:
                    counter = counter + 1
                    await sent.edit(content="Processing ..")
                if counter == 2:
                    await sent.edit(content="Processing ...")
                    image.save("undo.png")
                    await sent.delete()
                    await message.channel.send(file=discord.File("undo.png"))
                    return
        if m[i].embeds:
            if m[i].embeds[0].image:
                if is_valid_filetype(m[i].embeds[0].image.url):
                    readURL = m[i].embeds[0].image.url
                    response = requests.get(readURL, timeout=10)
                    image = Image.open(BytesIO(response.content))
                    if m[i].author.bot or counter == 1:
                        counter = counter + 1
                        await sent.edit(content="Processing ..")
                    if counter == 2:
                        await sent.edit(content="Processing ...")
                        image.save("undo.png")
                        await sent.delete()
                        await message.channel.send(file=discord.File("undo.png"))
                        return
        words = m[i].clean_content.split(' ')
        for word in words:
            if is_valid_filetype(word) and word[0:4] == "http":
                try:
                    response = requests.get(word, timeout=10)
                    image = Image.open(BytesIO(response.content))
                    if m[i].author.bot or counter == 1:
                        counter = counter + 1
                        await sent.edit(content="Processing ..")
                    if counter == 2:
                        await sent.edit(content="Processing ...")
                        image.save("undo.png")
                        await sent.delete()
                        await message.channel.send(file=discord.File("undo.png"))
                        return
                except OSError:
                    continue

    await sent.edit(content="Processing ...")
    await sent.delete()
    await message.channel.send("There's nothing to undo!")
    return


async def heejin_imagemaker(message):
    heejin_base_url = "https://rimgo.pussthecat.org/ZK4e545.png"
    heejin_cutout_url = "https://rimgo.pussthecat.org/qn7Un9h.png"

    sent = await message.channel.send("Processing .")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return
    await sent.edit(content="Processing ..")
    input_img = input_img.convert("RGBA")

    response = requests.get(heejin_base_url, timeout=10)
    img = Image.open(BytesIO(response.content))

    response = requests.get(heejin_cutout_url, timeout=10)
    cutout = Image.open(BytesIO(response.content))

    size = 365, 299
    input_img = rectangle_image_crop(input_img, size)
    input_img = input_img.rotate(10.7, resample=Image.BICUBIC, expand=1)

    blank = Image.new("RGBA", img.size, "rgba(230,230,230,255)")
    blank.paste(input_img, (119, 406), mask=input_img)
    await sent.edit(content="Processing ...")
    img_final = ImageChops.composite(img, blank, cutout)
    img_final.save("heejin.png")

    await sent.delete()
    await message.channel.send(file=discord.File("heejin.png"))


async def school_imagemaker(message):
    school_base_url = "https://rimgo.pussthecat.org/Q7RBEfz.png"
    school_cutout_url = "https://rimgo.pussthecat.org/NHahWmf.png"

    sent = await message.channel.send("Processing .")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return
    await sent.edit(content="Processing ..")

    input_img = input_img.convert("RGBA")

    response = requests.get(school_base_url, timeout=10)
    img = Image.open(BytesIO(response.content))

    response = requests.get(school_cutout_url, timeout=10)
    cutout = Image.open(BytesIO(response.content))

    size = 220, 153
    input_img = rectangle_image_crop(input_img, size)

    coeff = _create_coeff(
        (0, 0),
        (input_img.width, 0),
        (input_img.width, input_img.height),
        (0, input_img.height),
        # =>
        (0, 0),
        (input_img.width, -10),
        (input_img.width, input_img.height),
        (0, input_img.height + 10),
    )

    input_img = input_img.transform(size, Image.PERSPECTIVE, coeff, Image.BICUBIC)

    blank = Image.new("RGBA", img.size, "rgba(230,230,230,255)")
    blank.paste(input_img, (180, 125), mask=input_img)

    await sent.edit(content="Processing ...")

    img_final = ImageChops.composite(img, blank, cutout).crop((0, 0, 550, 500))
    img_final.save("school.png")

    await sent.delete()
    await message.channel.send(file=discord.File("school.png"))


async def lecture_imagemaker(message):
    lecture_base_url = "https://rimgo.pussthecat.org/K0Yy8Ef.png"
    lecture_cutout_url = "https://rimgo.pussthecat.org/yn2rbzY.png"

    sent = await message.channel.send("Processing .")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return
    await sent.edit(content="Processing ..")
    input_img = input_img.convert("RGBA")

    response = requests.get(lecture_base_url, timeout=10)
    img = Image.open(BytesIO(response.content))

    response = requests.get(lecture_cutout_url, timeout=10)
    cutout = Image.open(BytesIO(response.content))

    size = 415, 357
    input_img = rectangle_image_crop(input_img, size)

    coeff = _create_coeff(
        (0, 0),
        (input_img.width, 0),
        (input_img.width, input_img.height),
        (0, input_img.height),
        # =>
        (0, 0),
        (input_img.width + 10, 5),
        (input_img.width, input_img.height + 3),
        (0, input_img.height + 15),
    )

    input_img = input_img.transform(size, Image.PERSPECTIVE, coeff, Image.BICUBIC)

    blank = Image.new("RGBA", img.size, "rgba(230,230,230,255)")
    blank.paste(input_img, (268, 61), mask=input_img)

    await sent.edit(content="Processing ...")

    img_final = ImageChops.composite(img, blank, cutout)
    img_final.save("school.png")

    await sent.delete()
    await message.channel.send(file=discord.File("school.png"))


async def tesla_imagemaker(message):
    tesla_base_url = "https://rimgo.pussthecat.org/e8RIx2N.png"
    tesla_cutout_url = "https://rimgo.pussthecat.org/vusOnB8.png"

    sent = await message.channel.send("Processing...")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return

    input_img = input_img.convert("RGBA")

    response = requests.get(tesla_base_url, timeout=10)
    img = Image.open(BytesIO(response.content))

    response = requests.get(tesla_cutout_url, timeout=10)
    cutout = Image.open(BytesIO(response.content))

    size = 561, 448
    input_img = rectangle_image_crop(input_img, size)

    coeff = _create_coeff(
        (0, 0),
        (input_img.width, 0),
        (input_img.width, input_img.height),
        (0, input_img.height),
        # =>
        (-20, -20),
        (input_img.width, 0),
        (input_img.width + 20, input_img.height),
        (0, input_img.height + 220),
    )

    input_img = input_img.transform(size, Image.PERSPECTIVE, coeff, Image.BICUBIC)

    blank = Image.new("RGBA", img.size, "rgba(210,210,210,255)")
    blank.paste(input_img, (223, 269), mask=input_img)

    img_final = ImageChops.composite(img, blank, cutout)
    img_final.save("tesla.png")

    await sent.delete()
    await message.channel.send(file=discord.File("tesla.png"))


async def get_colour_from_hex(message):
    message_split = message.clean_content.split(' ')
    colour_val = ''
    size = 100

    try:
        colour = (message_split[1:])
        if not colour:
            await message.channel.send("Hey you need to add a hex code or rgb values to the end of the command!")
            return
    except IndexError:
        await message.channel.send("Hey you need to add a hex code or rgb values to the end of the command!")
        return
    if len(colour) == 1:
        if isinstance(message_split[1], discord.Role):
            colour_val = message_split[1].colour.to_rgb

        else:
            if colour[0][0] != '#':
                colour_val = "#" + str(colour[0])
            else:
                colour_val = str(colour[0])  # str(colour[0][1:])
        try:
            img = Image.new("RGB", (size, size), colour_val)
        except ValueError:
            await message.channel.send("Hey you need to add a valid hex code to the end of the command!")
        else:
            img.save("colour.png")
            await message.channel.send(file=discord.File("colour.png"))


async def osu_imagemaker(message):
    templates = [
        ("https://rimgo.pussthecat.org/jVvNla4.png", "https://rimgo.pussthecat.org/mK7vRZP.png", (902, 508), (31, 31)),
        ("https://rimgo.pussthecat.org/5mJ8JRe.png", "https://rimgo.pussthecat.org/gjZ6oAd.png", (1091, 614), (24, 11)),
        ("https://rimgo.pussthecat.org/rMPA3Oj.png", "https://rimgo.pussthecat.org/cBiW9GS.png", (1080, 605), (11, 13)),
        ("https://rimgo.pussthecat.org/lxHX0c5.png", "https://rimgo.pussthecat.org/UmRonoQ.png", (925, 516), (13, 12)),
        ("https://rimgo.pussthecat.org/FfpTUe5.png", "https://rimgo.pussthecat.org/ZaFklHg.png", (1083, 605), (16, 43)),
        ("https://rimgo.pussthecat.org/sayo07Z.png", "https://rimgo.pussthecat.org/osQve7x.png", (1034, 582), (5, 5)),
        ("https://rimgo.pussthecat.org/iwP94yb.png", "https://rimgo.pussthecat.org/3rrf6CA.png", (934, 529), (22, 24)),
        ("https://rimgo.pussthecat.org/pMdFgoQ.png", "https://rimgo.pussthecat.org/Y0zs7XW.png", (818, 470), (0, 0))
    ]

    index = random.randint(0, 7)

    osu_base_url = templates[index][0]
    osu_cutout_url = templates[index][1]

    sent = await message.channel.send("Processing .")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return

    await sent.edit(content="Processing ..")

    input_img = input_img.convert("RGBA")

    response = requests.get(osu_base_url, timeout=10)
    img = Image.open(BytesIO(response.content))

    response = requests.get(osu_cutout_url, timeout=10)
    cutout = Image.open(BytesIO(response.content))

    size = templates[index][2]
    input_img = rectangle_image_crop(input_img, size)

    top_left_corner = templates[index][3]

    blank = Image.new("RGBA", img.size, "rgba(20,20,20,255)")
    blank.paste(input_img, top_left_corner, mask=input_img)
    await sent.edit(content="Processing ...")
    img_final = ImageChops.composite(img, blank, cutout)
    img_final.save("osu.png")

    await sent.delete()
    await message.channel.send(file=discord.File("osu.png"))


async def noise_imagemaker(message):
    MAX_WIDTH = 500
    MAX_HEIGHT = 500

    message_split = message.clean_content.split(' ')
    try:
        width = int(message_split[1])
        height = int(message_split[2])
    except ValueError:
        await message.channel.send("Hey! You didnt enter valid numbers for height and width!")
        return
    except IndexError:
        await message.channel.send("Hey! You need to enter two values with your command for height and width!")
        return

    message_txt = 'Processing'
    sent = await message.channel.send(message_txt)

    invalidDimensions = [False, False]

    if width < 1:
        width = 1
        invalidDimensions[0] = True
    elif width > MAX_WIDTH:
        width = MAX_WIDTH
        invalidDimensions[0] = True
    if height < 1:
        height = 1
        invalidDimensions[1] = True
    elif height > MAX_HEIGHT:
        height = MAX_HEIGHT
        invalidDimensions[1] = True

    if invalidDimensions[0] or invalidDimensions[1]:
        message_txt = "Resizing to (" + str(width) + ", " + str(height) + "), " + message_txt

    message_txt = message_txt + '.'
    await sent.edit(content=message_txt)

    img = Image.new("RGB", (width, height), (0, 0, 0))
    for y in range(height):
        if int(y % (height / 3)) == int(height / 3 - 2):  # at approximately 33%, 66%, and 99% of the way through
            message_txt = message_txt + '.'  # the message is edited to contain another '.'
            await sent.edit(content=message_txt)
        for x in range(width):
            img.putpixel((x, y), (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    # rng = np.random.default_rng()
    # img = rng.integers(0, 2**8, (height, width, 3), dtype=np.uint8)

    img.save("noise.png")
    await sent.delete()
    await message.channel.send(file=discord.File("noise.png"))


async def mokou_imagemaker(message):
    base_url = "https://rimgo.pussthecat.org/HczH3lx.png"
    cutout_url = "https://rimgo.pussthecat.org/VGI3zY5.png"

    message_txt = 'Processing.'
    sent = await message.channel.send(message_txt)

    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return

    message_txt = message_txt + '.'
    await sent.edit(content=message_txt)

    input_img = input_img.convert("RGBA")

    response = requests.get(base_url, timeout=10)
    img = Image.open(BytesIO(response.content))

    response = requests.get(cutout_url, timeout=10)
    cutout = Image.open(BytesIO(response.content))

    size = 256, 177
    input_img = rectangle_image_crop(input_img, size)

    blank = Image.new("RGBA", img.size, "rgba(210,210,210,255)")
    blank.paste(input_img, (143, 110), mask=input_img)

    img_final = ImageChops.composite(img, blank, cutout)

    message_txt = message_txt + '.'
    await sent.edit(content=message_txt)

    img_final.save("mokou.png")

    await sent.delete()
    await message.channel.send(file=discord.File("mokou.png"))


async def image_shift(message):
    message_split = message.clean_content.split(' ')
    axis = 'i j'
    try:
        amount = int(message_split[-1])
    except ValueError:
        axis = str(message_split[-1])
        if axis in ('x', 'horizontal', 'h'):
            axis = 1
        elif axis in ('y', 'vertical', 'v'):
            axis = 0
        try:
            amount = int(message_split[-2])
        except (ValueError, IndexError):
            await message.channel.send("Hey! Those are not valid arguments! It should either look like "
                                       ";shift <number> <argument>  or  ;shift <number> !")
            return

    message_txt = 'Processing.'
    sent = await message.channel.send(message_txt)

    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return

    message_txt = message_txt + '.'
    await sent.edit(content=message_txt)

    input_img = input_img.convert("RGBA")

    img = np.array(input_img)

    if axis != 'i j':
        img = np.roll(img, amount, axis=axis)
    else:
        img = np.roll(img, amount)

    message_txt = message_txt + '.'
    await sent.edit(content=message_txt)

    final_img = Image.fromarray(img)

    final_img.save("warp.png")
    await sent.delete()
    await message.channel.send(file=discord.File("warp.png"))


async def megumin_imagemaker(message):
    base_url = "https://rimgo.pussthecat.org/muK6Bm6.png"
    cutout_url = "https://rimgo.pussthecat.org/FnOWeGT.png"

    sent = await message.channel.send("Processing...")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return

    input_img = input_img.convert("RGBA")

    response = requests.get(base_url, timeout=10)
    img = Image.open(BytesIO(response.content))

    response = requests.get(cutout_url, timeout=10)
    cutout = Image.open(BytesIO(response.content))

    size = 362, 200
    input_img = rectangle_image_crop(input_img, size)
    # input_img = input_img.rotate(37.7, expand=True)

    coeff = _create_coeff(
        (0, 0),
        (input_img.width, 0),
        (input_img.width, input_img.height),
        (0, input_img.height),
        # =>
        (-30, -185),
        (input_img.width + 265, 15),
        (input_img.width + 10, input_img.height - 20),
        (-57, input_img.height - 187),
    )

    input_img = input_img.transform((400, 520), Image.PERSPECTIVE, coeff, Image.BICUBIC)

    blank = Image.new("RGBA", img.size, "rgba(210,210,210,255)")
    blank.paste(input_img, (260, 115), mask=input_img)

    img_final = ImageChops.composite(img, blank, cutout)
    img_final = img_final.crop((397, 0, 1220, 1000))
    img_final.save("megumin.png")

    await sent.delete()
    await message.channel.send(file=discord.File("megumin.png"))


async def weezer_imagemaker(message):
    mask_url = 'http://rimgo.pussthecat.org/UUPCf9x.png'

    sent = await message.channel.send("Processing...")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return

    size = 800, 800

    input_img = rectangle_image_crop(input_img.convert("RGBA"), size)

    response = requests.get(mask_url, timeout=10)
    mask = Image.open(BytesIO(response.content))

    blank = Image.new("RGBA", size, "rgba(210,210,210,255)")
    blank.paste(input_img, mask=input_img)

    img_final = ImageChops.composite(mask.convert("RGB").convert("RGBA"), blank, mask)

    img_final.save("weezer.png")

    await sent.delete()
    await message.channel.send(file=discord.File("weezer.png"))


async def sickos_imagemaker(message):
    mask_url = 'https://rimgo.pussthecat.org/38TUcs6.png'

    sent = await message.channel.send("Processing...")
    try:
        input_img = await read_image(message)
    except Exception:
        await sent.edit(content="There\'s something wrong with your image :(")
        return
    if input_img is None:
        await sent.delete()
        return


    MAXSZ= 800
    if input_img.height > MAXSZ or input_img.width > MAXSZ:
        input_img = input_img.resize((MAXSZ, input_img.height*MAXSZ//input_img.width) if input_img.width > input_img.height
                                                else (input_img.width*MAXSZ//input_img.height, MAXSZ), resample=Image.BILINEAR).convert("RGBA")
    print((input_img.size))
    response = requests.get(mask_url, timeout=10)
    mask = Image.open(BytesIO(response.content))

    blank = Image.new("RGBA", input_img.size, "rgba(210,210,210,255)")
    try:
        blank.paste(input_img, mask=input_img)
    except Exception:
        blank.paste(input_img)

    if input_img.width > input_img.height:
        mask = mask.resize(
            (int(mask.width * (input_img.height/mask.height)), int(input_img.height)),
            resample=Image.BILINEAR)
        blank.paste(mask, box=(0, 0), mask=mask)
    else:
        mask = mask.resize(
            (int(input_img.width / 2), int(mask.height * (input_img.width / 2)/mask.width)) if input_img.width <= 382 else mask.size,
            resample=Image.BILINEAR)
        blank.paste(mask, box=(0, int(input_img.height/2 - mask.height/2)), mask=mask)

    blank.save("sickos.png")

    await sent.delete()
    await message.channel.send(file=discord.File("sickos.png"))


async def tom_imagemaker(message):
    mask_url = 'https://rimgo.pussthecat.org/XUt3CFq.png'

    sent = await message.channel.send("Processing...")
    try:
        input_img = await read_image(message)
    except Exception:
        await sent.edit(content="There\'s something wrong with your image :(")
        return
    if input_img is None:
        await sent.delete()
        return

    size = input_img.size

    input_img = input_img.convert("RGBA")

    response = requests.get(mask_url, timeout=10)
    mask = Image.open(BytesIO(response.content))
    if input_img.width > input_img.height:
        mask = mask.resize((input_img.height, input_img.height), resample=Image.BILINEAR)
    else:
        mask = mask.resize((input_img.width, input_img.width), resample=Image.BILINEAR)

    # blank_mask = Image.new("RGBA", size, "rgba(0,0,0,0)")
    # blank_mask.paste(mask, box=(input_img.width - mask.width, input_img.height - mask.height), mask=mask)
    blank = Image.new("RGBA", size, "rgba(210,210,210,255)")
    blank.paste(input_img, mask=input_img)
    blank.paste(mask, box=(input_img.width - mask.width, input_img.height - mask.height), mask=mask)

    # img_final = ImageChops.composite(blank_mask.convert("RGB").convert("RGBA"), blank, blank_mask)

    # img_final.save("tom.png")
    blank.save("tom.png")

    await sent.delete()
    await message.channel.send(file=discord.File("tom.png"))


async def to_rgb(message):
    sent = await message.channel.send("Processing...")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return
    input_img = input_img.convert("RGB")
    input_img.save("rgb.png")
    await sent.delete()
    await message.channel.send(file=discord.File("rgb.png"))


async def get_avatar(message):
    message_split = message.clean_content.split(' ')
    if len(message_split) == 1:
        await message.channel.send(message.author.avatar.url)
    else:
        msg = ''
        for member in message.mentions:
            msg = msg + str(member.avatar.url) + '\n'
        if msg == '':
            await message.channel.send(message.author.avatar.url)
        else:
            await message.channel.send(msg)


async def purple(message):
    sent = await message.channel.send("Processing...")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return

    input_img = input_img.convert("RGBA")

    MAX_DIM = 600
    if input_img.height > MAX_DIM:
        input_img = input_img.resize((int(input_img.width * MAX_DIM / input_img.height), MAX_DIM),
                                     resample=Image.BICUBIC)
    if input_img.width > MAX_DIM:
        input_img = input_img.resize((MAX_DIM, (int(input_img.height * MAX_DIM / input_img.width))),
                                     resample=Image.BICUBIC)

    for y in range(input_img.height):  # put all pixels in pixels[]
        for x in range(input_img.width):
            temp_px = input_img.getpixel((x, y))
            input_img.putpixel((x, y), (temp_px[0], temp_px[1] // 3, min(int(1.25 * temp_px[2]), 255), temp_px[3]))

    input_img.save("purple.png")
    await sent.delete()
    await message.channel.send(file=discord.File("purple.png"))
    return "sent"


async def whatifitwaspurple(message):
    if await purple(message) == "sent":
        await message.channel.send("https://rimgo.pussthecat.org/Id48ya7.png")


async def mixer(message):
    sent = await message.channel.send("Processing...")
    input_img = await read_image(message)
    if input_img is None:
        await sent.delete()
        return

    message_split = message.clean_content.split(' ')
    try:
        amount = int(message_split[-1]) * 5
    except ValueError:
        amount = 10

    if amount > 100:
        amount = 100

    input_img = input_img.convert("RGBA")

    MAX_DIM = 600
    if input_img.height > MAX_DIM:
        input_img = input_img.resize((int(input_img.width * MAX_DIM / input_img.height), MAX_DIM),
                                     resample=Image.BICUBIC)
    if input_img.width > MAX_DIM:
        input_img = input_img.resize((MAX_DIM, int(input_img.height * MAX_DIM / input_img.width)),
                                     resample=Image.BICUBIC)

    for y in range(input_img.height):
        for x in range(input_img.width):
            temp_px = input_img.getpixel((x, y))
            input_img.putpixel((x, y), (max(min(int(np.random.normal(0, amount) + temp_px[0]), 255), 0),
                                        max(min(int(np.random.normal(0, amount) + temp_px[1]), 255), 0),
                                        max(min(int(np.random.normal(0, amount) + temp_px[2]), 255), 0),
                                        temp_px[3]))

    input_img.save("mix.png")
    await sent.delete()
    await message.channel.send(file=discord.File("mix.png"))