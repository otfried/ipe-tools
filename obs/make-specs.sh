#
# Produce ipe.dsc and ipe_x.y.z-d.debian.tar.xz
#
# To create a new version, update IPEVERS below and add a new entry in debian/changelog
# Then run bash make-specs.sh, and upload the three files to build.opensuse.org

IPEVERS="7.2.19"
DEBVERS="1"

SOURCES=~/ipe-$IPEVERS-src.tar.gz

ORIGFILE=ipe_$IPEVERS.orig.tar.gz
DEBFILE=ipe_$IPEVERS-${DEBVERS}.debian.tar.xz
DSCFILE=ipe.dsc

rm -f $ORIGFILE $DEBFILE $DSCFILE

tar cJvf $DEBFILE debian
cat <<EOF > $DSCFILE
Format: 3.0 (quilt)
Source: ipe
EOF

echo "Version: $IPEVERS-$DEBVERS" >> $DSCFILE

cat <<EOF >> $DSCFILE
Binary: ipe
Maintainer: Otfried Cheong <ipe@otfried.org>
Architecture: any
Homepage: http://ipe.otfried.org/
Build-Depends: sharutils, debhelper (>= 9~), zlib1g-dev, qtbase5-dev, qtbase5-dev-tools, libfreetype6-dev, libcairo2-dev, libjpeg-dev, libpng-dev, liblua5.3-dev, libgsl-dev, libcurl4-openssl-dev, libfontconfig1-dev
Files:
EOF

cp $SOURCES $ORIGFILE
orig1=`md5sum $ORIGFILE | cut -d" " -f1`
orig2=`stat --printf="%s" $ORIGFILE`
deb1=`md5sum $DEBFILE | cut -d" " -f1`
deb2=`stat --printf="%s" $DEBFILE`

echo "" $orig1 $orig2 $ORIGFILE >> $DSCFILE
echo "" $deb1 $deb2 $DEBFILE >> $DSCFILE
