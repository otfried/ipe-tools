# Ipe in a snap

Linux users suffer from the problem that Linux distributions provide
packages for rather old versions of Ipe.  For instance, Ubuntu 16.04
still provides Ipe 7.1.10 (from late 2015). Distributions tend to be
conservative to ensure the stability of the system. 

[**Snappy**](http://snapcraft.io) is a new system that provides apps
in *encapsulated blocks* called **snap**.  A bug in a snap does not
affect the robustness of the remaining sytem, and so users can freely
upgrade individual snaps at will.  Ipe will now release an up-to-date
snap for each release, such that Linux users, like Windows and OSX
users, can start using immediately.

Snappy is available on recent Linux distributions such as Ubuntu
16.04, etc.  You install the system by installing the **snapd**
package.  On Ubuntu or Debian, you would use

```
sudo apt-get install snapd
```

See http://snapcraft.io/docs/core/install for how to install Snapcraft
on other Linux distributions such as Fedora, 


## Installing Ipe in a snap

Once you have the **snap** command on your system, you can install the
most recent version of Ipe by saying

```
sudo snap install ipe --edge
```

You can now start Ipe by simply saying `ipe` (which calls
`/snap/bin/ipe`).  Note that the other Ipe commands are available as
`ipe.ipetoipe`, `ipe.iperender`, etc.


## How Ipe uses Pdflatex

Snappy isolates each snap to ensure the robustness of the system when
a snap misbehaves.  This implies some severe restrictions: Ipe does
not have access to your system's files (with the exception of the
files in your home directory that do not start with a dot).  In
particular, Ipe does not have access to the Latex installation on your
system!

To allow Ipe to run *pdflatex*, the Ipe snap contains a *small Texlive
installation*.  You will need to remember that when Ipe fails to find
a Latex style or package that you are using, you will need to install
it **inside** the snap.  The following commands are exposed by the
snap to help you find Latex problems: `ipe.pdflatex`, `ipe.lualatex`,
`ipe.kpsewhich`.


## Installing additional Latex packages

You cannot add additional Latex styles or packages to the Texlive
installation inside a snap, as snaps reside entirely in read-only
memory.  However, Ipe's Latex installation can use a *user tree* where
you can add additional styles and fonts.  To install into this user
tree, you run the *texlive manager* `tlmgr` contained in the snap.
For technical reasons, it has to be run outside the snap, like this:

```
/snap/ipe/current/bin/tlmgr install dante-logo
```


## What doesn't work?

 * Opening the manual from the Ipe Help menu currently doesn't work
   (apparently a bug in snappy).  You can read the manual by opening
   the file `/snap/ipe/current/ipe/doc/manual.html`.

 * Declaring an external editor doesn't work.  This is currently a
   fundamental limitation of snappy (Ipe has no access to running an
   editor program that lives outside the snap).


## Anything else?

If you want to customize Ipe, you will need to know that some files
are in locations different from a classic Linux setup.  Use *Show
configuration* in the Help menu to find the right place.  For
instance, Ipe runs Latex in `~/snap/ipe/current/latexrun` (rather than
`~/.ipe/latexrun`), and the ipelet directory is
`~/snap/ipe/common/ipelets` rather than `~/.ipe/ipelets`,

