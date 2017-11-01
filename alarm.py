#!/usr/bin/env python3

import os
import sched
import sys
import socket
import time
import logging
import logging.config

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

DURATION = 60 * 3 + 46
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
        b'play\n'
        b'command_list_end\n'
        b'close\n'
    )
    logger.debug(sock.recv(4096).decode())
    sock.close()


def do_light_stuff():
    # Light time!
    logger.info('yeelight time')
    session.put(YEELIGHT_HOST + '/switch')
    scheduler = sched.scheduler(time.time, time.sleep)
    steps = DURATION // INTERVAL


    def set_light(**kwargs):
        logger.info('Set light {}'.format(kwargs))
        session.post(
            YEELIGHT_HOST + '/light',
            data=kwargs
        )


    def turn_off_yeelight():
        session.delete(YEELIGHT_HOST + '/switch')


    for step in range(steps):
        temp = int(MIN_TEMP + ((MAX_TEMP - MIN_TEMP) * (step / steps)))
        brightness = int(100 * step / steps)
        scheduler.enter(step * INTERVAL, 1, set_light, kwargs={
            'temp': temp,
            'brightness': brightness,
        })
    scheduler.enter(DURATION, 1, turn_off_yeelight)

    scheduler.run()

if __name__ == '__main__':

    load_playlist()
    do_light_stuff()
    turn_on_light()
    logger.info('done')

