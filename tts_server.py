import functools
import hashlib
import os
import subprocess
from os import path
from multiprocessing.pool import Pool

import appdirs
import requests
from flask import Flask, request, jsonify

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


# @async
def speak(msg, lang='en-us', rate=0):
    filename = os.path.join(
        cache_dir,
        hashlib.md5('{msg}:{lang}:{rate}'.format(
            msg=msg, lang=lang, rate=rate).encode('utf-8')).hexdigest())
    if os.path.exists(filename):
        subprocess.Popen(['mpg321', '-q', '-g120', filename])#.wait()
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
            subprocess.Popen(['mpg321', '-q', '-g120', filename])#.wait()


@app.route('/tts', methods=['POST'])
def tts():
    lang = get_param('lang')
    msg = get_param('msg')
    rate = get_param('rate')

    speak(msg, lang, rate)

    return 'OK'
