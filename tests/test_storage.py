import json

from tinydb import Query, TinyDB

from modules.storage import CachedJSONStorage, JsonDocument, ReloadingJsonFile, atomic_write_json


def _exercise(db):
    db.insert({"tag": "a", "owner": 1})
    db.insert({"tag": "b", "owner": 2})
    db.update({"owner": 3}, Query().tag == "a")
    db.remove(Query().tag == "b")
    db.table("123").insert({"image": "x"})
    db.upsert({"tag": "c", "owner": 4}, Query().tag == "c")


def test_cached_storage_writes_same_format_as_tinydb(tmp_path):
    default_path, cached_path = tmp_path / "default.json", tmp_path / "cached.json"
    _exercise(TinyDB(default_path))
    _exercise(TinyDB(cached_path, storage=CachedJSONStorage))
    assert cached_path.read_text() == default_path.read_text()


def test_cached_storage_reads_existing_and_empty_files(tmp_path):
    path = tmp_path / "db.json"
    TinyDB(path).insert({"id": 5, "prefix": "!"})
    assert TinyDB(path, storage=CachedJSONStorage).get(Query().id == 5)["prefix"] == "!"

    empty = tmp_path / "empty.json"
    empty.write_text("")
    db = TinyDB(empty, storage=CachedJSONStorage)
    assert db.all() == []
    db.insert({"server_number": 1})
    assert json.loads(empty.read_text())["_default"]["1"] == {"server_number": 1}


def test_cached_storage_only_parses_file_once(tmp_path, monkeypatch):
    path = tmp_path / "db.json"
    TinyDB(path).insert({"tag": "a"})
    db = TinyDB(path, storage=CachedJSONStorage)
    db.all()
    path.write_text("not json anymore")  # would explode if re-read
    assert db.search(Query().tag == "a")


def test_atomic_write_keeps_mode_and_leaves_no_temp_files(tmp_path):
    path = tmp_path / "data.json"
    path.write_text("{}")
    path.chmod(0o640)
    atomic_write_json(path, {"a": 1}, indent=4)
    assert json.loads(path.read_text()) == {"a": 1}
    assert path.stat().st_mode & 0o777 == 0o640
    assert [p.name for p in tmp_path.iterdir()] == ["data.json"]


def test_json_document_defaults_and_saves(tmp_path):
    doc = JsonDocument(tmp_path / "scores.json", indent=4)
    doc.data["x"] = 1
    doc.save()
    assert JsonDocument(tmp_path / "scores.json").data == {"x": 1}


def test_reloading_json_file_picks_up_changes(tmp_path):
    import os
    path = tmp_path / "f.json"
    path.write_text("[1]")
    f = ReloadingJsonFile(path)
    assert f.load() == [1]
    path.write_text("[2]")
    os.utime(path, (1, 1))
    assert f.load() == [2]
