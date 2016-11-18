# Ipe AppImage recipe

This is a recipe for building an [AppImage](http://appimage.org/) for
Ipe, based on the [fantastic work of Thomas
Leitz](https://github.com/unruhschuh/Ipe.AppImage) - I only tinkered
with a few details and added the Voronoi ipelet and pdftoipe.

Ipe requires `pdflatex` to be installed in order to render text
elements. It is not included in the AppImage so you need to have a
LaTeX distribution installed on your system. You can find informations
about LaTeX and how to install it at
[www.tug.org](https://www.tug.org/).


## Download

* [Download](https://bintray.com/otfried/generic/ipe#files/ipe) the
  latest AppImage for Ipe

* Make the AppImage executable, e.g. in the terminal run
  `chmod a+x ipe-x.y.z-x86_64.AppImage`


## How to use the Ipe AppImage

* To start Ipe, just click on the AppImage file.

* You can also start Ipe from the command line by executing the AppImage:
```
$ ./ipe-7.2.6-x86_64.AppImage
```

* If you want to use the Ipe command line tools, such as `ipetoipe`, `iperender`, `ipescript`, just prefix the command with the AppImage:
```
$ ./ipe-7.2.6-x86_64.AppImage ipetoipe -pdf ~/test.ipe
```

* If you want to start Ipe with a command line argument, proceed as for the tools: 
```
$ ./ipe-7.2.6-x86_64.AppImage ipe -sheet presentation ~/mytalk.pdf
```

Note that you will have to use **absolute filenames** in the arguments
to the command line tools, because the AppImage changes directory
before executing the code.


## How to create an AppImage for Ipe

The AppImage for Ipe is created inside a fresh installation of CentOS
6.7. In order to build the AppImage follow these steps

* Install CentOS 6.7 either on a PC or inside VirtualBox or any other
  virtualization program.

* Start the Terminal and run `git clone https://github.com/otfried/ipe-tools`

* Change directory with `cd ipe-tools/appimage`

* Download and compile the needed tools and libraries with
  `./setup.sh`.

* Start Ipe compilation and packaging process with `./recipe.sh`.
  This creates `ipe-7.x.y-x86_64.AppImage` inside the current directory.

