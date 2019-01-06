"""
This is a matplotlib backend to save in the Ipe file format.
(ipe7.sourceforge.net).

(c) 2014 Soyeon Baek, Otfried Cheong

You can find the most current version at:
http://www.github.com/otfried/ipe-tools/matplotlib

You can use this backend by saving it anywhere on your PYTHONPATH.
Use it as an external backend from matplotlib like this:

  import matplotlib
  matplotlib.use('module://backend_ipe')

"""

# --------------------------------------------------------------------

from __future__ import division, print_function, unicode_literals

import os, base64, tempfile, urllib, gzip, io, sys, codecs, re

import matplotlib
from matplotlib import rcParams
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import RendererBase, GraphicsContextBase
from matplotlib.backend_bases import FigureManagerBase, FigureCanvasBase
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox
from matplotlib.cbook import is_string_like, is_writable_file_like, maxdict
from matplotlib.path import Path

from xml.sax.saxutils import escape as escape_xml_text

from math import sin, cos, radians

from matplotlib.backends.backend_pgf import LatexManagerFactory, \
    LatexManager, common_texification
import atexit

from matplotlib.rcsetup import validate_bool, validate_path_exists

negative_number = re.compile(u"^\u2212([0-9]+)(\.[0-9]*)?$")

rcParams.validate['ipe.textsize'] = validate_bool
rcParams.validate['ipe.stylesheet'] = validate_path_exists
rcParams.validate['ipe.preamble'] = lambda s : s

# ----------------------------------------------------------------------
# SimpleXMLWriter class
#
# Based on an original by Fredrik Lundh, but modified here to:
#   1. Support modern Python idioms
#   2. Remove encoding support (it's handled by the file writer instead)
#   3. Support proper indentation
#   4. Minify things a little bit

# --------------------------------------------------------------------
# The SimpleXMLWriter module is
#
# Copyright (c) 2001-2004 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

def escape_cdata(s):
    s = s.replace(u"&", u"&amp;")
    s = s.replace(u"<", u"&lt;")
    s = s.replace(u">", u"&gt;")
    return s

def escape_attrib(s):
    s = s.replace(u"&", u"&amp;")
    s = s.replace(u"'", u"&apos;")
    s = s.replace(u"\"", u"&quot;")
    s = s.replace(u"<", u"&lt;")
    s = s.replace(u">", u"&gt;")
    return s

##
# XML writer class.
#
# @param file A file or file-like object.  This object must implement
#    a <b>write</b> method that takes an 8-bit string.

