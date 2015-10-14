#!/usr/bin/env bash

p=$HOME/predictor

case "$1" in
	start)
		screen -dmS modeler python3 $p/modeler/modeler.py
		;;

	stop)
		screen -XS modeler quit
		;;

	restart)
		screen -XS modeler quit
		screen -dmS modeler python3 $p/modeler/modeler.py
		;;

	*)
		echo "Usage: $0 {start|stop|restart}" >&2
		exit 3
		;;
esac
