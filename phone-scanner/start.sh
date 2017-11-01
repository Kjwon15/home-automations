#!/bin/bash

BASEDIR="$(dirname $0)"

exec python ${BASEDIR}/phone-scanner.py --ping-target=n5x.lan --redis-target=kjwon15
