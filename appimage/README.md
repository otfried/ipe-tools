# Ipe AppImage recipe

This is a recipe for building an [AppImage](http://appimage.org/) for
Ipe, based on the [fantastic work of Thomas
Leitz](https://github.com/unruhschuh/Ipe.AppImage) - I only tinkered
with a few details.

Ipe requires `pdflatex` to be installed in order to render text
elements. It is not included in the AppImage so you need to have a
LaTeX distribution installed on your system. You can find informations
about LaTeX and how to install it at
https://www.tug.org/[www.tug.org].


## Download

* [Download](https://bintray.com/otfried/generic/ipe#files/ipe) the
  latest AppImage for Ipe

* Make the AppImage executable, e.g. in the terminal run
  `chmod a+x Ipe-x.y.z-x86_64.AppImage`


## How to use it

* To start Ipe, just click on the AppImage file.

* You can also start Ipe from the command line by executing the AppImage:
```
$ ./Ipe-7.2.6-x86_64.AppImage
```

* If you want to use the Ipe command line tools, such as `ipetoipe`, `iperender`, `ipescript`, just prefix the command with the AppImage:
```
$ ./Ipe-7.2.6-x86_64.AppImage ipetoipe -pdf test.ipe
```


## How to create an AppImage for Ipe

The AppImage for Ipe is created inside a fresh installation of CentOS
6.7. In order to build the AppImage follow these steps

* Install CentOS 6.7 either on a PC or inside VirtualBox or any other virtualization program. 

* Start the Terminal and run `git clone https://github.com/otfried/ipe-tools`

* Change directory with `cd ipe-tools/appimage`

* Download and created needed tools with `./setup.sh`.

* Start compilation and packaging process with `./recipe.sh`.
  This creates `Ipe.AppImage` inside the current directory.

