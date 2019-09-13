ipe-tools
=========

These are various tools and helper programs to be used 
with the Ipe drawing editor (http://ipe.otfried.org).


svgtoipe.py
-----------

A script that converts an SVG figure to Ipe format. It cannot handle
all SVG features (many SVG features are not supported by Ipe anyway),
but it works for gradients.


ipepython
---------

A Python 3 extension module that will let you open and work with Ipe
documents from Python.


Poweripe
--------

Do you prefer to create your presentations in Ipe?  But your
bosses/colleagues/clients keep asking for Powerpoint files?

Fear no more!  Poweripe is a Python script that translates an Ipe
presentation into a Powerpoint presentation.


Matplotlib backend
------------------

Matplotlib is a Python module for scientific plotting.  With this
backend, you can create Ipe figures directly from matplotlib.


pdftoipe
--------

You can convert arbitrary Postscript or PDF files into Ipe documents,
making them editable.  The auxiliary program *pdftoipe* converts
(pages from) a PDF file into an Ipe XML-file. (If your source is
Postscript, you have to first convert it to PDF using Acrobat
Distiller or *ps2pdf*.)  Once converted to XML, the file can be opened
from Ipe as usual.

The conversion process should handle any graphics in the PDF file
fine, but doesn't do very well on text - Ipe's text model is just too
different.


ipe5toxml
---------

If you still have figures that were created with Ipe 5, you can use
*ipe5toxml* to convert them to Ipe 6 format.  You can then use
*ipe6upgrade* to convert them to Ipe 7 format.


figtoipe
--------

Figtoipe converts a figure in FIG format into an Ipe XML-file.  This
is useful if you used to make figures with Xfig before discovering
Ipe, of if your co-authors made figures for your article with Xfig
(converting them will have the added benefit of forcing your
co-authors to learn to use Ipe).  Finally, there are quite a number of
programs that can export to FIG format, and *figtoipe* effectively
turns that into the possibility of exporting to Ipe.

However, *figtoipe* is not quite complete.  The drawing models of FIG
and Ipe are also somewhat different, which makes it impossible to
properly render some FIG files in Ipe.  Ipe does not support depth
ordering independent of grouping, pattern fill, and Postscript fonts.
You may therefore have to edit the file after conversion.

*figtoipe* is now maintained by Alexander Bürger.

