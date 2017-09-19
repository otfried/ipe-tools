// -*- C++ -*-
// --------------------------------------------------------------------
// XmlOutputDev.h
// --------------------------------------------------------------------

#ifndef XMLOUTPUTDEV_H
#define XMLOUTPUTDEV_H

#include <stddef.h>
#include "Object.h"
#include "OutputDev.h"
#include "GfxState.h"

class GfxPath;
class GfxFont;

#define PDFTOIPE_VERSION "2017/09/19"

class XmlOutputDev : public OutputDev
{
public:

  // Open an XML output file, and write the prolog.
  XmlOutputDev(char *fileName, XRef *xrefA, Catalog *catalog,
	       int firstPage, int lastPage);
  
  // Destructor -- writes the trailer and closes the file.
  virtual ~XmlOutputDev();

  // Check if file was successfully created.
  virtual GBool isOk() { return ok; }

  bool hasUnicode() const { return iUnicode; }

  void setTextHandling(GBool math, GBool notext, GBool literal,
		       int mergeLevel, int unicodeLevel);
  
  //---- get info about output device

  // Does this device use upside-down coordinates?
  // (Upside-down means (0,0) is the top left corner of the page.)
  virtual GBool upsideDown() { return gFalse; }

  // Does this device use drawChar() or drawString()?
  virtual GBool useDrawChar() { return gTrue; }

  // Does this device use beginType3Char/endType3Char?  Otherwise,
  // text in Type 3 fonts will be drawn with drawChar/drawString.
  virtual GBool interpretType3Chars() { return gFalse; }

  //----- initialization and control

  // Start a page.
  virtual void startPage(int pageNum, GfxState *state); // poppler <=0.22
  virtual void startPage(int pageNum, GfxState *state, XRef *xrefA);

  // End a page.
  virtual void endPage();

  //----- update graphics state
  virtual void updateTextPos(GfxState *state);
  virtual void updateTextShift(GfxState *state, double shift);

  //----- path painting
  virtual void stroke(GfxState *state);
  virtual void fill(GfxState *state);
  virtual void eoFill(GfxState *state);

  //----- text drawing
  virtual void drawChar(GfxState *state, double x, double y,
			double dx, double dy,
			double originX, double originY,
			CharCode code, int nBytes, Unicode *u, int uLen);

  //----- image drawing
  virtual void drawImage(GfxState *state, Object *ref, Stream *str,
			 int width, int height, GfxImageColorMap *colorMap,
			 GBool interpolate, int *maskColors, GBool inlineImg);

protected:
  virtual void startDrawingPath();
  virtual void startText(GfxState *state, double x, double y);
  virtual void finishText();
  virtual void writePSUnicode(int ch);
  
  void doPath(GfxState *state);
  void writePSChar(int code);
  void writePS(const char *s);
  void writePSFmt(const char *fmt, ...);
  void writeColor(const char *prefix, const GfxRGB &rgb, const char *suffix);

protected:
  FILE *outputStream;
  int seqPage;			// current sequential page number
  XRef *xref;			// the xref table for this PDF file
  GBool ok;			// set up ok?
  bool iUnicode;                // has a Unicode character been used?

  bool iIsLiteral;              // take latex in text literally
  bool iIsMath;                 // make text objects math formulas
  bool iNoText;                 // discard text objects
  bool inText;                  // inside a text object
  int  iMergeLevel;             // text merge level
  int iUnicodeLevel;            // unicode handling
};

// --------------------------------------------------------------------
#endif
