#!/bin/bash
if [ -e /tmp/snooze ]; then
    rm /tmp/snooze
    exit
fi

./check_phone.py || exit 1

curl -XPUT http://omega2.lan:8000/switch/0


# SONGNAME="OST/Simon Viklund - PAYDAY 2 Official Soundtrack/Gustaf Grefberg - PAYDAY 2 Official Soundtrack - 01 Mayhem Dressed in a Suit.mp3"
SONGNAME="mixing/EDM/[Electro] - Noisestorm - Surge (Original Mix) [Monstercat EP Release].mp3"

PASSWORD=${MPD_HOST%@*}

nc localhost 6600 <<EOF >/dev/null
password $PASSWORD
command_list_begin
setvol 70
clear
addid "$SONGNAME" 0
load streaming
play 0
command_list_end
EOF
