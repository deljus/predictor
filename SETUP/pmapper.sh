#!/usr/bin/env bash

p=$HOME/predictor

case "$1" in
	start)
		screen -dmS mapper python3 $p/mapper/mapper.py
		;;

	stop)
		screen -XS mapper quit
		;;

	restart)
		screen -XS mapper quit
		screen -dmS mapper python3 $p/mapper/mapper.py
		;;

	*)
		echo "Usage: $0 {start|stop|restart}" >&2
		exit 3
		;;
esac