
Pdftoipe
========

This is Pdftoipe, a program that tries to read arbitrary PDF files and
to generate an XML file readable by Ipe.

You can report bugs on the issue tracking system at
"https://github.com/otfried/ipe-tools/issues".

Before reporting a bug, check that you have the latest version of
Pdftoipe, and check the existing reports to see whether your bug has
already been reported.  Please do not send bug reports directly to me
(the first thing I would do with the report is to enter it into the
tracking system).

Suggestions for features, or random comments on Pdftoipe can be sent
to the Ipe discussion mailing list at
<ipe-discuss@lists.science.uu.nl>.  If you have problems installing or
using Pdftoipe, the Ipe discussion mailing list would also be the best
place to ask.

You can send suggestions or comments directly to me by Email, but you
should then not expect a reply.  I cannot dedicate much time to Ipe,
and the little time I have I prefer to put into development.  I'm much
more likely to get involved in a discussion of desirable features on
the mailing list, where anyone interested can participate than by
direct Email.

	Otfried Cheong
	Dept. of Computer Science
	KAIST
	Daejeon, South Korea
	Email: otfried@ipe.airpost.net
	Ipe webpage: http://ipe.otfried.org

--------------------------------------------------------------------

Pdftoipe is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or (at your
option) any later version.

--------------------------------------------------------------------

Compiling
=========

You need the Poppler library (http://poppler.freedesktop.org).  On
Debian/Ubuntu, install the packages 'libpoppler-dev' and
'libpoppler-private-dev'. 

In source directory, say

make

This will create the single executable "pdftoipe".  Copy it to
whereever you like.  You may also install the man page "pdftoipe.1".

If you want to compile pdftoipe on Windows, please refer to
"compile_on_windows.pdf", written by Daniel Beckmann.

--------------------------------------------------------------------

Changes
=======

 * 2017/09/05
   Added -std=c++11 flag to Makefile for compiling with new poppler
   version. 

 * 2014/03/03
   Applied patch from bug #138 to fix compilation on newer poppler
   versions, as well as fix missing dollar signs for some greek
   letters. 

 * 2013/01/24 
   Applied patches from bugs #88 and #112 to fix compilation on
   newer poppler versions.

 * 2011/05/17 
   Built Windows binary and included instructions by Daniel
   Beckmann for compiling on Windows in the source download.

 * 2011/01/16
   Re-released to clarify that pdftoipe uses GPL V2, compatible with
   the poppler license.

 * 2009/10/14
   Changed to use libpoppler instead of using Xpdf's code directly.
   Generate Ipe 7 format.

 * 2007/05/09
   Applied patches provided by Philip Johnson (bug #160) to support
   latex markup in text objects, and to handle text transformations.
   Improved text transformations, and added -merge option to better
   control separation/merging of text.

 * 2005/11/14
   Generating header correct for Ipe 6.0 preview 25.

 * 2005/09/17
   Fixed handling of transformation matrix for text objects.  (Text
   was incorrectly positioned if pages had the /Rotate flag on.)

   Added -cyberbit option to automatically insert style sheet for
   using the Cyberbit font (but of course it has to be installed
   properly to be used from Pdflatex).

   Removed silly dependency on Qt.

   Added conversion of some Unicode characters to Latex macros.

 * 2003/06/30
   Added recognition of Unicode text (results in a message to the
   user) and escaping of the special Latex characters.

   Fixed generation of incorrect XML files (unterminated <text>
   objects).  
   
 * 2003/06/18
   Added -notext option to completely ignore all text in PDF file.

   Added man page.

 * 2003/06/13
   Packaged pdftoipe separately from Ipe.

 * 2003/06/04
   Fixed handling of transformation matrix in Pdftoipe.  Pdftoipe
   is now actually considered supported.

   Added option -math to pdftoipe.  With this option, all text objects 
   are turned into math formulas. 

--------------------------------------------------------------------
