import hashlib
import logging
import logging.config

from io import BytesIO
from xml.etree import ElementTree

import colorthief
import mpd
import requests


from os import path
import sys
p = path.abspath(path.join(path.dirname(__file__), path.pardir))
sys.path.append(p)
from mpd_env import MPD_HOST, MPD_PORT, MPD_PASSWORD


light_session = requests.session()
light_session.headers.update({
    'User-Agent': 'mpd-light',
})

logger = logging.getLogger('mpd-light')


def get_lastfm_cover(song):
    url = 'http://ws.audioscrobbler.com/2.0/'
    api_key = '7fb78a81b20bee7cb6e8fad4cbcb3694'

    artist = song.get('artist', None)
    album = song.get('album', None)

    if not any((artist, album)):
        return

    logger.info('{} - {}'.format(artist, album))
    resp = requests.get(url, {
        'method': 'album.getInfo',
        'artist': artist,
        'album': album,
        'api_key': api_key
    })

    try:
        tree = ElementTree.fromstring(resp.content)
        return tree.find('album').findall('image')[-1].text
    except Exception as e:
        logger.error('Failed to get album cover: {}'.format(e))
        return


class Listener():

    def __init__(self, host='localhost', port=6600, password=None,
                 light_host='http://localhost:31337'):
        self.host = host
        self.port = port
        self.password = password
        self.light_host = light_host

        self.connect()

    def connect(self):
        self.client = mpd.MPDClient()
        self.client.connect(self.host, self.port)
        if self.password:
            self.client.password(self.password)

    def start(self):
        last_song = None
        while True:
            try:
                song = self.client.currentsong()
                if song != last_song:
                    logger.info('{artist} - {album} / {title}'.format(
                        artist=song.get('artist'),
                        album=song.get('album'),
                        title=song.get('title'),
                    ))
                    color = self.get_color_code(song)
                    self.change_color(color)
                    last_song = song
            except Exception as e:
                logger.error(str(e))
                color = 'c0ffee'
                self.change_color(color)

            self.client.idle('player', 'playlist')

    def change_color(self, color):
        for retry in range(3):
            try:
                if not self._is_rgb_mode():
                    logger.info('Not in rgb mode, skipping')
                    return
                logger.info('Set color: {}'.format(color))
                # Devide red by 2 to calibrate.
                r = int(color[:2], 16) // 2
                color = '{:02x}{}'.format(r, color[2:])
                logger.info('Set calibrated color: {}'.format(color))
                light_session.post(self.light_host + "/light", {
                    'rgb': color
                })
            except Exception as e:
                logger.error(e)
            else:
                break
        else:
            logger.error('Max try count reached')
            exit(1)

    @staticmethod
    def get_color_code(song):
        try:
            img_url = get_lastfm_cover(song)
            if img_url:
                logger.info(img_url)
                resp = requests.get(img_url)
                file = BytesIO(resp.content)
                ct = colorthief.ColorThief(file)
                return '{:02x}{:02x}{:02x}'.format(*ct.get_color())
        except Exception as e:
            logger.error('Failed to get cover {}'.format(str(e)))
            pass

        txt = next(
            (song.get(x)
                for x in ('album', 'artist', 'title')
                if x in song))
        return hashlib.md5(txt.encode('utf-8')).hexdigest()[:6]

    def _is_rgb_mode(self):
        resp = light_session.get(self.light_host + '/status')
        mode = resp.json()['mode']
        return mode == 1


def set_logging():
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'brief': {
                'format': '%(asctime)s:%(name)s:%(levelname)s:%(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S %z',
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'brief',
                'level': 'DEBUG',
            }
        },
        'loggers': {
            'mpd-light': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': False,
            },
        },
        'root': {
            'level': 'WARNING',
            'handlers': ['console'],
        },
    })


if __name__ == '__main__':
    set_logging()
    listener = Listener(host=MPD_HOST, port=MPD_PORT, password=MPD_PASSWORD,
                        light_host='http://sakura.lan:31337')

    listener.start()
