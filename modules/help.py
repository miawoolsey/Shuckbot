import asyncio

import discord

shucks = [
    'https://rimgo.pussthecat.org/gacRkVx.png',
    'https://rimgo.pussthecat.org/gacRkVx.png',
    'https://rimgo.pussthecat.org/gacRkVx.png',
    'https://rimgo.pussthecat.org/MJRUgWk.png',
    'https://rimgo.pussthecat.org/UOdRaHR.png',
    'https://rimgo.pussthecat.org/31jOGPf.png',
    'https://rimgo.pussthecat.org/k7kTT2o.png',
    'https://rimgo.pussthecat.org/JvbBhc2.png',
    'https://rimgo.pussthecat.org/gWfuFB8.png',
    'https://rimgo.pussthecat.org/Dfz2xpo.png',
    'https://rimgo.pussthecat.org/EByj26t.png',
    'https://rimgo.pussthecat.org/tZxutE8.png',
    'https://rimgo.pussthecat.org/vkSksOv.png',
    'https://rimgo.pussthecat.org/G5KGuus.png',
    'https://rimgo.pussthecat.org/MtGmg3w.png',
    'https://rimgo.pussthecat.org/wnSibNm.png',
    'https://rimgo.pussthecat.org/cRDaS4i.png',
    'https://rimgo.pussthecat.org/mh1gqPV.png',
    'https://rimgo.pussthecat.org/0NgYWV7.png',
    'https://rimgo.pussthecat.org/CaIMs7Y.png',
    'https://rimgo.pussthecat.org/TQrwHx6.png',
    'https://rimgo.pussthecat.org/AX4Fsqr.png',
    'https://rimgo.pussthecat.org/inKNjPt.png',
    'https://rimgo.pussthecat.org/Yqpugd4.png',
    'https://rimgo.pussthecat.org/jJPTljI.png',
    'https://rimgo.pussthecat.org/N5Cu6Wx.png'
]

