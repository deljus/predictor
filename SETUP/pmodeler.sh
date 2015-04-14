#!/usr/bin/env bash

p=$HOME/predictor

case "$1" in
	start)
		screen -dmS modeler python3 $p/modeler/modeler.py
		;;

	stop)
		screen -XS modeler quit
		;;

	*)
		echo "Usage: $0 {start|stop}" >&2
		exit 3
		;;
esac