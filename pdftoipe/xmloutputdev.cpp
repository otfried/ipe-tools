// --------------------------------------------------------------------
// Output device writing XML stream
// --------------------------------------------------------------------

#include <stdio.h>
#include <stddef.h>
#include <stdarg.h>

#include "Object.h"
#include "Error.h"
#include "Gfx.h"
#include "GfxState.h"
#include "GfxFont.h"
#include "Catalog.h"
#include "Page.h"
#include "Stream.h"

#include "xmloutputdev.h"

#include <vector>
#include <cmath> 

//------------------------------------------------------------------------
// XmlOutputDev
//------------------------------------------------------------------------

XmlOutputDev::XmlOutputDev(const char *fileName, XRef *xrefA, Catalog *catalog,
			   int firstPage, int lastPage)
{
  FILE *f;

  if (!(f = fopen(fileName, "wb"))) {
    fprintf(stderr, "Couldn't open output file '%s'\n", fileName);
    ok = false;
    return;
  }
  outputStream = f;

  // initialize
  ok = true;
  xref = xrefA;
  inText = false;
  iUnicode = false;

  // set defaults
  iIsMath = false; 
  iNoText = false;
  iIsLiteral = false;
  iMergeLevel = 0;
  iUnicodeLevel = 1;

  Page *page = catalog->getPage(firstPage);
  double wid = page->getMediaWidth();
  double ht = page->getMediaHeight();

  /*
  int rot = page->getRotate();
  fprintf(stderr, "Page rotation: %d\n", rot);
  if (rot == 90 || rot == 270) {
    double t = wid;
    wid = ht;
    ht = t;
  }
  */

  const PDFRectangle *media = page->getMediaBox();
  const PDFRectangle *crop = page->getCropBox();

  fprintf(stderr, "MediaBox: %g %g %g %g (%g x %g)\n", 
	  media->x1, media->x2, media->y1, media->y2, wid, ht);
  fprintf(stderr, "CropBox: %g %g %g %g\n", 
	  crop->x1, crop->x2, crop->y1, crop->y2);

  writePS("<?xml version=\"1.0\"?>\n");
  writePS("<!DOCTYPE ipe SYSTEM \"ipe.dtd\">\n");
  writePSFmt("<ipe version=\"70000\" creator=\"pdftoipe %s\">\n", 
	     PDFTOIPE_VERSION);
  writePS("<ipestyle>\n");
  writePSFmt("<layout paper=\"%g %g\" frame=\"%g %g\" origin=\"%g %g\"/>\n", 
	     wid, ht, crop->x2 - crop->x1, crop->y2 - crop->y1, 
	     crop->x1 - media->x1, crop->y1 - media->y1);
  writePS("<symbol name=\"bullet\"><path matrix=\"0.04 0 0 0.04 0 0\" fill=\"black\">\n");
  writePS("18 0 0 18 0 0 e</path></symbol>\n");
  writePS("</ipestyle>\n");

  // initialize sequential page number
  seqPage = 1;
}

XmlOutputDev::~XmlOutputDev()
{
  if (ok) {
    finishText();
    writePS("</ipe>\n");
  }
  fclose(outputStream);
}

// ----------------------------------------------------------

void XmlOutputDev::setTextHandling(bool math, bool notext, 
                                   bool literal, int mergeLevel,
                                   int unicodeLevel)
{
  iIsMath = math;
  iNoText = notext;
  iIsLiteral = literal;
  iMergeLevel = mergeLevel;
  iUnicodeLevel = unicodeLevel;
  if (iUnicodeLevel >= 2) {
    writePS("<ipestyle>\n");
    writePS("<preamble>\\usepackage[utf8]{inputenc}</preamble>\n");
    writePS("</ipestyle>\n");
  }
}

// ----------------------------------------------------------

void XmlOutputDev::startPage(int pageNum, GfxState *state)
{
  startPage(pageNum, state, NULL);  // for poppler <= 0.22
}

void XmlOutputDev::startPage(int pageNum, GfxState *state, XRef *xrefA)
{
  writePSFmt("<!-- Page: %d %d -->\n", pageNum, seqPage);
  fprintf(stderr, "Converting page %d (numbered %d)\n", 
	  seqPage, pageNum);
  writePS("<page>\n");
  ++seqPage;
}

