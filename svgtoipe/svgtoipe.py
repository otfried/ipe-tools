#!/usr/bin/env python3
# --------------------------------------------------------------------
# convert SVG to Ipe format
# --------------------------------------------------------------------
#
# Copyright (C) 2009-2026  Otfried Cheong
#
# svgtoipe is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# svgtoipe is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with svgtoipe; if not, you can find it at
# "http://www.gnu.org/copyleft/gpl.html", or write to the Free
# Software Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# SVG Specification: https://www.w3.org/TR/SVG11
#
# TODO:
#  - coordinates used in gradients (e.g. intertwingly.svg)
#  - go through SVG test suite (see test_svg.py)
#
# --------------------------------------------------------------------

svgtoipe_version = "20261010"

import argparse
import base64
import io
import math
import re
import sys
import xml.dom.minidom as xml
from typing import NamedTuple
from xml.dom.minidom import Node
from xml.parsers.expat import ExpatError
from xml.sax.saxutils import escape, quoteattr

try:
    from PIL import Image

    have_pil = True
except ImportError:
    have_pil = False

assert sys.hexversion >= 0x3000000, "Please run svgtoipe using Python 3"

ignored_nodes = {
    "defs",
    "audio",
    "video",
    "metadata",
    "sodipodi:namedview",
    "style",
    "script",
    "SVGTestCase",
    "animate",
    "animateTransform",
    "set",
    "title",
    "desc",
}

# --------------------------------------------------------------------

# should extend this to cover list in https://www.w3.org/TR/SVG11/types.html#ColorKeywords

color_keywords = {
    "aqua": "rgb(0, 255, 255)",
    "black": "rgb(0, 0, 0)",
    "blue": "rgb(0, 0, 255)",
    "firebrick": "rgb(178, 34, 34)",
    "fuchsia": "rgb(255, 0, 255)",
    "gray": "rgb(128, 128, 128)",
    "green": "rgb(0, 128, 0)",
    "grey": "rgb(128, 128, 128)",
    "lime": "rgb(0, 255, 0)",
    "maroon": "rgb(128, 0, 0)",
    "navy": "rgb(0, 0, 128)",
    "olive": "rgb(128, 128, 0)",
    "purple": "rgb(128, 0, 128)",
    "red": "rgb(255, 0, 0)",
    "silver": "rgb(192, 192, 192)",
    "teal": "rgb(0, 128, 128)",
    "white": "rgb(255, 255, 255)",
    "yellow": "rgb(255, 255, 0)",
}

attribute_names = [
    "stroke",
    "fill",
    "stroke-opacity",
    "fill-opacity",
    "stroke-width",
    "fill-rule",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-dasharray",
    "stroke-dashoffset",
    "stroke-miterlimit",
    "opacity",
    "font-size",
    "visibility",
]


def printAttributes(n):
    a = n.attributes
    for i in range(a.length):
        name = a.item(i).name
        if name[:9] != "sodipodi:" and name[:9] != "inkscape:":
            sys.stderr.write(f"   {name} {n.getAttribute(name)}\n")


def text_content(node):
    return "".join(
        child.data
        if child.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE)
        else text_content(child)
        for child in node.childNodes
        if child.nodeType
        in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE, Node.ELEMENT_NODE)
    ).strip()


def parse_float(txt):
    if not txt:
        return None
    if txt.endswith(("px", "pt")):
        return float(txt[:-2])
    elif txt.endswith("pc"):
        return 12 * float(txt[:-2])
    elif txt.endswith("mm"):
        return 72.0 * float(txt[:-2]) / 25.4
    elif txt.endswith("cm"):
        return 72.0 * float(txt[:-2]) / 2.54
    elif txt.endswith("in"):
        return 72.0 * float(txt[:-2])
    else:
        return float(txt)


def parse_opacity(txt):
    if txt is None or txt == "":
        return None
    value = max(0.0, min(1.0, float(txt)))
    return 10 * math.floor(10 * value + 0.5)


def parse_list(string):
    return re.findall(r"([A-Za-z]|-?[0-9]+\.?[0-9]*(?:e-?[0-9]*)?)", string)


def parse_style(string):
    sdict = {}
    for item in string.split(";"):
        if ":" in item:
            key, value = item.split(":")
            sdict[key.strip()] = value.strip()
    return sdict


def parse_color_component(txt):
    if txt.endswith("%"):
        return float(txt[:-1]) / 100.0
    else:
        return int(txt) / 255.0


def parse_color(c):
    if not c or c == "none":
        return None
    if c in color_keywords:
        c = color_keywords[c]
    m = re.match(r"rgb\(([0-9\.]+%?),\s*([0-9\.]+%?),\s*([0-9\.]+%?)\s*\)", c)
    if m:
        r = parse_color_component(m.group(1))
        g = parse_color_component(m.group(2))
        b = parse_color_component(m.group(3))
        return (r, g, b)
    m = re.match(r"#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])$", c)
    if m:
        r = int(m.group(1), 16) / 15.0
        g = int(m.group(2), 16) / 15.0
        b = int(m.group(3), 16) / 15.0
        return (r, g, b)
    m = re.match(
        r"#([0-9a-fA-F][0-9a-fA-F])([0-9a-fA-F][0-9a-fA-F])"
        + r"([0-9a-fA-F][0-9a-fA-F])$",
        c,
    )
    if m:
        r = int(m.group(1), 16) / 255.0
        g = int(m.group(2), 16) / 255.0
        b = int(m.group(3), 16) / 255.0
        return (r, g, b)
    sys.stderr.write(f"Unknown color: {c}\n")
    return None


def pnext(d, n):
    l = []
    while n > 0:
        l.append(float(d.pop(0)))
        n -= 1
    return tuple(l)


