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
from codecs import getwriter
from math import cos, radians, sin
from os.path import exists
from re import compile

from matplotlib import cbook, rcParams
from matplotlib.backend_bases import (
    FigureCanvasBase, FigureManagerBase, RendererBase)
from matplotlib.backends.backend_pgf import LatexManager, _tex_escape
from matplotlib.backends.backend_svg import XMLWriter
from matplotlib.figure import Figure
from matplotlib.path import Path
from matplotlib.rcsetup import validate_bool, validate_string


class XMLWriterIpe(XMLWriter):
    def insertSheet(self, fname):
        self._XMLWriter__flush()
        with open(fname, "r", encoding="utf-8") as f:
            data = f.read()
            if (i := data.find("<ipestyle")) >= 0:
                self._XMLWriter__write(data[i:])


rcParams.validate["ipe.preamble"] = validate_string
rcParams.validate["ipe.stylesheet"] = lambda s: s if s and exists(s) else None
rcParams.validate["ipe.textsize"] = validate_bool
_negative_number = compile(r"^\u2212([0-9]+)(\.[0-9]*)?$")


class RendererIpe(RendererBase):
    def __init__(self, figure, ipewriter):
        width, height = figure.get_size_inches()
        self.dpi = figure.dpi
        self.width = width * self.dpi
        self.height = height * self.dpi
        self.writer = XMLWriterIpe(ipewriter)

        super().__init__()
        rcParams["pgf.texsystem"] = "pdflatex"  # use same latex as Ipe
        self.__write_header()
        self.writer.start("page")

    def __write_header(self):
        self._start_id = self.writer.start(
            "ipe",
            version="70006",
            creator="Matplotlib")
        self.__stylesheet()

    def __stylesheet(self):
        if "ipe.stylesheet" in rcParams and rcParams["ipe.stylesheet"]:
            self.writer.insertSheet(rcParams["ipe.stylesheet"])
        self.writer.start("ipestyle", name="opacity")
        self.__preamble()
        for i in range(10, 100, 10):
            self.writer.element("opacity", name=f"{i}%", value=f"{i / 100.0}")
        self.writer.end()

    def __preamble(self):
        if "ipe.preamble" in rcParams:
            self.writer.start("preamble")
            self.writer.data(rcParams["ipe.preamble"])
            self.writer.end(indent=False)

    def finalize(self):
        self.writer.close(self._start_id)
        self.writer.flush()

    def draw_path(self, gc, path, transform, rgbFace=None):
        cap = ("butt", "round", "projecting").index(gc.get_capstyle())
        join = ("miter", "round", "bevel").index(gc.get_joinstyle())
        offs, dl = gc.get_dashes()
        attrib = {}
        if offs is not None and dl is not None:
            attrib["dash"] = (f"[{dl}] {offs}" if type(dl) is float else
                              f"[{' '.join([str(x) for x in dl])}] {offs}")
        opaq = gc.get_rgb()[3]
        if rgbFace is not None:     # filling
            r, g, b, opaq = rgbFace
            attrib["fill"] = f"{r} {g} {b}"
        self.__gen_opacity(attrib, opaq)
        self._print_ipe_clip(gc)
        _r, _g, _b, _ = gc.get_rgb()
        self.writer.start(
            "path",
            attrib=attrib,
            stroke=f"{_r} {_g} {_b}",
            pen=f"{gc.get_linewidth()}",
            cap=f"{cap}",
            join=f"{join}",
            fillrule="wind"
        )
        self.writer.data(self._make_ipe_path(gc, path, transform))
        self.writer.end()
        self._print_ipe_clip_end()

    def _make_ipe_path(self, gc, path, transform):
        elem = ""
        for points, code in path.iter_segments(transform):
            if code == Path.MOVETO:
                x, y = tuple(points)
                elem += f"{x} {y} m\n"
            elif code == Path.CLOSEPOLY:
                elem += "h\n"
            elif code == Path.LINETO:
                x, y = tuple(points)
                elem += f"{x} {y} l\n"
            elif code == Path.CURVE3:
                cx, cy, px, py = tuple(points)
                elem += f"{cx} {cy} {px} {py} q\n"
            elif code == Path.CURVE4:
                c1x, c1y, c2x, c2y, px, py = tuple(points)
                elem += (f"{c1x} {c1y} {c2x} {c2y} {px} {py} c\n")
        return elem

    def draw_image(self, gc, x, y, im, transform=None):
        h, w = im.shape[:2]
        if w == 0 or h == 0:
            return
        self._print_ipe_clip(gc)
        self.writer.start(
            "image",
            width=f"{w}",
            height=f"{h}",
            ColorSpace="DeviceRGB",
            BitsPerComponent="8",
            matrix=f"1 0 0 -1 {x} {y}",
            rect=f"0 -{h} {w} 0"
        )
        for row in im:
            for r, g, b, a in row:
                self.writer.data(f"{r:02x}{g:02x}{b:02x}")
        self.writer.end()
        self._print_ipe_clip_end()

    def draw_text(self, gc, x, y, s, prop, angle, ismath=False, mtext=None):
        if _negative_number.match(s):
            s = f"${s.replace('\u2212', '-')}$"
        attrib = {}
        if mtext:
            x, y = mtext.get_transform().transform_point(mtext.get_position())
            attrib["halign"] = mtext.get_ha()
            attrib["valign"] = mtext.get_va()

        if angle != 0.0:
            ra = radians(angle)
            sa, ca = sin(ra), cos(ra)
            attrib["matrix"] = f"{ca} {sa} -{sa} {ca} {x} {y}"
            x, y = 0, 0

        self.__gen_opacity(attrib, gc.get_rgb()[3])
        _r, _g, _b, _ = gc.get_rgb()
        self.writer.start(
            "text",
            stroke=f"{_r} {_g} {_b}",
            type="label",
            size=f"{prop.get_size_in_points()}",
            pos=f"{x} {y}",
            attrib=attrib
        )
        self.writer.data(f"{_tex_escape(s)}")
        self.writer.end(indent=False)

    def _print_ipe_clip(self, gc):
        bbox = gc.get_clip_rectangle()
        self.use_clip_box = bbox is not None
        if self.use_clip_box:
            p1, p2 = bbox.get_points()
            x1, y1 = p1
            x2, y2 = p2
            self.writer.start(
                "group",
                clip=f"{x1} {y1} m {x2} {y1} l {x2} {y2} l {x1} {y2} l h"
            )
        clippath, clippath_trans = gc.get_clip_path()   # check for clip path
        self.use_clip_group = clippath is not None
        if self.use_clip_group:
            self.writer.start(
                "group",
                clip=f"{self._make_ipe_path(gc, clippath, clippath_trans)}")

    def _print_ipe_clip_end(self):
        if self.use_clip_group:
            self.writer.end()
        if self.use_clip_box:
            self.writer.end()

    def get_canvas_width_height(self):
        return self.width, self.height

    def get_text_width_height_descent(self, s, prop, ismath):
        if ("ipe.textsize" in rcParams and rcParams["ipe.textsize"] is True):
            w, h, d = (LatexManager._get_cached_or_new()
                       .get_width_height_descent(s, prop))
            return w * (f := (1/72) * self.dpi), h * f, d * f
        return 1, 1, 1

    @staticmethod
    def __gen_opacity(attrib, opaq):
        if opaq < 0.05:
            attrib["opacity"] = "10%"
        elif opaq < 0.95:
            o = round(opaq+10**(-len(str(opaq))-1), 1)
            attrib["opacity"] = f"{int(o * 100)}%"


class FigureCanvasIpe(FigureCanvasBase):
    filetypes = FigureCanvasBase.filetypes.copy()
    filetypes["ipe"] = "Ipe 7 file format"

    def print_ipe(self, filename, *args, **kwargs):
        with cbook.open_file_cm(filename, "w", encoding="utf-8") as writer:
            if not cbook.file_requires_unicode(writer):
                writer = getwriter("utf-8")(writer)
            self._print_ipe(filename, writer, **kwargs)

    def _print_ipe(self, filename, ipewriter, **kwargs):
        self.figure.set_dpi(72.0)
        renderer = RendererIpe(self.figure, ipewriter)
        self.figure.draw(renderer)
        renderer.finalize()

    def get_default_filetype(self):
        return "ipe"


class FigureManagerIpe(FigureManagerBase):
    def __init__(self, *args):
        FigureManagerBase.__init__(self, *args)


FigureCanvas = FigureCanvasIpe
FigureManager = FigureManagerIpe


def new_figure_manager(num, *args, **kwargs):
    FigureClass = kwargs.pop("FigureClass", Figure)
    fig = FigureClass(*args, **kwargs)
    return FigureManagerIpe(FigureCanvasIpe(fig), num)
