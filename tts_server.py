import datetime
import hashlib
import os
from os import path
import random
import subprocess
import sys
import time

import appdirs
from boto3 import client
import pyaudio

from flask import Flask, request

app = Flask(__name__)

audio = pyaudio.PyAudio()
audio_output = audio.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=16000,
    output=True)

polly = client('polly', region_name='ap-northeast-2')

voice_map = {
    ('en-US', 'female'): {'Ivy', 'Joanna', 'Kendra', 'Kimberly', 'Sali'},
    ('en-US', 'male'): {'Joey', 'Justin', 'Matthew'},
    ('en-GB', 'female'): {'Amy', 'Emma'},
    ('en-GB', 'male'): {'Brian'},
    ('ko-KR', 'female'): {'Seoyeon'},
    ('ko-KR', 'male'): set(),
    ('ja-JP', 'female'): {'Mizuki'},
    ('ja-JP', 'male'): {'Takumi'},
}

cache_dir = appdirs.user_cache_dir('tts_server', 'kjwon15')
if not path.exists(cache_dir):
    os.mkdir(cache_dir)


def is_valid(filename):
    now = time.time()
    return (
        path.exists(filename)
        and now - os.path.getmtime(filename) <
        datetime.timedelta(days=7).total_seconds()

    )


def get_param(name):
    data = request.json or request.form
    return data.get(name, None)


@app.route('/tts', methods=['POST'])
def tts():
    msg = get_param('msg')
    voice_id = get_param('voiceid')

    if voice_id is None:
        lang = get_param('lang')
        gender = get_param('gender')

        if gender:
            voice_id = random.choice(list(
                voice_map[(lang, gender)]
            ))
        else:
            voice_id = random.choice(list(
                voice_map[(lang, 'female')] |
                voice_map[(lang, 'male')]
            ))

    filename = path.join(
        cache_dir,
        hashlib.md5('{}:{}'.format(msg, voice_id).encode('utf-8')).hexdigest()
    )

    if not is_valid(filename):
        try:
            response = polly.synthesize_speech(
                Text=msg,
                OutputFormat='mp3',
                VoiceId=voice_id)
            with open(filename, 'wb') as fp:
                fp.write(response['AudioStream'].read())
        except Exception as e:
            print(e, file=sys.stderr)
            return str(e)

    subprocess.Popen(['mpg321', '-q', '-g120', filename]).wait()

    return 'OK'