def parse_arc_arg(d):
    """
    >>> parse_arc_arg("4.12 4.12 0 0 14.13 0".split())
    (4.12, 4.12, 0.0, 0.0, 1.0, 4.13, 0.0)
    """
    # After opcode 'A' or 'a' follows three numbers, then two flags, then two numbers.
    # Each flag is a single '0' or '1' not necessarily followed by whitespace,
    # meaning that in "a 4.12 4.12 0 0 14.13 0", the "1" in "14.13" is a flag,
    # so the correct parse is ('a', '4.12', '4.12', '0', '0', '1', '4.13', '0').
    # Further reading: https://svgwg.org/svg2-draft/paths.html#PathDataBNF
    l = []
    # First parse the three numbers.
    l.append(float(d.pop(0)))
    l.append(float(d.pop(0)))
    l.append(float(d.pop(0)))
    # Now parse the two flags and the next number.
    s = d.pop(0)
    while len(s) <= 2:
        s += d.pop(0)
    l.append(float(s[0]))
    l.append(float(s[1]))
    l.append(float(s[2:]))
    # Now parse the last number.
    l.append(float(d.pop(0)))
    return tuple(l)


def parse_path(out, d):
    try:
        _parse_path(out, d)
    except (IndexError, ValueError):
        sys.stderr.write("Ignoring malformed path data\n")


def _parse_path(output, d):
    d = re.findall(r"([A-Za-z]|-?(?:\.[0-9]+|[0-9]+\.?[0-9]*)(?:e-?[0-9]+)?)", d)
    x, y = 0.0, 0.0
    xs, ys = 0.0, 0.0
    x0, y0 = 0.0, 0.0
    pending_move = None
    while d:
        out = io.StringIO()
        if not d[0][0] in "01234567890.-":
            opcode = d.pop(0)
        if opcode == "M":
            x, y = pnext(d, 2)
            x0, y0 = x, y
            pending_move = f"{x:g} {y:g} m\n"
            opcode = "L"
        elif opcode == "m":
            x1, y1 = pnext(d, 2)
            x += x1
            y += y1
            x0, y0 = x, y
            pending_move = f"{x:g} {y:g} m\n"
            opcode = "l"
        elif opcode == "L":
            x, y = pnext(d, 2)
            out.write(f"{x:g} {y:g} l\n")
        elif opcode == "l":
            x1, y1 = pnext(d, 2)
            x += x1
            y += y1
            out.write(f"{x:g} {y:g} l\n")
        elif opcode == "H":
            x = pnext(d, 1)[0]
            out.write(f"{x:g} {y:g} l\n")
        elif opcode == "h":
            x += pnext(d, 1)[0]
            out.write(f"{x:g} {y:g} l\n")
        elif opcode == "V":
            y = pnext(d, 1)[0]
            out.write(f"{x:g} {y:g} l\n")
        elif opcode == "v":
            y += pnext(d, 1)[0]
            out.write(f"{x:g} {y:g} l\n")
        elif opcode == "C":
            x1, y1, xs, ys, x, y = pnext(d, 6)
            out.write(f"{x1:g} {y1:g} {xs:g} {ys:g} {x:g} {y:g} c\n")
        elif opcode == "c":
            x1, y1, xs, ys, xf, yf = pnext(d, 6)
            x1 += x
            y1 += y
            xs += x
            ys += y
            x += xf
            y += yf
            out.write(f"{x1:g} {y1:g} {xs:g} {ys:g} {x:g} {y:g} c\n")
        elif opcode == "S" or opcode == "s":
            x2, y2, xf, yf = pnext(d, 4)
            if opcode == "s":
                x2 += x
                y2 += y
                xf += x
                yf += y
            x1 = x + (x - xs)
            y1 = y + (y - ys)
            out.write(f"{x1:g} {y1:g} {x2:g} {y2:g} {xf:g} {yf:g} c\n")
            xs, ys = x2, y2
            x, y = xf, yf
        elif opcode == "Q":
            xs, ys, x, y = pnext(d, 4)
            out.write(f"{xs:g} {ys:g} {x:g} {y:g} q\n")
        elif opcode == "q":
            xs, ys, xf, yf = pnext(d, 4)
            xs += x
            ys += y
            x += xf
            y += yf
            out.write(f"{xs:g} {ys:g} {x:g} {y:g} q\n")
        elif opcode == "T" or opcode == "t":
            xf, yf = pnext(d, 2)
            if opcode == "t":
                xf += x
                yf += y
            x1 = x + (x - xs)
            y1 = y + (y - ys)
            out.write(f"{x1:g} {y1:g} {xf:g} {yf:g} q\n")
            xs, ys = x1, y1
            x, y = xf, yf
        elif opcode == "A" or opcode == "a":
            rx, ry, phi, large_arc, sweep, x2, y2 = parse_arc_arg(d)
            if opcode == "a":
                x2 += x
                y2 += y
            draw_arc(out, x, y, rx, ry, phi, large_arc, sweep, x2, y2)
            x, y = x2, y2
        elif opcode in "zZ":
            x, y = x0, y0
            if pending_move is None:
                out.write("h\n")
        else:
            sys.stderr.write(f"Unrecognised opcode: {opcode}\n")
        segment = out.getvalue()
        if segment:
            if pending_move is not None:
                output.write(pending_move)
                pending_move = None
            output.write(segment)


def parse_transformation(txt):
    d = re.findall(r"[a-zA-Z]+\([^)]*\)", txt)
    m = Matrix()
    while d:
        m1 = Matrix(d.pop(0))
        m = m * m1
    return m


def get_gradientTransform(n):
    if n.hasAttribute("gradientTransform"):
        return parse_transformation(n.getAttribute("gradientTransform"))
    return Matrix()


