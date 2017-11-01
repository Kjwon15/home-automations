import datetime
import functools
import hashlib
from multiprocessing.pool import Pool
import os
from os import path
import subprocess
import time

import appdirs
from flask import Flask, request
import requests

API_URL = 'https://api.voicerss.org/'
API_KEY = '80b6bc3bffb3432caf35b54b5078e2e3'

app = Flask(__name__)

pool = Pool()
cache_dir = appdirs.user_cache_dir('tts_server', 'kjwon15')
if not path.exists(cache_dir):
    os.mkdir(cache_dir)


def get_param(name):
    data = request.json or request.form
    return data.get(name, None)


def async(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        return pool.apply_async(f, args, kwargs)

    return wrapped


def is_valid(filename):
    now = time.time()
    return (
        os.path.exists(filename)
        and now - os.path.getmtime(filename) <
        datetime.timedelta(days=7).total_seconds()
    )


# @async
def speak(msg, lang='en-us', rate=0):
    filename = os.path.join(
        cache_dir,
        hashlib.md5('{msg}:{lang}:{rate}'.format(
            msg=msg, lang=lang, rate=rate).encode('utf-8')).hexdigest())
    if is_valid(filename):
        subprocess.Popen(['mpg321', '-q', '-g120', filename])
    else:
        try:
            resp = requests.post(API_URL, {
                'key': API_KEY,
                'src': msg,
                'hl': lang,
                'f': '44khz_16bit_mono',
                'r': rate,
            })
            if resp.headers['Content-Type'].startswith('text'):
                raise Exception('API error')
            with open(filename, 'wb') as fp:
                fp.write(resp.content)
        except Exception as e:
            print(e)
        else:
            print(msg)
            subprocess.Popen(['mpg321', '-q', '-g120', filename])


@app.route('/tts', methods=['POST'])
def tts():
    lang = get_param('lang')
    msg = get_param('msg')
    rate = get_param('rate')

    speak(msg, lang, rate)

    return 'OK'
