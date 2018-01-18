#!/usr/bin/env python3

import logging
import logging.config
import os
import sched
import socket
import time

import requests

from mpd_env import MPD_HOST, MPD_PORT, MPD_PASSWORD

session = requests.session()
session.headers.update({
    'User-Agent': 'alarm.py',
})

MAIN_LIGHT_SWITCH = 'http://omega2.lan:8000/switch/0'
YEELIGHT_HOST = 'http://tsubaki.lan:31337/'

MIN_TEMP = 1700
MAX_TEMP = 6500

DURATION = 60 * 3 + 46 - 20
INTERVAL = 10

logger = logging.getLogger(__name__)
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
        __name__: {
            'handlers': ['console'],
            'level': os.getenv('LOGLEVEL', 'WARNING').upper(),
            'propagate': False,
        }
    },
    'root': {
        'level': 'WARNING',
        'handlers': ['console'],
    },
})


def turn_on_light():
    # Turn on the light
    logger.info('Turn on the light')
    session.put(MAIN_LIGHT_SWITCH)


def load_playlist():
    logger.info('Load playlist')
    sock = socket.socket()
    sock.connect((MPD_HOST, MPD_PORT))
    if MPD_PASSWORD:
        sock.send('password {}\n'.format(MPD_PASSWORD).encode())

    sock.send(
        b'command_list_begin\n'
        b'setvol 70\n'
        b'clear\n'
        b'load alarm\n'
        b'consume 1\n'
        b'play 0\n'
        b'command_list_end\n'
        b'close\n'
    )
    logger.debug(sock.recv(4096).decode())
    sock.close()


def do_light_stuff():
    # Light time!
    logger.info('yeelight time')
    try:
        session.put(YEELIGHT_HOST + 'switch', timeout=5)
    except Exception as e:
        logger.error(e)
        logger.warning('Cannot on yeelight')
    else:
        time.sleep(1)
    scheduler = sched.scheduler(time.time, time.sleep)
    steps = DURATION // INTERVAL

    def set_light(**kwargs):
        logger.info('Set light {}'.format(kwargs))
        try:
            session.post(
                YEELIGHT_HOST + 'light',
                data=kwargs,
                timeout=5
            )
        except Exception as e:
            logger.error(e)
            logger.warning('Cannot controll yeelight')

    def turn_off_yeelight():
        try:
            session.post(
                YEELIGHT_HOST + 'light',
                data={
                    'brightness': 40,
                    'rgb': 'ff0000',
                },
                timeout=5
            )
            session.delete(YEELIGHT_HOST + 'switch')
        except Exception as e:
            logger.warning('Cannot off yeelight')
            logger.error(e)

    for step in range(steps):
        temp = int(MIN_TEMP + ((MAX_TEMP - MIN_TEMP) * (step / steps)))
        brightness = int(100 * step / steps) or 1
        scheduler.enter(step * INTERVAL, 1, set_light, kwargs={
            'temp': temp,
            'brightness': brightness,
        })
    scheduler.enter(DURATION, 1, turn_off_yeelight)

    scheduler.run()


def forecast():
    logger.info('forecast')
    try:
        resp = session.get(
            'https://query.yahooapis.com/v1/public/yql', params={
                'format': 'json',
                'q': ("select item.forecast from weather.forecast(1) where u='c' and"
                      " woeid in (select woeid from geo.places(1) where text = 'daejeon')"),
            }
        )

        forecast = resp.json()['query']['results']['channel']['item']['forecast']
    except Exception as e:
        print(resp.json())
        logger.error('Failed to get forecast: {}'.format(e))
        return

    try:
        msg = (
            "Today's forecast is {text}."
            " Highest temperature is {high} degrees"
            " and lowest temperature is {low} degrees."
        ).format(text=forecast['text'], high=forecast['high'], low=forecast['low'])
        session.post(
            'http://tsubaki.lan:1775/tts', {
                'msg': msg,
                'voiceid': 'Amy',
            }
        )
    except Exception as e:
        logger.error('Failed to request TTS: {}'.format(e))
        return


if __name__ == '__main__':

    load_playlist()
    do_light_stuff()
    turn_on_light()
    forecast()
    logger.info('done')
