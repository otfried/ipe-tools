# Ipe in a snap

**Snappy** is a system that allows Linux systems to maintain
up-to-date versions of software, as is common under Windows and OSX,
see http://snapcraft.io.

It is available on recent Linux distributions such as Ubuntu 16.04,
etc.  You install the system by installing the **snapd** package.  On
Ubuntu, you would use

```
sudo apt-get install snapd
```

See http://snapcraft.io/docs/core/install for how to install Snapcraft
on other Linux distributions.

Once you have the **snap** command on your system, you can install the
most recent version of Ipe by saying

```
sudo snap install ipe --edge
```

You can now start Ipe by simply saying `ipe` (which calls
`/snap/bin/ipe`).  The other Ipe commands are available as
`ipe.ipetoipe`, `ipe.iperender`, etc.

Snappy isolates the installed software from the system.  This means
that Ipe does not have access to your system's files (with the
exception of the files in your home directory that do not start with a
dot).  In particular, Ipe does not have access to the Latex
installation on your system.

I have currently "solved" this problem by *including a small Texlive
installation* inside the snap.  This works fine as long as all the
Latex packages you are using are part of the snap.  There is currently
no way to install new packages into this installation (since it is in
read-only memory).  I am working on a solution for this.

Opening the manual from the Ipe Help menu currently doesn't work.  You
can open it by opening the file
`/snap/ipe/current/ipe/doc/manual.html`.

Declaring an external editor doesn't work (as Ipe would have no access
to the editor program outside the snap).

If you want to customize Ipe, you need to know that some files are in
unusual locations.  For instance, the ipelet directory is
`~/snap/ipe/current/.ipe/ipelets` rather than `~/.ipe/ipelets`.

