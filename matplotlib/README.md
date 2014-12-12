matplotlib backend
==================

This is an Ipe backend for the Matplotlib plotting library for Python
([matplotlib.org](http://matplotlib.org/)), written by Soyeon Baek and
Otfried Cheong.

You can create Ipe files directly from Matplotlib.

To use the backend, copy the file *backend_ipe.py* somewhere on your
Python path. (The current directory will do.)

You activate the backend like this:

```python
  import matplotlib
  matplotlib.use('module://backend_ipe')
```

The Ipe backend allows you to save in Ipe format:

```python
  plt.savefig("my_plot.ipe", format="ipe")
```


Problems?
---------

If you need to report a problem, please include your matplotlib version.
You can find it as follows:

```python
  import matplotlib
  print matplotlib.__version__
```

The Ipe backend uses a background Latex process to measure the
dimensions of text as it will appear in the Ipe document.  By default,
it uses "xelatex", and this may not work if you do not have it
installed or do not have all the packages it needs.  You can switch to
using "pdflatex" (like Ipe itself does) with the following:

```python
  import matplotlib as mpl
  mpl.rcParams['pgf.texsystem'] = "pdflatex"
  mpl.use('module://backend_ipe')
```

(You can also set the *pgf.texsystem* parameter in your *matplotlibrc*
file, see the matplotlib documentation.)
