#!/usr/bin/env python3
# --------------------------------------------------------------------
# convert SVG to Ipe format
# --------------------------------------------------------------------
#
# Copyright (C) 2009-2019  Otfried Cheong
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
#  - sanitize paths (Ipe refuses to load illegal paths, but they are common in SVG)
#  - handle <use> elements
#  - store gradients in the dictionary in a more useful format
#  - parse title and desc elements and store in Ipe header
#  - go through SVG test suite (see test_svg.py)
#
# --------------------------------------------------------------------

svgtoipe_version = "20240516"

import sys
import argparse

import xml.dom.minidom as xml
from xml.dom.minidom import Node
from xml.parsers.expat import ExpatError

import re
import math
import base64
import io

try:
  from PIL import Image
  have_pil = True
except:
  have_pil = False

assert sys.hexversion >= 0x3000000, "Please run svgtoipe using Python 3"

ignored_nodes = set(["defs", "audio", "video", "metadata", "sodipodi:namedview", "style", "script", "SVGTestCase",
                     "animate", "animateTransform", "set" ])

# --------------------------------------------------------------------

# should extend this to cover list in https://www.w3.org/TR/SVG11/types.html#ColorKeywords

color_keywords = {
  "aqua" :"rgb(0, 255, 255)",
  "black" : "rgb(0, 0, 0)",
  "blue" :"rgb(0, 0, 255)",
  "firebrick" : "rgb(178, 34, 34)",
  "fuchsia" :"rgb(255, 0, 255)",
  "gray" :"rgb(128, 128, 128)",
  "green" :"rgb(0, 128, 0)",
  "grey" :"rgb(128, 128, 128)",
  "lime" :"rgb(0, 255, 0)",
  "maroon" :"rgb(128, 0, 0)",
  "navy" :"rgb(0, 0, 128)",
  "olive" :"rgb(128, 128, 0)",
  "purple" :"rgb(128, 0, 128)",
  "red" :"rgb(255, 0, 0)",
  "silver" :"rgb(192, 192, 192)",
  "teal" :"rgb(0, 128, 128)",
  "white" :"rgb(255, 255, 255)",
  "yellow" :"rgb(255, 255, 0)",
}

attribute_names = [ "stroke",
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
                    "font-size" ]

def printAttributes(n):
  a = n.attributes
  for i in range(a.length):
    name = a.item(i).name
    if name[:9] != "sodipodi:" and name[:9] != "inkscape:":
      sys.stderr.write("   %s %s\n" % (name, n.getAttribute(name)))

def parse_float(txt):
  if not txt:
    return None
  if txt.endswith('px') or txt.endswith('pt'):
    return float(txt[:-2])
  elif txt.endswith('pc'):
    return 12 * float(txt[:-2])
  elif txt.endswith('mm'):
    return 72.0 * float(txt[:-2]) / 25.4
  elif txt.endswith('cm'):
    return 72.0 * float(txt[:-2]) / 2.54
  elif txt.endswith('in'):
    return 72.0 * float(txt[:-2])
  else:
    return float(txt)

def parse_opacity(txt):
  if not txt:
    return None
  m = int(10 * (float(txt) + 0.05))
  if m == 0: m = 1
  return 10 * m

def parse_list(string):
  return re.findall(r"([A-Za-z]|-?[0-9]+\.?[0-9]*(?:e-?[0-9]*)?)", string)

def parse_style(string):
  sdict = {}
  for item in string.split(';'):
    if ':' in item:
      key, value = item.split(':')
      sdict[key.strip()] = value.strip()
  return sdict

def parse_color_component(txt):
  if txt.endswith("%"):
    return float(txt[:-1]) / 100.0
  else:
    return int(txt) / 255.0