void XmlOutputDev::endPage()
{
  finishText();
  writePS("</page>\n");
}

// --------------------------------------------------------------------

void XmlOutputDev::startDrawingPath()
{
  finishText();
}

void XmlOutputDev::stroke(GfxState *state)
{
  startDrawingPath();
  GfxRGB rgb;
  state->getStrokeRGB(&rgb);
  writeColor("<path stroke=", rgb, 0);
  writePSFmt(" pen=\"%g\"", state->getTransformedLineWidth());

  double *dash;
  double start;
  int length, i;

  state->getLineDash(&dash, &length, &start);
  if (length) {
    writePS(" dash=\"[");
    for (i = 0; i < length; ++i)
      writePSFmt("%g%s", state->transformWidth(dash[i]), 
		 (i == length-1) ? "" : " ");
    writePSFmt("] %g\"", state->transformWidth(start));
  }
    
  if (state->getLineJoin() > 0)
    writePSFmt(" join=\"%d\"", state->getLineJoin());
  if (state->getLineCap())
    writePSFmt(" cap=\"%d\"", state->getLineCap());

  writePS(">\n");
  doPath(state);
  writePS("</path>\n");
}

void XmlOutputDev::fill(GfxState *state)
{
  startDrawingPath();
  GfxRGB rgb;
  state->getFillRGB(&rgb);
  writeColor("<path fill=", rgb, " fillrule=\"wind\">\n");
  doPath(state);
  writePS("</path>\n");
}

void XmlOutputDev::eoFill(GfxState *state)
{
  startDrawingPath();
  GfxRGB rgb;
  state->getFillRGB(&rgb);
  writeColor("<path fill=", rgb, ">\n"); 
  doPath(state);
  writePS("</path>\n");
}

void XmlOutputDev::doPath(GfxState *state)
{
  GfxPath *path = state->getPath();
  GfxSubpath *subpath;
  int n, m, i, j;

  n = path->getNumSubpaths();

  double x, y, x1, y1, x2, y2;
  for (i = 0; i < n; ++i) {
    subpath = path->getSubpath(i);
    m = subpath->getNumPoints();
    state->transform(subpath->getX(0), subpath->getY(0), &x, &y);
    writePSFmt("%g %g m\n", x, y);
    j = 1;
    while (j < m) {
      if (subpath->getCurve(j)) {
	state->transform(subpath->getX(j), subpath->getY(j), &x, &y);
	state->transform(subpath->getX(j+1), subpath->getY(j+1), &x1, &y1);
	state->transform(subpath->getX(j+2), subpath->getY(j+2), &x2, &y2);
	writePSFmt("%g %g %g %g %g %g c\n", x, y, x1, y1, x2, y2);
	j += 3;
      } else {
	state->transform(subpath->getX(j), subpath->getY(j), &x, &y);
	writePSFmt("%g %g l\n", x, y);
	++j;
      }
    }
    if (subpath->isClosed()) {
      writePS("h\n");
    }
  }
}

// --------------------------------------------------------------------

void XmlOutputDev::updateTextPos(GfxState *)
{
  if (iMergeLevel < 2)
    finishText();
}

void XmlOutputDev::updateTextShift(GfxState *, double /*shift*/)
{
  if (iMergeLevel < 1)
    finishText();
}

void XmlOutputDev::drawChar(GfxState *state, double x, double y,
			    double dx, double dy,
			    double originX, double originY,
			    CharCode code, int nBytes, 
			    Unicode *u, int uLen)
{
  // check for invisible text -- this is used by Acrobat Capture
  if ((state->getRender() & 3) == 3)
    return;

  // get the font
  if (!state->getFont())
    return;

  if (iNoText) // discard text objects
    return;

  startText(state, x - originX, y - originY);

  if (uLen == 0) {
    if (code == 0x62) {
      // this is a hack to handle bullets created by pstricks and should 
      // probably be an option
      writePS("\\ipesymbol{bullet}{}{}{}");
    } else
      writePSFmt("[S+%02x]", code);
  } else {
    for (int i = 0; i < uLen; ++i)
      writePSUnicode(u[i]);
  }
}

