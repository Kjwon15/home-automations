#!/usr/bin/env python3

import subprocess
import sys
import time

import redis

try:
    from subprocess import DEVNULL
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')

try:
    conn = redis.StrictRedis(host='sakura.lan', socket_timeout=2)
    last_seen = conn.hget('kjwon15', 'lastseen')
    if last_seen:
        last_seen = float(last_seen)
        now = time.time()
        if now - last_seen < 5 * 60:
            exit(0)
except Exception as e:
    print("Redis check failed: {}".format(e), file=sys.stderr)

p = subprocess.Popen(
    ['ping', '-c1', '-W1', 'n5x.lan'],
    stdout=DEVNULL,
    stderr=DEVNULL)

return_code = p.wait()
if return_code == 0:
    exit(0)

exit(1)
