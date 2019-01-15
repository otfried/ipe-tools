%global majorversion 7.2

Name:           ipe
Version:        7.2.8
Release:        1
Summary:        The Ipe extensible drawing editor
Group:          Applications/Publishing
# GPLv2, with an exception for the CGAL libraries.
License:        GPLv2+ with exceptions
URL:            http://ipe.otfried.org/
Source0:	%{name}-%{version}-src.tar.gz

BuildRequires:	qt5-qtbase-devel
BuildRequires:  desktop-file-utils
BuildRequires:  pkgconfig
BuildRequires:  lua-devel >= 5.2
BuildRequires:  cairo-devel
BuildRequires:	libjpeg-devel

Requires:       tex(latex)
Requires:       xdg-utils

Provides:       ipe(api) = %{version}
Provides:       ipetoipe = %{version}
Provides:       iperender = %{version}

%description
Ipe is a drawing editor for creating figures in PDF format.  It
supports making small figures for inclusion into LaTeX-documents as
well as making multi-page PDF presentations.

%prep
%setup -n %{name}-%{version} -q

# fix files permissions
find src -type f -exec chmod -x {} +

%build
## !! make sure IPELIBDIR and IPELETDIR can be overridden!
export IPEPREFIX="%{_usr}"
export IPELIBDIR="%{_libdir}"
export IPELETDIR="$(IPELIBDIR)/ipe/$(IPEVERS)/ipelets"

export QT_SELECT=qt5
export MOC=moc-qt5
export LUA_PACKAGE=lua
#export LUA_CFLAGS=`pkg-config --cflags lua`
#export LUA_LIBS=`pkg-config --libs lua`

pushd src
make %{_smp_mflags}
popd 

%install
export IPEPREFIX="%{_usr}"
export IPELIBDIR="%{_libdir}"
export IPELETDIR="$(IPELIBDIR)/ipe/$(IPEVERS)/ipelets"
pushd src
make INSTALL_ROOT=$RPM_BUILD_ROOT install \
     INSTALL_PROGRAMS="install -m 0755"
popd

%post -p /sbin/ldconfig

%postun -p /sbin/ldconfig

%files
%license gpl.txt
%doc readme.txt gpl.txt news.txt

%{_bindir}/ipe
%{_bindir}/ipe6upgrade
%{_bindir}/ipeextract
%{_bindir}/iperender
%{_bindir}/ipescript
%{_bindir}/ipetoipe

%{_libdir}/libipe.so.%{version}
%{_libdir}/libipeui.so.%{version}
%{_libdir}/libipecairo.so.%{version}
%{_libdir}/libipecanvas.so.%{version}
%{_libdir}/libipelua.so.%{version}

%dir %{_libdir}/ipe
%dir %{_libdir}/ipe/%{version}
%dir %{_libdir}/ipe/%{version}/ipelets
%{_libdir}/ipe/%{version}/ipelets

%dir %{_datadir}/ipe
%dir %{_datadir}/ipe/%{version}
%{_datadir}/ipe/%{version}/icons
%{_datadir}/ipe/%{version}/lua
%{_datadir}/ipe/%{version}/styles
%{_datadir}/ipe/%{version}

%{_mandir}/man1/ipe.1.gz
%{_mandir}/man1/ipe6upgrade.1.gz
%{_mandir}/man1/ipeextract.1.gz
%{_mandir}/man1/iperender.1.gz
%{_mandir}/man1/ipescript.1.gz
%{_mandir}/man1/ipetoipe.1.gz

%{_includedir}/*.h

%changelog
* Tue Jan 15 2019 Otfried Cheong <otfried@ipe.otfried.org> - 7.2.8-1
- First try to build Ipe RPMs on openSuse build service.
