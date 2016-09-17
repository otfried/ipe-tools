#!/bin/sh
SNAP="/snap/ipe/current"
COMMAND=$1
shift
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$SNAP/lib:$SNAP/usr/lib:$SNAP/lib/x86_64-linux-gnu:$SNAP/usr/lib/x86_64-linux-gnu"
exec $SNAP/bin/$COMMAND $@
