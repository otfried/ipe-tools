#!/bin/bash --posix
# This should be run outside the snap,
# as the Perl in the snap is incomplete and cannot execute tlmgr.pl

findSnap() {
    local source="${BASH_SOURCE[0]}"
    while [ -h "$source" ] ; do
	local linked="$(readlink "$source")"
	local dir="$(cd -P $(dirname "$source") && cd -P $(dirname "$linked") && pwd)"
	source="$dir/$(basename "$linked")"
    done
    (cd -P "$(dirname "$source")/.." && pwd)
}

export SNAP="$(findSnap)"

export TEXMFHOME=$HOME/snap/ipe/common/texmf

TLMGR="$SNAP/texlive/bin/x86_64-linux/tlmgr"

#echo "SNAP is $SNAP"
#echo "TEXMFHOME is $TEXMFHOME"

if [ ! -d "$TEXMFHOME" ]; then
    echo "Creating personal texlive tree..."
    mkdir -p "$TEXMFHOME"
    perl $TLMGR init-usertree --usermode
fi

perl $TLMGR $@ --usermode