def parse_color(c):
  if not c or c == 'none':
    return None
  if c in color_keywords:
    c = color_keywords[c]
  m =  re.match(r"rgb\(([0-9\.]+%?),\s*([0-9\.]+%?),\s*([0-9\.]+%?)\s*\)", c)
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
  m = re.match(r"#([0-9a-fA-F][0-9a-fA-F])([0-9a-fA-F][0-9a-fA-F])"
               + r"([0-9a-fA-F][0-9a-fA-F])$", c)
  if m:
    r = int(m.group(1), 16) / 255.0
    g = int(m.group(2), 16) / 255.0
    b = int(m.group(3), 16) / 255.0
    return (r, g, b)
  sys.stderr.write("Unknown color: %s\n" % c)
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
  d = re.findall(r"([A-Za-z]|-?(?:\.[0-9]+|[0-9]+\.?[0-9]*)(?:e-?[0-9]+)?)", d)
  x, y = 0.0, 0.0
  xs, ys = 0.0, 0.0
  x0, y0 = 0.0, 0.0
  while d:
    if not d[0][0] in "01234567890.-":
      opcode = d.pop(0)
    if opcode == 'M':
      x, y = pnext(d, 2)
      x0, y0 = x, y
      # If this moveto command is the last command, it starts a nonsensical empty
      # new subpath, with crashes ipe. Thus, we skip this command in this case.
      # See also https://github.com/otfried/ipe-issues/issues/274
      if d:
        out.write("%g %g m\n" % (x, y))
      opcode = 'L'
    elif opcode == 'm':
      x1, y1 = pnext(d, 2)
      x += x1
      y += y1
      x0, y0 = x, y
      # If this moveto command is the last command, it starts a nonsensical empty
      # new subpath, with crashes ipe. Thus, we skip this command in this case.
      # See also https://github.com/otfried/ipe-issues/issues/274
      if d:
        out.write("%g %g m\n" % (x, y))
      opcode = 'l'
    elif opcode == 'L':
      x, y = pnext(d, 2)
      out.write("%g %g l\n" % (x, y))
    elif opcode == 'l':
      x1, y1 = pnext(d, 2)
      x += x1
      y += y1
      out.write("%g %g l\n" % (x, y))
    elif opcode == 'H':
      x = pnext(d, 1)[0]
      out.write("%g %g l\n" % (x, y))
    elif opcode == 'h':
      x += pnext(d, 1)[0]
      out.write("%g %g l\n" % (x, y))
    elif opcode == 'V':
      y = pnext(d, 1)[0]
      out.write("%g %g l\n" % (x, y))
    elif opcode == 'v':
      y += pnext(d, 1)[0]
      out.write("%g %g l\n" % (x, y))
    elif opcode == 'C':
      x1, y1, xs, ys, x, y = pnext(d, 6)
      out.write("%g %g %g %g %g %g c\n" % (x1, y1, xs, ys, x, y))
    elif opcode == 'c':
      x1, y1, xs, ys, xf, yf = pnext(d, 6)
      x1 += x; y1 += y
      xs += x; ys += y
      x += xf; y += yf
      out.write("%g %g %g %g %g %g c\n" % (x1, y1, xs, ys, x, y))
    elif opcode == 'S' or opcode == 's':
      x2, y2, xf, yf = pnext(d, 4)
      if opcode == 's':
        x2 += x; y2 += y
        xf += x; yf += y
      x1 = x + (x - xs); y1 = y + (y - ys)
      out.write("%g %g %g %g %g %g c\n" % (x1, y1, x2, y2, xf, yf))
      xs, ys = x2, y2
      x, y = xf, yf
    elif opcode == 'Q':
      xs, ys, x, y = pnext(d, 4)
      out.write("%g %g %g %g q\n" % (xs, ys, x, y))
    elif opcode == 'q':
      xs, ys, xf, yf = pnext(d, 4)
      xs += x; ys += y
      x += xf; y += yf
      out.write("%g %g %g %g q\n" % (xs, ys, x, y))
    elif opcode == 'T' or opcode == 't':
      xf, yf = pnext(d, 2)
      if opcode == 't':
        xf += x; yf += y
      x1 = x + (x - xs); y1 = y + (y - ys)
      out.write("%g %g %g %g q\n" % (x1, y1, xf, yf))
      xs, ys = x1, y1
      x, y = xf, yf
    elif opcode == 'A' or opcode == 'a':
      rx, ry, phi, large_arc, sweep, x2, y2 = parse_arc_arg(d)
      if opcode == 'a':
        x2 += x; y2 += y
      draw_arc(out, x, y, rx, ry, phi, large_arc, sweep, x2, y2)
      x, y = x2, y2
    elif opcode in 'zZ':
      x, y = x0, y0
      out.write("h\n")
    else:
      sys.stderr.write("Unrecognised opcode: %s\n" % opcode)

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
  cp = math.cos(phi); sp = math.sin(phi)
  dx = .5 * (x1 - x2); dy = .5 * (y1 - y2)
  x1p = cp * dx + sp * dy; y1p = -sp * dx + cp * dy
  r2 = (((rx * ry)**2 - (rx * y1p)**2 - (ry * x1p)**2)/
        ((rx * y1p)**2 + (ry * x1p)**2))
  if r2 < 0: r2 = 0
  r = math.sqrt(r2)
  if large_arc == sweep:
    r = -r
  cxp = r * rx * y1p / ry; cyp = -r * ry * x1p / rx
  cx = cp * cxp - sp * cyp + .5 * (x1 + x2)
  cy = sp * cxp + cp * cyp + .5 * (y1 + y2)
  m = Matrix([rx, 0, 0, ry, 0, 0])
  m = Matrix([cp, sp, -sp, cp, cx, cy]) * m
  if sweep == 0:
    m = m * Matrix([1, 0, 0, -1, 0, 0])
  out.write("%s %g %g a\n" % (str(m), x2, y2))

