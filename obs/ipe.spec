%global majorversion 7.2

Name:           ipe
Version:        7.2.12
Release:        1
Summary:        Extensible drawing editor
Group:          Productivity/Publishing/Presentation
License:        GPL-3.0-or-later
#License:        GNU General Public License v3.0 or later
URL:            http://ipe.otfried.org/
Source0:	%{name}-%{version}-src.tar.gz

BuildRequires:  desktop-file-utils
BuildRequires:  pkgconfig

BuildRequires:  zlib-devel
BuildRequires:	libjpeg-devel

BuildRequires:  pkgconfig(Qt5Core)
BuildRequires:  pkgconfig(Qt5Gui)
BuildRequires:  pkgconfig(Qt5Widgets)
BuildRequires:  pkgconfig(cairo) >= 1.10.0
BuildRequires:  pkgconfig(cairo-ft) >= 1.10.0
BuildRequires:  pkgconfig(cairo-pdf)
BuildRequires:  pkgconfig(cairo-ps)
BuildRequires:  pkgconfig(cairo-svg)
BuildRequires:  pkgconfig(freetype2)
BuildRequires:  pkgconfig(libpng)
BuildRequires:  pkgconfig(lua) >= 5.3

#Requires:       tex(latex)
#Requires:       xdg-utils

%description
A drawing editor for creating figures in PDF format.  It supports
making small figures for inclusion into LaTeX-documents as well as
making multi-page PDF presentations.

%package devel
Summary: Header files for writing Ipelets
Group: Development/Libraries/C and C++
Requires: %{name} = %{version}-%{release}
%description devel 
The header files necessary to link against ipelib.

%if 0%{?suse_version}
# Suse specific
%else
# Other distro
%endif

%prep
%setup -n %{name}-%{version} -q

sed -i 's#/usr/bin/env ipescript#/usr/bin/ipescript#' scripts/update-styles.lua
sed -i 's#/usr/bin/env ipescript#/usr/bin/ipescript#' scripts/update-master.lua
sed -i 's#/usr/bin/env ipescript#/usr/bin/ipescript#' scripts/add-style.lua

%build
export IPEPREFIX="%{_usr}"
export IPELIBDIR="%{_libdir}"
export IPELETDIR="%{_libdir}/ipe/%{version}/ipelets"

export QT_SELECT=qt5
export MOC=moc-qt5
export LUA_PACKAGE=lua

pushd src
make %{_smp_mflags}
popd 

%install
export IPEPREFIX="%{_usr}"
export IPELIBDIR="%{_libdir}"
export IPELETDIR="%{_libdir}/ipe/%{version}/ipelets"
pushd src
make INSTALL_ROOT=$RPM_BUILD_ROOT install \
     INSTALL_PROGRAMS="install -m 0755"
popd

%post -p /sbin/ldconfig

%postun -p /sbin/ldconfig

%files
%license gpl.txt
%doc readme.txt news.txt

%{_bindir}/ipe
%{_bindir}/ipepresenter
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

%{_libdir}/ipe/%{version}/ipelets

%dir %{_datadir}/ipe
%dir %{_datadir}/ipe/%{version}

%{_datadir}/ipe/%{version}/icons
%{_datadir}/ipe/%{version}/lua
%{_datadir}/ipe/%{version}/styles
%{_datadir}/ipe/%{version}/scripts
%{_datadir}/ipe/%{version}/doc

%{_mandir}/man1/ipe.1.gz
%{_mandir}/man1/ipe6upgrade.1.gz
%{_mandir}/man1/ipeextract.1.gz
%{_mandir}/man1/iperender.1.gz
%{_mandir}/man1/ipescript.1.gz
%{_mandir}/man1/ipetoipe.1.gz

%files devel
%{_includedir}/*.h
%{_libdir}/libipe.so
%{_libdir}/libipeui.so
%{_libdir}/libipecairo.so
%{_libdir}/libipecanvas.so
%{_libdir}/libipelua.so

%changelog
* Mon May 06 2019 Otfried Cheong <otfried@ipe.otfried.org> - 7.2.12-1
- New upstream version.

* Sun Mar 17 2019 Otfried Cheong <otfried@ipe.otfried.org> - 7.2.11-2
- Do not require tex in case user installed it differently.

* Sat Mar 09 2019 Otfried Cheong <otfried@ipe.otfried.org> - 7.2.11-1
- New upstream version.

* Mon Feb 04 2019 Otfried Cheong <otfried@ipe.otfried.org> - 7.2.10-1
- New upstream version.

* Wed Jan 16 2019 Otfried Cheong <otfried@ipe.otfried.org> - 7.2.9-1
- New upstream version.

* Tue Jan 15 2019 Otfried Cheong <otfried@ipe.otfried.org> - 7.2.8-1
- First try to build Ipe RPMs on openSuse build service.