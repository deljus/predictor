#!/bin/sh
# Start/stop pmapper/pmodeler

PIDFILE=/var/run/pmapper.pid

. /lib/lsb/init-functions

NAME=`basename $0`
RUN_AS=`id -u predictor`
CMD=/home/www/predictor/SETUP/$NAME
OPTS=

do_start() {
    start-stop-daemon --start --background --user $RUN_AS --pidfile $PIDFILE --chuid $RUN_AS --startas $CMD -- $OPTS
}

do_stop() {
    start-stop-daemon --stop --user $RUN_AS
}

case "$1" in
start)
    log_action_msg "Starting $NAME"
    do_start
        ;;
stop)
    log_action_msg "Stopping $NAME"
    do_stop
    ;;
restart)
    log_action_msg "Restarting $NAME"
    do_stop
    do_start
    ;;
*)
    log_action_msg "Usage: /etc/init.d/rhodecode {start|stop|restart}"
    exit 2
    ;;
esac
exit 0