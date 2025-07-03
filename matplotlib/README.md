matplotlib backend
==================

This is an Ipe backend for the [Matplotlib plotting
library](http://matplotlib.org/) for Python, written by Soyeon Baek
and Otfried Cheong.

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


Requirements
------------
- Python >=3.6
- Matplotlib  >=3.6

If either `Python` or `Matplotlib` is older than the version 3.6,
please switch to using `backend_ipe.py` from a previous version
in the directory `past`.



Options
-------

Some plots need to measure the size of text to place labels correctly
(see the *legend_demo* test for an example).  The Ipe backend can use
a background Latex process to measure the dimensions of text as it
will appear in the Ipe document.  By default this is not enabled, as
most plots don't need it and it slows down the processing of the plot.

If you want to enable text size measuring, set the matplotlib option
*ipe.textsize* to True, for instance like this:

```python
  import matplotlib
  matplotlib.use('module://backend_ipe')
  import matplotlib.pyplot as plt
  matplotlib.rcParams['ipe.textsize'] = True
```

(Note that the *ipe* options are only available after the backend has
been loaded, here caused by importing *pyplot*.)


If you want your plot to include an Ipe stylesheet, specify this using
the option *ipe.stylesheet*, with a full pathname.  (If you don't know
where your style sheets are, use Ipe -> Help -> Show Configuration.)
Here is an example:

```python
  import matplotlib
  matplotlib.use('module://backend_ipe')
  import matplotlib.pyplot as plt
  matplotlib.rcParams['ipe.stylesheet'] = "/sw/ipe/share/ipe/7.1.6/styles/basic.isy"
```

You can set the preamble of the Ipe document using the option
*ipe.preamble*.  This is useful, for instance, when you want to use
font sizes that are not available with the standard fonts (the test
*watermark_image* needs this).  You can then switch to a Postscript
font that can be scaled to any size:

```python
  import matplotlib
  matplotlib.use('module://backend_ipe')
  import matplotlib.pyplot as plt
  matplotlib.rcParams['ipe.preamble'] = r"""
\usepackage{times}
"""
```



Problems?
---------

If you need to report a problem, please include your matplotlib version.
You can find it as follows:

```python
  import matplotlib
  print matplotlib.__version__
```