# --------------------------------------------------------------------

class Matrix():

  # Default is identity matrix
  def __init__(self, string = None):
    self.values = [1, 0, 0, 1, 0, 0]
    if not string or string == "":
      return
    if isinstance(string, list):
      self.values = string
      return
    mat = re.match(r"([a-zA-Z]+)\(([^)]*)\)$", string)
    if not mat:
      sys.stderr.write("Unknown transform: %s\n" % string)
    op = mat.group(1)
    d = [float(x) for x in parse_list(mat.group(2))]
    if op == "matrix":
      self.values = d
    elif op == "translate":
      if len(d) == 1: d.append(0.0)
      self.values = [1, 0, 0, 1, d[0], d[1]]
    elif op == "scale":
      if len(d) == 1: d.append(d[0])
      sx, sy = d
      self.values = [sx, 0, 0, sy, 0, 0]
    elif op == "rotate":
      phi = math.pi * d[0] / 180.0
      self.values = [math.cos(phi), math.sin(phi),
                     -math.sin(phi), math.cos(phi), 0, 0]
    elif op == "skewX":
      tphi = math.tan(math.pi * d[0] / 180.0)
      self.values = [1, 0, tphi, 1, 0, 0]
    elif op == "skewY":
      tphi = math.tan(math.pi * d[0] / 180.0)
      self.values = [1, tphi, 0, 1, 0, 0]
    else:
      sys.stderr.write("Unknown transform: %s\n" % string)

  def __call__(self, other):
    return (self.values[0]*other[0] + self.values[2]*other[1] + self.values[4],
            self.values[1]*other[0] + self.values[3]*other[1] + self.values[5])

  def inverse(self):
    d = float(self.values[0]*self.values[3] - self.values[1]*self.values[2])
    return Matrix([self.values[3]/d, -self.values[1]/d,
                   -self.values[2]/d, self.values[0]/d,
                   (self.values[2]*self.values[5] -
                    self.values[3]*self.values[4])/d,
                   (self.values[1]*self.values[4] -
                    self.values[0]*self.values[5])/d])

  def __mul__(self, other):
    a, b, c, d, e, f = self.values
    u, v, w, x, y, z = other.values
    return Matrix([a*u + c*v, b*u + d*v, a*w + c*x,
                   b*w + d*x, a*y + c*z + e, b*y + d*z + f])

  def __str__(self):
    a, b, c, d, e, f = self.values
    return "%g %g %g %g %g %g" % (a, b, c, d, e, f)

# --------------------------------------------------------------------

