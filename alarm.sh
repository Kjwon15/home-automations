#!/bin/bash
path=`dirname $(readlink -e $0)`
cd $path

eval "$(~/.pyenv/bin/pyenv init -)"

if [ -e /tmp/snooze ]; then
    rm /tmp/snooze
    exit
fi

if ! ./check_phone.py; then
    echo "Phone is not alive"
    exit 1
fi

# Ping to light service
curl -qs -XGET http://tsubaki.lan:31337/light > /dev/null

./alarm.py
