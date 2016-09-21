
= AppImage for Ipe

Here you will find http://appimage.org/[AppImages] for http://ipe.otfried.org/[Ipe].
Please let me know if you have any problems with running Ipe using the AppImages offered on this site: thomas.leitz@web.de.

Ipe requires `pdflatex` to be installed in order to render text elements. It is not included in the AppImage so you need to have a LaTeX distribution installed on your system. You can find informations about LaTeX and how to install it at https://www.tug.org/[www.tug.org].

== Download

* https://bintray.com/unruhschuh/AppImages/Ipe/view#files[Download] the latest AppImage for Ipe
* Make the AppImage executable, e.g. in the terminal run `chmod a+x Ipe-x.y.z.AppImage`

== How to create an AppImage for Ipe

The AppImage for Ipe is created inside a fresh installation of CentOS 6.7. In order to build the AppImage follow these steps

* Install CentOS 6.7 either on a PC or inside VirtualBox or any other virtualization program. Using 'testappimage' of AppImageKit also works, but there are issues with dbus.
* Start the Terminal and run `git clone https://github.com/unruhschuh/Ipe.AppImage`
* Change directory with `cd Ipe.AppImage`
* Start compilation and packaging process with `./recipe.sh`. This creates `Ipe.AppImage` inside the current directory.

== Known issues

* The command line tools like `ipetoipe` won't work this way. There would have to be an AppImage for each of the tools. Maybe in a future release. Another approach would be to use `startipe.sh` to allow parameters to start these tools.