class XMLWriter:
    def __init__(self, file):
        self.__write = file.write
        if hasattr(file, "flush"):
            self.flush = file.flush
        self.__open = 0 # true if start tag is open
        self.__tags = []
        self.__data = []
        self.__indentation = u" " * 64

    def __flush(self, indent=True):
        # flush internal buffers
        if self.__open:
            if indent:
                self.__write(u">\n")
            else:
                self.__write(u">")
            self.__open = 0
        if self.__data:
            data = u''.join(self.__data)
            self.__write(escape_cdata(data))
            self.__data = []

    ## Opens a new element.  Attributes can be given as keyword
    # arguments, or as a string/string dictionary. The method returns
    # an opaque identifier that can be passed to the <b>close</b>
    # method, to close all open elements up to and including this one.
    #
    # @param tag Element tag.
    # @param attrib Attribute dictionary.  Alternatively, attributes
    #    can be given as keyword arguments.
    # @return An element identifier.

    def start(self, tag, attrib={}, **extra):
        self.__flush()
        tag = escape_cdata(tag)
        self.__data = []
        self.__tags.append(tag)
        self.__write(self.__indentation[:len(self.__tags) - 1])
        self.__write(u"<%s" % tag)
        if attrib or extra:
            attrib = attrib.copy()
            attrib.update(extra)
            attrib = sorted(attrib.items())
            for k, v in attrib:
                if not v == '':
                    k = escape_cdata(k)
                    v = escape_attrib(v)
                    self.__write(u" %s=\"%s\"" % (k, v))
        self.__open = 1
        return len(self.__tags)-1

    ##
    # Adds a comment to the output stream.
    #
    # @param comment Comment text, as a Unicode string.

    def comment(self, comment):
        self.__flush()
        self.__write(self.__indentation[:len(self.__tags)])
        self.__write(u"<!-- %s -->\n" % escape_cdata(comment))

    ##
    # Adds character data to the output stream.
    #
    # @param text Character data, as a Unicode string.

    def data(self, text):
        self.__data.append(text)

    ##
    # Closes the current element (opened by the most recent call to
    # <b>start</b>).
    #
    # @param tag Element tag.  If given, the tag must match the start
    #    tag.  If omitted, the current element is closed.

    def end(self, tag=None, indent=True):
        if tag:
            assert self.__tags, "unbalanced end(%s)" % tag
            assert escape_cdata(tag) == self.__tags[-1],\
                   "expected end(%s), got %s" % (self.__tags[-1], tag)
        else:
            assert self.__tags, "unbalanced end()"
        tag = self.__tags.pop()
        if self.__data:
            self.__flush(indent)
        elif self.__open:
            self.__open = 0
            self.__write(u"/>\n")
            return
        if indent:
            self.__write(self.__indentation[:len(self.__tags)])
        self.__write(u"</%s>\n" % tag)

    ##
    # Closes open elements, up to (and including) the element identified
    # by the given identifier.
    #
    # @param id Element identifier, as returned by the <b>start</b> method.

    def close(self, id):
        while len(self.__tags) > id:
            self.end()

    ##
    # Adds an entire element.  This is the same as calling <b>start</b>,
    # <b>data</b>, and <b>end</b> in sequence. The <b>text</b> argument
    # can be omitted.

    def element(self, tag, text=None, attrib={}, **extra):
        self.start(*(tag, attrib), **extra)
        if text:
            self.data(text)
        self.end(indent=False)

    def insertSheet(self, fname):
        self.__flush()
        data = open(fname, "rb").read()
        i = data.find("<ipestyle")
        if i >= 0:
            self.__write(data[i:].decode("utf-8"))

# ----------------------------------------------------------------------