class Svg():

  def __init__(self, fname):
    try:
      if fname == "--":
          self.dom = xml.parseString(sys.stdin.read())
      else:
          self.dom = xml.parse(fname)

    except ExpatError as exc:
      sys.stderr.write('ERROR: Input is not valid xml data:\n')
      sys.stderr.write(exc.message)
      return

    attr = { }
    for a in attribute_names:
      attr[a] = None
    self.attributes = [ attr ]
    self.defs = { }
    self.symbols = { }
    
    for n in self.dom.childNodes:
      if n.nodeType == Node.ELEMENT_NODE and n.tagName == "svg":
        if n.hasAttribute("viewBox"):
          x, y, w, h = [float(x) for x in parse_list(n.getAttribute("viewBox"))]
          self.width = w
          self.height = h
          self.origin = (x, y)
        else:
          self.width = parse_float(n.getAttribute("width")) or 500
          self.height = parse_float(n.getAttribute("height")) or 500
          self.origin = (0, 0)
        self.root = n
        return

# --------------------------------------------------------------------

  def write_ipe_header(self):
    self.out.write('<?xml version="1.0"?>\n')
    self.out.write('<!DOCTYPE ipe SYSTEM "ipe.dtd">\n')
    self.out.write('<ipe version="70212" creator="svgtoipe %s">\n' %
                   svgtoipe_version)
    self.out.write('<ipestyle>\n')
    self.out.write(('<layout paper="%d %d" frame="%d %d" ' +
                    'origin="0 0" crop="no"/>\n') %
                   (self.width, self.height, self.width, self.height))
    for t in range(10, 100, 10):
      self.out.write('<opacity name="%d%%" value="0.%d"/>\n' % (t, t))
    # set SVG defaults
    self.out.write('<pathstyle cap="0" join="0" fillrule="wind"/>\n')
    self.out.write('</ipestyle>\n')
    # collect definitions
    self.collect_definitions(self.root)
    # write definitions into stylesheet
    if len(self.defs) > 0:
      self.out.write('<ipestyle>\n')
      for k in self.defs:
        if self.defs[k][0] == "linearGradient":
          self.write_linear_gradient(k)
        elif self.defs[k][0] == "radialGradient":
          self.write_radial_gradient(k)
      self.out.write('</ipestyle>\n')

  def collect_definitions(self, node):
    # Collect Everything inside a <defs> tag for which we have a defs_<tagname>() method
    defs_children = node.getElementsByTagName('defs')
    for c in defs_children:
      for my_attr in dir(self):
        if my_attr[:4] == 'def_':
          tag_name = my_attr[4:]
          # There is a parsing method for tags named <tag_name>
          parseable_tags = node.getElementsByTagName(tag_name)
          for tag in parseable_tags:
            getattr(self, my_attr)(tag)

  def parse_svg(self, outname, **kwargs):
    """ parses the svg, and writes it to file.
        outname, str, output filename. if '--' then parse_svg writes to stdout.

        Keywords:

        outmode, str, 'file' write in ipe file format.
                      'clipboard', write as ipe clipboard selection
    """
    outmode = kwargs.get('outmode', 'file')

    if outname == '--':
      self.out = sys.stdout
    else:
      self.out = open(outname, "w")
      # write header

    if outmode == 'file':
      self.write_ipe_header()
      self.out.write('<page>\n')
    elif outmode == "clipboard":
      self.out.write('<ipeselection pos="0 0">\n')
    else:
      sys.stderr.write("bad output mode '{}'".format(outmode))
      return

    self.write_data()

    if outmode == 'file':
      self.out.write('</page>\n')
      self.out.write('</ipe>\n')
    elif outmode == 'clipboard':
      self.out.write('</ipeselection>\n')

    self.out.close()

  def write_data(self):
    # start real data
    m = Matrix([1, 0, 0, 1, 0, self.height / 2.0])
    m = m * Matrix([1, 0, 0, -1, 0, 0])
    m = m * Matrix([1, 0, 0, 1,
                    -self.origin[0], -(self.origin[1] + self.height / 2.0)])
    self.out.write('<group matrix="%s">\n' % str(m))
    self.parse_nodes(self.root)
    self.out.write('</group>\n')

  def parse_nodes(self, root):
    """ parses recognized svg elements """
    for n in root.childNodes:
      if n.nodeType != Node.ELEMENT_NODE:
        continue

      if n.tagName in ignored_nodes:
        continue

      nodeName = "node_" + n.tagName.replace(":","_")

      if hasattr(self, nodeName):
        getattr(self, nodeName)(n)
      else:
        sys.stderr.write("Unhandled node: %s\n" % n.tagName)

