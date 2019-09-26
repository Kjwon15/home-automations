#!/bin/bash

BASEDIR="$(dirname "$0")"

cd "$BASEDIR"

exec python3 ./random_pl_album.py -d
