#!/usr/bin/env bash

p=$HOME/predictor

case "$1" in
	start)
		screen -dmS mapper python3 $p/mapper/mapper.py
		;;

	stop)
		screen -XS mapper quit
		;;

	*)
		echo "Usage: $0 {start|stop}" >&2
		exit 3
		;;
esac