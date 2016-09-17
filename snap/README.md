# Ipe for Snapcraft

**Snapcraft** is a system that allows Linux systems to maintain
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
sudo snap install ipe
```

You can now start Ipe by simply saying `ipe` (which calls
`/snap/bin/ipe`).  The other Ipe commands are available as
`ipe.ipetoipe`, `ipe.iperender`, etc.

Unfortunately, this doesn't quite work: Snapcraft isolates the
installed software from the system, and this doesn't give Ipe access
to running Latex. (Also not working: starting the manual from the Help
menu, finding your ipelets in your home directory).

You therefore need to work around the protection provided by
Snapcraft.  A script `ipewrapper` is provided as
`/snap/ipe/current/bin/ipewrapper` that you can use to start Ipe and
its tools without the protection.

So, to start Ipe, run
```
/snap/ipe/current/bin/ipewrapper ipe
```

To run `ipetoipe`, say
```
/snap/ipe/current/bin/ipewrapper ipetoipe -pdf -export test.ipe
```
