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

try:
    from subprocess import DEVNULL
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('--mpd-host', default='localhost')
arg_parser.add_argument('--mpd-port', type=int, default=6600)
arg_parser.add_argument('--mpd-password')
arg_parser.add_argument('--interval', type=int, default=10)
arg_parser.add_argument('--timeout', type=int, default=300)
arg_parser.add_argument('-v', '--verbose', action='store_true')
arg_parser.add_argument('-l', '--log-file', help='Log file')
arg_parser.add_argument('--redis-target', help='Target key for wifi-monitor.')
arg_parser.add_argument('--ping-target', help='Target hostname for ping.')



class MpdManager():

    def __init__(self, interval, timeout,
                 host='localhost', port=6600, password=None,
                redis_target=None, ping_target=None):
        self.redis_target = redis_target
        self.ping_target = ping_target
        self.interval = interval
        self.timeout = timeout
        self.host = host
        self.port = port
        self.password = password
        self.redis = redis.StrictRedis('asakura.lan', socket_timeout=2)
        self.logger = logging.getLogger('MpdManager')

        self.prev_on = True
        self.last_on = time.time()

        self.connect()

    def connect(self):
        self.logger.info('Connecting MPD')
        self.mpd = MPDClient()
        self.mpd.connect(self.host, self.port)
        if self.password:
            self.mpd.password(self.password)

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

            self.logger.debug('{}, {}'.format(
                last_seen,
                difference))

            if difference < self.timeout:
                if not self.prev_on:
                    self.on_connected()
                    self.prev_on = True
            else:
                self.on_disconnected()
                self.prev_on = False

            if last_seen:
                self.last_on = last_seen

            time.sleep(self.interval)

    def on_connected(self):
        self.check_mpd_connection()

        if self.mpd.status()['state'] == 'play':
            return

        if (time.time() - self.last_on) <= (4 * 60 * 60):
            self.logger.info('Start music')
            self.mpd.play()
        else:
            self.logger.info('Clear and start music')
            self.mpd.command_list_ok_begin()
            self.mpd.clear()
            self.mpd.setvol(70)
            self.mpd.load('streaming')
            self.mpd.play()
            self.mpd.command_list_end()


        try:
            requests.post('http://kimidori.lan:31337/switch', {'switch': 'on'})
            time.sleep(0.5)
            requests.post('http://kimidori.lan:31337/light', {
                'brightness': 50,
                'warm': 0.4,
            })
        except Exception as e:
            self.logger.error(str(e))

    def on_disconnected(self):
        self.check_mpd_connection()

        if self.mpd.status()['state'] == 'play':
            self.logger.info('Stop music')
            self.mpd.stop()

        if self.prev_on:
            try:
                requests.post('http://kimidori.lan:31337/switch',
                              {'switch': 'off'})
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
            try:
                last_seen = self.redis.hget(self.redis_target, 'lastseen')
                if last_seen:
                    last_seen = float(last_seen)
                    self.logger.debug('Redis {}'.format(last_seen))
                    return last_seen
            except:
                pass

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

    manager = MpdManager(args.interval, args.timeout,
                         args.mpd_host, args.mpd_port, args.mpd_password,
                         redis_target=args.redis_target,
                         ping_target=args.ping_target)
    manager.run()
