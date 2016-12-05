#!/bin/bash

BASEDIR="$(dirname $0)"

if [ -d $HOME/.pyenv/bin ]; then
    export PATH="/home/kjwon15/.pyenv/bin:$PATH"
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
fi

export PYENV_VERSION="home-auto"

exec python ${BASEDIR}/phone-scanner.py --mpd-password=derkuchen --ping-target=n5x.lan --redis-target=kjwon15
