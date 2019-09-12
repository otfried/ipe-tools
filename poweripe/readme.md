# Poweripe

Do you prefer to create your presentations in Ipe?  But your
bosses/colleagues/clients keep asking for Powerpoint files?

Fear no more!  Poweripe is a Python script that translates an Ipe
presentation into a Powerpoint presentation.


## Installation

Poweripe requires some Python modules:

1. Install `pylatexenc` by saying `pip3 install pylatexenc`. (This module is used to parse Latex.)

2. Install the [ipepython](https://github.com/otfried/ipe-tools/tree/master/ipepython) module. (This module is used to read Ipe files.)

3. Install the `python-pptx` module (a module for creating Powerpoint documents). 
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

## Running

You run Poweripe from the command line like this:
```
python3 poweripe.py presentation.pdf
```
The output will be stored in `presentation.pptx`.  Alternatively, provide the `--output` option to select a different output file.

In this simplest mode, Poweripe stores all the contents of the Ipe
document as an image in the pptx output.  The image contains both an
SVG-version, which gives high-quality vector graphics, and a
lower-resolution bitmap as a fallback.  Recent Powerpoint versions
will display the SVG contents, but it seems that Libreoffice does not
yet support SVG and shows the bitmap version instead.

With the `--text` option, Poweripe will convert all minipage text
objects that do not contain Latex markup into text objects that can be
edited in the pptx file.

With the `--latex` option, Poweripe will also convert minipage text
objects that contain Latex markup.  Translating some simple Latex
commands (for color, emphasis, and itemizing) is planned for the near
future.

