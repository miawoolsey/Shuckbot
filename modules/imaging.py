"""Pure image transformations used by the image commands.

Everything here is synchronous and CPU-bound; callers run it via ``asyncio.to_thread``
so the bot stays responsive while images are processed.
"""
from __future__ import annotations

import io
import random

import numpy as np
from PIL import Image, ImageChops, ImageSequence

from modules.config import ASSETS_DIR

TEMPLATES_DIR = ASSETS_DIR / "templates"

BICUBIC = Image.Resampling.BICUBIC
BILINEAR = Image.Resampling.BILINEAR
PERSPECTIVE = Image.Transform.PERSPECTIVE


def template(name: str) -> Image.Image:
    img = Image.open(TEMPLATES_DIR / name)
    img.load()
    return img


# ---------------------------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------------------------

# taken from https://hhsprings.bitbucket.io/docs/programming/examples/python/PIL/Image__class_Image.html
def perspective_coeffs(src, dst) -> np.ndarray:
    """Coefficients for Image.transform(PERSPECTIVE) mapping the 4 ``dst`` corners onto ``src``."""
    rows, rhs = [], []
    for (xa, ya), (xb, yb) in zip(src, dst):
        rows.append([xa, ya, 1, 0, 0, 0, -xb * xa, -xb * ya])
        rows.append([0, 0, 0, xa, ya, 1, -yb * xa, -yb * ya])
        rhs.extend([xb, yb])
    return np.linalg.solve(np.array(rows, dtype=np.float32), np.array(rhs, dtype=np.float32))


def _warp(img: Image.Image, out_size, dst_corners) -> Image.Image:
    w, h = img.size
    coeffs = perspective_coeffs([(0, 0), (w, 0), (w, h), (0, h)], dst_corners)
    return img.transform(out_size, PERSPECTIVE, coeffs, BICUBIC)


