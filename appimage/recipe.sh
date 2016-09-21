#!/bin/bash

# Halt on errors
set -e

#scl enable devtoolset-2
source /opt/rh/devtoolset-2/enable

BASE=`pwd`

APP=Ipe
APP_DIR=$BASE/$APP.AppDir
APP_IMAGE=$BASE/$APP.AppImage

# Cleanup 
rm -fr build
rm -fr $APP_DIR

######################################################
# create AppDir
######################################################
mkdir $APP_DIR
mkdir -p $APP_DIR/usr/bin/platforms
mkdir -p $APP_DIR/usr/lib/qt5

# Change directory to build. Everything happens in build.
mkdir -p build
cd build

######################################################
# Build Ipe
######################################################

wget https://dl.bintray.com/otfried/generic/ipe/7.2/ipe-7.2.6-src.tar.gz
tar xfvz ipe-7.2.6-src.tar.gz

cd ipe-7.2.6/src

export QT_SELECT=5
export MOC=moc-qt5
# use libpng16
export PNG_CFLAGS="-I\/usr\/local\/include\/libpng16"
export PNG_LIBS="-lpng16"
export LUA_CFLAGS="-I/usr/local/include"
export LUA_LIBS="-L/usr/local/lib -llua -lm"

export IPEPREFIX=$APP_DIR/usr

make IPEAPPIMAGE=1
make install IPEAPPIMAGE=1

######################################################
# Populate Ipe.AppDir
######################################################

cd $BASE

cp AppImageKit/AppRun $APP_DIR
cp ipe.png $APP_DIR
cp Ipe.desktop $APP_DIR
cp startipe.sh $APP_DIR/usr/bin
cp appimage.lua $APP_DIR/usr/ipe/ipelets

cp -R /usr/lib64/qt5/plugins $APP_DIR/usr/lib/qt5/
cp $APP_DIR/usr/lib/qt5/plugins/platforms/libqxcb.so $APP_DIR/usr/bin/platforms/

