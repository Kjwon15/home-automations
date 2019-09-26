#!/usr/bin/env python
import argparse
import time
import logging
import redis
import requests
import socket
import subprocess
from logging.handlers import RotatingFileHandler

from mpd import MPDClient, ConnectionError

import sys
sys.path.insert(1, '..')
import mpd_env  # noqa

MAIN_SWITCH = 'http://omega2.lan:8000/switch/0'
SUB_SWITCH = 'http://sakura.lan:31337/switch'

try:
    from subprocess import DEVNULL
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--interval', type=int, default=10)
arg_parser.add_argument('--timeout', type=int, default=300)
arg_parser.add_argument('--gap', type=int, default=(4 * 60 * 60))
arg_parser.add_argument('-v', '--verbose', action='store_true')
arg_parser.add_argument('-l', '--log-file', help='Log file')
arg_parser.add_argument('--redis-target', help='Target key for wifi-monitor.')
arg_parser.add_argument('--ping-target', help='Target hostname for ping.')


class MpdManager():

    def __init__(self, interval, timeout, gap,
                 host='localhost', port=6600, password=None,
                 redis_target=None, ping_target=None):
        self.redis_target = redis_target
        self.ping_target = ping_target
        self.interval = interval
        self.timeout = timeout
        self.gap = gap
        self.host = host
        self.port = port
        self.password = password
        self.redis = redis.StrictRedis()
        self.logger = logging.getLogger('MpdManager')
        self.is_mpd_on = False

        self.prev_on = True
        self.last_on = time.time()

        self.connect()

    def connect(self):
        self.logger.info('Connecting MPD')
        self.mpd = MPDClient()
        try:
            self.mpd.connect(self.host, self.port)
            if self.password:
                self.mpd.password(self.password)
            self.is_mpd_on = True
        except Exception as e:
            self.logger.debug(e)
            raise e
            self.logger.info('MPD disabled')
            self.is_mpd_on = False

    def check_mpd_connection(self):
        try:
            self.mpd.ping()
        except ConnectionError:
            self.connect()

    def run(self):
        while 1:
            # Multiple tests
            last_seen = max(filter(bool, (
                self.check_alive_ping(),
                self.check_alive_redis(),
                self.last_on,
            )))

            now = time.time()

            difference = now - last_seen

            self.logger.debug('Last seen: {} diff: {}'.format(
                last_seen,
                difference))

            if difference < self.timeout:
                if not self.prev_on:
                    self.on_connected()
                    self.prev_on = True
            else:
                if self.prev_on:
                    self.on_disconnected()
                    self.prev_on = False

            if last_seen:
                self.last_on = last_seen

            time.sleep(self.interval)

    def on_connected(self):
        self.logger.info('Connected')

        if self.is_mpd_on:
            self.check_mpd_connection()

            if (time.time() - self.last_on) <= self.gap:
                self.logger.info('Start music')
                self.mpd.play()
            else:
                self.logger.info('Over gap')
                self.mpd.command_list_ok_begin()
                self.mpd.clear()
                self.mpd.setvol(70)
                self.mpd.load('latest')
                self.mpd.play()
                self.mpd.command_list_end()

        try:
            requests.put(MAIN_SWITCH)
        except Exception as e:
            self.logger.error(str(e))

    def on_disconnected(self):
        self.logger.info('Disconnected')

        if self.is_mpd_on:
            self.check_mpd_connection()
            self.logger.info('Stop music')
            self.mpd.stop()

        for switch in (MAIN_SWITCH, SUB_SWITCH):
            try:
                requests.delete(switch)
            except Exception as e:
                self.logger.error(str(e))

    def check_alive_ping(self):
        p = subprocess.Popen(['ping', '-c1', '-W1', self.ping_target],
                             stdout=DEVNULL,
                             stderr=DEVNULL)
        return_code = p.wait()
        now = time.time()

        if return_code == 0:
            self.logger.debug('Ping {}'.format(now))
            self._last_ping_timestamp = now
            return self._last_ping_timestamp
        else:
            return getattr(self, '_last_ping_timestamp', None)

    def check_alive_redis(self):
            # subprocess.Popen(['ping', '-c1', '-W1', self.ping_target],
            #                  stdout=DEVNULL,
            #                  stderr=DEVNULL)
            last_seen = self.redis.hget(self.redis_target, 'lastseen')
            if last_seen:
                last_seen = float(last_seen)
                self.logger.debug('Redis {}'.format(last_seen))
                return last_seen
            else:
                return None


if __name__ == '__main__':
    args = arg_parser.parse_args()

    logging.basicConfig(
        datefmt='%y-%m-%d %H:%M:%S',
        format='%(asctime)s:%(levelname)s: %(message)s')

    if args.log_file:
        handler = RotatingFileHandler(args.log_file)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)


    logger = logging.getLogger('MpdManager')
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    logger.info(f'Using {mpd_env.MPD_HOST} {mpd_env.MPD_PORT} {mpd_env.MPD_PASSWORD}')

    manager = MpdManager(args.interval, args.timeout, args.gap,
                         mpd_env.MPD_HOST, mpd_env.MPD_PORT, mpd_env.MPD_PASSWORD,
                         redis_target=args.redis_target,
                         ping_target=args.ping_target)
    manager.run()