def parse_transform(n):
    if n.hasAttribute("transform"):
        return parse_transformation(n.getAttribute("transform"))
    return None


# Convert from endpoint to center parameterization
# www.w3.org/TR/2003/REC-SVG11-20030114/implnote.html#ArcImplementationNotes
def draw_arc(out, x1, y1, rx, ry, phi, large_arc, sweep, x2, y2):
    phi = math.pi * phi / 180.0
    cp = math.cos(phi)
    sp = math.sin(phi)
    dx = 0.5 * (x1 - x2)
    dy = 0.5 * (y1 - y2)
    x1p = cp * dx + sp * dy
    y1p = -sp * dx + cp * dy
    r2 = ((rx * ry) ** 2 - (rx * y1p) ** 2 - (ry * x1p) ** 2) / (
        (rx * y1p) ** 2 + (ry * x1p) ** 2
    )
    r2 = max(r2, 0)
    r = math.sqrt(r2)
    if large_arc == sweep:
        r = -r
    cxp = r * rx * y1p / ry
    cyp = -r * ry * x1p / rx
    cx = cp * cxp - sp * cyp + 0.5 * (x1 + x2)
    cy = sp * cxp + cp * cyp + 0.5 * (y1 + y2)
    m = Matrix([rx, 0, 0, ry, 0, 0])
    m = Matrix([cp, sp, -sp, cp, cx, cy]) * m
    if sweep == 0:
        m = m * Matrix([1, 0, 0, -1, 0, 0])
    out.write(f"{m!s} {x2:g} {y2:g} a\n")


# --------------------------------------------------------------------


class Matrix:
    # Default is identity matrix
    def __init__(self, string=None):
        self.values = [1, 0, 0, 1, 0, 0]
        if not string or string == "":
            return
        if isinstance(string, list):
            self.values = string
            return
        mat = re.match(r"([a-zA-Z]+)\(([^)]*)\)$", string)
        if not mat:
            sys.stderr.write(f"Unknown transform: {string}\n")
        op = mat.group(1)
        d = [float(x) for x in parse_list(mat.group(2))]
        if op == "matrix":
            self.values = d
        elif op == "translate":
            if len(d) == 1:
                d.append(0.0)
            self.values = [1, 0, 0, 1, d[0], d[1]]
        elif op == "scale":
            if len(d) == 1:
                d.append(d[0])
            sx, sy = d
            self.values = [sx, 0, 0, sy, 0, 0]
        elif op == "rotate":
            phi = math.pi * d[0] / 180.0
            self.values = [
                math.cos(phi),
                math.sin(phi),
                -math.sin(phi),
                math.cos(phi),
                0,
                0,
            ]
        elif op == "skewX":
            tphi = math.tan(math.pi * d[0] / 180.0)
            self.values = [1, 0, tphi, 1, 0, 0]
        elif op == "skewY":
            tphi = math.tan(math.pi * d[0] / 180.0)
            self.values = [1, tphi, 0, 1, 0, 0]
        else:
            sys.stderr.write(f"Unknown transform: {string}\n")

    def __call__(self, other):
        return (
            self.values[0] * other[0] + self.values[2] * other[1] + self.values[4],
            self.values[1] * other[0] + self.values[3] * other[1] + self.values[5],
        )

    def inverse(self):
        d = float(self.values[0] * self.values[3] - self.values[1] * self.values[2])
        return Matrix(
            [
                self.values[3] / d,
                -self.values[1] / d,
                -self.values[2] / d,
                self.values[0] / d,
                (self.values[2] * self.values[5] - self.values[3] * self.values[4]) / d,
                (self.values[1] * self.values[4] - self.values[0] * self.values[5]) / d,
            ]
        )

    def __mul__(self, other):
        a, b, c, d, e, f = self.values
        u, v, w, x, y, z = other.values
        return Matrix(
            [
                a * u + c * v,
                b * u + d * v,
                a * w + c * x,
                b * w + d * x,
                a * y + c * z + e,
                b * y + d * z + f,
            ]
        )

    def __str__(self):
        a, b, c, d, e, f = self.values
        return f"{a:g} {b:g} {c:g} {d:g} {e:g} {f:g}"


# --------------------------------------------------------------------


class LinearGradient(NamedTuple):
    x1: float
    y1: float
    x2: float
    y2: float
    stops: list
    matrix: Matrix
    href: str


class RadialGradient(NamedTuple):
    cx: float
    cy: float
    r: float
    fx: float
    fy: float
    stops: list
    matrix: Matrix
    href: str