class RendererIpe(RendererBase):
    """
    The renderer handles drawing/rendering operations.
    Refer to backend_bases.RendererBase for documentation of 
    the classes methods.
    """
    def __init__(self, width, height, ipewriter, basename):
        self.width = width
        self.height = height
        self.writer = XMLWriter(ipewriter)
        self.basename = basename

        RendererBase.__init__(self)

        # use same latex as Ipe (default is xelatex)
        rcParams['pgf.texsystem'] = "pdflatex"
        self.latexManager = None
        if rcParams.get("ipe.textsize", False):
            self.latexManager = LatexManagerFactory.get_latex_manager()

        self._start_id = self.writer.start(
            u'ipe',
            version=u"70005",
            creator="matplotlib")
        pre = rcParams.get('ipe.preamble', "")
        if pre != "":
            self.writer.start(u'preamble')
            self.writer.data(pre)
            self.writer.end(indent=False)
        sheet = rcParams.get('ipe.stylesheet', "")
        if sheet != "":
            self.writer.insertSheet(sheet)
        self.writer.start(u'ipestyle', name=u"opacity")

        for i in range(10,100,10):
            self.writer.element(u'opacity', name=u'%02d%%'% i, 
                                value=u'%g'% (i/100.0))
        self.writer.end()
        self.writer.start(u'page')


    def finalize(self):
        self.writer.close(self._start_id)
        self.writer.flush()

    def draw_path(self, gc, path, transform, rgbFace=None):
        capnames = ('butt', 'round', 'projecting')
        cap = capnames.index(gc.get_capstyle())
        
        joinnames = ('miter', 'round', 'bevel')
        join = joinnames.index(gc.get_joinstyle())
        
        # filling
        has_fill = rgbFace is not None
        
        offs, dl = gc.get_dashes()
        attrib = {}
        if offs != None and dl != None:
            if type(dl) == float:
                dashes = "[%g] %g" % (dl, offs)
            else:
                dashes = "[" + " ".join(["%g" % x for x in dl]) + "] %g" % offs
            attrib['dash'] = dashes
        if has_fill:
            attrib['fill'] = "%g %g %g" % tuple(rgbFace)[:3]
        opaq = gc.get_rgb()[3]
        if rgbFace is not None and len(rgbFace) > 3:
            opaq =  rgbFace[3]
        self.gen_opacity(attrib, opaq)  
        self._print_ipe_clip(gc)
        self.writer.start(
            u'path',
            attrib=attrib,
            stroke="%g %g %g" % gc.get_rgb()[:3],
            pen="%g" % gc.get_linewidth(),
            cap="%d" % cap,
            join="%d" % join,
            fillrule="wind"
        )
        self.writer.data(self._make_ipe_path(gc, path, transform))
        self.writer.end()
        self._print_ipe_clip_end()
        

    def draw_image(self, gc, x, y, im, dx=None, dy=None, transform=None):
        h,w = im.get_size_out()
        
        if dx is not None:
            w = dx
        if dy is not None:
            h = dy
        rows, cols, buffer = im.as_rgba_str()
        self._print_ipe_clip(gc)
        self.writer.start(
            u'image',
            width=u"%d" % cols,
            height=u"%d" % rows,
            ColorSpace=u"DeviceRGB",
            BitsPerComponent=u"8",
            matrix=u"1 0 0 -1 %g %g" % (x, y),
            rect="%g %g %g %g" % (0, -h, w, 0)
        )
        for i in xrange(rows * cols):
            rgb = buffer[4*i:4*i+3]
            self.writer.data(u"%02x%02x%02x" % (ord(rgb[0]), ord(rgb[1]),
                                                ord(rgb[2])))
        self.writer.end()
        self._print_ipe_clip_end() 
        
    def draw_text(self, gc, x, y, s, prop, angle, ismath=False, mtext=None):
        if negative_number.match(s):
            s = u"$" + s.replace(u'\u2212', u'-') + "$"
        attrib = {}
        if mtext:
            # if text anchoring can be supported, get the original coordinates
            # and add alignment information
            x, y = mtext.get_transform().transform_point(mtext.get_position())
        
            attrib['halign'] = mtext.get_ha()
            attrib['valign'] = mtext.get_va()
        
        if angle != 0.0:
            ra = radians(angle)
            sa = sin(ra); ca = cos(ra)
            attrib['matrix'] = "%g %g %g %g %g %g" % (ca, sa, -sa, ca, x, y)
            x, y  = 0, 0
 
        self.gen_opacity(attrib, gc.get_rgb()[3])
        
        self.writer.start(
            u'text',
            stroke="%g %g %g" % gc.get_rgb()[:3],
            type="label",
            size="%g" % prop.get_size_in_points(),
            pos="%g %g" % (x,y),
            attrib=attrib            
        )

        s = common_texification(s)
        self.writer.data(u"%s" % s)
        self.writer.end(indent=False)
        
    def _make_ipe_path(self, gc, path, transform):
        elem = ""
        for points, code in path.iter_segments(transform):
            if code == Path.MOVETO:
                x, y = tuple(points)
                elem += "%g %g m\n" % (x, y)
            elif code == Path.CLOSEPOLY:
                elem += "h\n"
            elif code == Path.LINETO:
                x, y = tuple(points)
                elem += "%g %g l\n" % (x, y)
            elif code == Path.CURVE3:
                cx, cy, px, py = tuple(points)
                elem += "%g %g %g %g q\n" % (cx, cy, px, py)
            elif code == Path.CURVE4:
                c1x, c1y, c2x, c2y, px, py = tuple(points)
                elem += ("%g %g %g %g %g %g c\n" % 
                                (c1x, c1y, c2x, c2y, px, py))
        return elem
                
    def _print_ipe_clip(self, gc):
        bbox = gc.get_clip_rectangle()
        self.use_clip_box = bbox is not None
        if self.use_clip_box:
            p1, p2 = bbox.get_points()
            x1, y1 = p1
            x2, y2 = p2
            self.writer.start(
                            u'group',
                            clip=u"%g %g m %g %g l %g %g l %g %g l h" %
                             (x1, y1, x2, y1, x2, y2, x1, y2)
                        )            
        # check for clip path
        clippath, clippath_trans = gc.get_clip_path()
        self.use_clip_group = clippath is not None
        if self.use_clip_group:
            self.writer.start(
                u'group',
                clip=u"%s" % self._make_ipe_path(gc, clippath, clippath_trans)
            )
            
    def _print_ipe_clip_end(self):
        if self.use_clip_group:
            self.writer.end()
        if self.use_clip_box:
            self.writer.end()
        
    def flipy(self):
        return True

    def get_canvas_width_height(self):
        return self.width, self.height

    def get_text_width_height_descent(self, s, prop, ismath):
        if self.latexManager:
            s = common_texification(s)
            w, h, d = self.latexManager.get_width_height_descent(s, prop)
            return w, h, d
        else:
            return 1, 1, 1

    def new_gc(self):
        return GraphicsContextIpe()

    def points_to_pixels(self, points):
        return points
    
    def gen_opacity(self, attrib, opaq):
        if opaq > 0.99: return
        opaq += 0.05
        o = int(opaq * 10) * 10
        if o > 90: o = 90
        if o < 10: o = 10
        attrib["opacity"] = u"%02d%%" % o
        
