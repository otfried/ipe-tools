annotate.py
==========

This Python script takes a PDF file and creates an Ipe document that
shows the pages of the PDF page by page, allowing you to annotate the
PDF document, for instance using ink mode on a tablet or by simply
creating new text objects.

To run it, you will need the *PyPDF2* library from
https://github.com/mstamy2/PyPDF2.  The easiest way to install
*PyPDF2* is using PIP - on Linux it will suffice to say

```
apt-get install python3-pip
pip3 install PyPDF2
```

(Or, if using Python~2, install `python-pip` and call `pip`.)

Run it with a PDF file as an argument:

```
python3 annotate.py doc.pdf
```

It will create the new file `annotate-doc.ipe`.

When opening `annotate-doc.ipe` using Ipe, you will need to have the
original PDF file `doc.pdf` available for Ipe.  You either have to
copy it into Ipe's Latex directory (e.g. `~/.ipe/latexrun`), or you
have to set the `TEXINPUTS` environment variable.