void XmlOutputDev::startText(GfxState *state, double x, double y)
{
  if (inText)
    return;

  double xt, yt;
  state->transform(x, y, &xt, &yt);

  const double *T = state->getTextMat();
  const double *C = state->getCTM();

  /*
  fprintf(stderr, "TextMatrix = %g %g %g %g %g %g\n", 
	  T[0], T[1], T[2], T[3], T[4], T[5]);
  fprintf(stderr, "CTM = %g %g %g %g %g %g\n", 
	  C[0], C[1], C[2], C[3], C[4], C[5]);
  */

  double M[4];
  M[0] = C[0] * T[0] + C[2] * T[1];
  M[1] = C[1] * T[0] + C[3] * T[1];
  M[2] = C[0] * T[2] + C[2] * T[3];
  M[3] = C[1] * T[2] + C[3] * T[3];

  GfxRGB rgb;
  state->getFillRGB(&rgb);
  writeColor("<text stroke=", rgb, " pos=\"0 0\" transformations=\"affine\" ");
  writePS("valign=\"baseline\" ");
  writePSFmt("size=\"%g\" matrix=\"%g %g %g %g %g %g\">",
	     state->getFontSize(), M[0], M[1], M[2], M[3], xt, yt);

  if (iIsMath)
    writePS("$");
  inText = true;
}

void XmlOutputDev::finishText()
{
  if (inText) {
    if (iIsMath)
      writePS("$");
    writePS("</text>\n");
  }
  inText = false;
}

// --------------------------------------------------------------------

void XmlOutputDev::drawImage(GfxState *state, Object *ref, Stream *str,
                             int width, int height, GfxImageColorMap *colorMap,
                             bool interpolate, int *maskColors, 
                             bool inlineImg)
{
  finishText();

  ImageStream *imgStr;
  Guchar *p;
  GfxRGB rgb;
  int x, y;
  int c;

  writePSFmt("<image width=\"%d\" height=\"%d\"", width, height);

  const double *mat = state->getCTM();
  double tx = mat[0] + mat[2] + mat[4];
  double ty = mat[1] + mat[3] + mat[5];
  writePSFmt(" rect=\"%g %g %g %g\"", mat[4], mat[5], tx, ty);
  
  if (str->getKind() == strDCT && !inlineImg &&
      3 <= colorMap->getNumPixelComps() && colorMap->getNumPixelComps() <= 4) {
    // dump JPEG stream
    std::vector<char> buffer;
    // initialize stream
    str = str->getNextStream();
    str->reset();
    // copy the stream
    while ((c = str->getChar()) != EOF)
      buffer.push_back(char(c));
    str->close();

    if (colorMap->getNumPixelComps() == 3)
      writePS(" ColorSpace=\"DeviceRGB\"");
    else 
      writePS(" ColorSpace=\"DeviceCMYK\"");
    writePS(" BitsPerComponent=\"8\"");
    writePS(" Filter=\"DCTDecode\"");
    writePSFmt(" length=\"%d\"", buffer.size());
    writePS(">\n");
    
    for (unsigned int i = 0; i < buffer.size(); ++i)
      writePSFmt("%02x", buffer[i] & 0xff);

#if 0
  } else if (colorMap->getNumPixelComps() == 1 && colorMap->getBits() == 1) {
    // 1 bit depth -- not implemented in Ipe

    // initialize stream
    str->reset();
    // copy the stream
    size = height * ((width + 7) / 8);
    for (i = 0; i < size; ++i) {
      writePSFmt("%02x", (str->getChar() ^ 0xff));
    }
    str->close();
#endif
  } else if (colorMap->getNumPixelComps() == 1) {
    // write as gray level image
    writePS(" ColorSpace=\"DeviceGray\"");
    writePS(" BitsPerComponent=\"8\"");
    writePS(">\n");
    
    // initialize stream
    imgStr = new ImageStream(str, width, colorMap->getNumPixelComps(),
			     colorMap->getBits());
    imgStr->reset();
    
    // for each line...
    for (y = 0; y < height; ++y) {
      
      // write the line
      p = imgStr->getLine();
      for (x = 0; x < width; ++x) {
	GfxGray gray;
	colorMap->getGray(p, &gray);
	writePSFmt("%02x", colToByte(gray));
	p += colorMap->getNumPixelComps();
      }
    }
    delete imgStr;

  } else {
    // write as RGB image
    writePS(" ColorSpace=\"DeviceRGB\"");
    writePS(" BitsPerComponent=\"8\"");
    writePS(">\n");
    
    // initialize stream
    imgStr = new ImageStream(str, width, colorMap->getNumPixelComps(),
			     colorMap->getBits());
    imgStr->reset();
    
    // for each line...
    for (y = 0; y < height; ++y) {
      
      // write the line
      p = imgStr->getLine();
      for (x = 0; x < width; ++x) {
	colorMap->getRGB(p, &rgb);
	writePSFmt("%02x%02x%02x", 
		   colToByte(rgb.r), colToByte(rgb.g), colToByte(rgb.b));
	p += colorMap->getNumPixelComps();
      }
    }
    delete imgStr;
  }
  writePS("\n</image>\n");
}

