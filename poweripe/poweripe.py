#
# poweripe.py
#
# Translate an Ipe presentation to Powerpoint
#

import sys, os
import datetime

import pptx
from pptx.util import Pt
from pptx.enum.text import PP_ALIGN

from pylatexenc.latexwalker import LatexWalker, LatexEnvironmentNode

import ipe as Ipe
ipe = Ipe.ipe()

assert sys.hexversion >= 0x3060000

# --------------------------------------------------------------------

sizeMap = { "huge": 2.8 * 17,
            "large": 2.8 * 12,
            "normal": 28,
}

# from size10.clo:
"""
\newcommand\tiny{\@setfontsize\tiny\@vpt\@vipt}
\newcommand\large{\@setfontsize\large\@xiipt{14}}
\newcommand\Large{\@setfontsize\Large\@xivpt{18}}
\newcommand\LARGE{\@setfontsize\LARGE\@xviipt{22}}
\newcommand\huge{\@setfontsize\huge\@xxpt{25}}
\newcommand\Huge{\@setfontsize\Huge\@xxvpt{30}}
\newcommand\footnotesize{%
   \@setfontsize\footnotesize\@viiipt{9.5}%
\newcommand\small{%
   \@setfontsize\small\@ixpt{11}%
\renewcommand\normalsize{%
   \@setfontsize\normalsize\@xpt\@xiipt
"""

class PowerIpe:
  def convertTime(self, s):
    return datetime.datetime(int(s[2:6]),
                             int(s[6:8]),
                             int(s[8:10]),
                             int(s[10:12]),
                             int(s[12:14]),
                             int(s[14:]))

  def convertText(self, slide, obj):
    mp = obj.get(obj, "minipage")
    if not mp:
      return False
    s = obj.text(obj)
    matrix = ipe.Matrix()
    textStyle = obj.get(obj, "textstyle")
    textSize = obj.get(obj, "textsize")
    color = obj.get(obj, "stroke")
    box = ipe.Rect()
    obj.addToBBox(obj, box, matrix)
    pos = box.topLeft(box)
    #print(textSize, textStyle, color)
    w = LatexWalker(s)
    nodes, lpos, llen = w.get_latex_nodes(pos=0)
    #print(nodes, lpos, llen)
    txBox = slide.shapes.add_textbox(Pt(self.x0 + pos.x), Pt(self.y0 - pos.y),
                                     Pt(box.width(box)), Pt(box.height(box)))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = s
    if textStyle == "center":
      p.alignment = PP_ALIGN.CENTER
    elif textStyle == "item":
      p.level = 1
    run.font.size = Pt(sizeMap.get(textSize, 12))

  def convertPage(self, pageNo, viewNo):
    sys.stderr.write("Converting page %d\n" % pageNo)
    p = self.doc[pageNo]
    t = p.titles(p)
    if t.title != "":
      slide = self.prs.slides.add_slide(self.title_slide_layout)
      title_placeholder = slide.shapes.title
      title_placeholder.text = t.title
    else:
      slide = self.prs.slides.add_slide(self.blank_slide_layout)
    svgobjs = set()
    for i in range(1, len(p)):
      if not p.visible(p, viewNo, i):
        continue
      obj = p[i]
      ty = obj.type(obj)
      if ty == "text":
        if not self.convertText(slide, obj):
          svgobjs.add(i)
      #elif ty == "image":
      #  info = obj.info(obj)
      else:
        svgobjs.add(i)
    l = p.addLayer(p, "poweripe")
    x = p.countViews(p) + 1
    p.insertView(p, x, "poweripe")
    p.setVisible(p, x, "poweripe", True)
    for i in svgobjs:
      p.setLayerOf(p, i, "poweripe")
    print("Exporting!", pageNo, x)
    self.doc.save(self.doc, "tmpipe%d.ipe" % pageNo, "xml", None)

  def convert(self, ipename, pptname):
    self.doc = ipe.Document(ipename)
    iprops = self.doc.properties(self.doc)

    self.prs = pptx.Presentation()

    props = self.prs.core_properties
    props.author = iprops.author
    props.last_modified_by = "" # shouldn't be python-pptx author
    props.title = iprops.title
    props.created = self.convertTime(iprops.created)
    props.modified = self.convertTime(iprops.modified)
    props.keywords = iprops.keywords
    props.subject = iprops.subject
    
    style = self.doc.sheets(self.doc)
    layout = style.find(style, "layout")
    self.x0 = layout.origin.x
    self.y0 = layout.origin.y + layout.papersize.y
  
    self.prs.slide_width = Pt(layout.papersize.x)
    self.prs.slide_height = Pt(layout.papersize.y)
  
    self.bullet_slide_layout = self.prs.slide_layouts[1]
    self.title_slide_layout = self.prs.slide_layouts[5]
    self.blank_slide_layout = self.prs.slide_layouts[6]

    fallback_icon = "/mnt/d/Devel/ipe/group/ipe32.png"
  
    for pageNo in range(1, len(self.doc) + 1):
      p = self.doc[pageNo]
      viewNo = p.countViews(p)
      self.convertPage(pageNo, viewNo)
    #os.system("/mnt/d/Devel/ipe/mingw64/bin/iperender.exe -svg -page %d -nocrop %s %s" % (page + 1, ipename, svgname))
    #pic = slide.shapes.add_svg_picture(svgname, fallback_icon, 0, 0)
  
    self.prs.save(pptname)
  
# --------------------------------------------------------------------

if __name__ == "__main__":
  powerIpe = PowerIpe()
  powerIpe.convert("retreat-consultancy-projects-20190910.pdf", "test.pptx")

# --------------------------------------------------------------------
