
Svgtoipe
========

This is Svgtoipe, a Python script that reads SVG figures and generates
an XML file readable by Ipe.

You'll need Python3 installed on your system.  To process embedded
images in SVG figures will also require the Python Image Library
(PIL).  (On Ubuntu/Debian, install python3-image).

For installation, just copy "svgtoipe" to a suitable location on your
system.

You can report bugs on the issue tracking system at
"https://github.com/otfried/ipe-tools/issues".

Before reporting a bug, check that you have the latest version of
Svgtoipe, and check the existing reports to see whether your bug has
already been reported.  Please do not send bug reports directly to me
(the first thing I would do with the report is to enter it into the
bug tracking system).

Suggestions for features, or random comments on Svgtoipe can be sent
to the Ipe discussion mailing list at <ipe-discuss@cs.uu.nl>.  If you
have problems installing or using Svgtoipe, the Ipe discussion mailing
list would also be the best place to ask.

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

Copyright (C) 2009-2019 Otfried Cheong

svgtoipe is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 3 of the License, or (at your
option) any later version.

svgtoipe is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with svgtoipe; if not, you can find it at
"http://www.gnu.org/copyleft/gpl.html", or write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

--------------------------------------------------------------------

Changes
=======

 * 2019/08/01
   Handle missing attributes in various elements. More color
   keywords. A test script to go through SVG samples.  Handle 'a'
   elements.  Default for 'fill' is black.

 * 2019/06/02
   Handle coordinates without a digit before the period.
   Migrate to Python 3.

 * 2016/12/09
   Command line argument to generate Ipe selection format, ability to
   read/write stdin/stdout (thanks to Christian Kapeller).

 * 2013/11/07
   Bugs in path parsing and Latex generation fixed by Will Evans.

 * 2010/06/08
   Added copyright notice and GPL license to svgtoipe distribution.

 * 2009/10/18
   First version of svgtoipe.

--------------------------------------------------------------------
