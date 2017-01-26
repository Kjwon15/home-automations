import hashlib
import colorthief
import mpd
import requests

from io import BytesIO
from xml.etree import ElementTree


def get_lastfm_cover(song):
    url = 'http://ws.audioscrobbler.com/2.0/'
    api_key = '7fb78a81b20bee7cb6e8fad4cbcb3694'

    artist = song.get('artist', None)
    album = song.get('album', None)

    if not any((artist, album)):
        return

    print('{} - {}'.format(artist, album))
    resp = requests.get(url, {
        'method': 'album.getInfo',
        'artist': artist,
        'album': album,
        'api_key': api_key
    })

    tree = ElementTree.fromstring(resp.content)

    return tree.find('album').findall('image')[-1].text


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
                    print('{artist} - {album} / {title}'.format(
                        artist=song.get('artist'),
                        album=song.get('album'),
                        title=song.get('title'),
                    ))
                    color = self.get_color_code(song)
                    self.change_color(color)
            except Exception as e:
                print(str(e))
                color = 'c0ffee'
                self.change_color(color)

            self.client.idle('player', 'playlist')

    def change_color(self, color):
        print(color)
        requests.post(self.light_host + "/light", {
            'rgb': color
        })

    @staticmethod
    def get_color_code(song):
        try:
            img_url = get_lastfm_cover(song)
            if img_url:
                print(img_url)
                resp = requests.get(img_url)
                file = BytesIO(resp.content)
                ct = colorthief.ColorThief(file)
                return '{:02x}{:02x}{:02x}'.format(*ct.get_color())
        except Exception as e:
            print('Failed to get cover {}'.format(str(e)))
            pass

        txt = next(
            (song.get(x)
             for x in ('album', 'artist', 'title')
             if x in song
            ))
        return hashlib.md5(txt.encode('utf-8')).hexdigest()[:6]



if __name__ == '__main__':
    listener = Listener(host='tsubaki.lan', port=6600, password='derkuchen',
                        light_host='http://tsubaki.lan:31337')

    listener.start()
