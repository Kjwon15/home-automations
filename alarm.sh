#!/bin/bash
path=`dirname $(readlink -e $0)`
cd $path

if [ -e /tmp/snooze ]; then
    rm /tmp/snooze
    exit
fi

./check_phone.py || exit 1

./alarm.py
