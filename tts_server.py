import sys

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


def get_param(name):
    data = request.json or request.form
    return data.get(name, None)


@app.route('/tts', methods=['POST'])
def tts():
    msg = get_param('msg')
    voice_id = get_param('voiceid')

    try:
        response = polly.synthesize_speech(
            Text=msg,
            OutputFormat='pcm',
            VoiceId=voice_id)
        audio_output.write(response['AudioStream'].read())
    except Exception as e:
        print(e, file=sys.stderr)
        return str(e)
    else:
        return 'OK'