# --------------------------------------------------------------------

  def write_linear_gradient(self, k):
    typ, x1, x2, y1, y2, stops, matrix = self.defs[k]
    self.out.write('<gradient name="g%s" type="axial" extend="yes"\n' % k)
    self.out.write(' matrix="%s"' % str(matrix))
    self.out.write(' coords="%g %g %g %g">\n' % (x1, y1, x2, y2))
    for s in stops:
      offset, color = s
      self.out.write(' <stop offset="%g" color="%g %g %g"/>\n' %
                     (offset, color[0], color[1], color[2]))
    self.out.write('</gradient>\n')

  def write_radial_gradient(self, k):
    typ, cx, cy, r, fx, fy, stops, matrix = self.defs[k]
    self.out.write('<gradient name="g%s" type="radial" extend="yes"\n' % k)
    self.out.write(' matrix="%s"' % str(matrix))
    self.out.write(' coords="%g %g %g %g %g %g">\n' % (fx, fy, 0, cx, cy, r))
    for s in stops:
      offset, color = s
      self.out.write(' <stop offset="%g" color="%g %g %g"/>\n' %
                     (offset, color[0], color[1], color[2]))
    self.out.write('</gradient>\n')

  def get_stops(self, n):
    stops = []
    for m in n.childNodes:
      if m.nodeType != Node.ELEMENT_NODE:
        continue
      if m.tagName != "stop":
        continue # should not happen
      offs = m.getAttribute("offset") or "0"
      if offs.endswith("%"):
        offs = float(offs[:-1]) / 100.0
      else:
        offs = float(offs)
      if m.hasAttribute("stop-color"):
        color = parse_color(m.getAttribute("stop-color"))
      else:
        color = [ 0, 0, 0 ]
      if m.hasAttribute("style"):
        sdict = parse_style(m.getAttribute("style"))
        if "stop-color" in sdict:
          color = parse_color(sdict["stop-color"])
      stops.append((offs, color))
    if len(stops) == 0:
      if n.hasAttribute("xlink:href"):
        ref = n.getAttribute("xlink:href")
        if ref.startswith("#") and ref[1:] in self.defs:
          gradient = self.defs[ref[1:]]
          # TODO: use a class instead of a tuple!
          if gradient[0] == "linearGradient":
            stops = gradient[5]
          else:
            stops = gradient[6]
    return stops


  def node_inkscape_clipboard(self, node):
    self.parse_nodes(node)

  def def_symbol(self, node):
    # Symbols are parsed by pretending the symbol node is a group node and storing it in
    # self.symbols. Later, whenever a <use ...> tag is encountered,
    # we call node_g() on the fake group node.
    self.symbols[node.getAttribute('id')] = node

  def def_linearGradient(self, n):
    #printAttributes(n)
    kid = n.getAttribute("id")
    x1 = 0; y1 = 0
    x2 = self.width; y2 = self.height
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
    self.defs[kid] = ("linearGradient", x1, x2, y1, y2, stops, matrix)

  def def_radialGradient(self, n):
    #printAttributes(n)
    kid = n.getAttribute("id")
    cx = "50%"; cy = "50%"; r = "50%"
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
    self.defs[kid] = ("radialGradient", cx, cy, r, fx, fy, stops, matrix)

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
    attr = { }
    for a in attribute_names:
      if n.hasAttribute(a):
        attr[a] = n.getAttribute(a)
      else:
        attr[a] = pattr[a]
    if n.hasAttribute("style"):
      sdict = parse_style(n.getAttribute("style"))
      for a in attribute_names:
        if a in sdict:
          attr[a] = sdict[a]
    return attr

  def write_pathattributes(self, a):
    stroke = parse_color(a["stroke"])
    if stroke:
      self.out.write(' stroke="%g %g %g"' % stroke)
    fill = a["fill"]
    if fill and fill.startswith("url("):
      mat = re.match(r"url\(#([^)]+)\).*", fill)
      if mat:
        grad = mat.group(1)
        if grad in self.defs and (self.defs[grad][0] == "linearGradient" or
                                  self.defs[grad][0] == "radialGradient"):
          self.out.write(' fill="1" gradient="g%s"' % grad)
    elif fill is None:
      self.out.write(' fill="0"')
    else:
      fill = parse_color(fill)
      if fill:
        self.out.write(' fill="%g %g %g"' % fill)
    opacity = parse_opacity(a["opacity"])
    fill_opacity = parse_opacity(a["fill-opacity"])
    stroke_opacity = parse_opacity(a["stroke-opacity"])
    if fill and fill_opacity:
      opacity = fill_opacity
    if not fill and stroke and stroke_opacity:
      opacity = stroke_opacity
    if opacity and opacity != 100:
      self.out.write(' opacity="%d%%"' % opacity)
    stroke_width = parse_float(a["stroke-width"])
    if a["stroke-width"]:
      self.out.write(' pen="%g"' % stroke_width)
    if a["fill-rule"] == "nonzero":
      self.out.write(' fillrule="wind"')
    k = {"butt" : 0, "round" : 1, "square" : 2 }
    if a["stroke-linecap"] in k:
      self.out.write(' cap="%d"' % k[a["stroke-linecap"]])
    k = {"miter" : 0, "round" : 1, "bevel" : 2 }
    if a["stroke-linejoin"] in k:
      self.out.write(' join="%d"' % k[a["stroke-linejoin"]])
    dasharray = a["stroke-dasharray"]
    dashoffset = a["stroke-dashoffset"]
    if dasharray and dashoffset and dasharray != "none":
      d = parse_list(dasharray)
      off = parse_float(dashoffset)
      self.out.write(' dash="[%s] %g"' % (" ".join(d), off))