commands = [
    # {'command': 'prefix <character>', 'info': "Changes the command prefix for the server", 'page': 1},
    {
        'prefix': ('emote', 'e'),
        'command': 'e <emote> <scale (optional)>',
        'info': 'Your emote will become an image',
        'page': 1,
        'help': ('Turns your emote/emoji into a large image \nAdding a number after the emote scales it by that amount',
                 'Aliases:',
                 'e, emote',
                 'Usage:',
                 ';e <emote>\n'
                 ';e <emote> <number>\n'
                 ';emote <emote>\n'
                 ';emote <emote> <number>',
                 'Examples:',
                 ';e :apple:\n'
                 ';emote :thinking: 0.75\n'
                 ';e <:shuck:607469301007515650> 2'
                 )
    },

    {
        'prefix': ('image', 'img', 'im', 'i'),
        'command': 'i/im/img/image <query>',
        'info': "Google image searches for an image",
        'page': 1,
        'help': ('Searches Google Images for your picture',
                 'Aliases:',
                 'i, im, img, image',
                 'Navigation:',
                 'n to go next\n'
                 'b to go back\n'
                 'p[X] to go to page [X] (ex. p1, p20, p50, etc.)\n'
                 's to close the window',
                 'Usage:',
                 ';i <google search>\n'
                 ';im <google search>\n'
                 ';img <google search>',
                 'Examples:',
                 ';i Shuckle\n'
                 ';im Space Cop\n'
                 ';img League of Legends')
    },

    {
        'prefix': ('metar', ''),
        'command': 'metar <ICAO airport code>',
        'info': 'Meteorological aviation data',
        'page': 1,
        'help': ('Provides aviation weather data for an airport given its ICAO code\n'
                 'a list of these codes can be located at '
                 'http://www.flugzeuginfo.net/table_airportcodes_country-location_en.php',
                 'Aliases:',
                 'metar',
                 'Usage:',
                 ';metar <ICAO code>\n'
                 'Examples:',
                 ';metar CYVR\n'
                 ';metar rjff'
                 )
    },

    {
        'prefix': ('picturebook', 'pb'),
        'command': 'pb/picturebook | pb/picturebook add <image> | pb/picturebook rm/remove',
        'info': "A serverwide picturebook to store your images!",
        'page': 1,
        'help': ('A server-wide picture book that you can save any images to\n'
                 'You can look through the picture book, add new images, and delete images '
                 '(if you are the one who added the image)',
                 'Aliases:',
                 'pb, picturebook',
                 'Navigation:',
                 'n to go next\n'
                 'b to go back\n'
                 'p[X] to go to page [X] (ex. p1, p20, p50, etc.)\n'
                 's to close the window',
                 'Usage:',
                 ';pb\n'
                 ';picturebook add <image>\n'
                 ';pb rm\n'
                 ';picturebook remove\n',
                 'Examples:',
                 ';pb\n'
                 ';pb add https://rimgo.pussthecat.org/0VIk7Cu.png\n'
                 ';picturebook rm'
                 )
    },

    {
        'prefix': ('ping', ''),
        'command': 'ping',
        'info': 'Measures Shuckbot\'s ping',
        'page': 1,
        'help': ('Tells the time it took from message being sent to being received by the bot',
                 'Aliases:',
                 'ping',
                 'Usage:',
                 ';ping\n'
                 )
    },

    {
        'prefix': ('r34', ''),
        'command': 'r34 <query>',
        'info': 'You will see a series of disturbing images',
        'page': 1,
        'help': ('Searches R34 for your picture by tags\nTags are separated by spaces\nThis is a nsfw command, so '
                 'don\'t use this in your sfw channels! We are not responsible if'
                 ' you get in trouble for using this command',
                 'Aliases:',
                 'r34',
                 'Navigation:',
                 'n to go next\n'
                 'b to go back\n'
                 'p[X] to go to page [X] (ex. p1, p20, p50, etc.)\n'
                 's to close the window',
                 'Usage:',
                 ';r34 <search>\n',
                 'Examples:',
                 ';r34 Shuckle\n'
                 ';r34 Mike_Stoklasa Jay_Bauman')
    },

    {
        'prefix': ('tag', 't'),
        'command': 't/tag <tag> | t/tag add/edit <tag> <content> | t/tag owner/remove <tag> | t/tag list | t/tag random',
        'info': 'Access, add, edit, and remove a tag, find its owner, or pull up a random tag! Disclaimer: There is a chance'
                'that a given tag is NSFW! Be careful when using this command out in the wild.',
        'page': 1,
        'help': ('A tag system where you can save longer bits of text in convenient tags\n'
                 'Access a tag by typing \";t <tag>\" or \";tag <tag>\" \n'
                 'You can add new tags, edit or remove your own tags, find out a tag\'s owner, or list all your tags',
                 'Aliases:',
                 't, tag',
                 'Usage:',
                 ';t <tag>\n'
                 ';tag add <tag> <content>\n'
                 ';t edit <tag> <content>\n'
                 ';tag remove <tag>\n'
                 ';t owner <tag>\n'
                 ';tag list',
                 'Examples:',
                 ';t shucks\n'
                 ';tag add Bees According to all known laws of aviation...\n'
                 ';t edit Bees there is no way a bee should be able to fly.\n'
                 ';tag remove Bees\n'
                 ';t owner shuck\n'
                 ';tag list')
    },

    {
        'prefix': ('drawing', 'draw'),
        'command': 'draw/drawing <image URL / @user>',
        'info': 'A respectable young man will draw your image on a whiteboard',
        'page': 2,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will be drawn on a whiteboard by a young man',
                 'Aliases:',
                 'draw, drawing',
                 'Usage:',
                 ';draw <image URL>\n'
                 ';drawing <user mention>\n'
                 ';draw\n',
                 'Examples:',
                 ';draw https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';drawing @Shuckbot#6675\n')
    },

    {
        'prefix': ('exmilitary', 'exm'),
        'command': 'exm/exmilitary <image URL / @user>',
        'info': 'Your image will turn into Sacramento based experimental hip hop band Death Grip\'s first mixtape',
        'page': 2,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will become Sacramento based experimental hip hop band Death Grip\'s first mixtape',
                 'Aliases:',
                 'exm, exmilitary',
                 'Usage:',
                 ';exm <image URL>\n'
                 ';exmilitary <user mention>\n'
                 ';exm\n',
                 'Examples:',
                 ';exm https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';exmilitary @Shuckbot#6675\n')
    },

    {
        'prefix': ('fantano', 'fan', 'review', 'tnd'),
        'command': 'fan/fantano/review/tnd <image URL / @user>',
        'info': 'Funny internet music man will review your image',
        'page': 2,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will be reviewed by the internet\'s busiest music nerd',
                 'Aliases:',
                 'fan, fantano, review, tnd',
                 'Usage:',
                 ';fan <image URL>\n'
                 ';fantano <user mention>\n'
                 ';review\n',
                 'Examples:',
                 ';tnd https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';fan @Shuckbot#6675\n')
    },

    {
        'prefix': ('holding', 'hold'),
        'command': 'hold/holding <image URL / @user>',
        'info': 'A perplexed man will hold your image',
        'page': 2,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will be held by a perplexed young man',
                 'Aliases:',
                 'hold, holding',
                 'Usage:',
                 ';hold <image URL>\n'
                 ';holding <user mention>\n'
                 ';hold\n',
                 'Examples:',
                 ';holding https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';hold @Shuckbot#6675\n')
    },

    {
        'prefix': ('kim', ''),
        'command': 'kim <image URL / @user>',
        'info': 'Your image will be applauded by the Supreme Leader of North Korea and his team',
        'page': 2,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will be applauded by the Supreme Leader of North Korea and his team',
                 'Aliases:',
                 'kim',
                 'Usage:',
                 ';kim <image URL>\n'
                 ';kim <user mention>\n'
                 ';kim\n',
                 'Examples:',
                 ';kim https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';kim @Shuckbot#6675\n')
    },

    {
        'prefix': ('lecture', 'lect'),
        'command': 'lect/lecture <image URL / @user>',
        'info': 'Your image will be presented to students in a lecture',
        'page': 2,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will be shown in a college lecture',
                 'Aliases:',
                 'lect, lecture',
                 'Usage:',
                 ';lect <image URL>\n'
                 ';lecture <user mention>\n'
                 ';lect\n',
                 'Examples:',
                 ';lect https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';lecture @Shuckbot#6675\n')
    },

    {
        'prefix': ('loona', 'heejin'),
        'command': 'loona/heejin <image URL / @user>',
        'info': 'Heejin from kpop group LOONA will hold your image',
        'page': 2,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will be held by Heejin from kpop group LOONA',
                 'Aliases:',
                 'loona, heejin',
                 'Usage:',
                 ';loona <image URL>\n'
                 ';heejin <user mention>\n'
                 ';loona\n',
                 'Examples:',
                 ';loona https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';heejin @Shuckbot#6675\n')
    },

    {
        'prefix': ('megumin', 'megu'),
        'command': 'megu/megumin <image URL / @user>',
        'info': 'Megumin from Konosuba will be used as a mousepad while Kazuma from Konosuba looks at your image '
                '(Art by @luizhtx)',
        'page': 2,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will be seen by Kazuma from Konosuba while Megumin from Konosuba is being used'
                 'as a mousepad (Art by @luizhtx on twitter)',
                 'Aliases:',
                 'megu, megumin',
                 'Usage:',
                 ';megu <image URL>\n'
                 ';megumin <user mention>\n'
                 ';megu\n',
                 'Examples:',
                 ';megu https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';megumin @Shuckbot#6675\n')
    },

    {
        'prefix': ('mokou', 'gf'),
        'command': 'mokou/gf <image URL / @user>',
        'info': 'Mokou from Touhou will contemplate her existence because of your image (Art by @jokanhiyou)',
        'page': 2,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will be seen by Mokou from Touhou on her computer (art by @jokanhiyou on twitter)',
                 'Aliases:',
                 'mokou, gf',
                 'Usage:',
                 ';mokou <image URL>\n'
                 ';gf <user mention>\n'
                 ';mokou\n',
                 'Examples:',
                 ';gf https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';mokou @Shuckbot#6675\n')
    },

    {
        'prefix': ('noise', ''),
        'command': 'noise <width> <height>',
        'info': 'An image with random colour pixels will be made',
        'page': 3,
        'help': ('Given a width and a height (positive integers), a randomized, noisy image will be made!',
                 'Aliases:',
                 'noise',
                 'Usage:',
                 ';noise <width> <height>',
                 'Examples:',
                 ';noise 30 50\n'
                 ';noise 500 250')
    },

    {
        'prefix': (' osu', 'osu', ''),
        'command': 'osu <image URL / @user>',
        'info': 'An osu! streamer will play your image',
        'page': 3,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will be streamed on twitch by a random osu player!',
                 'Aliases:',
                 'osu',
                 'Usage:',
                 ';osu <image URL>\n'
                 ';osu <user mention>\n'
                 ';osu\n',
                 'Examples:',
                 ';osu https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';osu @Shuckbot#6675\n')
    },

    {
        'prefix': ('resize', 'scale'),
        'command': 'resize/scale <image URL / @user> <scale factor>',
        'info': 'Scales your image by a specified factor',
        'page': 3,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will be scaled by a specified amount. It will be limited if the given number is '
                 'too large or too small',
                 'Aliases:',
                 'resize, scale',
                 'Usage:',
                 ';resize <image URL> <number>\n'
                 ';scale <user mention> <number>\n'
                 ';resize <number>\n',
                 'Examples:',
                 ';resize https://img.pokemondb.net/artwork/large/shuckle.jpg 0.8\n'
                 ';scale @Shuckbot#6675 2.5\n')
    },

    {
        'prefix': ('school', ''),
        'command': 'school <image URL / @user>',
        'info': 'A schoolkid will draw your image in MSPaint',
        'page': 3,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will be drawn on MSPaint by a schoolkid',
                 'Aliases:',
                 'school',
                 'Usage:',
                 ';school <image URL>\n'
                 ';school <user mention>\n'
                 ';school\n',
                 'Examples:',
                 ';school https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';school @Shuckbot#6675\n')
    },

    {
        'prefix': ('tesla', ''),
        'command': 'tesla <image URL / @user>',
        'info': 'Your image will appear in a tesla',
        'page': 3,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will appear on a tesla dashboard',
                 'Aliases:',
                 'tesla',
                 'Usage:',
                 ';tesla <image URL>\n'
                 ';tesla <user mention>\n'
                 ';tesla\n',
                 'Examples:',
                 ';tesla https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';tesla @Shuckbot#6675\n')
    },

    {
        'prefix': ('twice', 'mina'),
        'command': 'twice/mina <image URL / @user>',
        'info': 'Mina from kpop group Twice will hold your image',
        'page': 3,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will be held by Mina from kpop group Twice',
                 'Aliases:',
                 'twice, mina',
                 'Usage:',
                 ';twice <image URL>\n'
                 ';mina <user mention>\n'
                 ';twice\n',
                 'Examples:',
                 ';twice https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';mina @Shuckbot#6675\n')
    },

    {
        'prefix': ('undo', ''),
        'command': 'undo',
        'info': 'Undoes the last image command',
        'page': 3,
        'help': ('Undoes the last image command performed by Shuckbot. Results may vary',
                 'Aliases:',
                 'undo',
                 'Usage:',
                 ';undo\n')
    },

    {
        'prefix': ('weezer', ''),
        'command': 'weezer <image URL / @user>',
        'info': 'Weezer from Weezer (Blue Album) will pose in front of your image',
        'page': 3,
        'help': ('Given an image URL, image attachment, user mention, or the last posted image, '
                 'Weezer from Weezer (Blue Album) will stand in front of your inputted photo',
                 'Aliases:',
                 'weezer',
                 'Usage:',
                 ';weezer <image URL>\n'
                 ';weezer <user mention>\n'
                 ';weezer\n',
                 'Examples:',
                 ';weezer https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';weezer @Shuckbot#6675\n')
    },

    {
        'prefix': ('1bit', 'one'),
        'command': '1bit/one <image URL / @user>',
        'info': 'Your image will be represented in 1-bit colour space',
        'page': 4,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will get transformed into a 1-bit colour space!',
                 'Aliases:',
                 '1bit, one',
                 'Usage:',
                 ';1bit <image URL>\n'
                 ';one <user mention>\n'
                 ';1bit\n',
                 'Examples:',
                 ';1bit https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';one @Shuckbot#6675\n')
    },

    {
        'prefix': ('rgb', 'torgb'),
        'command': 'rgb/torgb <image URL / @user>',
        'info': 'Remove the image\'s alpha channel!',
        'page': 4,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, the image\'s alpha channel will vanish!',
                 'Aliases:',
                 'rgb, torgb',
                 'Usage:',
                 ';rgb <image URL>\n'
                 ';torgb <user mention>\n'
                 ';rgb\n',
                 'Examples:',
                 ';rgb https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';rgb @Shuckbot#6675\n')
    },

    {
        'prefix': ('shift', ''),
        'command': 'shift <image URL / @user> <shift amount> <axis (optional)>',
        'info': 'Your image\'s pixels will be shifted by a certain amount',
        'page': 4,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will be shifted around by an inputted amount\n'
                 'If no axis value is given, it will be shifted somewhat similar to the horizontal shift, but '
                 'a lot funkier',
                 'Aliases:',
                 'shift',
                 'Axis Aliases:',
                 'horizontal, h, x  |  vertical, v, y',
                 'Usage:',
                 ';shift <image URL> <number> <axis>\n'
                 ';shift <user mention> <number>\n'
                 ';shift <number> <number>\n',
                 'Examples:',
                 ';pixelshuffle https://img.pokemondb.net/artwork/large/shuckle.jpg 30 x\n'
                 ';shuffle @Shuckbot#6675 70\n')
    },

    {
        'prefix': ('shuffle', 'pixelshuffle'),
        'command': 'shuffle/pixelshuffle <image URL / @user> <shuffle factor (optional)>',
        'info': 'Your image\'s pixels will be shuffled',
        'page': 4,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image will be shuffled around by an inputted factor\n'
                 'If no value is given, the maximum shuffle for that image size will be applied',
                 'Aliases:',
                 'shuffle, pixelshuffle',
                 'Usage:',
                 ';shuffle <image URL> <number>\n'
                 ';pixelshuffle <user mention>\n'
                 ';shuffle <number>\n',
                 'Examples:',
                 ';pixelshuffle https://img.pokemondb.net/artwork/large/shuckle.jpg 3\n'
                 ';shuffle @Shuckbot#6675\n')
    },

    {
        'prefix': ('sort', 'pixelsort'),
        'command': 'sort/pixelsort <image URL / @user> <column || row (optional)>',
        'info': 'Your image\'s pixels will be sorted from darkest to lightest, or if arguments are specified, '
                'the image\'s rows or columms will be sorted from darkest to lightest',
        'page': 4,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, said image\'s pixels will be sorted from darkest to lightest, or if arguments are specified, '
                 'the image\'s rows or columms will be sorted from darkest to lightest\n'
                 'NOTE: this resizes images to 500x500 max for speed',
                 'Aliases:',
                 'sort, pixelsort',
                 'Row sort aliases:',
                 'row, rows, x, hor, horizontal',
                 'Column sort aliases:',
                 'col, column, y, vert, vertical',
                 'Usage:',
                 ';sort <image URL>\n'
                 ';pixelsort <image URL> <row/column argument>\n'
                 ';sort <user mention>\n'
                 ';pixelsort <user mention> <row/column argument> \n'
                 ';sort\n',
                 'Examples:',
                 ';sort https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';pixelsort @Shuckbot#6675 horizontal\n')
    },

    {
        'prefix': ('size', ''),
        'command': 'size <image URL / @user>',
        'info': 'Tells the size of the image',
        'page': 5,
        'help': ('Given an image URL, image attachment, user mention, or if no arguments are given: the last posted '
                 'image, the image\'s size gets outputted as (width, height)',
                 'Aliases:',
                 'size',
                 'Usage:',
                 ';size <image URL>\n'
                 ';size <user mention>\n'
                 ';size\n',
                 'Examples:',
                 ';size https://img.pokemondb.net/artwork/large/shuckle.jpg\n'
                 ';size @Shuckbot#6675\n')
    },

    {
        'prefix': ('game color', 'game colour', 'game col', 'game c', 'g color', 'g colour', 'g col', 'g c',),
        'command': 'game color/colour/col/c <multiplayer/multi/m> <time in seconds to guess>',
        'info': 'Guess the color\'s hex code!',
        'page': 6,
        'help': ('Try and guess the color\'s hex code! Your answer should be just 6 hexadecimal numbers (ex. '
                 'the colour code for this embed is f1c40f)! Can be played in '
                 'singleplayer, or in multiplayer by adding multiplayer/multi/m to your command',
                 'Aliases:',
                 'color, colour, col, c',
                 'Usage:',
                 ';game color\n',
                 'Examples:',
                 ';g c\n'
                 ';game col multi\n'
                 ';g c m 45\n')
    },

    {
        'prefix': ('game flag', 'game f', 'g flag', 'g f'),
        'command': 'game flag/f <difficulty> <multiplayer/multi/m> <multiplayer rounds>',
        'info': 'Guess the flag!',
        'page': 6,
        'help': ('Try and guess the flag! The difficulties are:\neasy/e: easy country flags\nnormal/n: slightly harder country flags\n'
                 'hard/h: more obscure country flags\n all/a: all available flags (including states, cities, and more!)\n'
                 'japan/j: japanese prefectures\nAdding multiplayer/multi/m to your command will launch multiplayer'
                 ' mode, where the first person to get the flag right gets a point, and first to <multiplayer rounds> wins!',
                 'Aliases:',
                 'flag, f',
                 'Usage:',
                 ';game flag <difficulty> <multiplayer/multi/m> <multiplayer rounds>\n',
                 'Examples:',
                 ';g f\n'
                 ';game flag all\n'
                 ';g f h m 10\n')
    },

    {
        'prefix': ('game geo', 'game g', 'g geo', 'g g', 'game geography', 'g geography'),
        'command': 'game geography/geo/g <region> <mode>',
        'info': 'Geography related games!',
        'page': 6,
        'help': ('Geography related games!\nThe current regions are: Japan\nThe current modes are: Map',
                 'Aliases:',
                 'geography, geo, g',
                 'Usage:',
                 ';game geography/geo/g <region> <mode>\n',
                 'Examples:',
                 ';game geography japan map\n'
                 ';game g j m\n')
    },
    {
        'prefix': ('game stats', 'game s', 'g stats', 'g s'),
        'command': 'game stats/s <game> <user mention>',
        'info': 'Get a user\' game stats!',
        'page': 6,
        'help': ('States for a user\'s games, you can get more stats by entering the name of the game',
                 'Aliases:',
                 'stats, s',
                 'Usage:',
                 ';game stats/s <game> <user mention>\n',
                 'Examples:',
                 ';game stats flag\n'
                 ';game s geo @Shuckbot#6675\n')
    },
    {
        'prefix': ('game leaderboard', 'game l', 'g leaderboard', 'g l', 'game top', 'g top'),
        'command': 'game leaderboard/l/top',
        'info': 'Get the global leaderboard for games!',
        'page': 6,
        'help': ('Gets the global leaderboard for the games',
                 'Aliases:',
                 'leaderboard, l, top',
                 'Usage:',
                 ';game leaderboard/l/top\n',
                 'Examples:',
                 ';game leaderboard\n'
                 ';g l\n')
    },
    {
        'command': 'Page 1: ',
        'info': 'General Commands',
        'page': 0
    },

    {
        'command': 'Page 2: ',
        'info': 'Image editor Commands [A - M]',
        'page': 0
    },

    {
        'command': 'Page 3: ',
        'info': 'Image editor Commands [N - Z]',
        'page': 0
    },

    {
        'command': 'Page 4: ',
        'info': 'Image filter Commands',
        'page': 0
    },

    {
        'command': 'Page 5: ',
        'info': 'Image info Commands',
        'page': 0
    },

    {
        'command': 'Page 6: ',
        'info': 'Game Commands',
        'page': 0
    },

    {
        'command': 'Access other pages with',
        'info': ';help <page #>',
        'page': 0
    },

    {
        'command': 'To get help with a specific command, do',
        'info': ';help <command>',
        'page': 0
    }
]

