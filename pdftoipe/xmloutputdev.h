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

#define PDFTOIPE_VERSION "2021/09/08"

class XmlOutputDev : public OutputDev
{
public:

  // Open an XML output file, and write the prolog.
  XmlOutputDev(const std::string& fileName, XRef *xrefA, Catalog *catalog,
               int firstPage, int lastPage);
  
  // Destructor -- writes the trailer and closes the file.
  virtual ~XmlOutputDev();

  // Check if file was successfully created.
  bool isOk() { return ok; }

  bool hasUnicode() const { return iUnicode; }

  void setTextHandling(bool math, bool notext, bool literal,
                       int mergeLevel, bool noTextSize, int unicodeLevel);
  
  //---- get info about output device

  // Does this device use upside-down coordinates?
  // (Upside-down means (0,0) is the top left corner of the page.)
  virtual bool upsideDown() override { return false; }

  // Does this device use drawChar() or drawString()?
  virtual bool useDrawChar() override { return true; }

  // Does this device use beginType3Char/endType3Char?  Otherwise,
  // text in Type 3 fonts will be drawn with drawChar/drawString.
  virtual bool interpretType3Chars() override { return false; }

  //----- initialization and control

  // Start a page.
  virtual void startPage(int pageNum, GfxState *state, XRef *xrefA) override;

  // End a page.
  virtual void endPage() override;

  //----- update graphics state
  virtual void updateTextPos(GfxState *state) override;
  virtual void updateTextShift(GfxState *state, double shift) override;

  //----- path painting
  virtual void stroke(GfxState *state) override;
  virtual void fill(GfxState *state) override;
  virtual void eoFill(GfxState *state) override;

  //----- text drawing
  virtual void drawChar(GfxState *state, double x, double y,
			double dx, double dy,
			double originX, double originY,
			CharCode code, int nBytes, const Unicode *u, int uLen) override;

  //----- image drawing
  virtual void drawImage(GfxState *state, Object *ref, Stream *str,
			 int width, int height, GfxImageColorMap *colorMap,
			 bool interpolate, const int *maskColors, bool inlineImg) override;

protected:
  void startDrawingPath();
  void startText(GfxState *state, double x, double y);
  void finishText();
  void writePSUnicode(int ch);
  
  void doPath(GfxState *state);
  void writePSChar(int code);
  void writePS(const char *s);
  void writePSFmt(const char *fmt, ...);
  void writeColor(const char *prefix, const GfxRGB &rgb, const char *suffix);

protected:
  FILE *outputStream;
  int seqPage;			// current sequential page number
  XRef *xref;			// the xref table for this PDF file
  bool ok;			    // set up ok?
  bool iUnicode;                // has a Unicode character been used?

  bool iIsLiteral;              // take latex in text literally
  bool iIsMath;                 // make text objects math formulas
  bool iNoText;                 // discard text objects
  bool inText;                  // inside a text object
  bool iNoTextSize;             // all text objects at normal size
  int  iMergeLevel;             // text merge level
  int iUnicodeLevel;            // unicode handling
};

// --------------------------------------------------------------------
#endif
