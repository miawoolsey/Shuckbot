import json
import random
from collections import Counter
from types import SimpleNamespace

import pytest

from modules.games import colour, flags, geo
from modules.games.stats import ScoreStore


def test_flag_difficulty_pools_select_matching_flags():
    rng = random.Random(0)
    for difficulty, pool in flags.DIFFICULTY_POOLS.items():
        seen = Counter(flags.pick_flag(difficulty, rng)["difficulty"] for _ in range(300))
        if pool is not None:
            assert set(seen) <= pool
    assert {flags.pick_flag(6, rng)["difficulty"] for _ in range(2000)} == {1, 2, 3, 4, 5, 7}


def test_flag_difficulty_words():
    assert flags.difficulty_from_arg("hard") == 3
    assert flags.difficulty_from_arg("x") == 5
    assert flags.difficulty_from_arg("10") == 0
    assert flags.SUBJECT[7] == "Japanese Prefecture"


def test_colour_score():
    assert colour.calculate_score("ff0000", "ff0000") == 100
    assert 0 <= colour.calculate_score("000000", "ffffff") < 10
    assert colour.calculate_score("fe0000", "ff0000") == 100


@pytest.mark.parametrize("text,ok", [("a1B2c3", True), ("0x12ab", False), ("+12345", False), ("1_2345", False),
                                     ("12345", False), ("1234567", False)])
def test_hex_validation(text, ok):
    assert bool(colour.HEX_CODE.fullmatch(text)) is ok


def test_colour_result_image_stacks_guesses():
    img = colour.result_image("000000", ["ffffff", "ff0000"])
    assert img.getpixel((10, 10)) == (0, 0, 0)
    assert img.getpixel((140, 10)) == (255, 255, 255)
    assert img.getpixel((140, 140)) == (255, 0, 0)


def test_random_hex_is_six_digits():
    assert all(len(colour.random_hex()) == 6 for _ in range(200))


def test_geo_helpers():
    assert geo.with_zoom("https://x/map?size=1&zoom=12&a=b", "2") == "https://x/map?size=1&zoom=2&a=b"
    assert geo.with_zoom("https://x/map?zoom=7", "13") == "https://x/map?zoom=13"
    assert geo.parse_game_time("5") == 10
    assert geo.parse_game_time("1000") == 600
    assert geo.parse_game_time("abc") == 60
    assert geo.parse_game_time(None) == 60
    assert geo.geoguesser_points(0) > 4900
    assert geo.geoguesser_points(20000) < 1


def _user(i):
    return SimpleNamespace(id=i)


def test_score_store_layout(tmp_path):
    path = tmp_path / "scores.json"
    store = ScoreStore(path)
    store.record_flag_win(_user(1), 3, "Peru")
    store.record_flag_win(_user(1), 3, "Peru", multiplayer_round=True)
    store.record_flag_game_win(_user(1))
    store.record_geography(_user(1), "japan", "map")
    store.record_geoguesser(_user(1), 4000, 100.0)
    store.record_geoguesser(_user(1), 2000, 300.0)
    data = json.loads(path.read_text())
    assert data == {"<@1>": {
        "color": {},
        "flag": {"difficulty_3": 2, "flag": {"Peru": 2}, "total": 2, "rounds_won": 1, "games_won": 1},
        "geography": {"area": {"japan": 1, "japan_map_": 1}, "mode": {"map": 1, "japan_map_": 1}},
        "geoguesser": {"total": 2, "total_points": 6000, "gold_stars": 0, "total_distance": 400.0,
                       "avg_pointsA": 3000.0, "avg_distanceA": 200.0},
    }}
