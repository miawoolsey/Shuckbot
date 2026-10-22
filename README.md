# Shuckbot
A discord bot for some basic commands,image manipulation, and games!

Collaboration with @billofbong


## Commands
Shuckbot has a variety of commands! You can access a full list on the bot with the command `;help `

For help on a specific command do `;help <command>`

#### Example commands:
> `;img <search>`  -  Searches google images, produces a navigatable list of 10

![Screen Shot 2020-05-13 at 11 55 40 PM](https://user-images.githubusercontent.com/44738399/81903648-45a44480-957f-11ea-84a2-3a7cae6ad8f7.png)

> `;picturebook` - A collection of saved images, similar to pins but server-wide and unlimited

![Screen Shot 2020-05-13 at 11 56 44 PM](https://user-images.githubusercontent.com/44738399/81903622-3e7d3680-957f-11ea-8ad6-63a294ba152f.png)

> `;holding <image URL/attached image>` - Your inputted image will be held by a perplexed man

![Screen Shot 2020-05-13 at 11 57 42 PM](https://user-images.githubusercontent.com/44738399/81903849-9a47bf80-957f-11ea-8528-2e53252630bd.png)

> `;draw <image URL/attached image>` - Your inputted image will be drawn by a young man on a whiteboard

![Screen Shot 2020-05-14 at 1 18 04 AM](https://user-images.githubusercontent.com/44738399/81904662-cd3e8300-9580-11ea-8734-e6a0c87cad78.png)

> `;pixelsort <image URL/attached image> <row/column> ` - Sort the image's rows or columns by pixel brightness

![Screen Shot 2020-05-14 at 12 00 46 AM](https://user-images.githubusercontent.com/44738399/81903645-44731780-957f-11ea-8593-da4b1e566824.png)

> `@Shuckbot <message> ` - Shuckbot will reply to your message with hyperadvanced and realistic AI

![Screen Shot 2020-05-14 at 12 03 08 AM](https://user-images.githubusercontent.com/44738399/81903647-450bae00-957f-11ea-81a8-d50b7dfa8d45.png)

There are many more commands for you to explore!

Ask either `@_michaeL#9999` or `@billofbong#12021` for an invite to the bot!

_this bot is in really rough development, so please feel free to submit pull requests or issues!_

## Development

### Running the bot
1. Copy `keys.txt.template` to `keys.txt` and fill in your keys (`token` is the only required one).
2. `docker compose up -d --build`, or locally: `pip install -r requirements.txt && python Shuckbot.py`
   (the `;e` emoji command needs the system `libcairo2` library).

### Tests
```
pip install -r requirements-dev.txt
python -m pytest
```
The tests run fully offline: Discord objects and network calls are faked.

### Layout
| Path | What lives there |
|------|------------------|
| `Shuckbot.py` | Entry point: builds the bot, loads every cog, global error handling |
| `modules/core.py` | `;prefix`, `;ping`, `;invite` and per-server prefix storage |
| `modules/help.py` | Help page text and the `;help` command |
| `modules/imagefun.py` | Image commands (Discord side); `modules/imaging.py` holds the pure PIL/numpy transforms |
| `modules/image_input.py` | Finds the image a user meant (URL, mention, attachment, or recent chat history) |
| `modules/imagesearch.py`, `modules/viewer.py` | `;img` / `;r34` and the `n`/`b`/`p<N>`/`s` paginated viewer (shared with `;pb`) |
| `modules/picturebook.py`, `modules/tags.py` | Server picturebook and global tags |
| `modules/games/` | `;game` colour, flag, geography and geoguesser games, plus stats/leaderboard |
| `modules/avwx.py`, `modules/identify.py`, `modules/readycheck.py` | METAR/TAF, Google Vision, Dota ready check |
| `modules/storage.py`, `modules/net.py` | Atomic JSON storage and the shared non-blocking HTTP client |
| `assets/` | Meme templates and help icons, bundled so the bot doesn't depend on any image host |

### Data files
Runtime data is kept in JSON files that are not committed: `prefixes.json`, `tags.json`, `tags_disabled.json`,
`tags_servers_disabled.json`, `picturebook.json` (TinyDB format) in the repository root, and `modules/scores.json`,
`modules/prefectures.json`, `modules/geoguessing.json` in `modules/`. The bot loads these into memory at startup and
writes changes back atomically, so **stop the bot before hand-editing them** or your edits may be overwritten.
`prefectures.json`, `geoguessing.json` and `flags.json` are re-read automatically when they change.
