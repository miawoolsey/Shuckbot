import numpy as np
import pytest
from PIL import Image

from modules import imaging


def _sample(w=23, h=17, seed=0, mode="RGBA"):
    rng = np.random.default_rng(seed)
    return Image.fromarray(rng.integers(0, 256, (h, w, 4), dtype=np.uint8), "RGBA").convert(mode)


def _naive_sort(img, direction):
    """The original per-pixel getpixel/putpixel implementation."""
    img = img.convert("RGBA").copy()
    key = lambda px: px[0] + px[1] + px[2]
    if direction in imaging.SORT_COLUMN_WORDS:
        for x in range(img.width):
            col = sorted((img.getpixel((x, y)) for y in range(img.height)), key=key)
            for y, px in enumerate(col):
                img.putpixel((x, y), px)
    elif direction in imaging.SORT_ROW_WORDS:
        for y in range(img.height):
            row = sorted((img.getpixel((x, y)) for x in range(img.width)), key=key)
            for x, px in enumerate(row):
                img.putpixel((x, y), px)
    else:
        pixels = sorted((img.getpixel((x, y)) for y in range(img.height) for x in range(img.width)), key=key)
        for i, px in enumerate(pixels):
            img.putpixel((i % img.width, i // img.width), px)
    return img


@pytest.mark.parametrize("direction", ["col", "vertical", "rows", "x", "anything"])
def test_sort_pixels_matches_original_algorithm(direction):
    img = _sample()
    assert np.array_equal(np.asarray(imaging.sort_pixels(img, direction)), np.asarray(_naive_sort(img, direction)))


def test_purple_matches_original_formula():
    img = _sample()
    out = np.asarray(imaging.purple(img)).astype(int)
    src = np.asarray(img).astype(int)
    assert np.array_equal(out[..., 0], src[..., 0])
    assert np.array_equal(out[..., 1], src[..., 1] // 3)
    assert np.array_equal(out[..., 2], np.minimum((1.25 * src[..., 2]).astype(int), 255))
    assert np.array_equal(out[..., 3], src[..., 3])


def test_purple_and_mix_cap_size_at_600():
    big = Image.new("RGB", (1200, 300))
    assert imaging.purple(big).size == (600, 150)
    assert imaging.mix(big, 10).size == (600, 150)


def test_mix_keeps_alpha_and_range():
    img = _sample()
    out = np.asarray(imaging.mix(img, 100, np.random.default_rng(1)))
    assert np.array_equal(out[..., 3], np.asarray(img)[..., 3])
    assert not np.array_equal(out, np.asarray(img))


def test_shuffle_preserves_pixels():
    img = _sample(40, 30)
    out = imaging.shuffle_pixels(img, 5, rng=__import__("random").Random(3))
    before = sorted(map(tuple, np.asarray(img).reshape(-1, 4)))
    after = sorted(map(tuple, np.asarray(out).reshape(-1, 4)))
    assert before == after
    assert not np.array_equal(np.asarray(out), np.asarray(img))


def test_shuffle_zero_is_identity():
    img = _sample()
    assert np.array_equal(np.asarray(imaging.shuffle_pixels(img, 0)), np.asarray(img))


def test_noise_dimensions():
    assert imaging.noise(7, 3).size == (7, 3)


@pytest.mark.parametrize("w,h,expected_max", [(2000, 1000, 1), (1, 1, 250), (100, 100, 10), (950, 1000, 1)])
def test_resize_limits(w, h, expected_max):
    max_factor, min_factor = imaging.resize_limits(w, h)
    assert max_factor == expected_max
    assert min_factor == max(1 / w, 1 / h)


def test_shift_axes():
    img = _sample(5, 4)
    src = np.asarray(img)
    assert np.array_equal(np.asarray(imaging.shift(img, 2, 1)), np.roll(src, 2, axis=1))
    assert np.array_equal(np.asarray(imaging.shift(img, -1, 0)), np.roll(src, -1, axis=0))
    assert np.array_equal(np.asarray(imaging.shift(img, 3, None)), np.roll(src, 3))


def test_solid_colour_rejects_invalid_hex():
    assert imaging.solid_colour("#ff0000").getpixel((0, 0)) == (255, 0, 0)
    with pytest.raises(ValueError):
        imaging.solid_colour("#nothex")


@pytest.mark.parametrize("emoji,code", [
    ("😀", "1f600"),
    ("☀️", "2600"),          # FE0F dropped
    ("🇨🇦", "1f1e8-1f1e6"),  # flag sequence
    ("👩‍💻", "1f469-200d-1f4bb"),
])
def test_twemoji_code(emoji, code):
    assert imaging.twemoji_code(emoji) == code


def test_all_templates_used_by_code_exist_and_decode():
    names = {"holding_base.jpg", "holding_mask.png", "exmilitary_base.png", "exmilitary_mask.png",
             "exmilitary_texture.png", "kim_base.png", "kim_cutout.png", "twice_base.png", "twice_cutout.png",
             "drawing_base.png", "drawing_cutout.png", "heejin_base.png", "heejin_cutout.png", "school_base.png",
             "school_cutout.png", "lecture_base.png", "lecture_cutout.png", "tesla_base.png", "tesla_cutout.png",
             "mokou_base.png", "mokou_cutout.png", "megumin_base.png", "megumin_cutout.png", "weezer_mask.png",
             "sickos_mask.png", "tom_mask.png"}
    names |= {n for base, cutout, *_ in imaging.FANTANO_VARIANTS for n in (base, cutout)}
    names |= {f"osu_{i}_{kind}.png" for i in range(1, len(imaging.OSU_VARIANTS) + 1) for kind in ("base", "cutout")}
    for name in names:
        assert imaging.template(name).size[0] > 0


@pytest.mark.parametrize("render", [
    imaging.holding, imaging.exmilitary, imaging.kim, imaging.twice, imaging.drawing, imaging.heejin,
    imaging.school, imaging.lecture, imaging.tesla, imaging.mokou, imaging.megumin, imaging.weezer,
    imaging.sickos, imaging.tom_scott, imaging.one_bit, imaging.to_rgb,
    lambda img: imaging.fantano(img, 2), lambda img: imaging.osu(img, 7),
])
@pytest.mark.parametrize("mode,size", [("RGB", (320, 200)), ("RGBA", (150, 260)), ("P", (64, 64)), ("L", (90, 90))])
def test_templates_render_for_common_image_modes(render, mode, size):
    out = render(_sample(*size, mode=mode))
    assert out.size[0] > 0 and out.size[1] > 0


def test_scale_animation_keeps_frames():
    import io
    frames = [Image.new("RGB", (10, 10), c) for c in ("red", "blue", "green")]
    buf = io.BytesIO()
    frames[0].save(buf, "GIF", save_all=True, append_images=frames[1:], duration=50, loop=0)
    out = Image.open(io.BytesIO(imaging.scale_animation(buf.getvalue(), 2)))
    assert out.size == (20, 20)
    assert getattr(out, "n_frames", 1) == 3