class Svg:
    def __init__(self, fname):
        try:
            if fname == "--":
                self.dom = xml.parseString(sys.stdin.read())
            else:
                self.dom = xml.parse(fname)

        except ExpatError as exc:
            sys.stderr.write("ERROR: Input is not valid xml data:\n")
            sys.stderr.write(exc.message)
            return

        attr = {}
        for a in attribute_names:
            attr[a] = None
        self.attributes = [attr]
        self.defs = {}
        self.symbols = {}
        self.elements = {}
        self.active_uses = set()
        self.title = None
        self.description = None

        for n in self.dom.childNodes:
            if n.nodeType == Node.ELEMENT_NODE and n.tagName == "svg":
                if n.hasAttribute("viewBox"):
                    x, y, w, h = [
                        float(x) for x in parse_list(n.getAttribute("viewBox"))
                    ]
                    self.width = w
                    self.height = h
                    self.origin = (x, y)
                else:
                    self.width = parse_float(n.getAttribute("width")) or 500
                    self.height = parse_float(n.getAttribute("height")) or 500
                    self.origin = (0, 0)
                self.root = n
                self.elements = {
                    element.getAttribute("id"): element
                    for element in (n, *n.getElementsByTagName("*"))
                    if element.hasAttribute("id")
                }
                for child in n.childNodes:
                    if child.nodeType != Node.ELEMENT_NODE:
                        continue
                    if child.tagName == "title":
                        self.title = text_content(child)
                    elif child.tagName == "desc":
                        self.description = text_content(child)
                return

    # --------------------------------------------------------------------

    def write_ipe_header(self):
        self.out.write('<?xml version="1.0"?>\n')
        self.out.write('<!DOCTYPE ipe SYSTEM "ipe.dtd">\n')
        self.out.write(f'<ipe version="70212" creator="svgtoipe {svgtoipe_version}">\n')
        if self.title:
            self.out.write(f"<info title={quoteattr(self.title)}/>\n")
        self.out.write("<ipestyle>\n")
        self.out.write(
            ('<layout paper="%d %d" frame="%d %d" ' + 'origin="0 0" crop="no"/>\n')
            % (self.width, self.height, self.width, self.height)
        )
        for t in range(0, 100, 10):
            self.out.write(f'<opacity name="{t}%" value="{t / 100:g}"/>\n')
        # set SVG defaults
        self.out.write('<pathstyle cap="0" join="0" fillrule="wind"/>\n')
        self.out.write("</ipestyle>\n")
        # collect definitions
        self.collect_definitions(self.root)
        self.resolve_gradient_stops()
        # write definitions into stylesheet
        if len(self.defs) > 0:
            self.out.write("<ipestyle>\n")
            for k, definition in self.defs.items():
                if isinstance(definition, LinearGradient) and definition.stops:
                    self.write_linear_gradient(k)
                elif isinstance(definition, RadialGradient) and definition.stops:
                    self.write_radial_gradient(k)
            self.out.write("</ipestyle>\n")

    def resolve_gradient_stops(self):
        def resolve(name, resolving):
            gradient = self.defs[name]
            if gradient.stops or not gradient.href or name in resolving:
                return
            inherited = self.defs.get(gradient.href)
            if type(inherited) is not type(gradient):
                return
            resolve(gradient.href, resolving | {name})
            inherited = self.defs[gradient.href]
            if inherited.stops:
                self.defs[name] = gradient._replace(stops=inherited.stops)

        for name, gradient in list(self.defs.items()):
            if isinstance(gradient, (LinearGradient, RadialGradient)):
                resolve(name, set())

    def collect_definitions(self, node):
        # Collect Everything inside a <defs> tag for which we have a defs_<tagname>() method
        defs_children = node.getElementsByTagName("defs")
        for c in defs_children:
            for my_attr in dir(self):
                if my_attr[:4] == "def_":
                    tag_name = my_attr[4:]
                    # There is a parsing method for tags named <tag_name>
                    parseable_tags = node.getElementsByTagName(tag_name)
                    for tag in parseable_tags:
                        getattr(self, my_attr)(tag)

    def parse_svg(self, outname, **kwargs):
        """parses the svg, and writes it to file.
        outname, str, output filename. if '--' then parse_svg writes to stdout.

        Keywords:

        outmode, str, 'file' write in ipe file format.
                      'clipboard', write as ipe clipboard selection
        """
        outmode = kwargs.get("outmode", "file")

        if outname == "--":
            self.out = sys.stdout
            self.parse_svg_inner(outmode)
        else:
            with open(outname, "w") as self.out:
                self.parse_svg_inner(outmode)

    def parse_svg_inner(self, outmode):
        # write header
        if outmode == "file":
            self.write_ipe_header()
            self.out.write("<page>\n")
            if self.description:
                self.out.write("<notes>")
                self.out.write(escape(self.description))
                self.out.write("</notes>\n")
        elif outmode == "clipboard":
            self.out.write('<ipeselection pos="0 0">\n')
        else:
            sys.stderr.write(f"bad output mode '{outmode}'")
            return

        self.write_data()

        if outmode == "file":
            self.out.write("</page>\n")
            self.out.write("</ipe>\n")
        elif outmode == "clipboard":
            self.out.write("</ipeselection>\n")

    def write_data(self):
        # start real data
        m = Matrix([1, 0, 0, 1, 0, self.height / 2.0])
        m = m * Matrix([1, 0, 0, -1, 0, 0])
        m = m * Matrix(
            [1, 0, 0, 1, -self.origin[0], -(self.origin[1] + self.height / 2.0)]
        )
        self.out.write(f'<group matrix="{m!s}">\n')
        self.parse_nodes(self.root)
        self.out.write("</group>\n")

    def parse_nodes(self, root):
        """parses recognized svg elements"""
        for n in root.childNodes:
            if n.nodeType != Node.ELEMENT_NODE:
                continue

            if n.tagName in ignored_nodes:
                continue

            self.parse_node(n)

    def parse_node(self, node):
        if node.tagName not in (
            "g",
            "a",
            "inkscape:clipboard",
        ) and self.parse_attributes(node)["visibility"] in ("hidden", "collapse"):
            return
        node_name = "node_" + node.tagName.replace(":", "_")
        if hasattr(self, node_name):
            getattr(self, node_name)(node)
        else:
            sys.stderr.write(f"Unhandled node: {node.tagName}\n")

    # --------------------------------------------------------------------

    def write_linear_gradient(self, k):
        gradient = self.defs[k]
        self.out.write(f'<gradient name="g{k}" type="axial" extend="yes"\n')
        self.out.write(f' matrix="{gradient.matrix!s}"')
        self.out.write(
            f' coords="{gradient.x1:g} {gradient.y1:g} '
            f'{gradient.x2:g} {gradient.y2:g}">\n'
        )
        for s in gradient.stops:
            offset, color = s
            self.out.write(
                f' <stop offset="{offset:g}" color="{color[0]:g} {color[1]:g} {color[2]:g}"/>\n'
            )
        self.out.write("</gradient>\n")

    def write_radial_gradient(self, k):
        gradient = self.defs[k]
        self.out.write(f'<gradient name="g{k}" type="radial" extend="yes"\n')
        self.out.write(f' matrix="{gradient.matrix!s}"')
        self.out.write(
            f' coords="{gradient.fx:g} {gradient.fy:g} {0:g} '
            f'{gradient.cx:g} {gradient.cy:g} {gradient.r:g}">\n'
        )
        for s in gradient.stops:
            offset, color = s
            self.out.write(
                f' <stop offset="{offset:g}" color="{color[0]:g} {color[1]:g} {color[2]:g}"/>\n'
            )
        self.out.write("</gradient>\n")

    def get_stops(self, n):
        stops = []
        for m in n.childNodes:
            if m.nodeType != Node.ELEMENT_NODE:
                continue
            if m.tagName != "stop":
                continue  # should not happen
            offs = m.getAttribute("offset") or "0"
            if offs.endswith("%"):
                offs = float(offs[:-1]) / 100.0
            else:
                offs = float(offs)
            if m.hasAttribute("stop-color"):
                color = parse_color(m.getAttribute("stop-color"))
            else:
                color = [0, 0, 0]
            if m.hasAttribute("style"):
                sdict = parse_style(m.getAttribute("style"))
                if "stop-color" in sdict:
                    color = parse_color(sdict["stop-color"])
            stops.append((offs, color))
        return stops

    def node_inkscape_clipboard(self, node):
        self.parse_nodes(node)

    def def_symbol(self, node):
        # Symbols are parsed by pretending the symbol node is a group node and storing it in
        # self.symbols. Later, whenever a <use ...> tag is encountered,
        # we call node_g() on the fake group node.
        self.symbols[node.getAttribute("id")] = node

    def def_linearGradient(self, n):
        # printAttributes(n)
        kid = n.getAttribute("id")
        x1 = 0
        y1 = 0
        x2 = self.width
        y2 = self.height
        if n.hasAttribute("x1"):
            s = n.getAttribute("x1")
            if s.endswith("%"):
                x1 = self.width * float(s[:-1]) / 100.0
            else:
                x1 = parse_float(s)
        if n.hasAttribute("x2"):
            s = n.getAttribute("x2")
            if s.endswith("%"):
                x2 = self.width * float(s[:-1]) / 100.0
            else:
                x2 = parse_float(s)
        if n.hasAttribute("y1"):
            s = n.getAttribute("y1")
            if s.endswith("%"):
                y1 = self.width * float(s[:-1]) / 100.0
            else:
                y1 = parse_float(s)
        if n.hasAttribute("y2"):
            s = n.getAttribute("y2")
            if s.endswith("%"):
                y2 = self.width * float(s[:-1]) / 100.0
            else:
                y2 = parse_float(s)
        matrix = get_gradientTransform(n)
        stops = self.get_stops(n)
        href = n.getAttribute("xlink:href")
        href = href[1:] if href.startswith("#") else ""
        self.defs[kid] = LinearGradient(x1, y1, x2, y2, stops, matrix, href)

    def def_radialGradient(self, n):
        # printAttributes(n)
        kid = n.getAttribute("id")
        cx = "50%"
        cy = "50%"
        r = "50%"
        if n.hasAttribute("cx"):
            cx = n.getAttribute("cx")
        if cx.endswith("%"):
            cx = self.width * float(cx[:-1]) / 100.0
        else:
            cx = parse_float(cx)
        if n.hasAttribute("cy"):
            cy = n.getAttribute("cy")
        if cy.endswith("%"):
            cy = self.width * float(cy[:-1]) / 100.0
        else:
            cy = parse_float(cy)
        if n.hasAttribute("r"):
            r = n.getAttribute("r")
        if r.endswith("%"):
            r = self.width * float(r[:-1]) / 100.0
        else:
            r = parse_float(r)
        if n.hasAttribute("fx"):
            s = n.getAttribute("fx")
            if s.endswith("%"):
                fx = self.width * float(s[:-1]) / 100.0
            else:
                fx = parse_float(s)
        else:
            fx = cx
        if n.hasAttribute("fy"):
            s = n.getAttribute("fy")
            if s.endswith("%"):
                fy = self.width * float(s[:-1]) / 100.0
            else:
                fy = parse_float(s)
        else:
            fy = cy
        matrix = get_gradientTransform(n)
        stops = self.get_stops(n)
        href = n.getAttribute("xlink:href")
        href = href[1:] if href.startswith("#") else ""
        self.defs[kid] = RadialGradient(cx, cy, r, fx, fy, stops, matrix, href)

    def def_clipPath(self, node):
        kid = node.getAttribute("id")
        # only a single path is implemented
        for n in node.childNodes:
            if n.nodeType != Node.ELEMENT_NODE or n.tagName != "path":
                continue
            m = parse_transform(n)
            d = n.getAttribute("d")
            output = io.StringIO()
            parse_path(output, d)
            path = output.getvalue()
            output.close()
            self.defs[kid] = ("clipPath", m, path)
            return

    def def_g(self, group):
        self.collect_definitions(group)

    def def_defs(self, node):
        self.collect_definitions(node)

    # --------------------------------------------------------------------

    def parse_attributes(self, n):
        pattr = self.attributes[-1]
        attr = {}
        for a in attribute_names:
            if n.hasAttribute(a):
                value = n.getAttribute(a)
                attr[a] = pattr[a] if value == "inherit" else value
            else:
                attr[a] = pattr[a]
        if n.hasAttribute("style"):
            sdict = parse_style(n.getAttribute("style"))
            for a in attribute_names:
                if a in sdict:
                    value = sdict[a]
                    attr[a] = pattr[a] if value == "inherit" else value
        return attr

    def write_pathattributes(self, a):
        stroke = parse_color(a["stroke"])
        if stroke:
            self.out.write(' stroke="{:g} {:g} {:g}"'.format(*stroke))
        fill = a["fill"]
        if fill and fill.startswith("url("):
            mat = re.match(r"url\(#([^)]+)\).*", fill)
            if mat:
                grad = mat.group(1)
                if (
                    grad in self.defs
                    and isinstance(self.defs[grad], (LinearGradient, RadialGradient))
                    and self.defs[grad].stops
                ):
                    self.out.write(f' fill="1" gradient="g{grad}"')
                else:
                    self.out.write(' fill="0"')
        elif fill is None:
            self.out.write(' fill="0"')
        else:
            fill = parse_color(fill)
            if fill:
                self.out.write(' fill="{:g} {:g} {:g}"'.format(*fill))
        opacity = float(a["opacity"] or "1")
        fill_opacity = parse_opacity(opacity * float(a["fill-opacity"] or "1"))
        stroke_opacity = parse_opacity(opacity * float(a["stroke-opacity"] or "1"))
        if a["fill"] == "none" and stroke is None:
            stroke_opacity = 0
        if fill_opacity < 100:
            self.out.write(f' opacity="{fill_opacity}%"')
        if stroke_opacity < 100:
            self.out.write(f' stroke-opacity="{stroke_opacity}%"')
        stroke_width = parse_float(a["stroke-width"])
        if stroke_width is None:
            stroke_width = 1.0
        self.out.write(f' pen="{stroke_width:g}"')
        if a["fill-rule"] == "nonzero":
            self.out.write(' fillrule="wind"')
        k = {"butt": 0, "round": 1, "square": 2}
        if a["stroke-linecap"] in k:
            self.out.write(f' cap="{k[a["stroke-linecap"]]}"')
        k = {"miter": 0, "round": 1, "bevel": 2}
        if a["stroke-linejoin"] in k:
            self.out.write(f' join="{k[a["stroke-linejoin"]]}"')
        dasharray = a["stroke-dasharray"]
        dashoffset = a["stroke-dashoffset"]
        if dasharray and dashoffset and dasharray != "none":
            d = parse_list(dasharray)
            off = parse_float(dashoffset)
            self.out.write(' dash="[{}] {:g}"'.format(" ".join(d), off))

    # --------------------------------------------------------------------

    def node_g(self, group):
        # printAttributes(group)
        attr = self.parse_attributes(group)
        self.attributes.append(attr)
        self.out.write("<group")
        m = parse_transform(group)
        if m:
            self.out.write(f' matrix="{m}"')
        self.out.write(">\n")
        self.parse_nodes(group)
        self.out.write("</group>\n")
        self.attributes.pop()

    def node_use(self, n):
        if not n.hasAttribute("xlink:href"):
            print("Ignoring use node without xlink:href")
            return

        target_name = n.getAttribute("xlink:href")
        if not target_name.startswith("#"):
            print("Ignoring use node not referencing symbol ID")
            return

        target_name = target_name[1:]
        target = self.symbols.get(target_name) or self.elements.get(target_name)

        if target is None:
            print(f"Ignoring use node for unknown ID '{target_name}'")
            return

        if target_name in self.active_uses:
            print(f"Ignoring recursive use of '{target_name}'")
            return

        translate_x = "0"
        translate_y = "0"
        if n.hasAttribute("x"):
            translate_x = n.getAttribute("x")
        if n.hasAttribute("y"):
            translate_y = n.getAttribute("y")

        scale_x = 1.0
        scale_y = 1.0
        if target_name in self.symbols:
            if n.hasAttribute("width"):
                if not n.getAttribute("width").endswith("%"):
                    print("Ignoring use with non-relative width scale.")
                    return
                scale_x = float(n.getAttribute("width")[:-1]) / 100.0
            if n.hasAttribute("height"):
                if not n.getAttribute("height").endswith("%"):
                    print("Ignoring use with non-relative height scale.")
                    return
                scale_y = float(n.getAttribute("height")[:-1]) / 100.0

        scale_m = Matrix(f"scale({scale_x} {scale_y})")
        translate_m = Matrix(f"translate({translate_x} {translate_y})")
        m = scale_m * translate_m

        # Use a group for the possible transform matrix from this
        # use node
        self.out.write(f'<group   matrix="{m}">\n')
        self.attributes.append(self.parse_attributes(n))
        self.active_uses.add(target_name)
        try:
            if target_name in self.symbols:
                self.node_g(target)
            else:
                self.parse_node(target)
        finally:
            self.active_uses.remove(target_name)
            self.attributes.pop()
        self.out.write("</group>\n")

    def node_a(self, n):
        url = n.getAttribute("xlink:href")
        if url is not None:
            self.out.write(f'<group url="{url}">')
        self.parse_nodes(n)
        if url is not None:
            self.out.write("</group>\n")

    def collect_text(self, root):
        for n in root.childNodes:
            if n.nodeType == Node.TEXT_NODE:
                self.text += n.data
            if n.nodeType != Node.ELEMENT_NODE:
                continue
            if n.tagName == "tspan":  # recurse
                self.collect_text(n)

    def parse_text_style(self, t):
        attrs = {}
        if not t.hasAttribute("style"):
            return attrs

        tokens = t.getAttribute("style").split(";")
        for token in tokens:
            if len(token.split(":")) != 2:
                # Strange token
                sys.stderr.write(f"Ignored style token: {token}\n")
                continue
            key, value = token.split(":")
            value = value.strip().lower()
            key = key.strip().lower()

            if key == "font-weight":
                if value in ("bold", "bolder"):
                    attrs["weight"] = "bold"
            elif key == "font-size":
                attrs["size"] = parse_float(value)
            elif key == "font-family":
                attrs["svg-families"] = [v.strip() for v in (value.split(","))]
            elif key == "text-anchor":
                attrs["anchor"] = value

        return attrs

    def parse_text_attrs(self, t):
        raw_attrs = self.parse_attributes(t)
        attrs = {}

        if raw_attrs["font-size"]:
            attrs["size"] = parse_float(raw_attrs["font-size"])
        if raw_attrs["fill"]:
            attrs["color"] = parse_color(raw_attrs["fill"])

        return attrs

    def map_svg_font_families(self, families):
        # return the first family for which we find a mapping
        for family in families:
            if family in ("helvetica", "sans-serif"):
                return "phv"
            elif family in ("times new roman", "times", "serif"):
                return "ptm"
        return None

    def node_text(self, t):
        if not t.hasAttribute("x"):
            x = 0.0
        else:
            x = float(t.getAttribute("x"))

        if not t.hasAttribute("y"):
            y = 0.0
        else:
            y = float(t.getAttribute("y"))

        attributes = self.parse_text_style(t)
        attributes.update(self.parse_text_attrs(t))

        self.out.write(f'<text pos="{x:g} {y:g}"')
        self.out.write(' transformations="affine" valign="baseline"')
        m = parse_transform(t)
        if not m:
            m = Matrix()
        m = m * Matrix([1, 0, 0, -1, x, y]) * Matrix([1, 0, 0, 1, -x, -y])
        self.out.write(f' matrix="{m}"')

        if "size" in attributes:
            self.out.write(' size="{:g}"'.format(attributes["size"]))

        if "color" in attributes and attributes["color"] is not None:
            self.out.write(' stroke="{:g} {:g} {:g}"'.format(*attributes["color"]))

        halign = "left"
        valign = "bottom"
        if "anchor" in attributes:
            if attributes["anchor"] == "middle":
                halign = "center"
                valign = "center"
            elif attributes["anchor"] == "end":
                halign = "right"
        self.out.write(f' valign="{valign}"')
        self.out.write(f' halign="{halign}"')

        self.text = ""
        self.collect_text(t)
        self.text = self.text.translate(
            str.maketrans(
                {
                    "\\": r"$\backslash$",
                    **{character: "\\" + character for character in "#$%&_^"},
                }
            )
        )

        if "svg-families" in attributes:
            mapped_family = self.map_svg_font_families(attributes["svg-families"])
            if mapped_family is not None:
                self.text = (
                    "{\\fontfamily{"
                    + mapped_family
                    + "}\\selectfont{}"
                    + self.text
                    + "}"
                )

        if "weight" in attributes and attributes["weight"] == "bold":
            self.text = "\\bf{" + self.text + "}"

        self.out.write(f">{escape(self.text)}</text>\n")

    def node_image(self, node):
        if not have_pil:
            sys.stderr.write("No Python image library, <image> ignored\n")
            return
        href = node.getAttribute("xlink:href")
        if not href.startswith("data:image/png;base64,"):
            sys.stderr.write(f"Image ignored, href = {href[:40]}...\n")
            return
        x = float(node.getAttribute("x"))
        y = float(node.getAttribute("y"))
        w = float(node.getAttribute("width"))
        h = float(node.getAttribute("height"))
        clipped = False
        if node.hasAttribute("clip-path"):
            mat = re.match(r"url\(#([^)]+)\).*", node.getAttribute("clip-path"))
            if mat:
                cp = mat.group(1)
                if cp in self.defs and self.defs[cp][0] == "clipPath":
                    cp, m, path = self.defs[cp]
                    clipped = True
                    self.out.write(f'<group matrix="{m!s}" clip="{path}">\n')
                    self.out.write(f'<group matrix="{m.inverse()!s}">\n')
        self.out.write(f'<image rect="{x:g} {y:g} {x + w:g} {y + h:g}"')
        data = base64.b64decode(href[22:])
        fin = io.BytesIO(data)
        image = Image.open(fin)
        has_alpha = "A" in image.getbands() or "transparency" in image.info
        image = image.convert("RGBA" if has_alpha else "RGB")
        m = parse_transform(node)
        if not m:
            m = Matrix()
        m = m * Matrix([1, 0, 0, -1, x, y + h]) * Matrix([1, 0, 0, 1, -x, -y])
        self.out.write(f' matrix="{m}"')
        color_space = "DeviceRGBAlpha" if has_alpha else "DeviceRGB"
        self.out.write(
            f' width="{image.size[0]}" height="{image.size[1]}" ColorSpace="{color_space}"'
        )
        self.out.write(' BitsPerComponent="8" encoding="base64"> \n')
        data = bytearray()
        for pixel in image.getdata():
            if has_alpha:
                data.extend((pixel[3], pixel[0], pixel[1], pixel[2]))
            else:
                data.extend(pixel[:3])
        self.out.write(base64.b64encode(data).decode("ascii"))
        fin.close()
        self.out.write("</image>\n")
        if clipped:
            self.out.write("</group>\n</group>\n")

    # handled in def pass
    def node_linearGradient(self, n):
        pass

    def node_radialGradient(self, n):
        pass

    def node_rect(self, n):
        attr = self.parse_attributes(n)
        self.out.write("<path")
        m = parse_transform(n)
        if m:
            self.out.write(f' matrix="{m}"')
        self.write_pathattributes(attr)
        self.out.write(">\n")
        if not n.hasAttribute("x"):
            x = 0.0
        else:
            x = parse_float(n.getAttribute("x"))

        if not n.hasAttribute("y"):
            y = 0.0
        else:
            y = parse_float(n.getAttribute("y"))
        w = parse_float(n.getAttribute("width"))
        h = parse_float(n.getAttribute("height"))
        self.out.write(
            f"{x:g} {y:g} m {x + w:g} {y:g} l {x + w:g} {y + h:g} l {x:g} {y + h:g} l h\n"
        )
        self.out.write("</path>\n")

    def node_circle(self, n):
        self.out.write("<path")
        m = parse_transform(n)
        if m:
            self.out.write(f' matrix="{m}"')
        attr = self.parse_attributes(n)
        self.write_pathattributes(attr)
        self.out.write(">\n")
        cx = 0
        cy = 0
        if n.hasAttribute("cx"):
            cx = parse_float(n.getAttribute("cx"))
        if n.hasAttribute("cy"):
            cy = parse_float(n.getAttribute("cy"))
        r = parse_float(n.getAttribute("r"))
        self.out.write(f"{r:g} 0 0 {r:g} {cx:g} {cy:g} e\n")
        self.out.write("</path>\n")

    def node_ellipse(self, n):
        self.out.write("<path")
        m = parse_transform(n)
        if m:
            self.out.write(f' matrix="{m}"')
        attr = self.parse_attributes(n)
        self.write_pathattributes(attr)
        self.out.write(">\n")
        cx = 0
        cy = 0
        if n.hasAttribute("cx"):
            cx = float(n.getAttribute("cx"))
        if n.hasAttribute("cy"):
            cy = float(n.getAttribute("cy"))
        rx = float(n.getAttribute("rx"))
        ry = float(n.getAttribute("ry"))
        self.out.write(f"{rx:g} 0 0 {ry:g} {cx:g} {cy:g} e\n")
        self.out.write("</path>\n")

    def node_line(self, n):
        self.out.write("<path")
        m = parse_transform(n)
        if m:
            self.out.write(f' matrix="{m}"')
        attr = self.parse_attributes(n)
        self.write_pathattributes(attr)
        self.out.write(">\n")
        x1 = 0
        y1 = 0
        x2 = 0
        y2 = 0
        if n.hasAttribute("x1"):
            x1 = float(n.getAttribute("x1"))
        if n.hasAttribute("y1"):
            y1 = float(n.getAttribute("y1"))
        if n.hasAttribute("x2"):
            x2 = float(n.getAttribute("x2"))
        if n.hasAttribute("y2"):
            y2 = float(n.getAttribute("y2"))
        self.out.write(f"{x1:g} {y1:g} m {x2:g} {y2:g} l\n")
        self.out.write("</path>\n")

    def node_polyline(self, n):
        self.polygon(n, closed=False)

    def node_polygon(self, n):
        self.polygon(n, closed=True)

    def polygon(self, n, closed):
        self.out.write("<path")
        m = parse_transform(n)
        if m:
            self.out.write(f' matrix="{m}"')
        attr = self.parse_attributes(n)
        self.write_pathattributes(attr)
        self.out.write(">\n")
        d = parse_list(n.getAttribute("points"))
        op = "m"
        while d:
            x = float(d.pop(0))
            y = float(d.pop(0))
            self.out.write(f"{x:g} {y:g} {op}\n")
            op = "l"
        if closed:
            self.out.write("h\n")
        self.out.write("</path>\n")

    def node_path(self, n):
        d = n.getAttribute("d")
        if len(d) == 0:
            # Empty paths crash ipe, filter them out
            return

        self.out.write("<path")
        m = parse_transform(n)
        if m:
            self.out.write(f' matrix="{m}"')
        attr = self.parse_attributes(n)
        self.write_pathattributes(attr)
        self.out.write(">\n")
        parse_path(self.out, d)
        self.out.write("</path>\n")


