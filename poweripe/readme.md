# Poweripe

Do you prefer to create your presentations in Ipe?  But your
bosses/colleagues/clients keep asking for Powerpoint files?

Fear no more!  Poweripe is a Python script that translates an Ipe
presentation into a Powerpoint presentation.

Poweripe requires Ipe 7.2.13 or later.

## Installation

Poweripe requires some Python modules:

<!--
1. Install `pylatexenc` by saying `pip3 install pylatexenc`. (This
module is used to parse Latex.)
-->

1. Install the
[ipepython](https://github.com/otfried/ipe-tools/tree/master/ipepython)
module. (This module is used to read Ipe files.) 

2. Install the `python-pptx` module (a module for creating Powerpoint documents). 
Currently, you need to get my fork of this module, with added SVG
support.  You can find it at
https://github.com/otfried/python-pptx. Make sure to get the **svg-pictures** branch!

<!--
It requires the python-pptx module, which you can install with
```
pip3 install python-pptx
```
(See https://python-pptx.readthedocs.io/ for details.)
-->

## Usage

You run Poweripe from the command line like this:
```
python3 poweripe.py --no-text presentation.pdf
```
The output will be stored in `presentation.pptx`.  Alternatively,
provide the `--output` option to select a different output file. 

In this simplest mode, Poweripe stores **all** the contents of the Ipe
document, including all text, as *graphics* in the pptx output.  There
is both an SVG-version of this graphics, which gives high-quality
vector output, and a lower-resolution bitmap as a fallback.  Recent
Powerpoint versions will display the SVG contents, but it seems that
Libreoffice does not yet support SVG and shows the bitmap version
instead.

If you remove `--no-text` option, Poweripe will convert all minipage
text objects contain only simple Latex markup into text objects that
can be edited in the pptx file.

With the `--latex` option, Poweripe will also convert minipage text
objects that contain Latex markup.  You will have to edit the
resulting pptx file to make it useful.

Since the `python-pptx` library does not yet support making slides
that build up incrementally, Poweripe currently converts only the
**last view** of each page.