# --------------------------------------------------------------------

  def node_g(self, group):
    # printAttributes(group)
    attr = self.parse_attributes(group)
    self.attributes.append(attr)
    self.out.write('<group')
    m = parse_transform(group)
    if m:
      self.out.write(' matrix="%s"' % m)
    self.out.write('>\n')
    self.parse_nodes(group)
    self.out.write('</group>\n')
    self.attributes.pop()

  def node_use(self, n):
    if not n.hasAttribute('xlink:href'):
      print("Ignoring use node without xlink:href")
      return

    symbol_name = n.getAttribute('xlink:href')
    if symbol_name[0] != '#':
      print("Ignoring use node not referencing symbol ID")
      return

    symbol_name = symbol_name[1:]

    if symbol_name not in self.symbols:
      print("Ignoring use node for unknown symbol '{}'".format(symbol_name))
      return

    translate_x = '0'
    if n.hasAttribute('x'):
      translate_x = n.getAttribute('x')
      translate_y = '0'
    if n.hasAttribute('y'):
      translate_y = n.getAttribute('y')

    scale_x = 1.0
    if n.hasAttribute('width'):
      if n.getAttribute('width')[-1] != '%':
        print("Ignoring use with non-relative width scale.")
        return
      scale_x = float(n.getAttribute('width')[:-1]) / 100.0

    scale_y = 1.0
    if n.hasAttribute('height'):
      if n.getAttribute('height')[-1] != '%':
        print("Ignoring use with non-relative height scale.")
        return
      scale_y = float(n.getAttribute('height')[:-1]) / 100.0

    scale_m = Matrix("scale({} {})".format(scale_x, scale_y))
    translate_m = Matrix(
      "translate({} {})".format(translate_x, translate_y))
    m = scale_m * translate_m

    # Use a group for the possible transform matrix from this
    # use node
    self.out.write('<group   matrix="{}">\n'.format(m))
    self.node_g(self.symbols[symbol_name])
    self.out.write('</group>\n')

  def node_a(self, n):
    url = n.getAttribute("xlink:href")
    if url is not None:
      self.out.write('<group url="%s">' % url)
    self.parse_nodes(n)
    if url is not None:
      self.out.write('</group>\n')

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
      if (len(token.split(":")) != 2):
        # Strange token
        sys.stderr.write("Ignored style token: %s\n" % token)
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

    self.out.write('<text pos="%g %g"' % (x,y))
    self.out.write(' transformations="affine" valign="baseline"')
    m = parse_transform(t)
    if not m: m = Matrix()
    m = m * Matrix([1, 0, 0, -1, x, y]) * Matrix([1, 0, 0, 1, -x, -y])
    self.out.write(' matrix="%s"' % m)

    if "size" in attributes:
      self.out.write(' size="%g"' % attributes["size"])

    if "color" in attributes and attributes["color"] is not None:
      self.out.write(' stroke="%g %g %g"' % attributes["color"])

    halign = "left"
    valign = "bottom"
    if "anchor" in attributes:
      if attributes["anchor"] == "middle":
        halign = "center"
        valign = "center"
      elif attributes["anchor"] == "end":
        halign = "right"
    self.out.write(' valign="%s"' % valign)
    self.out.write(' halign="%s"' % halign)

    self.text = ""
    self.collect_text(t)

    if "svg-families" in attributes:
      mapped_family = self.map_svg_font_families(attributes["svg-families"])
      if mapped_family is not None:
        self.text = "{\\fontfamily{" + mapped_family + "}\\selectfont{}" + self.text + "}"

    if "weight" in attributes:
      if attributes["weight"] == "bold":
        self.text = "\\bf{" + self.text + "}"

    self.out.write('>%s</text>\n' % self.text)

  def node_image(self, node):
    if not have_pil:
      sys.stderr.write("No Python image library, <image> ignored\n")
      return
    href = node.getAttribute("xlink:href")
    if not href.startswith("data:image/png;base64,"):
      sys.stderr.write("Image ignored, href = %s...\n" % href[:40])
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
          self.out.write('<group matrix="%s" clip="%s">\n' % (str(m), path))
          self.out.write('<group matrix="%s">\n' % str(m.inverse()))
    self.out.write('<image rect="%g %g %g %g"' % (x, y, x + w, y + h))
    data = base64.b64decode(href[22:])
    fin = io.StringIO(data)
    image = Image.open(fin)
    m = parse_transform(node)
    if not m:
      m = Matrix()
    m = m * Matrix([1, 0, 0, -1, x, y+h]) * Matrix([1, 0, 0, 1, -x, -y])
    self.out.write(' matrix="%s"' % m)
    self.out.write(' width="%d" height="%d" ColorSpace="DeviceRGB"' %
                   image.size)
    self.out.write(' BitsPerComponent="8" encoding="base64"> \n')
    if True:
      data = io.StringIO()
      for pixel in image.getdata():
        data.write("%c%c%c" % pixel[:3])
      self.out.write(base64.b64encode(data.getvalue()))
      data.close()
    else:
      count = 0
      for pixel in image.getdata():
        self.out.write("%02x%02x%02x" % pixel[:3])
        count += 1
        if count == 10:
          self.out.write("\n")
          count = 0
    fin.close()
    self.out.write('</image>\n')
    if clipped:
      self.out.write('</group>\n</group>\n')

  # handled in def pass
  def node_linearGradient(self, n):
    pass

  def node_radialGradient(self, n):
    pass

  def node_rect(self, n):
    attr = self.parse_attributes(n)
    self.out.write('<path')
    m = parse_transform(n)
    if m:
      self.out.write(' matrix="%s"' % m)
    self.write_pathattributes(attr)
    self.out.write('>\n')
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
    self.out.write("%g %g m %g %g l %g %g l %g %g l h\n" %
                   (x, y, x + w, y, x + w, y + h, x, y + h))
    self.out.write('</path>\n')

  def node_circle(self, n):
    self.out.write('<path')
    m = parse_transform(n)
    if m:
      self.out.write(' matrix="%s"' % m)
    attr = self.parse_attributes(n)
    self.write_pathattributes(attr)
    self.out.write('>\n')
    cx = 0
    cy = 0
    if n.hasAttribute("cx"):
      cx = parse_float(n.getAttribute("cx"))
    if n.hasAttribute("cy"):
      cy = parse_float(n.getAttribute("cy"))
    r = parse_float(n.getAttribute("r"))
    self.out.write("%g 0 0 %g %g %g e\n" % (r, r, cx, cy))
    self.out.write('</path>\n')

  def node_ellipse(self, n):
    self.out.write('<path')
    m = parse_transform(n)
    if m:
      self.out.write(' matrix="%s"' % m)
    attr = self.parse_attributes(n)
    self.write_pathattributes(attr)
    self.out.write('>\n')
    cx = 0
    cy = 0
    if n.hasAttribute("cx"):
      cx = float(n.getAttribute("cx"))
    if n.hasAttribute("cy"):
      cy = float(n.getAttribute("cy"))
    rx = float(n.getAttribute("rx"))
    ry = float(n.getAttribute("ry"))
    self.out.write("%g 0 0 %g %g %g e\n" % (rx, ry, cx, cy))
    self.out.write('</path>\n')

  def node_line(self, n):
    self.out.write('<path')
    m = parse_transform(n)
    if m:
      self.out.write(' matrix="%s"' % m)
    attr = self.parse_attributes(n)
    self.write_pathattributes(attr)
    self.out.write('>\n')
    x1 = 0; y1 = 0; x2 = 0; y2 = 0
    if n.hasAttribute("x1"):
      x1 = float(n.getAttribute("x1"))
    if n.hasAttribute("y1"):
      y1 = float(n.getAttribute("y1"))
    if n.hasAttribute("x2"):
      x2 = float(n.getAttribute("x2"))
    if n.hasAttribute("y2"):
      y2 = float(n.getAttribute("y2"))
    self.out.write("%g %g m %g %g l\n" % (x1, y1, x2, y2))
    self.out.write('</path>\n')

  def node_polyline(self, n):
    self.polygon(n, closed=False)

  def node_polygon(self, n):
    self.polygon(n, closed=True)

  def polygon(self, n, closed):
    self.out.write('<path')
    m = parse_transform(n)
    if m:
      self.out.write(' matrix="%s"' % m)
    attr = self.parse_attributes(n)
    self.write_pathattributes(attr)
    self.out.write('>\n')
    d = parse_list(n.getAttribute("points"))
    op = "m"
    while d:
      x = float(d.pop(0))
      y = float(d.pop(0))
      self.out.write("%g %g %s\n" % (x, y, op))
      op = "l"
    if closed:
      self.out.write("h\n")
    self.out.write('</path>\n')

  def node_path(self, n):
    d = n.getAttribute("d")
    if len(d) == 0:
      # Empty paths crash ipe, filter them out
      return
    
    self.out.write('<path')
    m = parse_transform(n)
    if m:
      self.out.write(' matrix="%s"' % m)
    attr = self.parse_attributes(n)
    self.write_pathattributes(attr)
    self.out.write('>\n')
    parse_path(self.out, d)
    self.out.write('</path>\n')

