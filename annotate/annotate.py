#
# Create an Ipe file including pages of given PDF document
#

import sys, os
import PyPDF2 as pdf

# --------------------------------------------------------------------

def create_ipe(pdffile):
  i = pdffile.rfind("/")
  if i >= 0:
    outfile = pdffile[i+1:]
  else:
    outfile = pdffile
  if outfile.endswith(".pdf"):
    outfile = outfile[:-4]
    
  outfile = "annotate-" + outfile + ".ipe"
  doc = pdf.PdfFileReader(pdffile)
  numPages = doc.numPages
  out = open(outfile, "w")
  out.write("""<ipe version="70205">
<ipestyle>
<preamble>
\\usepackage{graphicx}
</preamble>
</ipestyle>
<ipestyle name="basic">
</ipestyle>
""")
  for i in range(numPages):
    out.write("""<page>
<text pos="0 0">\includegraphics[page=%d]{%s}</text>
    </page>\n""" % (i+1, pdffile))
  out.write("</ipe>\n")
  out.close()
  os.system("ipescript update-styles %s" % outfile)

# --------------------------------------------------------------------

if len(sys.argv) != 2:
  sys.stderr.write("Usage: python annotate.py <document.pdf>\n")
  sys.exit(9)

pdffile = sys.argv[1]
create_ipe(pdffile)

# --------------------------------------------------------------------
