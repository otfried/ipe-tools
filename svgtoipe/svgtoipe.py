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

ignored_nodes = {
    "defs",
    "clipPath",
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
    "font-weight",
    "font-family",
    "text-anchor",
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


def parse_stop_opacity(txt):
    if not txt:
        return 1.0
    value = float(txt[:-1]) / 100.0 if txt.endswith("%") else float(txt)
    return max(0.0, min(1.0, value))


def parse_dash(dasharray, dashoffset):
    """(lengths, offset) for stroke-dasharray, or None for solid or invalid dashes."""
    values = [v for v in re.split(r"[\s,]+", (dasharray or "").strip()) if v]
    if not values or values == ["none"]:
        return None
    try:
        dashes = [parse_float(v) for v in values]
        offset = parse_float(dashoffset) or 0.0
    except ValueError:
        return None
    if len(dashes) % 2:
        dashes *= 2  # an odd list is repeated, so that dashes and gaps alternate
    if min(dashes) < 0 or sum(dashes) == 0:
        return None
    return dashes, offset


def parse_list(string):
    # numbers may start with the decimal point, as in "scale(.5)"
    return re.findall(
        r"([A-Za-z]|-?(?:\.[0-9]+|[0-9]+\.?[0-9]*)(?:[eE][-+]?[0-9]+)?)", string
    )


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


# a gradient paint is written "url(#id) fallback" in SVG
GRADIENT_PAINT = re.compile(r"\s*url\(\s*#([^)\s]+)\s*\)\s*(.*)$")


def get_href(n):
    """Link target of an element; SVG 2 allows href without the xlink prefix."""
    return n.getAttribute("xlink:href") or n.getAttribute("href")


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
    last_op = None
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
            if last_op in ("C", "c", "S", "s"):
                x1 = x + (x - xs)
                y1 = y + (y - ys)
            else:
                x1, y1 = x, y
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
            if last_op in ("Q", "q", "T", "t"):
                x1 = x + (x - xs)
                y1 = y + (y - ys)
            else:
                x1, y1 = x, y
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
        last_op = opcode


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


def viewport_length(txt):
    # percentages and missing values mean no usable absolute size
    if not txt or txt.endswith("%"):
        return None
    return parse_float(txt)


def viewbox_matrix(viewbox, size, aspect):
    """Matrix mapping viewBox user space to a viewport of the given size."""
    x, y, w, h = viewbox
    width, height = size
    tokens = (aspect or "").split()
    if tokens and tokens[0] == "defer":
        tokens = tokens[1:]
    align = tokens[0] if tokens else "xMidYMid"
    sx, sy = width / w, height / h
    tx = ty = 0.0
    if align != "none":
        sx = sy = max(sx, sy) if tokens[1:] == ["slice"] else min(sx, sy)
        tx = (width - sx * w) * {"xMin": 0.0, "xMax": 1.0}.get(align[:4], 0.5)
        ty = (height - sy * h) * {"YMin": 0.0, "YMax": 1.0}.get(align[4:], 0.5)
    return Matrix([sx, 0, 0, sy, tx - sx * x, ty - sy * y])


def bezier_points(p0, p1, p2, p3):
    """Endpoints and axis-extreme points of a cubic Bezier segment."""
    points = [p0, p3]
    ts = []
    for axis in (0, 1):
        v0, v1, v2, v3 = p0[axis], p1[axis], p2[axis], p3[axis]
        a = -v0 + 3 * v1 - 3 * v2 + v3
        b = 2 * (v0 - 2 * v1 + v2)
        c = v1 - v0
        if abs(a) > 1e-12:
            disc = b * b - 4 * a * c
            if disc >= 0:
                ts += [(-b + s * math.sqrt(disc)) / (2 * a) for s in (1, -1)]
        elif abs(b) > 1e-12:
            ts.append(-c / b)
    for t in ts:
        if 0 < t < 1:
            u = 1 - t
            points.append(
                tuple(
                    u**3 * p0[i]
                    + 3 * u * u * t * p1[i]
                    + 3 * u * t * t * p2[i]
                    + t**3 * p3[i]
                    for i in (0, 1)
                )
            )
    return points


def unit_circle_angle(matrix, p):
    """Angle of point p on the unit circle that the matrix maps to the ellipse."""
    a, b, c, d, e, f = matrix
    px, py = p[0] - e, p[1] - f
    det = a * d - b * c
    return math.atan2((a * py - b * px) / det, (d * px - c * py) / det)


def geometry_bbox(geometry):
    """Exact bounding box (x0, y0, x1, y1) of Ipe path operators, or None."""
    points = []
    nums = []
    cur = None
    for token in geometry.split():
        if not (len(token) == 1 and token.isalpha()):
            nums.append(float(token))
            continue
        pts = list(zip(nums[0::2], nums[1::2]))
        if token in ("m", "l"):
            cur = pts[0]
            points.append(cur)
        elif token == "c":
            points += bezier_points(cur, *pts)
            cur = pts[-1]
        elif token == "q":
            q1, q2 = pts
            points += bezier_points(
                cur,
                (cur[0] + 2 * (q1[0] - cur[0]) / 3, cur[1] + 2 * (q1[1] - cur[1]) / 3),
                (q2[0] + 2 * (q1[0] - q2[0]) / 3, q2[1] + 2 * (q1[1] - q2[1]) / 3),
                q2,
            )
            cur = q2
        elif token == "e":
            a, b, c, d, e, f = nums
            hx, hy = math.hypot(a, c), math.hypot(b, d)
            points += [(e - hx, f - hy), (e + hx, f + hy)]
        elif token == "a":
            a, b, c, d, e, f, x, y = nums
            det = a * d - b * c
            if det != 0:
                start = unit_circle_angle(nums[:6], cur)
                span = (unit_circle_angle(nums[:6], (x, y)) - start) % (2 * math.pi)
                for t in (math.atan2(c, a), math.atan2(d, b)):
                    for angle in (t, t + math.pi):
                        if (angle - start) % (2 * math.pi) <= span:
                            cos, sin = math.cos(angle), math.sin(angle)
                            points.append(
                                (a * cos + c * sin + e, b * cos + d * sin + f)
                            )
            cur = (x, y)
            points.append(cur)
        nums = []
    if not points:
        return None
    xs, ys = zip(*points)
    return (min(xs), min(ys), max(xs), max(ys))


# Convert from endpoint to center parameterization
# www.w3.org/TR/2003/REC-SVG11-20030114/implnote.html#ArcImplementationNotes
def draw_arc(out, x1, y1, rx, ry, phi, large_arc, sweep, x2, y2):
    if x1 == x2 and y1 == y2:
        return  # SVG omits the arc entirely
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0:
        out.write(f"{x2:g} {y2:g} l\n")  # SVG treats it as a straight line
        return
    phi = math.pi * phi / 180.0
    cp = math.cos(phi)
    sp = math.sin(phi)
    dx = 0.5 * (x1 - x2)
    dy = 0.5 * (y1 - y2)
    x1p = cp * dx + sp * dy
    y1p = -sp * dx + cp * dy
    # radii too small to reach the endpoint are scaled up (SVG F.6.6)
    scale = math.sqrt((x1p / rx) ** 2 + (y1p / ry) ** 2)
    if scale > 1:
        rx *= scale
        ry *= scale
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
            c, s = math.cos(phi), math.sin(phi)
            cx, cy = (d[1], d[2]) if len(d) >= 3 else (0.0, 0.0)
            self.values = [c, s, -s, c, cx - c * cx + s * cy, cy - s * cx - c * cy]
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

    def determinant(self):
        a, b, c, d = self.values[:4]
        return a * d - b * c

    def linear_scale(self):
        return math.sqrt(abs(self.determinant()))


# --------------------------------------------------------------------


class LinearGradient(NamedTuple):
    x1: float
    y1: float
    x2: float
    y2: float
    stops: list
    matrix: Matrix
    href: str
    units: str = "objectBoundingBox"


class RadialGradient(NamedTuple):
    cx: float
    cy: float
    r: float
    fx: float
    fy: float
    stops: list
    matrix: Matrix
    href: str
    units: str = "objectBoundingBox"


class ClipPath(NamedTuple):
    shapes: list  # (matrix, Ipe path operators) for each child shape
    ref: str  # clip-path of the clipPath itself, intersected with its shapes
    supported: bool


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
        attr["matrix"] = Matrix()
        self.attributes = [attr]
        self.defs = {}
        self.bbox_gradients = {}
        self.warned = set()
        self.symbols = {}
        self.elements = {}
        self.active_uses = set()
        self.title = None
        self.description = None

        for n in self.dom.childNodes:
            if n.nodeType == Node.ELEMENT_NODE and n.tagName == "svg":
                if n.hasAttribute("viewBox"):
                    viewbox = [float(x) for x in parse_list(n.getAttribute("viewBox"))]
                    # user-space size, used for percentages in gradients
                    self.width = viewbox[2]
                    self.height = viewbox[3]
                    self.paper = (
                        viewport_length(n.getAttribute("width")) or self.width,
                        viewport_length(n.getAttribute("height")) or self.height,
                    )
                    self.viewbox_matrix = viewbox_matrix(
                        viewbox, self.paper, n.getAttribute("preserveAspectRatio")
                    )
                else:
                    self.width = viewport_length(n.getAttribute("width")) or 500
                    self.height = viewport_length(n.getAttribute("height")) or 500
                    self.paper = (self.width, self.height)
                    self.viewbox_matrix = Matrix()
                self.root = n
                # the viewBox scale also applies to stroke widths
                attr["matrix"] = self.viewbox_matrix
                self.attributes = [self.parse_attributes(n)]
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
            ('<layout paper="%g %g" frame="%g %g" ' + 'origin="0 0" crop="no"/>\n')
            % (*self.paper, *self.paper)
        )
        for t in range(0, 100, 10):
            self.out.write(f'<opacity name="{t}%" value="{t / 100:g}"/>\n')
        # set SVG defaults
        self.out.write('<pathstyle cap="0" join="0" fillrule="wind"/>\n')
        self.out.write("</ipestyle>\n")
        # write definitions into stylesheet
        gradients = [
            (f"g{k}", definition)
            for k, definition in self.defs.items()
            if isinstance(definition, (LinearGradient, RadialGradient))
            and definition.stops
            and definition.units == "userSpaceOnUse"
        ]
        gradients += self.bbox_gradients.values()
        if gradients:
            self.out.write("<ipestyle>\n")
            for name, gradient in gradients:
                if isinstance(gradient, LinearGradient):
                    self.write_linear_gradient(name, gradient)
                else:
                    self.write_radial_gradient(name, gradient)
            self.out.write("</ipestyle>\n")

    def resolve_gradient_stops(self):
        def resolve(name, resolving):
            gradient = self.defs[name]
            if gradient.stops or not gradient.href or name in resolving:
                return
            inherited = self.defs.get(gradient.href)
            # stops may come from a gradient of either type
            if not isinstance(inherited, (LinearGradient, RadialGradient)):
                return
            resolve(gradient.href, resolving | {name})
            inherited = self.defs[gradient.href]
            if inherited.stops:
                self.defs[name] = gradient._replace(stops=inherited.stops)

        for name, gradient in list(self.defs.items()):
            if isinstance(gradient, (LinearGradient, RadialGradient)):
                resolve(name, set())

    def collect_definitions(self, node):
        # SVG allows these elements anywhere, not only inside <defs>
        for my_attr in dir(self):
            if my_attr[:4] == "def_":
                for tag in node.getElementsByTagName(my_attr[4:]):
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
        if outmode not in ("file", "clipboard"):
            sys.stderr.write(f"bad output mode '{outmode}'")
            return

        if outmode == "file":
            self.collect_definitions(self.root)
            self.resolve_gradient_stops()

        # the body goes first into a buffer: per-shape gradients are only known
        # after writing it, but the stylesheet must precede the page
        out, self.out = self.out, io.StringIO()
        self.write_data()
        body, self.out = self.out.getvalue(), out

        if outmode == "file":
            self.write_ipe_header()
            self.out.write("<page>\n")
            if self.description:
                self.out.write("<notes>")
                self.out.write(escape(self.description))
                self.out.write("</notes>\n")
        else:
            self.out.write('<ipeselection pos="0 0">\n')

        self.out.write(body)

        if outmode == "file":
            self.out.write("</page>\n")
            self.out.write("</ipe>\n")
        else:
            self.out.write("</ipeselection>\n")

    def write_data(self):
        # start real data: viewBox mapping, then flip y into Ipe's y-up paper
        m = Matrix([1, 0, 0, -1, 0, self.paper[1]]) * self.viewbox_matrix
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
        if not hasattr(self, node_name):
            sys.stderr.write(f"Unhandled node: {node.tagName}\n")
            return
        opened = self.open_clip_groups(node)
        getattr(self, node_name)(node)
        self.out.write("</group>\n" * opened)

    # --------------------------------------------------------------------

    def write_linear_gradient(self, name, gradient):
        self.out.write(f'<gradient name="{name}" type="axial" extend="yes"\n')
        self.out.write(f' matrix="{gradient.matrix!s}"')
        self.out.write(
            f' coords="{gradient.x1:g} {gradient.y1:g} '
            f'{gradient.x2:g} {gradient.y2:g}">\n'
        )
        self.write_stops(gradient)
        self.out.write("</gradient>\n")

    def write_radial_gradient(self, name, gradient):
        self.out.write(f'<gradient name="{name}" type="radial" extend="yes"\n')
        self.out.write(f' matrix="{gradient.matrix!s}"')
        self.out.write(
            f' coords="{gradient.fx:g} {gradient.fy:g} {0:g} '
            f'{gradient.cx:g} {gradient.cy:g} {gradient.r:g}">\n'
        )
        self.write_stops(gradient)
        self.out.write("</gradient>\n")

    def write_stops(self, gradient):
        for offset, color, opacity in gradient.stops:
            self.out.write(
                f' <stop offset="{offset:g}" color="{color[0]:g} {color[1]:g} {color[2]:g}"'
            )
            if opacity < 1:
                self.out.write(f' opacity="{opacity:g}"')
            self.out.write("/>\n")

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
            opacity = m.getAttribute("stop-opacity")
            if m.hasAttribute("style"):
                sdict = parse_style(m.getAttribute("style"))
                if "stop-color" in sdict:
                    color = parse_color(sdict["stop-color"])
                opacity = sdict.get("stop-opacity", opacity)
            stops.append((offs, color, parse_stop_opacity(opacity)))
        return stops

    def node_inkscape_clipboard(self, node):
        self.parse_nodes(node)

    def def_symbol(self, node):
        # Symbols are parsed by pretending the symbol node is a group node and storing it in
        # self.symbols. Later, whenever a <use ...> tag is encountered,
        # we call node_g() on the fake group node.
        self.symbols[node.getAttribute("id")] = node

    def gradient_units(self, n):
        """Returns the gradient's units and the sizes that percentages refer to."""
        if n.getAttribute("gradientUnits") == "userSpaceOnUse":
            diagonal = math.sqrt((self.width**2 + self.height**2) / 2)
            return "userSpaceOnUse", (self.width, self.height, diagonal)
        # also the fallback for invalid values; percentages are fractions of the box
        return "objectBoundingBox", (1.0, 1.0, 1.0)

    def gradient_length(self, n, name, default, size):
        s = n.getAttribute(name) or default
        if s.endswith("%"):
            return float(s[:-1]) / 100.0 * size
        return parse_float(s)

    def def_linearGradient(self, n):
        kid = n.getAttribute("id")
        units, (w, h, _) = self.gradient_units(n)
        x1 = self.gradient_length(n, "x1", "0%", w)
        y1 = self.gradient_length(n, "y1", "0%", h)
        x2 = self.gradient_length(n, "x2", "100%", w)
        y2 = self.gradient_length(n, "y2", "0%", h)
        matrix = get_gradientTransform(n)
        stops = self.get_stops(n)
        href = get_href(n)
        href = href[1:] if href.startswith("#") else ""
        self.defs[kid] = LinearGradient(x1, y1, x2, y2, stops, matrix, href, units)

    def def_radialGradient(self, n):
        kid = n.getAttribute("id")
        units, (w, h, diagonal) = self.gradient_units(n)
        cx = self.gradient_length(n, "cx", "50%", w)
        cy = self.gradient_length(n, "cy", "50%", h)
        r = self.gradient_length(n, "r", "50%", diagonal)
        # the focal point defaults to the centre
        fx = self.gradient_length(n, "fx", n.getAttribute("cx") or "50%", w)
        fy = self.gradient_length(n, "fy", n.getAttribute("cy") or "50%", h)
        matrix = get_gradientTransform(n)
        stops = self.get_stops(n)
        href = get_href(n)
        href = href[1:] if href.startswith("#") else ""
        self.defs[kid] = RadialGradient(cx, cy, r, fx, fy, stops, matrix, href, units)

    def def_clipPath(self, node):
        shapes = []
        supported = node.getAttribute("clipPathUnits") != "objectBoundingBox"
        for n in node.childNodes:
            if n.nodeType != Node.ELEMENT_NODE or n.tagName in ignored_nodes:
                continue
            shape = self.clip_shape(n)
            if shape is None:
                supported = False
            else:
                shapes.append(shape)
        self.defs[node.getAttribute("id")] = ClipPath(
            shapes, self.clip_reference(node), supported
        )

    def clip_shape(self, n, seen=()):
        """(matrix, Ipe path operators) of a shape in a clipPath, None if unsupported."""
        if n.tagName == "use":
            href = get_href(n)
            target = self.elements.get(href[1:])
            if not href.startswith("#") or target is None or href in seen:
                return None
            inner = self.clip_shape(target, (*seen, href))
            if inner is None:
                return None
            dx = parse_float(n.getAttribute("x")) or 0.0
            dy = parse_float(n.getAttribute("y")) or 0.0
            offset = Matrix([1, 0, 0, 1, dx, dy])
            return ((parse_transform(n) or Matrix()) * offset * inner[0], inner[1])
        geometry = self.shape_geometry(n)
        if geometry is None:
            return None
        return (parse_transform(n) or Matrix(), geometry)

    def clip_reference(self, n):
        if n.hasAttribute("style"):
            ref = parse_style(n.getAttribute("style")).get("clip-path")
            if ref:
                return ref
        return n.getAttribute("clip-path")

    def warn_once(self, message):
        if message not in self.warned:
            self.warned.add(message)
            sys.stderr.write(message + "\n")

    def clip_regions(self, ref, seen=()):
        """Shapes whose intersection is the clip region; None if not expressible."""
        mat = re.match(r"url\(\s*#([^)\s]+)\s*\)", ref)
        clip = self.defs.get(mat.group(1)) if mat else None
        if not isinstance(clip, ClipPath):
            return []
        name = mat.group(1)
        if not clip.supported or len(clip.shapes) != 1 or name in seen:
            if not clip.supported:
                reason = "unsupported content or clipPathUnits"
            elif name in seen:
                reason = "it refers to itself"
            else:
                reason = (
                    f"union of {len(clip.shapes)} shapes"
                    if clip.shapes
                    else "no shapes"
                )
            self.warn_once(f"Ignoring clipPath '{name}' (no clipping): {reason}")
            return None
        nested = self.clip_regions(clip.ref, (*seen, name)) if clip.ref else []
        if nested is None:
            return None
        return [clip.shapes[0], *nested]

    def open_clip_groups(self, n):
        """Opens groups clipping to n's clip-path, returns how many were opened."""
        # the clip lives in n's user space, so n's own transform applies to it too
        transform = parse_transform(n) or Matrix()
        opened = 0
        for matrix, path in self.clip_regions(self.clip_reference(n)) or []:
            m = transform * matrix
            if abs(m.determinant()) < 1e-12:
                continue
            self.out.write(f'<group matrix="{m}" clip="{" ".join(path.split())}">\n')
            self.out.write(f'<group matrix="{m.inverse()}">\n')
            opened += 2
        return opened

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
        m = parse_transform(n)
        if m:
            attr["matrix"] = pattr.get("matrix", Matrix()) * m
        else:
            attr["matrix"] = pattr.get("matrix", Matrix())
        return attr

    def usable_gradient(self, name):
        gradient = self.defs.get(name)
        if isinstance(gradient, (LinearGradient, RadialGradient)) and gradient.stops:
            return gradient
        return None

    def gradient_name(self, name, gradient, geometry):
        """Ipe name of the gradient for this shape, or None if it paints nothing."""
        if gradient.units == "userSpaceOnUse":
            return f"g{name}"
        bbox = geometry_bbox(geometry)
        # SVG paints nothing for a degenerate bounding box
        if bbox is None or bbox[0] == bbox[2] or bbox[1] == bbox[3]:
            return None
        if (name, bbox) not in self.bbox_gradients:
            x0, y0, x1, y1 = bbox
            unit_box = Matrix([x1 - x0, 0, 0, y1 - y0, x0, y0])
            self.bbox_gradients[name, bbox] = (
                f"g{name}_{len(self.bbox_gradients) + 1}",
                gradient._replace(matrix=unit_box * gradient.matrix),
            )
        return self.bbox_gradients[name, bbox][0]

    def paint_gradient(self, paint, geometry):
        """For a 'url(#id) fallback' paint: (colour, Ipe gradient name or None)."""
        name, fallback = paint.group(1), parse_color(paint.group(2))
        gradient = self.usable_gradient(name)
        if gradient is None:
            element = self.elements.get(name)
            if element is None:
                reason = "not found"
            elif element.tagName in ("linearGradient", "radialGradient"):
                reason = "has no stops"
            else:
                reason = f"is a <{element.tagName}>, which is not supported"
            self.warn_once(f"Paint server '{name}' {reason}")
            return fallback, None
        gname = self.gradient_name(name, gradient, geometry)
        if gname is None:
            return None, None  # degenerate bounding box: nothing is painted
        return fallback or gradient.stops[0][1], gname

    def write_pathattributes(self, a, geometry):
        stroke_gradient = None
        paint = GRADIENT_PAINT.match(a["stroke"] or "")
        if paint:
            stroke, stroke_gradient = self.paint_gradient(paint, geometry)
        else:
            stroke = parse_color(a["stroke"])
        if stroke:
            self.out.write(' stroke="{:g} {:g} {:g}"'.format(*stroke))
        if stroke_gradient:
            self.out.write(f' stroke-gradient="{stroke_gradient}"')
        fill = a["fill"]
        fill_painted = True
        paint = GRADIENT_PAINT.match(fill or "")
        if paint:
            colour, fill_gradient = self.paint_gradient(paint, geometry)
            if fill_gradient:
                self.out.write(f' fill="1" gradient="{fill_gradient}"')
            elif colour:
                self.out.write(' fill="{:g} {:g} {:g}"'.format(*colour))
            else:
                fill_painted = False
        elif fill is None:
            self.out.write(' fill="0"')
        else:
            colour = parse_color(fill)
            if colour:
                self.out.write(' fill="{:g} {:g} {:g}"'.format(*colour))
            elif fill == "none":
                fill_painted = False
        opacity = float(a["opacity"] or "1")
        fill_opacity = parse_opacity(opacity * float(a["fill-opacity"] or "1"))
        stroke_opacity = parse_opacity(opacity * float(a["stroke-opacity"] or "1"))
        if not fill_painted and stroke is None:
            stroke_opacity = 0
        if fill_opacity < 100:
            self.out.write(f' opacity="{fill_opacity}%"')
        if stroke_opacity < 100:
            self.out.write(f' stroke-opacity="{stroke_opacity}%"')
        elif fill_opacity < 100:
            # if stroke-opacity is missing, Ipe uses opacity!
            self.out.write(' stroke-opacity="opaque"')
        stroke_width = parse_float(a["stroke-width"])
        if stroke_width is None:
            stroke_width = 1.0
        matrix = a.get("matrix")
        scale = matrix.linear_scale() if matrix else 1.0
        stroke_width *= scale
        self.out.write(f' pen="{stroke_width:g}"')
        # the stylesheet makes "wind" (SVG's default) the default; Ipe's own is even-odd
        fill_rules = {"nonzero": "wind", "evenodd": "eofill"}
        if a["fill-rule"] in fill_rules:
            self.out.write(f' fillrule="{fill_rules[a["fill-rule"]]}"')
        k = {"butt": 0, "round": 1, "square": 2}
        if a["stroke-linecap"] in k:
            self.out.write(f' cap="{k[a["stroke-linecap"]]}"')
        k = {"miter": 0, "round": 1, "bevel": 2}
        if a["stroke-linejoin"] in k:
            self.out.write(f' join="{k[a["stroke-linejoin"]]}"')
        dash = parse_dash(a["stroke-dasharray"], a["stroke-dashoffset"])
        if dash:
            dashes, offset = dash
            lengths = " ".join(f"{v * scale:g}" for v in dashes)
            self.out.write(f' dash="[{lengths}] {offset * scale:g}"')

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
        target_name = get_href(n)
        if not target_name:
            print("Ignoring use node without href")
            return

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
        use_transform = parse_transform(n)
        group_m = use_transform * m if use_transform else m

        # Use a group for the possible transform matrix from this
        # use node
        self.out.write(f'<group   matrix="{group_m}">\n')
        # parse_attributes already folded the use's own transform into "matrix"
        attr = self.parse_attributes(n)
        attr["matrix"] = attr["matrix"] * m
        self.attributes.append(attr)
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
        url = get_href(n)
        if url is not None:
            self.out.write(f'<group url="{url}">')
        self.parse_nodes(n)
        if url is not None:
            self.out.write("</group>\n")

    def collect_text(self, root):
        for n in root.childNodes:
            if n.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE):
                self.text += n.data
            if n.nodeType != Node.ELEMENT_NODE:
                continue
            if n.tagName == "tspan":  # recurse
                self.collect_text(n)

    def parse_text_attrs(self, t):
        raw_attrs = self.parse_attributes(t)
        attrs = {}

        if raw_attrs["font-size"]:
            attrs["size"] = parse_float(raw_attrs["font-size"])
        if raw_attrs["fill"]:
            attrs["color"] = parse_color(raw_attrs["fill"])
        weight = (raw_attrs["font-weight"] or "").strip().lower()
        if weight in ("bold", "bolder"):
            attrs["weight"] = "bold"
        if raw_attrs["font-family"]:
            attrs["svg-families"] = [
                f.strip().strip("'\"").lower()
                for f in raw_attrs["font-family"].split(",")
            ]
        if raw_attrs["text-anchor"]:
            attrs["anchor"] = raw_attrs["text-anchor"].strip().lower()

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

        attributes = self.parse_text_attrs(t)

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

        # text-anchor affects only the horizontal position; SVG's y is the baseline
        halign = {"middle": "center", "end": "right"}.get(
            attributes.get("anchor"), "left"
        )
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
        href = get_href(node)
        if not href.startswith("data:image/png;base64,"):
            sys.stderr.write(f"Image ignored, href = {href[:40]}...\n")
            return
        x = float(node.getAttribute("x"))
        y = float(node.getAttribute("y"))
        w = float(node.getAttribute("width"))
        h = float(node.getAttribute("height"))
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

    # handled in def pass
    def node_linearGradient(self, n):
        pass

    def node_radialGradient(self, n):
        pass

    def write_path(self, n, geometry):
        """Writes a <path> for element n; geometry is Ipe path operators."""
        if not geometry.strip():
            return  # empty paths crash Ipe
        self.out.write("<path")
        m = parse_transform(n)
        if m:
            self.out.write(f' matrix="{m}"')
        self.write_pathattributes(self.parse_attributes(n), geometry)
        self.out.write(">\n")
        self.out.write(geometry)
        self.out.write("</path>\n")

    def shape_geometry(self, n):
        """Ipe path operators for a basic shape element, None for other elements."""
        method = getattr(self, "geometry_" + n.tagName, None)
        return method(n) if method else None

    def node_rect(self, n):
        self.write_path(n, self.geometry_rect(n))

    def geometry_rect(self, n):
        geometry = io.StringIO()
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

        rx = None
        ry = None
        if n.hasAttribute("rx"):
            s = n.getAttribute("rx")
            if s.endswith("%"):
                rx = w * float(s[:-1]) / 100.0
            else:
                rx = parse_float(s)
        if n.hasAttribute("ry"):
            s = n.getAttribute("ry")
            if s.endswith("%"):
                ry = h * float(s[:-1]) / 100.0
            else:
                ry = parse_float(s)
        if n.hasAttribute("style"):
            sdict = parse_style(n.getAttribute("style"))
            if "rx" in sdict and rx is None:
                s = sdict["rx"]
                if s.endswith("%"):
                    rx = w * float(s[:-1]) / 100.0
                else:
                    rx = parse_float(s)
            if "ry" in sdict and ry is None:
                s = sdict["ry"]
                if s.endswith("%"):
                    ry = h * float(s[:-1]) / 100.0
                else:
                    ry = parse_float(s)
        if rx is None and ry is None:
            rx = 0.0
            ry = 0.0
        elif rx is None:
            rx = ry
        elif ry is None:
            ry = rx
        rx = max(0.0, min(rx, w / 2.0))
        ry = max(0.0, min(ry, h / 2.0))

        if rx == 0.0 or ry == 0.0:
            geometry.write(
                f"{x:g} {y:g} m {x + w:g} {y:g} l {x + w:g} {y + h:g} l {x:g} {y + h:g} l h\n"
            )
        else:
            geometry.write(f"{x + rx:g} {y:g} m\n")
            if w > 2 * rx:
                geometry.write(f"{x + w - rx:g} {y:g} l\n")
            geometry.write(
                f"{rx:g} 0 0 {ry:g} {x + w - rx:g} {y + ry:g} {x + w:g} {y + ry:g} a\n"
            )
            if h > 2 * ry:
                geometry.write(f"{x + w:g} {y + h - ry:g} l\n")
            geometry.write(
                f"{rx:g} 0 0 {ry:g} {x + w - rx:g} {y + h - ry:g} {x + w - rx:g} {y + h:g} a\n"
            )
            if w > 2 * rx:
                geometry.write(f"{x + rx:g} {y + h:g} l\n")
            geometry.write(
                f"{rx:g} 0 0 {ry:g} {x + rx:g} {y + h - ry:g} {x:g} {y + h - ry:g} a\n"
            )
            if h > 2 * ry:
                geometry.write(f"{x:g} {y + ry:g} l\n")
            geometry.write(
                f"{rx:g} 0 0 {ry:g} {x + rx:g} {y + ry:g} {x + rx:g} {y:g} a\n"
            )
            geometry.write("h\n")
        return geometry.getvalue()

    def node_circle(self, n):
        self.write_path(n, self.geometry_circle(n))

    def geometry_circle(self, n):
        cx = 0
        cy = 0
        if n.hasAttribute("cx"):
            cx = parse_float(n.getAttribute("cx"))
        if n.hasAttribute("cy"):
            cy = parse_float(n.getAttribute("cy"))
        r = parse_float(n.getAttribute("r"))
        return f"{r:g} 0 0 {r:g} {cx:g} {cy:g} e\n"

    def node_ellipse(self, n):
        self.write_path(n, self.geometry_ellipse(n))

    def geometry_ellipse(self, n):
        cx = 0
        cy = 0
        if n.hasAttribute("cx"):
            cx = float(n.getAttribute("cx"))
        if n.hasAttribute("cy"):
            cy = float(n.getAttribute("cy"))
        rx = float(n.getAttribute("rx"))
        ry = float(n.getAttribute("ry"))
        return f"{rx:g} 0 0 {ry:g} {cx:g} {cy:g} e\n"

    def node_line(self, n):
        self.write_path(n, self.geometry_line(n))

    def geometry_line(self, n):
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
        return f"{x1:g} {y1:g} m {x2:g} {y2:g} l\n"

    def node_polyline(self, n):
        self.write_path(n, self.geometry_polyline(n))

    def node_polygon(self, n):
        self.write_path(n, self.geometry_polygon(n))

    def geometry_polyline(self, n):
        return self.polygon_geometry(n, closed=False)

    def geometry_polygon(self, n):
        return self.polygon_geometry(n, closed=True)

    def polygon_geometry(self, n, closed):
        geometry = io.StringIO()
        d = parse_list(n.getAttribute("points"))
        op = "m"
        while d:
            x = float(d.pop(0))
            y = float(d.pop(0))
            geometry.write(f"{x:g} {y:g} {op}\n")
            op = "l"
        if closed:
            geometry.write("h\n")
        return geometry.getvalue()

    def node_path(self, n):
        self.write_path(n, self.geometry_path(n))

    def geometry_path(self, n):
        geometry = io.StringIO()
        parse_path(geometry, n.getAttribute("d"))
        return geometry.getvalue()


# --------------------------------------------------------------------


def parse_arguments():
    """parses command line arguments"""
    parser = argparse.ArgumentParser(
        description="convert SVG into Ipe files",
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
