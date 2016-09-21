#!/bin/bash
# 
# Download and install all prerequisites for making the Ipe AppImage
#

# Halt on errors
set -e

######################################################
# install packages
######################################################
# epel-release for newest Qt and stuff
sudo yum -y install epel-release
sudo yum -y install readline-devel zlib-devel cairo-devel
sudo yum -y install cmake binutils fuse glibc-devel glib2-devel fuse-devel gcc zlib-devel # AppImageKit dependencies
sudo yum -y install poppler-devel

# Need a newer gcc, getting it from Developer Toolset 2
sudo wget http://people.centos.org/tru/devtools-2/devtools-2.repo -O /etc/yum.repos.d/devtools-2.repo
sudo yum -y install devtoolset-2-gcc devtoolset-2-gcc-c++ devtoolset-2-binutils
# /opt/rh/devtoolset-2/root/usr/bin/gcc
# now holds gcc and c++ 4.8.2
#scl enable devtoolset-2
source /opt/rh/devtoolset-2/enable

######################################################
# Install Qt
######################################################
#wget http://download.qt.io/official_releases/online_installers/qt-unified-linux-x86-online.run
#chmod +x qt-unified-linux-x86-online.run
#./qt-unified-linux-x86-online.run --script qt-installer-noninteractive.qs
# wget http://download.qt.io/official_releases/qt/5.5/5.5.1/qt-opensource-linux-x64-5.5.1.run
# chmod +x qt-opensource-linux-x64-5.5.1.run
# ./qt-opensource-linux-x64-5.5.1.run --script qt-installer-noninteractive.qs

sudo yum -y install qt5-qtbase-devel qt5-qtbase-gui
# qt5-qtlocation-devel qt5-qtscript-devel qt5-qtwebkit-devel qt5-qtsvg-devel qt5-linguist qt5-qtconnectivity-devel

######################################################
# build libraries from source
######################################################
# Change directory to build. Everything happens in build.
mkdir build
cd build

# libjpeg
wget http://www.ijg.org/files/jpegsrc.v8d.tar.gz
tar xfvz jpegsrc.v8d.tar.gz
cd jpeg-8d
./configure && make && sudo make install
cd ..

# lua
wget http://www.lua.org/ftp/lua-5.3.3.tar.gz
tar xfvz lua-5.3.3.tar.gz
cd lua-5.3.3/src
#sed -i 's/^CFLAGS=/CFLAGS= -fPIC /g' Makefile
cd ..
make linux CFLAGS="-fPIC" 
sudo make install
cd ..

# libpng
wget http://download.sourceforge.net/libpng/libpng-1.6.21.tar.gz
tar xfvz libpng-1.6.21.tar.gz
cd libpng-1.6.21
./configure
make check
sudo make install
cd ..

# qhull
wget http://www.qhull.org/download/qhull-2015-src-7.2.0.tgz
tar xfvz qhull-2015-src-7.2.0.tgz
cd qhull-2015.2
make
sudo install -d /usr/local/include/qhull
sudo install -m 0644 src/libqhull/*.h /usr/local/include/qhull
sudo install -m 0755 lib/libqhullstatic.a /usr/local/lib
cd ..

######################################################
# Build AppImageKit (into top level)
######################################################

cd ..
git clone https://github.com/probonopd/AppImageKit.git
cd AppImageKit/
cmake .
make clean
make

######################################################
