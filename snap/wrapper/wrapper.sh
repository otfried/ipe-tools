#!/bin/sh
export PATH="$SNAP/texlive/bin/x86_64-linux:$PATH"
export TEXMFHOME="$SNAP_USER_COMMON/texmf"
export IPELATEXDIR="$SNAP_USER_DATA/latexrun"
export IPELETPATH="$SNAP_USER_COMMON/ipelets:_"
export IPESTYLES="$SNAP_USER_COMMON/styles:_"
exec "$@"