titles = [
    "Shuckbot help",
    "General commands",
    "Image editor commands [A - M]",
    "Image editor commands [N - Z]",
    "Image filter commands",
    "Image info commands",
    "Game commands"
]


async def show_help(message):
    page_num = 0
    maxpage = 6
    if len(message.content) != 5:
        if message.content[6:].isdigit():
            page_num = int(message.content[6:])
            if page_num > maxpage:
                page_num = maxpage
            if page_num < 0:
                page_num = 0
        else:  # The user likely entered in a command
            if message.content[6:] in ['g', 'game']:
                page_num = 6
            else:
                command = str(message.content[6:])
                is_invalid = True
                for item in commands:
                    try:
                        for prefix in item['prefix']:
                            if prefix == command:
                                page_num = -1
                                is_invalid = False
                                help_txt = item['help']
                                gen_pfx = item['prefix'][0]
                    except KeyError:  # it got to the end without finding the command
                        break
                if is_invalid:
                    page_num = 0

    embed = discord.Embed()
    embed.colour = discord.Color.gold()
    embed.type = "rich"

    if page_num >= 0:
        embed.title = titles[page_num]
        for item in commands:
            if item['page'] == page_num:
                embed.add_field(name=item['command'], value=item['info'], inline=False)
        embed.set_footer(text="Page " + str(page_num) + "/" + str(maxpage) + "     type ;help <page number> "
                                                                             "to see the other pages!",
                         icon_url=shucks[message.id % len(shucks)])
    else:
        embed.title = gen_pfx.capitalize() + " command help!"
        embed.add_field(name="Description:", value=help_txt[0], inline=False)
        for i in range(1, int(len(help_txt) - 1), 2):
            embed.add_field(name=help_txt[i], value=help_txt[i + 1], inline=False)
    # ('Searches Google Images for your picture\n',
    #  'Navigate with:\n',
    #  'n to go next\n'
    #  'b to go back\n'
    #  'p[X] to go to page [X] (ex. p1, p20, p50, etc.)\n'
    #  's to close the window\n\n',
    #  'Usage:\n',
    #  ';i <google search>\n'
    #  ';im <google search>\n'
    #  ';img <google search>\n\n',
    #  'Examples:\n',
    #  ';i Shuckle\n'
    #  ';im Space Cop\n'
    #  ';img League of Legends')
    msg = await message.channel.send(embed=embed)
# reactL = await msg.add_reaction(":shuckL:706690260519747604")
# reactR = await msg.add_reaction(":shuckR:706690259890733087")
#
# def check(reaction, user):
# 	return user == message.author and (reaction.emoji == reactL or reaction.emoji == reactR)
#
# try:
# 	reaction, user = await client.wait_for('reaction_add', timeout=10.0, check=check)
# except asyncio.TimeoutError:
# 	await message.channel.send('TIMEOUT')
# else:
# 	await message.channel.send('yes')
