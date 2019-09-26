#!/bin/bash

BASEDIR="$(dirname $0)"

if [ -d $HOME/.pyenv/bin ]; then
    export PATH="/home/kjwon15/.pyenv/bin:$PATH"
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
fi

export PYENV_VERSION="home-auto"

cd "$BASEDIR"

exec python ${BASEDIR}/phone-scanner.py --ping-target=pixel2.lan --redis-target=kjwon15 $@