// --------------------------------------------------------------------

struct UnicodeToLatex {
  int iUnicode;
  const char *iLatex;
};

static const UnicodeToLatex unicode2latex[] = {
  // { 0xed, "{\\'\\i}" },
  // --------------------------------------------------------------------
  { 0xb1,  "$\\pm$" },
  { 0x391, "$\\Alpha$" },
  { 0x392, "$\\Beta$" },
  { 0x393, "$\\Gamma$" },
  { 0x394, "$\\Delta$" },
  { 0x395, "$\\Epsilon$" },
  { 0x396, "$\\Zeta$" },
  { 0x397, "$\\Eta$" },
  { 0x398, "$\\Theta$" },
  { 0x399, "$\\Iota$" },
  { 0x39a, "$\\Kappa$" },
  { 0x39b, "$\\Lambda$" },
  { 0x39c, "$\\Mu$" },
  { 0x39e, "$\\Nu$" },
  { 0x39e, "$\\Xi$" },
  { 0x39f, "$\\Omicron$" },
  { 0x3a0, "$\\Pi$" },
  { 0x3a1, "$\\Rho$" },
  { 0x3a3, "$\\Sigma$" },   // sometimes \\sum would be better
  { 0x3a4, "$\\Tau$" },
  { 0x3a5, "$\\Upsilon$" },
  { 0x3a6, "$\\Phi$" },
  { 0x3a7, "$\\Chi$" },
  { 0x3a8, "$\\Psi$" },
  { 0x3a9, "$\\Omega$" },
  // --------------------------------------------------------------------
  { 0x3b1, "$\\alpha$" },
  { 0x3b2, "$\\beta$" },
  { 0x3b3, "$\\gamma$" },
  { 0x3b4, "$\\delta$" },
  { 0x3b5, "$\\varepsilon$" },
  { 0x3b6, "$\\zeta$" },
  { 0x3b7, "$\\eta$" },
  { 0x3b8, "$\\theta$" },
  { 0x3b9, "$\\iota$" },
  { 0x3ba, "$\\kappa$" },
  { 0x3bb, "$\\lambda$" },
  { 0x3bc, "$\\mu$" },
  { 0x3be, "$\\nu$" },
  { 0x3be, "$\\xi$" },
  { 0x3bf, "$\\omicron$" },
  { 0x3c0, "$\\pi$" },
  { 0x3c1, "$\\rho$" },
  { 0x3c3, "$\\sigma$" },
  { 0x3c4, "$\\tau$" },
  { 0x3c5, "$\\upsilon$" },
  { 0x3c6, "$\\phi$" },
  { 0x3c7, "$\\chi$" },
  { 0x3c8, "$\\psi$" },
  { 0x3c9, "$\\omega$" },
  // --------------------------------------------------------------------
  { 0x2013, "-" },
  { 0x2019, "'" },
  { 0x2022, "$\\bullet$" },
  { 0x2026, "$\\cdots$" },
  { 0x2190, "$\\leftarrow$" },
  { 0x21d2, "$\\Rightarrow$" },
  { 0x2208, "$\\in$" },
  { 0x2209, "$\\not\\in$" },
  { 0x2211, "$\\sum$" },
  { 0x2212, "-" },
  { 0x221e, "$\\infty$" },
  { 0x222a, "$\\cup$" },
  { 0x2260, "$\\neq$" },
  { 0x2264, "$\\leq$" },
  { 0x2265, "$\\geq$" },
  { 0x22c5, "$\\cdot$" },
  { 0x2286, "$\\subseteq$" },
  { 0x25aa, "$\\diamondsuit$" },
  // --------------------------------------------------------------------
  // ligatures
  { 0xfb00, "ff" },
  { 0xfb01, "fi" },
  { 0xfb02, "fl" },
  { 0xfb03, "ffi" },
  { 0xfb04, "ffl" },
  { 0xfb06, "st" },
  // --------------------------------------------------------------------
};