# --------------------------------------------------------------------


def parse_arguments():
    """parses command line arguments"""
    parser = argparse.ArgumentParser(
        description="convert SVG into Ipe files",
        epilog="""
              Supported SVG elements:
                  path,image,rect,circle,ellipse,line,polygon,polyline
              Supported SVG attributes:
                  group,clipPath,linearGradient,radialGradient
              """,
    )

    parser.add_argument(
        "-c",
        "--clipboard",
        dest="clipboard",
        action="store_true",
        help="""
        if -c is present, svg data is written as clipboard content.
        This allows pasting svg data from inkscape to ipe:
        (1) Copy Inkscape elements to clipboard,
        (2) run: 'xsel | ./svgtoipe.py -c -- | xsel -i',
        (3) paste clipboard content into Ipe.
        """,
    )

    parser.add_argument(
        "infile",
        metavar="svg-file.svg",
        help="input file in svg format. If infile = '--' svg data is read from stdin.",
    )

    parser.add_argument(
        "outfile",
        metavar="ipe-file.ipe",
        nargs="?",
        help="""
                filename to write output. If no filename is given, the input filename
                together with '.ipe' extension is used. If outfile is '--', then data
                is written to stdout.""",
    )

    parser.set_defaults(
        infile="--",
        verbosity=0,
        clipboard=False,
    )

    args = parser.parse_args()
    if args.outfile is None and args.infile != "--":
        args.outfile = args.infile[:-4] + ".ipe"

    return args


def main():
    args = parse_arguments()

    svg = Svg(args.infile)
    if args.clipboard:
        svg.parse_svg(args.outfile, outmode="clipboard")
    else:
        svg.parse_svg(args.outfile)

    sys.exit(0)


if __name__ == "__main__":
    main()

# --------------------------------------------------------------------
