matplotlib backend
==================

This is an Ipe backend for the Matplotlib plotting library for Python.
(http://matplotlib.org/)

You can create Ipe files directly from Matplotlib.

To use the backend, copy the file 'backend_ipe.py' somewhere on your
Python path. (The current directory will do.)

You activate the backend like this:

  import matplotlib
  matplotlib.use('module://backend_ipe')

The Ipe backend allows you to save in Ipe format:

  plt.savefig("my_plot.ipe", format="ipe")


