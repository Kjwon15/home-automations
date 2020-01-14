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
YEELIGHT_HOST = 'http://sakura.lan:31337/'
TTS_HOST = 'http://sakura.lan:1775/'

MIN_TEMP = 1700
MAX_TEMP = 4500  # 6500 isn't pretty

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


def load_playlist(name, clear=False):
    logger.info('Load playlist')
    sock = socket.socket()
    try:
        sock.connect((MPD_HOST, MPD_PORT))
        if MPD_PASSWORD:
            sock.send('password {}\n'.format(MPD_PASSWORD).encode())

        sock.send((
            'command_list_begin\n'
            + ((
                'setvol 80\n'
                'clear\n'
            ) if clear else '') +
            f'load {name}\n'
            'consume 1\n'
            + (
                'play 0\n'
                if clear else '') +
            'command_list_end\n'
            'close\n'
            ).encode('utf-8')
        )
        logger.debug(sock.recv(4096).decode())
    except Exception as e:
        logger.warning(f'Failed to connect to MPD: {e}')
    finally:
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
        brightness = int(1 + 99 * step / steps)
        scheduler.enter(step * INTERVAL, 1, set_light, kwargs={
            'temp': temp,
            'brightness': brightness,
        })
    scheduler.enter(DURATION, 1, turn_off_yeelight)

    scheduler.run()


def forecast():
    def format_temp(temp):
        if temp < 0:
            value = abs(temp)
            return f'영하 {value:.1f}'
        return f'{temp:.1f}'

    try:
        data = requests.get(
                'https://api.darksky.net/forecast/f9ea8e29d0209855ff9e675cedc2e885/'
                '37.5413512,127.0873911?units=si'
        ).json()
        todays = data['daily']['data'][0]
        summary = todays['summary']
        temp_cur = data['currently']['temperature']
        temp_max = todays['temperatureMax']
        temp_min = todays['temperatureMin']

        msg = (
            f"Today's forecast is {summary}\n"
            f'The highest temperature is {temp_max:.1f} '
            f'and the lowest is  {temp_min:.1f}, '
            f'Currently {temp_cur:.1f} degrees celsius.')

        requests.post(
            'http://sakura.lan:1775/tts', json={
                'msg': msg,
                'voiceid': 'Amy',
            }
        )
    except Exception as e:
        logger.error('Failed to forecast {}'.format(e))


if __name__ == '__main__':

    load_playlist('alarm', clear=True)
    do_light_stuff()
    turn_on_light()
    forecast()
    load_playlist('morning')
    logger.info('done')