# --------------------------------------------------------------------

class GraphicsContextIpe(GraphicsContextBase):
    pass
    
# --------------------------------------------------------------------

class FigureCanvasIpe(FigureCanvasBase):
    filetypes = FigureCanvasBase.filetypes.copy()
    filetypes['ipe'] = 'Ipe 7 file format'

    def print_ipe(self, filename, *args, **kwargs):
        if is_string_like(filename):
            fh_to_close = ipewriter = io.open(filename, 'w', encoding='utf-8')
        elif is_writable_file_like(filename):
            if not isinstance(filename, io.TextIOBase):
                if sys.version_info[0] >= 3:
                    ipewriter = io.TextIOWrapper(filename, 'utf-8')
                else:
                    ipewriter = codecs.getwriter('utf-8')(filename)
            else:
                ipewriter = filename
            fh_to_close = None
        else:
            raise ValueError("filename must be a path or a file-like object")
        return self._print_ipe(filename, ipewriter, fh_to_close, **kwargs)

    def _print_ipe(self, filename, ipewriter, fh_to_close=None, **kwargs):
        try:
            self.figure.set_dpi(72.0)
            width, height = self.figure.get_size_inches()
            w, h = width*72, height*72
            renderer = RendererIpe(w, h, ipewriter, filename)
            self.figure.draw(renderer)
            renderer.finalize()
        finally:
            if fh_to_close is not None:
                ipewriter.close()

    def get_default_filetype(self):
        return 'ipe'

# --------------------------------------------------------------------

# Provide the standard names that backend.__init__ is expecting

class FigureManagerIpe(FigureManagerBase):
    def __init__(self, *args):
        FigureManagerBase.__init__(self, *args)

FigureCanvas = FigureCanvasIpe
FigureManager = FigureManagerIpe

def new_figure_manager(num, *args, **kwargs):
    FigureClass = kwargs.pop('FigureClass', Figure)
    thisFig = FigureClass(*args, **kwargs)
    return new_figure_manager_given_figure(num, thisFig)

def new_figure_manager_given_figure(num, figure):
    """
    Create a new figure manager instance for the given figure.
    """
    canvas  = FigureCanvasIpe(figure)
    manager = FigureManagerIpe(canvas, num)
    return manager

# --------------------------------------------------------------------

def _cleanup():
    LatexManager._cleanup_remaining_instances()
    # This is necessary to avoid a spurious error
    # caused by the atexit at the end of the PGF backend
    LatexManager.__del__ = lambda self : None

atexit.register(_cleanup)

# --------------------------------------------------------------------