set +e
ldd $APP_DIR/usr/lib/qt5/plugins/platforms/libqxcb.so | grep "=>" | awk '{print $3}' | xargs -I '{}' cp -v '{}' $APP_DIR/usr/lib
ldd $APP_DIR/usr/bin/* | grep "=>" | awk '{print $3}' | xargs -I '{}' cp -v '{}' $APP_DIR/usr/lib 
find $APP_DIR/usr/lib -name "*.so*" | xargs ldd | grep "=>" | awk '{print $3}' | xargs -I '{}' cp -v '{}' $APP_DIR/usr/lib

set -e

cp /usr/local/lib/libjpeg.so.8 $APP_DIR/usr/lib
cp /usr/local/lib/libpng16.so.16 $APP_DIR/usr/lib/

cp $(ldconfig -p | grep libEGL.so.1 | cut -d ">" -f 2 | xargs) $APP_DIR/usr/lib/ # Otherwise F23 cannot load the Qt platform plugin "xcb"

# this prevents "symbol lookup error libunity-gtk-module.so: undefined symbol: g_settings_new" on ubuntu 14.04
rm -f $APP_DIR/usr/lib/qt5/plugins/platformthemes/libqgtk2.so || true 
rmdir $APP_DIR/usr/lib/qt5/plugins/platformthemes || true # should be empty after deleting libqgtk2.so
rm -f $APP_DIR/usr/lib/libgio* || true # these are not needed if we don't use gtk

# Removed unused parts of Qt
rm -f $APP_DIR/usr/lib/libQt5PrintSupport.so.5 || true
rm -f $APP_DIR/usr/lib/libQt5Network.so.5 || true
rm -f $APP_DIR/usr/lib/libQt5Sql.so.5 || true

# Delete potentially dangerous libraries
rm -f $APP_DIR/usr/lib/libstdc* $APP_DIR/usr/lib/libgobject* $APP_DIR/usr/lib/libc.so.* || true

# The following are assumed to be part of the base system
rm -f $APP_DIR/usr/lib/libgtk-x11-2.0.so.0 || true # this prevents Gtk-WARNINGS about missing themes
rm -f $APP_DIR/usr/lib/libdbus-1.so.3 || true # this prevents '/var/lib/dbus/machine-id' error on fedora 22/23 live cd
rm -f $APP_DIR/usr/lib/libGL.so.* || true
rm -f $APP_DIR/usr/lib/libdrm.so.* || true
rm -f $APP_DIR/usr/lib/libxcb.so.1 || true
rm -f $APP_DIR/usr/lib/libX11.so.6 || true
rm -f $APP_DIR/usr/lib/libcom_err.so.2 || true
rm -f $APP_DIR/usr/lib/libcrypt.so.1 || true
rm -f $APP_DIR/usr/lib/libdl.so.2 || true
rm -f $APP_DIR/usr/lib/libexpat.so.1 || true
rm -f $APP_DIR/usr/lib/libfontconfig.so.1 || true
rm -f $APP_DIR/usr/lib/libgcc_s.so.1 || true
rm -f $APP_DIR/usr/lib/libglib-2.0.so.0 || true
rm -f $APP_DIR/usr/lib/libgpg-error.so.0 || true
rm -f $APP_DIR/usr/lib/libgssapi_krb5.so.2 || true
rm -f $APP_DIR/usr/lib/libgssapi.so.3 || true
rm -f $APP_DIR/usr/lib/libhcrypto.so.4 || true
rm -f $APP_DIR/usr/lib/libheimbase.so.1 || true
rm -f $APP_DIR/usr/lib/libheimntlm.so.0 || true
rm -f $APP_DIR/usr/lib/libhx509.so.5 || true
rm -f $APP_DIR/usr/lib/libICE.so.6 || true
rm -f $APP_DIR/usr/lib/libidn.so.11 || true
rm -f $APP_DIR/usr/lib/libk5crypto.so.3 || true
rm -f $APP_DIR/usr/lib/libkeyutils.so.1 || true
rm -f $APP_DIR/usr/lib/libkrb5.so.26 || true
rm -f $APP_DIR/usr/lib/libkrb5.so.3 || true
rm -f $APP_DIR/usr/lib/libkrb5support.so.0 || true
# rm -f $APP_DIR/usr/lib/liblber-2.4.so.2 || true # needed for debian wheezy
# rm -f $APP_DIR/usr/lib/libldap_r-2.4.so.2 || true # needed for debian wheezy
rm -f $APP_DIR/usr/lib/libm.so.6 || true
rm -f $APP_DIR/usr/lib/libp11-kit.so.0 || true
rm -f $APP_DIR/usr/lib/libpcre.so.3 || true
rm -f $APP_DIR/usr/lib/libpthread.so.0 || true
rm -f $APP_DIR/usr/lib/libresolv.so.2 || true
rm -f $APP_DIR/usr/lib/libroken.so.18 || true
rm -f $APP_DIR/usr/lib/librt.so.1 || true
rm -f $APP_DIR/usr/lib/libsasl2.so.2 || true
rm -f $APP_DIR/usr/lib/libSM.so.6 || true
rm -f $APP_DIR/usr/lib/libusb-1.0.so.0 || true
rm -f $APP_DIR/usr/lib/libuuid.so.1 || true
rm -f $APP_DIR/usr/lib/libwind.so.0 || true
rm -f $APP_DIR/usr/lib/libz.so.1 || true

# patch hardcoded '/usr/lib' in binaries away
find $APP_DIR/usr/ -type f -exec sed -i -e 's|/usr/lib|././/lib|g' {} \;

######################################################
# Create AppImage
######################################################
# Convert the AppDir into an AppImage
$BASE/AppImageKit/AppImageAssistant.AppDir/package $APP_DIR/ $APP_IMAGE