def square_image_crop(img: Image.Image, size: int) -> Image.Image:
    """Resize so the short side is ``size`` and centre-crop to a square."""
    w, h = img.size
    if w == h:
        return img.resize((size, size), resample=BICUBIC)
    if w > h:
        img = img.resize((int(size * w / h), size), resample=BICUBIC)
        return img.crop((((img.size[0] - size) / 2) // 1, 0, ((img.size[0] + size) / 2) // 1, img.size[1]))
    img = img.resize((size, int(size * h / w)), resample=BICUBIC)
    return img.crop((0, ((img.size[1] - size) / 2) // 1, img.size[0], ((img.size[1] + size) / 2) // 1))


def rectangle_image_crop(img: Image.Image, size) -> Image.Image:
    """Resize to cover ``size`` (width, height) and centre-crop to that aspect ratio."""
    tw, th = size
    if img.width * th > img.height * tw:
        img = img.resize((int(th * img.width / img.height), th), BILINEAR)
        excess = img.width - (img.height * tw / th)
        return img.crop((int(excess / 2), 0, int(img.width - excess / 2), img.height))
    img = img.resize((tw, int(tw * img.height / img.width)), BILINEAR)
    excess = img.height - (img.width * th / tw)
    return img.crop((0, int(excess / 2), img.width, int(img.height - excess / 2)))


def _cover_square_crop(img: Image.Image, size: int) -> Image.Image:
    """Resize so the short side is ``size`` then centre-crop (used by holding/exmilitary)."""
    w, h = img.size
    if w > h:
        img = img.resize((int(size * w / h) // 1, size), BILINEAR)
    else:
        img = img.resize((size, int(size * h / w) // 1), BILINEAR)
    return img.crop(((img.size[0] - size) / 2, (img.size[1] - size) / 2,
                     (img.size[0] + size) / 2, (img.size[1] + size) / 2))


def _fit_within(img: Image.Image, max_dim: int, resample=BICUBIC) -> Image.Image:
    if img.height > max_dim:
        img = img.resize((int(img.width * max_dim / img.height), max_dim), resample=resample)
    if img.width > max_dim:
        img = img.resize((max_dim, int(img.height * max_dim / img.width)), resample=resample)
    return img


def _composite_onto(base: Image.Image, cutout: Image.Image, background: str, picture: Image.Image,
                    position) -> Image.Image:
    """Place ``picture`` behind ``base`` wherever ``cutout`` is transparent."""
    blank = Image.new("RGBA", base.size, background)
    blank.paste(picture, position, mask=picture)
    return ImageChops.composite(base, blank, cutout)


# ---------------------------------------------------------------------------------------------
# Meme templates
# ---------------------------------------------------------------------------------------------

def holding(inner: Image.Image) -> Image.Image:
    base, mask = template("holding_base.jpg"), template("holding_mask.png")
    im_size = 260
    inner = inner.convert("RGBA")
    # width/height ratio * 1000, floored; > 1000 means landscape
    xyratio = max((inner.size[0] / inner.size[1]) * 1000 // 1, 1)
    if xyratio > 1000:
        inside = inner.resize((int(xyratio * im_size / 1000) // 1, im_size), BILINEAR)
    else:
        inside = inner.resize((im_size, int(im_size * 1000 / xyratio) // 1), BILINEAR)
    inside = inside.crop(((inside.size[0] - im_size) / 2, (inside.size[1] - im_size) / 2,
                          (inside.size[0] + im_size) / 2, (inside.size[1] + im_size) / 2))
    rotated_mask = Image.new("L", inside.size, "white").rotate(17, expand=True)
    inside = inside.rotate(17, BILINEAR, expand=True)
    inside.putalpha(rotated_mask)

    x, y = 123, 232
    result = Image.new("RGBA", base.size, "rgba(0,0,0,255)")
    result.paste(inside, box=(x, y, inside.size[0] + x, inside.size[1] + y), mask=rotated_mask)
    result.paste(base, mask=mask)
    return result


def exmilitary(inner: Image.Image) -> Image.Image:
    im_size = 500
    base = template("exmilitary_base.png").convert("L").resize((im_size, im_size), BILINEAR)
    mask = template("exmilitary_mask.png").resize((im_size, im_size), BILINEAR)
    texture = template("exmilitary_texture.png").resize((im_size, im_size)).convert("RGBA")

    inside = _cover_square_crop(inner.convert("RGBA"), im_size)
    inside.paste(texture, mask=Image.new("L", (im_size, im_size), 110))

    result = mask.copy()
    result.paste(inside, mask=base)
    return result.resize((im_size, im_size), BILINEAR).convert("RGB")


# (base, cutout, paste position, size, top-right dy, bottom-right dy, bottom-left dx)
FANTANO_VARIANTS = [
    ("fantano_1_base.png", "fantano_1_cutout.png", (49, 28), 500, -20, 30, -30),
    ("fantano_2_base.png", "fantano_2_cutout.png", (22, 20), 475, -20, 5, -5),
    ("fantano_3_base.png", "fantano_3_cutout.png", (26, 24), 495, -30, 20, -25),
]


def fantano(inner: Image.Image, variant: int) -> Image.Image:
    base_name, cutout_name, position, size, tr_dy, br_dy, bl_dx = FANTANO_VARIANTS[variant]
    picture = square_image_crop(inner, size).convert("RGBA")
    w, h = picture.size
    picture = _warp(picture, (size, size), [(0, 0), (w, tr_dy), (w, h + br_dy), (bl_dx, h)])
    blank = Image.new("RGBA", (1280, 720), "rgba(220,220,220,255)")
    blank.paste(picture, position, mask=picture)
    return ImageChops.composite(template(base_name), blank, template(cutout_name))


def one_bit(inner: Image.Image) -> Image.Image:
    return inner.convert("RGBA").convert("1")


def kim(inner: Image.Image) -> Image.Image:
    picture = rectangle_image_crop(inner, (260, 155))
    w, h = picture.size
    picture = _warp(picture, (268, 235), [(-3, 0), (w, -19), (w + 5, h - 60), (0, h + 12)]).convert("RGBA")
    base = template("kim_base.png")
    return _composite_onto(base, template("kim_cutout.png"), "rgba(20,20,20,255)", picture, (753, 202))


def twice(inner: Image.Image) -> Image.Image:
    picture = rectangle_image_crop(inner.convert("RGBA"), (372, 272))
    base = template("twice_base.png")
    return _composite_onto(base, template("twice_cutout.png"), "rgba(230,230,230,255)", picture, (116, 221))


def drawing(inner: Image.Image) -> Image.Image:
    picture = rectangle_image_crop(inner.convert("RGBA"), (1089, 961))

    bigger = Image.new("RGBA", (1400, 1280), (0, 0, 0, 255))
    bigger.paste(template("drawing_base.png"), (572, 0))
    cutout = Image.new("RGBA", (1400, 1280), (0, 0, 0, 0))
    cutout.paste(template("drawing_cutout.png"), (300, 0))

    w, h = picture.size
    picture = _warp(picture, (1400, 1280), [(-176, 200), (w - 180, -840), (w + 183, h), (0, h)])
    blank = Image.new("RGBA", bigger.size, "rgba(189,177,166,255)")
    blank.paste(picture, (243, 33), mask=picture)
    return ImageChops.composite(bigger, blank, cutout).crop((572, 0, 1400, 1280))


def heejin(inner: Image.Image) -> Image.Image:
    picture = rectangle_image_crop(inner.convert("RGBA"), (365, 299))
    picture = picture.rotate(10.7, resample=BICUBIC, expand=1)
    base = template("heejin_base.png")
    return _composite_onto(base, template("heejin_cutout.png"), "rgba(230,230,230,255)", picture, (119, 406))


def school(inner: Image.Image) -> Image.Image:
    size = 220, 153
    picture = rectangle_image_crop(inner.convert("RGBA"), size)
    w, h = picture.size
    picture = _warp(picture, size, [(0, 0), (w, -10), (w, h), (0, h + 10)])
    base = template("school_base.png")
    result = _composite_onto(base, template("school_cutout.png"), "rgba(230,230,230,255)", picture, (180, 125))
    return result.crop((0, 0, 550, 500))


def lecture(inner: Image.Image) -> Image.Image:
    size = 415, 357
    picture = rectangle_image_crop(inner.convert("RGBA"), size)
    w, h = picture.size
    picture = _warp(picture, size, [(0, 0), (w + 10, 5), (w, h + 3), (0, h + 15)])
    base = template("lecture_base.png")
    return _composite_onto(base, template("lecture_cutout.png"), "rgba(230,230,230,255)", picture, (268, 61))


def tesla(inner: Image.Image) -> Image.Image:
    size = 561, 448
    picture = rectangle_image_crop(inner.convert("RGBA"), size)
    w, h = picture.size
    picture = _warp(picture, size, [(-20, -20), (w, 0), (w + 20, h), (0, h + 220)])
    base = template("tesla_base.png")
    return _composite_onto(base, template("tesla_cutout.png"), "rgba(210,210,210,255)", picture, (223, 269))


# (picture size, top-left corner) for osu_<n>_base.png / osu_<n>_cutout.png
OSU_VARIANTS = [
    ((902, 508), (31, 31)),
    ((1091, 614), (24, 11)),
    ((1080, 605), (11, 13)),
    ((925, 516), (13, 12)),
    ((1083, 605), (16, 43)),
    ((1034, 582), (5, 5)),
    ((934, 529), (22, 24)),
    ((818, 470), (0, 0)),
]


def osu(inner: Image.Image, variant: int) -> Image.Image:
    size, corner = OSU_VARIANTS[variant]
    picture = rectangle_image_crop(inner.convert("RGBA"), size)
    base = template(f"osu_{variant + 1}_base.png")
    cutout = template(f"osu_{variant + 1}_cutout.png")
    return _composite_onto(base, cutout, "rgba(20,20,20,255)", picture, corner)


def mokou(inner: Image.Image) -> Image.Image:
    picture = rectangle_image_crop(inner.convert("RGBA"), (256, 177))
    base = template("mokou_base.png")
    return _composite_onto(base, template("mokou_cutout.png"), "rgba(210,210,210,255)", picture, (143, 110))


def megumin(inner: Image.Image) -> Image.Image:
    picture = rectangle_image_crop(inner.convert("RGBA"), (362, 200))
    w, h = picture.size
    picture = _warp(picture, (400, 520), [(-30, -185), (w + 265, 15), (w + 10, h - 20), (-57, h - 187)])
    base = template("megumin_base.png")
    result = _composite_onto(base, template("megumin_cutout.png"), "rgba(210,210,210,255)", picture, (260, 115))
    return result.crop((397, 0, 1220, 1000))


def weezer(inner: Image.Image) -> Image.Image:
    size = 800, 800
    picture = rectangle_image_crop(inner.convert("RGBA"), size)
    mask = template("weezer_mask.png")
    blank = Image.new("RGBA", size, "rgba(210,210,210,255)")
    blank.paste(picture, mask=picture)
    return ImageChops.composite(mask.convert("RGB").convert("RGBA"), blank, mask)


def sickos(inner: Image.Image) -> Image.Image:
    max_size = 800
    if inner.height > max_size or inner.width > max_size:
        new_size = ((max_size, inner.height * max_size // inner.width) if inner.width > inner.height
                    else (inner.width * max_size // inner.height, max_size))
        inner = inner.resize(new_size, resample=BILINEAR).convert("RGBA")
    mask = template("sickos_mask.png")

    result = Image.new("RGBA", inner.size, "rgba(210,210,210,255)")
    try:
        result.paste(inner, mask=inner)
    except ValueError:  # image has no usable alpha channel
        result.paste(inner)

    if inner.width > inner.height:
        mask = mask.resize((int(mask.width * (inner.height / mask.height)), int(inner.height)), resample=BILINEAR)
        result.paste(mask, box=(0, 0), mask=mask)
    else:
        if inner.width <= 382:
            mask = mask.resize((int(inner.width / 2), int(mask.height * (inner.width / 2) / mask.width)),
                               resample=BILINEAR)
        result.paste(mask, box=(0, int(inner.height / 2 - mask.height / 2)), mask=mask)
    return result


def tom_scott(inner: Image.Image) -> Image.Image:
    inner = inner.convert("RGBA")
    side = min(inner.width, inner.height)
    mask = template("tom_mask.png").resize((side, side), resample=BILINEAR)
    result = Image.new("RGBA", inner.size, "rgba(210,210,210,255)")
    result.paste(inner, mask=inner)
    result.paste(mask, box=(inner.width - mask.width, inner.height - mask.height), mask=mask)
    return result


# ---------------------------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------------------------

def to_rgb(inner: Image.Image) -> Image.Image:
    return inner.convert("RGB")


def purple(inner: Image.Image) -> Image.Image:
    img = _fit_within(inner.convert("RGBA"), 600)
    px = np.asarray(img, dtype=np.int32)
    out = np.empty(px.shape, dtype=np.uint8)
    out[..., 0] = px[..., 0]
    out[..., 1] = px[..., 1] // 3
    out[..., 2] = np.minimum((1.25 * px[..., 2]).astype(np.int32), 255)
    out[..., 3] = px[..., 3]
    return Image.fromarray(out, "RGBA")


def mix(inner: Image.Image, amount: float, rng: np.random.Generator | None = None) -> Image.Image:
    """Add gaussian noise with standard deviation ``amount`` to every colour channel."""
    rng = rng or np.random.default_rng()
    img = _fit_within(inner.convert("RGBA"), 600)
    px = np.asarray(img).copy()
    noisy = np.trunc(rng.normal(0, amount, px[..., :3].shape) + px[..., :3])
    px[..., :3] = np.clip(noisy, 0, 255).astype(np.uint8)
    return Image.fromarray(px, "RGBA")


def noise(width: int, height: int, rng: np.random.Generator | None = None) -> Image.Image:
    rng = rng or np.random.default_rng()
    return Image.fromarray(rng.integers(0, 256, (height, width, 3), dtype=np.uint8), "RGB")


SORT_COLUMN_WORDS = {"vert", "vertical", "y", "columns", "cols", "col"}
SORT_ROW_WORDS = {"hor", "horizontal", "x", "row", "rows"}


def sort_pixels(inner: Image.Image, direction: str) -> Image.Image:
    """Stable-sort pixels by brightness (r+g+b): per column, per row, or across the whole image."""
    img = inner.convert("RGBA")
    max_size = 500
    if img.height >= img.width:
        if img.height > max_size:
            img = img.resize((int(img.width * max_size / img.height), max_size), BICUBIC)
    elif img.width > max_size:
        img = img.resize((max_size, int(img.height * max_size / img.width)), BICUBIC)

    px = np.asarray(img)
    brightness = px[..., :3].astype(np.int32).sum(axis=2)
    if direction in SORT_COLUMN_WORDS:
        order = np.argsort(brightness, axis=0, kind="stable")
        px = np.take_along_axis(px, order[..., None], axis=0)
    elif direction in SORT_ROW_WORDS:
        order = np.argsort(brightness, axis=1, kind="stable")
        px = np.take_along_axis(px, order[..., None], axis=1)
    else:
        order = np.argsort(brightness.ravel(), kind="stable")
        px = px.reshape(-1, 4)[order].reshape(px.shape)
    return Image.fromarray(np.ascontiguousarray(px), "RGBA")


def shuffle_limit(width: int, height: int) -> int:
    return int(3314233 / (width * height + 100000))


def shuffle_pixels(inner: Image.Image, swap_factor: float, rng: random.Random | None = None) -> Image.Image:
    """Swap ``swap_factor * pixels / 20`` random pairs of pixels."""
    rng = rng or random.Random()
    img = inner.convert("RGBA")
    w, h = img.size
    swaps = int(swap_factor * w * h // 20)
    flat = np.ascontiguousarray(np.asarray(img)).view(np.uint32).reshape(-1)
    pixels = flat.tolist()
    n = w * h
    for _ in range(max(swaps, 0)):
        a, b = rng.randrange(n), rng.randrange(n)
        pixels[a], pixels[b] = pixels[b], pixels[a]
    out = np.array(pixels, dtype=np.uint32).view(np.uint8).reshape(h, w, 4)
    return Image.fromarray(out, "RGBA")


def resize_limits(width: int, height: int) -> tuple[float, float]:
    """(max_factor, min_factor) that keep resized images a sensible size."""
    pixels = width * height
    if pixels > 1000000:
        max_factor = 1
    elif pixels > 1:
        max_factor = max(int(1000000 / (pixels + 90000)), 1)
    elif pixels == 1:
        max_factor = 250
    else:
        max_factor = 1
    return max_factor, max(1 / width, 1 / height)


def resize(inner: Image.Image, factor: float) -> Image.Image:
    return inner.convert("RGBA").resize((int(inner.width * factor), int(inner.height * factor)), BICUBIC)


def shift(inner: Image.Image, amount: int, axis: int | None) -> Image.Image:
    """Roll pixels along an axis (0 = vertical, 1 = horizontal), or through the raw byte buffer."""
    px = np.asarray(inner.convert("RGBA"))
    px = np.roll(px, amount) if axis is None else np.roll(px, amount, axis=axis)
    return Image.fromarray(px, "RGBA")


def solid_colour(colour: str, size: int = 100) -> Image.Image:
    return Image.new("RGB", (size, size), colour)


# ---------------------------------------------------------------------------------------------
# Emoji
# ---------------------------------------------------------------------------------------------

TWEMOJI_SVG_SIZE = 36
MAX_EMOJI_RENDER_PX = 8000


def twemoji_code(emoji: str) -> str:
    """Twemoji asset name: lowercase hex codepoints joined by '-', dropping FE0F outside ZWJ sequences."""
    codepoints = [ord(c) for c in emoji]
    if 0x200D not in codepoints:
        codepoints = [c for c in codepoints if c != 0xFE0F]
    return "-".join(f"{c:x}" for c in codepoints)


def render_svg(svg: bytes, scale: float) -> bytes:
    import cairosvg

    return cairosvg.svg2png(bytestring=svg, scale=scale)


def scale_animation(data: bytes, scale: float) -> bytes:
    """Resize every frame of a (possibly animated) GIF."""
    img = Image.open(io.BytesIO(data))
    size = (max(int(img.width * scale), 1), max(int(img.height * scale), 1))
    frames = [frame.convert("RGBA").resize(size, BICUBIC) for frame in ImageSequence.Iterator(img)]
    out = io.BytesIO()
    frames[0].save(out, format="GIF", save_all=len(frames) > 1, append_images=frames[1:],
                   loop=img.info.get("loop", 0), duration=img.info.get("duration", 100), disposal=2)
    return out.getvalue()


def scale_image(data: bytes, scale: float) -> bytes:
    img = Image.open(io.BytesIO(data))
    img = img.resize((max(int(img.width * scale), 1), max(int(img.height * scale), 1)), BICUBIC)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def encode_png(img: Image.Image) -> bytes:
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
