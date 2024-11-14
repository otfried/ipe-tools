// --------------------------------------------------------------------
// Pdftoipe: convert PDF file to editable Ipe XML file
// --------------------------------------------------------------------

#include <memory>
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <string.h>

#include "goo/GooString.h"
#include "goo/gmem.h"
#include "Object.h"
#include "Stream.h"
#include "Array.h"
#include "Dict.h"
#include "XRef.h"
#include "Catalog.h"
#include "Page.h"
#include "PDFDoc.h"
#include "Error.h"
#include "GlobalParams.h"

#include "parseargs.h"
#include "xmloutputdev.h"

static int firstPage = 1;
static int lastPage = 0;
static int mergeLevel = 0;
static int unicodeLevel = 1;
static char ownerPassword[33] = "";
static char userPassword[33] = "";
static bool quiet = false;
static bool printHelp = false;
static bool math = false;
static bool literal = false;
static bool notext = false;
static bool noTextSize = false;

static ArgDesc argDesc[] = {
  {"-f",      argInt,      &firstPage,      0,
   "first page to convert"},
  {"-l",      argInt,      &lastPage,       0,
   "last page to convert"},
  {"-opw",    argString,   ownerPassword,   sizeof(ownerPassword),
   "owner password (for encrypted files)"},
  {"-upw",    argString,   userPassword,    sizeof(userPassword),
   "user password (for encrypted files)"},
  {"-q",      argFlag,     &quiet,          0,
   "don't print any messages or errors"},
  {"-math",   argFlag,     &math,           0,
   "turn all text objects into math formulas"},
  {"-literal", argFlag,    &literal,        0,
   "allow math mode in input text objects"},
  {"-notext", argFlag,     &notext,         0,
   "discard all text objects"},
  {"-notextsize", argFlag, &noTextSize,     0,
   "ignore size of text objects"},
  {"-merge",  argInt,      &mergeLevel,     0,
   "how eagerly should consecutive text be merged: 0, 1, or 2 (default 0)"},
  {"-unicode",  argInt,    &unicodeLevel,       0,
   "how much Unicode should be used: 1, 2, or 3 (default 1)"},
  {"-h",      argFlag,     &printHelp,      0,
   "print usage information"},
  {"-help",   argFlag,     &printHelp,      0,
   "print usage information"},
  {"--help",  argFlag,     &printHelp,      0,
   "print usage information"},
  {"-?",      argFlag,     &printHelp,      0,
   "print usage information"},
  {NULL, argFlag, 0, 0, 0}
};

int main(int argc, char *argv[])
{
  // parse args
  bool ok = parseArgs(argDesc, &argc, argv);
  if (!ok || argc < 2 || argc > 3 || printHelp) {
    fprintf(stderr, "pdftoipe version %s\n", PDFTOIPE_VERSION);
    printUsage("pdftoipe", "<PDF-file> [<XML-file>]", argDesc);
    return 1;
  }

  GooString *fileName = new GooString(argv[1]);

  globalParams = std::make_unique<GlobalParams>();
  if (quiet)
    globalParams->setErrQuiet(quiet);

  #if POPPLER_VERSION_AT_LEAST(22, 3, 0)
    std::optional<GooString> ownerPW, userPW;
  #else
    GooString *ownerPW, *userPW;
  #endif
  if (ownerPassword[0]) {
    #if POPPLER_VERSION_AT_LEAST(22, 3, 0)
      ownerPW = GooString(ownerPassword);
    #else
      ownerPW = new GooString(ownerPassword);
    #endif
  } else {
    #if POPPLER_VERSION_AT_LEAST(22, 3, 0)
      ownerPW = std::nullopt;
    #else
      ownerPW = 0;
    #endif
  }
  if (userPassword[0]) {
    #if POPPLER_VERSION_AT_LEAST(22, 3, 0)
      userPW = GooString(userPassword);
    #else
      userPW = new GooString(userPassword);
    #endif
  } else {
    #if POPPLER_VERSION_AT_LEAST(22, 3, 0)
      userPW = std::nullopt;
    #else
      userPW = 0;
    #endif
  }

    // open PDF file
    #if POPPLER_VERSION_AT_LEAST(22, 3, 0)
      PDFDoc *doc = new PDFDoc(std::make_unique<GooString>(fileName), ownerPW, userPW);
    #else
      PDFDoc *doc = new PDFDoc(fileName, ownerPW, userPW);
      delete userPW;
      delete ownerPW;
    #endif

  if (!doc->isOk())
    return 1;
  
  // construct XML file name
  std::string xmlFileName;
  if (argc == 3) {
    xmlFileName = argv[2];
  } else {
    const char *p = fileName->c_str() + fileName->getLength() - 4;
    if (!strcmp(p, ".pdf") || !strcmp(p, ".PDF")) {
        xmlFileName = std::string(fileName->c_str(),
                                  fileName->getLength() - 4);
    } else {
      xmlFileName = fileName->c_str();
    }
    xmlFileName += ".ipe";
  }

  // get page range
  if (firstPage < 1)
    firstPage = 1;

  if (lastPage < 1 || lastPage > doc->getNumPages())
    lastPage = doc->getNumPages();

  // write XML file
  XmlOutputDev *xmlOut = 
    new XmlOutputDev(xmlFileName, doc->getXRef(),
                     doc->getCatalog(), firstPage, lastPage);

  // tell output device about text handling
  xmlOut->setTextHandling(math, notext, literal, mergeLevel, noTextSize, unicodeLevel);
  
  int exitCode = 2;
  if (xmlOut->isOk()) {
    doc->displayPages(xmlOut, firstPage, lastPage, 
		      // double hDPI, double vDPI, int rotate,
		      // bool useMediaBox, bool crop, bool printing,
		      72.0, 72.0, 0, false, false, false);
    exitCode = 0;
  }

  if (xmlOut->hasUnicode()) {
    fprintf(stderr, "The document contains Unicode (non-ASCII) text.\n");
    if (unicodeLevel <= 1)
      fprintf(stderr, "Unknown Unicode characters were replaced by [U+XXX].\n");
    else
      fprintf(stderr, "UTF-8 was set as document encoding in the preamble.\n");
  }

  // clean up
  delete xmlOut;
  delete doc;

  return exitCode;
}

// --------------------------------------------------------------------
