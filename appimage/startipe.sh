#!/bin/bash
CMD=$1
if [ "x${CMD}x" == "xx" ]; then
    ipe -style fusion "$@"
else
    shift
    $CMD "$@"
fi
