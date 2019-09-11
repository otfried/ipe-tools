# Poweripe

Do you prefer to create your presentations in Ipe?  But your
bosses/colleagues/clients keep asking for Powerpoint files?

Fear no more!  Poweripe is a Python script that translates an Ipe
presentation into a Powerpoint presentation.


## Installation

Poweripe requires two Python modules, one for reading Ipe files, and
one for creating Powerpoint documents.

1. Install the [ipepython](https://github.com/otfried/ipe-tools/tree/python3/ipepython) module.

2. Install the `python-pptx` module.

Currently, you need to get my fork of this module, with added SVG
support.  You can find it at
https://github.com/otfried/python-pptx/tree/svg-pictures.

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

The output will be stored in `presentation.pptx`.