#define UNICODE2LATEX_LEN (sizeof(unicode2latex) / sizeof(UnicodeToLatex))
    
void XmlOutputDev::writePSUnicode(int ch)
{
  if (iIsLiteral  &&  ch == '\\') {
    writePSChar(ch);
    return;
  }

  if (!iIsLiteral) {
    if (ch == '&' || ch == '$' || ch == '#' || ch == '%'
	|| ch == '_' || ch == '{' || ch == '}') {
      writePS("\\");
      writePSChar(ch);
      return;
    }
    if (ch == '<') {
      writePS("$&lt;$");
      return;
    }
    if (ch == '>') {
      writePS("$&gt;$");
      return;
    }
    if (ch == '^') {
      writePS("\\^{}");
      return;
    }
    if (ch == '~') {
      writePS("\\~{}");
      return;
    }
    if (ch == '\\') {
      writePS("$\\setminus$");
      return;
    }
  }

  // replace some common Unicode characters
  if (1 <= iUnicodeLevel && iUnicodeLevel <= 2) {
    for (int i = 0; i < UNICODE2LATEX_LEN; ++i) {
      if (ch == unicode2latex[i].iUnicode) {
	writePS(unicode2latex[i].iLatex);
	return;
      }
    }
  }
  
  writePSChar(ch);
}

void XmlOutputDev::writePSChar(int code)
{
  if (code == '<')
    writePS("&lt;");
  else if (code == '>')
    writePS("&gt;");
  else if (code == '&')
    writePS("&amp;");
  else if (code < 0x80)
    writePSFmt("%c", code);
  else {
    iUnicode = true;
    if (iUnicodeLevel < 2) {
      writePSFmt("[U+%x]", code);
      fprintf(stderr, "Unknown Unicode character U+%x on page %d\n", 
	      code, seqPage);
    } else {
      if (code < 0x800) {
	writePSFmt("%c%c", 
		   (((code & 0x7c0) >> 6) | 0xc0),
		   ((code & 0x03f) | 0x80)); 
      } else {
	// Do we never need to write UCS larger than 0x10000?
	writePSFmt("%c%c%c", 
		   (((code & 0x0f000) >> 12) | 0xe0),
		   (((code & 0xfc0) >> 6) | 0x80),
		   ((code & 0x03f) | 0x80));
      }
    }
  }
}

void XmlOutputDev::writeColor(const char *prefix, const GfxRGB &rgb, 
			      const char *suffix)
{
  if (prefix)
    writePS(prefix);
  writePSFmt("\"%f %f %f\"", colToDbl(rgb.r), colToDbl(rgb.g), colToDbl(rgb.b));
  if (suffix)
    writePS(suffix);
}

void XmlOutputDev::writePS(const char *s)
{
  fwrite(s, 1, strlen(s), outputStream);
}

void XmlOutputDev::writePSFmt(const char *fmt, ...)
{
  va_list args;
  char buf[512];

  va_start(args, fmt);
  vsprintf(buf, fmt, args);
  va_end(args);
  fwrite(buf, 1, strlen(buf), outputStream);
}

// --------------------------------------------------------------------