# --------------------------------------------------------------------

def parse_arguments():
    """ parses command line arguments"""
    parser = argparse.ArgumentParser(
            description="convert SVG into Ipe files",
            epilog="""
              Supported SVG elements:
                  path,image,rect,circle,ellipse,line,polygon,polyline
              Supported SVG attributes:
                  group,clipPath,linearGradient,radialGradient
              """)

    parser.add_argument('-c', '--clipboard', dest='clipboard',
        action='store_true',
        help="""
        if -c is present, svg data is written as clipboard content.
        This allows pasting svg data from inkscape to ipe:
        (1) Copy Inkscape elements to clipboard,
        (2) run: 'xsel | ./svgtoipe.py -c -- | xsel -i',
        (3) paste clipboard content into Ipe.
        """)

    parser.add_argument('infile', metavar='svg-file.svg',
                        help="input file in svg format. If infile = '--' svg data is read from stdin.")

    parser.add_argument('outfile', metavar='ipe-file.ipe', nargs='?',
            help="""
                filename to write output. If no filename is given, the input filename
                together with '.ipe' extension is used. If outfile is '--', then data
                is written to stdout.""")

    parser.set_defaults(
        infile="--",
        verbosity=0,
        clipboard=False,
    )

    #try:
    args = parser.parse_args()
    if args.outfile is None:
      if args.infile != "--":
        args.outfile = args.infile[:-4] + ".ipe"

    return args
    #except Exception as exc:
        #sys.stderr.write("parsing error:\n")
        #sys.exit(1)

def main():
  args = parse_arguments()

  svg = Svg(args.infile)
  if args.clipboard:
    svg.parse_svg(args.outfile, outmode="clipboard")
  else:
    svg.parse_svg(args.outfile)

  sys.exit(0)

if __name__ == '__main__':
  main()

# --------------------------------------------------------------------
