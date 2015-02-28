/*

    This file is part of the extensible drawing editor Ipe.
    Copyright (C) 1993-2008 Otfried Cheong <otfried@ipe.airpost.net>

    Ipe is free software; you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    As a special exception, you have permission to link Ipe with the
    CGAL library and distribute executables, as long as you follow the
    requirements of the Gnu General Public License in regard to all of
    the software in the executable aside from CGAL.

    Ipe is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
    or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
    License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
*/
/*
 * figtoipe.cpp
 *
 * This program converts files in FIG format (as used by Xfig) to XML
 * format as used by Ipe 6.0.
 *
 * All versions of the FIG file format are documented here:
 *  "http://duke.usask.ca/~macphed/soft/fig/formats.html"
 *
 * This program can read only versions 3.0, 3.1, and 3.2.
 *
 * Changes:
 *
 * 2005/10/31 - replace double backslash by single one in text.
 * 2005/11/14 - generate correct header for Ipe 6.0 preview 25.
 * 2007/08/19 - Alexander Buerger acfb@users.sf.net
 *              + include some images with anytopnm
 *              + correct FIG3.1 problem (bugzilla #237)
 *              + fixed rotation of text and ellipses
 *              + do not write invisible ellipses / polylines / arcs
 *              + accept double values in some places (points, thickness, ...;
 *                extends FIG format)
 *              + skip comments between FIG objects
 *              + replaced some %g formats as they illegally appear in the PDF
 * 2007/09/26 - Alexander Buerger acfb@users.sf.net
 *              + compress bitmap images
 *              + include compressed JPEG images
 * 2008/04/26 - Alexander Buerger acfb@users.sf.net
 *              + support grayscale pnm
 *              + added -g and -p options
 * 2009/10/22 - Alexander Buerger acfb@users.sf.net
 *              + added -c option to use cropbox for output figure
 *              + check fgets/fscanf return values
 * 2009/12/05 - Alexander Buerger acfb@users.sf.net
 *              + write ipe 7 format by default
 *              + added -6 option to write in ipe 6 format
 *              + added simple_getopt function to parse options
 *              + reduce filesize for images by putting 36 bytes per line
 * 2015/02/28 - Alexander Buerger acfb@users.sf.net
 *              + check color array indices
 *              + limit image filename string length in fscanf
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <zlib.h>

#include <vector>
#include <string>
#include <sstream>
#include <fstream>
#include <algorithm>

#define FIGTOIPE_VERSION "figtoipe 2015/02/28"

const int MEDIABOX_WIDTH = 595;
const int MEDIABOX_HEIGHT = 842;
bool ipe7 = true;

const int NFIXEDCOLORS = 32, NUSERCOLORS = 512,
    NCOLORS = NFIXEDCOLORS + NUSERCOLORS;

// --------------------------------------------------------------------

struct Arrow {
  int iType;
  int iStyle;
  double iThickness; // 1/80 inch
  double iWidth;     // Fig units
  double iHeight;    // Fig units
};

struct Point {
  double iX, iY;
};

struct FigObject {
  int iType;
  int iSubtype;     // meaning depends on type
  int iLinestyle;   // solid, dashed, etc
  double iThickness;   // 0 means no stroke
  int iPenColor;
  int iFillColor;
  int iDepth;       // depth ordering
  int iPenStyle;    // not used by FIG
  int iAreaFill;    // how to fill: color, pattern
  double iStyle;    // length of dash/dot pattern
  int iCapStyle;
  int iJoinStyle;
  int iDirection;
  int iForwardArrow;
  Arrow iForward;
  int iBackwardArrow;
  Arrow iBackward;
  double iCenterX, iCenterY;  // center of ellipse and arc
  Point iArc1, iArc2, iArc3;
  double iAngle;    // orientation of main axis of ellipse
  Point iRadius;    // half-axes of ellipse
  int iArcBoxRadius;
  Point iPos;       // position of text
  int iFont;
  int iFontFlags;
  double iFontSize;
  std::vector<char> iString;
  std::vector<Point> iPoints;
  std::string image_filename;
  bool image_flipped;
};

// --------------------------------------------------------------------

class FigReader {
public:
  FigReader(FILE *fig) :
      iFig(fig) { }
  bool ReadHeader();
  double Magnification() const { return iMagnification; }
  double UnitsPerPoint() const { return iUnitsPerPoint; }
  bool ReadObjects();
  const std::vector<FigObject> &Objects() const { return iObjects; }
  const unsigned int *UserColors() const { return iUserColors; }
private:
  bool GetLine(char *buf);
  int GetInt();
  int GetColorInt();
  double GetDouble();
  Point GetPoint();
  void GetColor();
  void GetArc(FigObject &obj);
  void GetEllipse(FigObject &obj);
  void GetPolyline(FigObject &obj);
  void GetSpline(FigObject &obj);
  void GetText(FigObject &obj);
  void GetArrow(Arrow &a);
  void GetArrows(FigObject &obj);
  int ComputeDepth(unsigned int &i);

private:
  FILE *iFig;
  int iVersion;  // minor version of FIG format
  double iMagnification;
  double iUnitsPerPoint;
  std::vector<FigObject> iObjects;
  unsigned int iUserColors[NUSERCOLORS];
};

// --------------------------------------------------------------------

const int BUFSIZE = 0x100;

// skip comment lines (in the header)
bool FigReader::GetLine(char *buf)
{
  do {
    if (fgets(buf, BUFSIZE, iFig) == NULL)
      return false;
  } while (buf[0] == '#');
  return true;
}

int FigReader::GetInt()
{
  int num = -1;
  if( fscanf(iFig, "%d", &num) != 1 && !feof(iFig))
      fprintf(stderr, "Could not read integer value.\n");
  return num;
}

int FigReader::GetColorInt()
{
  int color = GetInt();
  if( color < 0 || color >= NCOLORS ) {
    fprintf(stderr, "Color value %d out of range.\n", color);
    color = 0;
  }
  return color;
}

double FigReader::GetDouble()
{
  double num = -1;
  if( fscanf(iFig, "%lg", &num) != 1 )
      fprintf(stderr, "Could not read double value.\n");
  return num;
}

Point FigReader::GetPoint()
{
  Point p;
  p.iX = GetDouble();
  p.iY = GetDouble();
  return p;
}

void FigReader::GetArrow(Arrow &a)
{
  a.iType = GetInt();
  a.iStyle = GetInt();
  a.iThickness = GetDouble();
  a.iWidth = GetDouble();
  a.iHeight = GetDouble();
}

void FigReader::GetArrows(FigObject &obj)
{
  if (obj.iForwardArrow)
    GetArrow(obj.iForward);
  if (obj.iBackwardArrow)
    GetArrow(obj.iBackward);
}

// --------------------------------------------------------------------

bool FigReader::ReadHeader()
{
  char line[BUFSIZE];
  if (fgets(line, BUFSIZE, iFig) != line)
      return false;
  if (strncmp(line, "#FIG", 4))
    return false;

  // check FIG version
  int majorVersion;
  sscanf(line + 4, "%d.%d", &majorVersion, &iVersion);
  if (majorVersion != 3 || iVersion<0 || iVersion>2 ) {
    fprintf(stderr, "Figtoipe supports FIG versions 3.0 - 3.2 only.\n");
    return false;
  }

  fprintf(stderr, "FIG format version %d.%d\n", majorVersion, iVersion);

  // skip orientation and justification
  if (!GetLine(line))
    return false;
  if (!GetLine(line))
    return false;

  bool metric = false;
  if (!GetLine(line))
    return false;
  if (!strncmp(line, "Metric", 6))
    metric = true;
  (void) metric; // not yet used

  int magnification = 100, resolution=1200;
  if (iVersion == 2) {
    // Version 3.2:
    // papersize
    if (!GetLine(line))
      return false;
    // export and print magnification
    if (!GetLine(line))
      return false;
    sscanf(line, "%d", &magnification);
    // multi-page mode
    if (!GetLine(line))
      return false;
    // transparent color
    if (!GetLine(line))
      return false;
  }
  // resolution and coord_system
  if (!GetLine(line))
      return false;
  int coord_system;
  sscanf(line, "%d %d", &resolution, &coord_system);
  
  iUnitsPerPoint = (resolution / 72.0);
  iMagnification = magnification / 100.0;
  return true;
}

// link start and end of compounds together,
// and assign depth to compound object
int FigReader::ComputeDepth(unsigned int &i)
{
  if (iObjects.at(i).iType != 6)
    return iObjects.at(i++).iDepth;
  int pos = i;
  int depth = 1000;
  ++i;
  while (iObjects.at(i).iType != -6) {
    int od = ComputeDepth(i);
    if (od < depth) depth = od;
  }
  iObjects.at(pos).iDepth = depth;
  iObjects.at(pos).iSubtype = i;
  ++i;
  return depth;
}

// --------------------------------------------------------------------

// objects are appended to list
bool FigReader::ReadObjects()
{
  int level = 0;
  for (;;) {
      int objType = GetInt();
      //fprintf(stderr, "object type %d\n", objType);
      if (objType == -1 && fgetc(iFig)=='#' ) {
          char buf[1024];
          if( fgets(buf, sizeof(buf), iFig) == NULL ) {
              fprintf(stderr, "Read error while skipping comment.\n");
              return false;
          }
         continue;
     }
    if (objType == -1) { // EOF
      if (level > 0)
	return false;
      unsigned int i = 0;
      while (i < iObjects.size())
	ComputeDepth(i);
      return true;
    }
    if (objType == 0) { // user-defined color
      GetColor();
    } else {
      FigObject obj;
      obj.iType = objType;
      switch (obj.iType) {
      case 1: // ELLIPSE
	GetEllipse(obj);
	break;
      case 2: // POLYLINE
	GetPolyline(obj);
	break;
      case 3: // SPLINE
	GetSpline(obj);
	break;
      case 4: // TEXT
	GetText(obj);
	break;
      case 5: // ARC
	GetArc(obj);
	break;
      case 6: // COMPOUND
	(void) GetInt(); // read and ignore bounding box
	(void) GetInt();
	(void) GetInt();
	(void) GetInt();
	++level;
	break;
      case -6: // END of COMPOUND
	if (level == 0)
	  return false;
	--level;
	break;
      default:
	fprintf(stderr, "Unknown object type in FIG file.\n");
	return false;
      }
      iObjects.push_back(obj);
    }
  }
}

void FigReader::GetColor()
{
  int colorNum = GetInt();    // color number
  int rgb = 0;
  if( fscanf(iFig," #%x", &rgb) != 1 )  // RGB string in hex
      fprintf(stderr, "Could not read rgb string.\n");
  if( colorNum<NFIXEDCOLORS || colorNum>=NCOLORS ) {
    fprintf(stderr, "User color number %d out of range, replacing with %d.\n",
            colorNum, NFIXEDCOLORS);
    colorNum = NFIXEDCOLORS;
  }
  iUserColors[colorNum - NFIXEDCOLORS] = rgb;
}

void FigReader::GetEllipse(FigObject &obj)
{
  obj.iSubtype = GetInt();
  obj.iLinestyle = GetInt();
  obj.iThickness = GetDouble();
  obj.iPenColor = GetColorInt();
  obj.iFillColor = GetColorInt();
  obj.iDepth = GetInt();
  obj.iPenStyle = GetInt();  // not used
  obj.iAreaFill = GetInt();
  obj.iStyle = GetDouble();
  obj.iDirection = GetInt(); // always 1
  obj.iAngle = GetDouble();  // radians, the angle of the x-axis
  obj.iCenterX = GetDouble();
  obj.iCenterY = GetDouble();
  obj.iRadius = GetPoint();
  (void) GetPoint(); // start
  (void) GetPoint(); // end
}

void FigReader::GetPolyline(FigObject &obj)
{
  obj.iSubtype = GetInt();
  obj.iLinestyle = GetInt();
  obj.iThickness = GetDouble();
  obj.iPenColor = GetColorInt();
  obj.iFillColor = GetColorInt();
  obj.iDepth = GetInt();
  obj.iPenStyle = GetInt(); // not used
  obj.iAreaFill = GetInt();
  obj.iStyle = GetDouble();
  obj.iJoinStyle = GetInt();
  obj.iCapStyle = GetInt();
  obj.iArcBoxRadius = GetInt();
  obj.iForwardArrow = GetInt();
  obj.iBackwardArrow = GetInt();
  int nPoints = GetInt();
  GetArrows(obj);
  if (obj.iSubtype == 5) { // Imported image
      int orientation;
      char image_filename[1024];
      // orientation and filename
      if( fscanf(iFig, "%d %1020s", &orientation, image_filename) != 2 ) {
          fprintf(stderr, "Could not read image orientation and/or filename. Exit.\n");
          exit(-1);
      }
      obj.image_flipped = (orientation==1);
      obj.image_filename = std::string(image_filename);
  }
  for (int i = 0; i < nPoints; ++i)
      obj.iPoints.push_back( GetPoint() );
}


void FigReader::GetSpline(FigObject &obj)
{
  /* 0: opened approximated spline
     1: closed approximated spline
     2: opened interpolated spline
     3: closed interpolated spline
     4: opened x-spline (FIG 3.2)
     5: closed x-spline (FIG 3.2)
  */
  obj.iSubtype = GetInt();
  obj.iLinestyle = GetInt();
  obj.iThickness = GetDouble();
  obj.iPenColor = GetColorInt();
  obj.iFillColor = GetColorInt();
  obj.iDepth = GetInt();
  obj.iPenStyle = GetInt(); // not used
  obj.iAreaFill = GetInt();
  obj.iStyle = GetDouble();
  obj.iCapStyle = GetInt();
  obj.iForwardArrow = GetInt();
  obj.iBackwardArrow = GetInt();

  int nPoints = GetInt();
  GetArrows(obj);

  for (int i = 0; i < nPoints; ++i)
      obj.iPoints.push_back( GetPoint() );

  if (iVersion == 2) {
    // shape factors exist in FIG 3.2 only
    for (int i = 0; i < nPoints; ++i) {
      (void) GetDouble(); // double shapeFactor
    }
  } else {
    if (obj.iSubtype > 1) {
      for (int i = 0; i < nPoints; ++i) {
	(void) GetDouble(); // double lx
	(void) GetDouble(); // double ly
	(void) GetDouble(); // double rx
	(void) GetDouble(); // double ry
      }
    }
  }
}

void FigReader::GetText(FigObject &obj)
{
  obj.iSubtype = GetInt();
  obj.iThickness = 1;       // stroke
  obj.iPenColor = GetColorInt();
  obj.iDepth = GetInt();
  obj.iPenStyle = GetInt(); // not used
  obj.iFont = GetInt();
  obj.iFontSize = GetDouble();
  obj.iAngle = GetDouble();
  obj.iFontFlags = GetInt();
  (void) GetDouble(); // height
  (void) GetDouble(); // length
  obj.iPos = GetPoint();
  // skip blank
  fgetc(iFig);
  std::vector<char> string;
  for (;;) {
    int ch = fgetc(iFig);
    if (ch == EOF)
      break;
    if (ch < 0x80) {
      string.push_back(char(ch));
    } else {
      // convert to UTF-8
      string.push_back(char(0xc0 + ((ch >> 6) & 0x3)));
      string.push_back(char(ch & 0x3f));
    }
    if (string.size() >= 4 &&
	!strncmp(&string[string.size() - 4], "\\001", 4)) {
      string.resize(string.size() - 4);
      break;
    }
    // fig seems to store "\" as "\\"
    if (string.size() >= 2 &&
	!strncmp(&string[string.size() - 2], "\\\\", 2)) {
      string.resize(string.size() - 1);
    }
  }
  string.push_back('\0');
  obj.iString = string;
}

void FigReader::GetArc(FigObject &obj)
{
  obj.iSubtype = GetInt();
  obj.iLinestyle = GetInt();
  obj.iThickness = GetDouble();
  obj.iPenColor = GetColorInt();
  obj.iFillColor = GetColorInt();
  obj.iDepth = GetInt();
  obj.iPenStyle = GetInt();  // not used
  obj.iAreaFill = GetInt();
  obj.iStyle = GetDouble();
  obj.iCapStyle = GetInt();
  obj.iDirection = GetInt();
  obj.iForwardArrow = GetInt();
  obj.iBackwardArrow = GetInt();
  obj.iCenterX = GetDouble();
  obj.iCenterY = GetDouble();
  obj.iArc1 = GetPoint();
  obj.iArc2 = GetPoint();
  obj.iArc3 = GetPoint();
  GetArrows(obj);
}

// --------------------------------------------------------------------

unsigned int ColorTable[] = {
  0x000000, 0x0000ff, 0x00ff00, 0x00ffff,
  0xff0000, 0xff00ff, 0xffff00, 0xffffff,
  0x000090, 0x0000b0, 0x0000d0, 0x87ceff,
  0x009000, 0x00b000, 0x00d000, 0x009090,
  0x00b0b0, 0x00d0d0, 0x900000, 0xb00000,
  0xd00000, 0x900090, 0xb000b0, 0xd000d0,
  0x803000, 0xa04000, 0xc06000, 0xff8080,
  0xffa0a0, 0xffc0c0, 0xffe0e0, 0xffd700
};

class FigWriter {
public:
  FigWriter(FILE *xml, const std::string& figname,
            double mag, double upp, const unsigned int *uc) :
    iXml(xml), iFigName(figname), iMagnification(mag),  iUnitsPerPoint(upp),
    iUserColors(uc) { }
  void WriteObjects(const std::vector<FigObject> &objects, int start, int fin);

private:
  void WriteEllipse(const FigObject &obj);
  void WriteImage(const FigObject &obj);
  void WritePolyline(const FigObject &obj);
  void WriteSpline(const FigObject &obj);
  void WriteText(const FigObject &obj);
  void WriteArc(const FigObject &obj);

  void WriteStroke(const FigObject &obj);
  void WriteFill(const FigObject &obj);
  void WriteLineStyle(const FigObject &obj);
  void WriteArrows(const FigObject &obj);

  double X(double x);
  double Y(double y);
  unsigned int rgbColor(int colornum);

private:
  FILE *iXml;
  const std::string iFigName;
  double iMagnification;
  double iUnitsPerPoint;
  const unsigned int *iUserColors;
};

double FigWriter::X(double x)
{
  return (x / iUnitsPerPoint) * iMagnification;
}

double FigWriter::Y(double y)
{
  return MEDIABOX_HEIGHT - X(y);
}

unsigned int FigWriter::rgbColor(int colornum)
{
  if (colornum < 0 || colornum >= NCOLORS)
    colornum = 0;
  if (colornum < NFIXEDCOLORS)
    return ColorTable[colornum];
  else
    return iUserColors[colornum - NCOLORS];
}

void FigWriter::WriteStroke(const FigObject &obj)
{
  if (obj.iThickness == 0)  // no stroke
    return;
  unsigned int rgb = rgbColor(obj.iPenColor);
  fprintf(iXml, " stroke=\"%g %g %g\"",
	  ((rgb >> 16) & 0xff) / 255.0,
	  ((rgb >> 8) & 0xff) / 255.0,
	  (rgb & 0xff) / 255.0);
}

void FigWriter::WriteFill(const FigObject &obj)
{
  // unfilled
  if (obj.iAreaFill == -1)
    return;

  int fill = obj.iAreaFill;
  if (fill > 40) {
    fprintf(stderr, "WARNING: fill pattern %d replaced by solid filling.\n",
	    fill);
    fill = 20;
  }

  if (obj.iFillColor < 1) { // BLACK & DEFAULT
    fprintf(iXml, " fill=\"%g\"", 1.0 - (fill / 20.0));
  } else {
    unsigned int rgb = rgbColor(obj.iFillColor);
    double r = ((rgb >> 16) & 0xff) / 255.0;
    double g = ((rgb >> 8) & 0xff) / 255.0;
    double b = (rgb & 0xff) / 255.0;
    if (fill < 20) {
      // mix down to black
      double scale = fill / 20.0;
      r *= scale;
      g *= scale;
      b *= scale;
    } else if (fill > 20) {
      // mix up to white
      double scale = (40 - fill) / 20.0;  // 40 is pure white
      r = 1.0 - (1.0 - r) * scale;
      g = 1.0 - (1.0 - g) * scale;
      b = 1.0 - (1.0 - b) * scale;
    }
    fprintf(iXml, " fill=\"%g %g %g\"", r, g, b);
  }
}

void FigWriter::WriteLineStyle(const FigObject &obj)
{
  if (obj.iThickness == 0)
    return;
  fprintf(iXml, " pen=\"%g\"",
	  iMagnification * 72.0 * (obj.iThickness / 80.0));
  switch (obj.iLinestyle) {
  case -1: // Default
  case 0:  // Solid
    break;
  case 1:
    fprintf(iXml, " dash=\"dashed\"");
    break;
  case 2:
    fprintf(iXml, " dash=\"dotted\"");
    break;
  case 3:
    fprintf(iXml, " dash=\"dash dotted\"");
    break;
  case 4:
    fprintf(iXml, " dash=\"dash dot dotted\"");
    break;
  case 5: // Dash-triple-dotted (maybe put this in a stylesheet)
    fprintf(iXml, " dash=\"[4 2 1 2 1 2 1 2] 0\"");
    break;
  }
}

void FigWriter::WriteArrows(const FigObject &obj)
{
  if (obj.iForwardArrow)
    fprintf(iXml, " arrow=\"%g\"", X(obj.iForward.iHeight));
  if (obj.iBackwardArrow)
    fprintf(iXml, " backarrow=\"%g\"", X(obj.iBackward.iHeight));
}

// --------------------------------------------------------------------

class DepthCompare {
public:
  DepthCompare(const std::vector<FigObject> &objects)
    : iObjects(objects) { /* nothing */ }
  int operator()(int lhs, int rhs) const
  {
    return (iObjects.at(lhs).iDepth > iObjects.at(rhs).iDepth);
  }
private:
  const std::vector<FigObject> &iObjects;
};

void FigWriter::WriteObjects(const std::vector<FigObject> &objects,
			     int start, int fin)
{
  // collect indices of objects
  std::vector<int> objs;
  int i = start;
  while (i < fin) {
    objs.push_back(i);
    if (objects.at(i).iType == 6)
        i = objects.at(i).iSubtype;  // link to END OF COMPOUND
    ++i;
  }
  // now sort the objects
  DepthCompare comp(objects);
  std::stable_sort(objs.begin(), objs.end(), comp);
  // now render them
  for (unsigned int j = 0; j < objs.size(); ++j) {
    i = objs[j];
    if (i<0 || i >= (int)objects.size())
      continue;
    switch (objects[i].iType) {
    case 1: // ELLIPSE
      WriteEllipse(objects[i]);
      break;
    case 2: // POLYLINE
      WritePolyline(objects[i]);
      break;
    case 3: // SPLINE
      WriteSpline(objects[i]);
	break;
    case 4: // TEXT
      WriteText(objects[i]);
      break;
    case 5: // ARC
      WriteArc(objects[i]);
      break;
    case 6: // COMPOUND
      fprintf(iXml, "<group>\n");
      // recursively render elements of the compound
      WriteObjects(objects, i+1, objects[i].iSubtype);
      fprintf(iXml, "</group>\n");
      break;
    }
  }
}

// --------------------------------------------------------------------

void FigWriter::WriteEllipse(const FigObject &obj)
{
    if (obj.iThickness == 0 && obj.iAreaFill==-1 ) {
        fprintf(stderr, "WARNING: ellipse with neither fill nor line ignored.\n");
        return;
    }
    fprintf(iXml, "<path ");
    WriteStroke(obj);
    WriteFill(obj);
    WriteLineStyle(obj);
    fprintf(iXml, ">\n");
    const double ca = cos(obj.iAngle);
    const double sa = sin(obj.iAngle);
    fprintf(iXml, "%g %g %g %g %g %g e\n</path>\n",
            X( obj.iRadius.iX * ca),
            X( obj.iRadius.iX * sa),
            X(-obj.iRadius.iY * sa),
            X( obj.iRadius.iY * ca),
            X( obj.iCenterX),
            Y( obj.iCenterY) );
}

// --------------------------------------------------------------------

namespace {

unsigned int JPEG_read1( std::ifstream& jpeg_in )
{
    unsigned char c;
    jpeg_in.read( reinterpret_cast<char*>(&c), 1 );
    if( jpeg_in.fail() )
        throw std::string( "Failed to read 1 byte." );
    return c;
}

unsigned int JPEG_read2( std::ifstream& jpeg_in )
{
    return (JPEG_read1(jpeg_in) << 8) + JPEG_read1(jpeg_in);
}

typedef enum {
    jpeg_SOF0 = 0xC0,
    jpeg_SOF1 = 0xC1,
    jpeg_SOF2 = 0xC2,
    jpeg_SOF3 = 0xC3,
    jpeg_SOF5 = 0xC5,
    jpeg_SOF6 = 0xC6,
    jpeg_SOF7 = 0xC7,
    jpeg_SOF9 = 0xC9,
    jpeg_SOF10 = 0xCA,
    jpeg_SOF11 = 0xCB,
    jpeg_SOF13 = 0xCD,
    jpeg_SOF14 = 0xCE,
    jpeg_SOF15 = 0xCF,
    jpeg_SOI = 0xD8,
    jpeg_EOI = 0xD9,
    jpeg_SOS = 0xDA,
    jpeg_APP0 = 0xE0,
    jpeg_APP12 = 0xEC,
    jpeg_COM = 0xFE
} JPEG_markers;

int JPEG_next_marker( std::ifstream& jpeg_in )
{
    unsigned int c;
    do {
        c = JPEG_read1(jpeg_in);
    } while( c != 0xFF );
    do {
        c = JPEG_read1(jpeg_in);
    } while( c == 0xFF );
    return c;
}

void JPEG_skip_segment( std::ifstream& jpeg_in )
{
    unsigned int l = JPEG_read2(jpeg_in);
    jpeg_in.seekg( l-2, std::ios::cur );
}

typedef enum { IMAGE_GRAY=0, IMAGE_RGB=1, IMAGE_CMYK=2 } IPE_COLORSPACE;

bool ReadJPEGData( std::ifstream& jpeg_in, int& image_width, int& image_height,
                   int& image_colorspace, int& bitspercomponent )
{
    int required_segments = 0;
    try {
        const unsigned int soi = JPEG_read2(jpeg_in);
        if( (soi & 0xFF) != jpeg_SOI )
            return false;

        while( required_segments != 3 && !jpeg_in.eof() ) {
            const unsigned int marker = JPEG_next_marker(jpeg_in);
            switch( marker ) {
            case jpeg_APP0: {
                unsigned int l = JPEG_read2(jpeg_in);
                const char* JFIF = "JFIF";
                for( int i=0; i<5; ++i )
                    if( JFIF[i] != (int)JPEG_read1(jpeg_in) )
                        return false;
                jpeg_in.seekg( l-5-2, std::ios::cur );

                required_segments |= 1;
                break;
            }
            case jpeg_SOF0: 
            case jpeg_SOF1: 
            case jpeg_SOF2: 
            case jpeg_SOF3: {
                unsigned int l = JPEG_read2(jpeg_in);
                bitspercomponent = JPEG_read1(jpeg_in);
                image_height = JPEG_read2(jpeg_in);
                image_width  = JPEG_read2(jpeg_in);
                unsigned int ncomponents = JPEG_read1(jpeg_in);
                switch( ncomponents ) {
                case 1: image_colorspace = IMAGE_GRAY; break;
                case 3: image_colorspace = IMAGE_RGB;  break;
                case 4: image_colorspace = IMAGE_CMYK; break;
                default:
                    return false;
                }
                if( l != 8 + 3*ncomponents )
                    throw std::string("Unexpected SOFx length.");
                
                required_segments |= 2;
                break;
            }
            default:
                JPEG_skip_segment(jpeg_in);
            }
        }
    } catch( std::string msg ) {
        fprintf(stderr, "Error while reading JPEG: %s.\n", msg.c_str() );
    }
    return required_segments == 3;
}

std::string make_safe_filename( const std::string& filename )
{
    std::ostringstream s_sf;
    s_sf << '\'';
    for( unsigned i=0; i<filename.size(); ++i ) {
        if( filename[i]=='\'' )
            s_sf << "'\"'\"'";
        else
            s_sf << filename[i];
    }
    s_sf << '\'';
    return s_sf.str();
}

} // anonymous namespace

// --------------------------------------------------------------------

void FigWriter::WriteImage(const FigObject &obj)
{
    if( obj.iPoints.size() != 5 ) {
        fprintf(stderr, "WARNING: image with != 5 points. Skipping.\n" );
        return;
    }

    // build filename from directory and image filename
    std::string filename;
    const size_t firstdash = iFigName.find_first_of("\\/");
    const size_t  lastdash = iFigName.find_last_of ("\\/");
    if( firstdash>0 && lastdash != std::string::npos )
        filename = iFigName.substr( 0, lastdash+1 );
    filename += obj.image_filename;

    // try to build safe filename
    const std::string safe_filename = make_safe_filename( filename );

    // image data to be filled by reading procedure
    int image_width=0, image_height=0;
    int image_colorspace = IMAGE_RGB;
    int bitspercomponent = 8;
    std::string image_data, filter;

    std::ifstream jpeg_in( filename.c_str() );
    
    // try reading a JPEG file
    if( ReadJPEGData( jpeg_in, image_width, image_height,
                      image_colorspace, bitspercomponent ) ) {

        // determine file size
        jpeg_in.seekg( 0, std::ios::end );
        const unsigned jpeg_size = jpeg_in.tellg();
        jpeg_in.seekg( 0, std::ios::beg );

        // copy file contents
        image_data.resize( jpeg_size );
        jpeg_in.read( const_cast<char*>(image_data.data()), jpeg_size );

        if( jpeg_in.fail() ) {
            fprintf(stderr, "WARNING: reading jpeg data failed. Skipping image.\n");
            return;
        }

        filter = "DCTDecode";
    } else {
        // other images are read by anytopnm and then compressed

        // build anytopnm command line
        std::string cmd = "anytopnm ";
        cmd += safe_filename;

        // open pipe to read anytopnm output
        FILE* anytopnm = popen( cmd.c_str(), "r" );
        
        // running anytopnm somehow failed
        if( !anytopnm ) {
            fprintf(stderr, "WARNING: anytopnm failed to run. Skipping image.\n");
            return;
        }
        
        try {
            // check image type; should be P4 (pbm), P5 (pgm) or P6 (ppm)
            char type_P, fmt;
            if( fscanf( anytopnm, "%c%c", &type_P, &fmt ) != 2 )
                throw std::string("anytopnm output not understood");
            if( type_P!='P' || ( fmt!='4' && fmt!='5' && fmt!='6' ) )
                throw std::string("anytopnm output not understood");
            
            if( fscanf( anytopnm, "%d %d", &image_width, &image_height ) != 2 )
                throw std::string("anytopnm output not understood (w&h)");
            if( image_width<=0 || image_width>5000 )
                throw std::string("image width out of range [0,5000])");
            if( image_height<=0 || image_height>5000 )
                throw std::string("image height out of range [0,5000])");
            
            if( fmt=='4' ) {
                // bitmap
                throw std::string("bitmap not implemented");
            } else {
                int maxcolor;
                if( fscanf( anytopnm, "%d", &maxcolor ) != 1 )
                    throw std::string("anytopnm output not understood (maxcolor)");
                if( maxcolor<=0 || maxcolor>65535 )
                    throw std::string("anytopnm output not understood (maxcolor)");

                bitspercomponent = 8;
                image_colorspace = (fmt=='5') ? IMAGE_GRAY : IMAGE_RGB;

                // skip single whitespace
                (void)fgetc( anytopnm );
                std::ostringstream idata;
                for( int r=0; r<image_height; ++r ) {
                    for( int c=0; c<image_width; ++c ) {
                        for( int i=0; i<(fmt=='5' ? 1 : 3); ++i ) {
                            int component = fgetc( anytopnm );
                            if( component<0 )
                                throw std::string("anytopnm output: eof");
                            if( maxcolor>=256 ) {
                                int component2 = fgetc( anytopnm );
                                if( component2<0 )
                                    throw std::string("anytopnm output: eof");
                                if( maxcolor == 65535 ) {
                                    component = component2;
                                } else {
                                    component = (component<<8) | component2;
                                    component = int(255.0*component/float(maxcolor));
                                }
                            } else if( maxcolor!=255 ) {
                                component = int(255.0*component/float(maxcolor));
                            }
                            const unsigned char c = (unsigned char)component;
                            idata.write( (const char*)&c, 1 );
                        }
                    }
                }
                image_data = idata.str();
            }
            pclose( anytopnm );
        } catch( std::string msg ) {
            pclose( anytopnm );
            fprintf(stderr, "WARNING: anytopnm problem. Skipping image.\n");
            return;
        }
        
        if( true ) {
            // compress image
            const uLongf zbuf_size = compressBound( image_data.size() );
            uLongf compressed_size = zbuf_size;
            char zbuf[zbuf_size];
            const int ok = compress2( (Bytef*)zbuf, &compressed_size,
                                      (const Bytef*)image_data.data(),
                                      image_data.size(), 9 );
            if( ok == Z_OK ) {
                image_data = std::string(zbuf, zbuf+compressed_size);
                filter = "FlateDecode";
            } else {
                fprintf(stderr, "Failed to compress image (%d)."
                        " Will store uncompressed image.\n", ok );
            }
        }
    }

    if( bitspercomponent != 8 ) {
        fprintf(stderr, "WARNING: Unsupported n.o. bits per component. Skipping image.\n");
        return;
    }

    fprintf(iXml, "<image " );
    if( image_width>0 && image_height>0 )
        fprintf(iXml, "width=\"%d\" height=\"%d\" ", image_width, image_height );

    const char* image_colorspaces[3] = { "DeviceGray", "DeviceRGB", "DeviceCMYK" };
    fprintf(iXml, "ColorSpace=\"%s\" BitsPerComponent=\"8\" ",
            image_colorspaces[image_colorspace] );
    if( !filter.empty() )
         fprintf(iXml, " length=\"%ld\" Filter=\"%s\"", long(image_data.size()), filter.c_str() );

    const double x1 = X(obj.iPoints[0].iX), y1 = Y(obj.iPoints[0].iY);
    const double x2 = X(obj.iPoints[2].iX), y2 = Y(obj.iPoints[2].iY);
    if( obj.image_flipped ) {
        const double r = (x2-x1)/(y2-y1);
        const double tx = (x1+x2)/2, ty = (y1+y2)/2;
        fprintf(iXml, " matrix=\"0 %f %f 0 %f %f\"", 1/r, r, tx-r*ty, ty-tx/r );
    }
    fprintf(iXml, " rect=\"%g %g %g %g\"", x1, y1, x2, y2 );
    
    fprintf(iXml, ">\n" );

    int linebreak=0;
    for( unsigned i=0; i<image_data.size(); ++i ) {
        const char hexchars[] = "0123456789abcdef";
        const unsigned char c = image_data[i];
        fprintf(iXml, "%c%c", hexchars[(c/16)&0xF], hexchars[c&0xF] );
        if( ++linebreak == 36 ) {
            linebreak = 0;
            fputc( '\n', iXml );
        }
    }
    if( linebreak > 0 )
        fputc( '\n', iXml );
    
    fprintf(iXml, "</image>\n");
    return;
}

void FigWriter::WritePolyline(const FigObject &obj)
{
  /* 1: polyline
     2: box
     3: polygon
     4: arc-box
     5: imported-picture bounding-box
  */
  if (obj.iPoints.size() < 2) {
    fprintf(stderr, "WARNING: polyline with less than two vertices ignored.\n");
    return;
  }
  if (obj.iThickness == 0 && obj.iAreaFill==-1 ) {
      fprintf(stderr, "WARNING: polyline with neither fill nor line ignored.\n");
      return;
  }
  if (obj.iSubtype == 4)
    fprintf(stderr, "WARNING: turning arc-box into rectangle.\n");
  if (obj.iSubtype == 5) {
      WriteImage( obj );
      return;
  }
  fprintf(iXml, "<path ");
  WriteStroke(obj);
  WriteFill(obj);
  WriteLineStyle(obj);
  WriteArrows(obj);
  if (obj.iJoinStyle)
    fprintf(iXml, " join=\"%d\"", obj.iJoinStyle);
  if (obj.iCapStyle)
    fprintf(iXml, " cap=\"%d\"", obj.iCapStyle);
  fprintf(iXml, ">\n");
  for (unsigned int i = 0; i < obj.iPoints.size(); ++i) {
    double x = obj.iPoints[i].iX;
    double y = obj.iPoints[i].iY;
    if (i == 0) {
      fprintf(iXml, "%g %g m\n", X(x), Y(y));
    } else if (i == obj.iPoints.size() - 1 && obj.iSubtype > 1) {
      fprintf(iXml, "h\n"); // close path
    } else {
      fprintf(iXml, "%g %g l\n", X(x), Y(y));
    }
  }
  fprintf(iXml, "</path>\n");
}

void FigWriter::WriteSpline(const FigObject &obj)
{
  /* 0: opened approximated spline
     1: closed approximated spline
     2: opened interpolated spline
     3: closed interpolated spline
     4: opened x-spline (FIG 3.2)
     5: closed x-spline (FIG 3.2)
  */
  FigObject obj1 = obj;
  obj1.iJoinStyle = 0;
  obj1.iSubtype = (obj.iSubtype & 1) ? 3 : 1;
  fprintf(stderr, "WARNING: spline replaced by polyline.\n");
  WritePolyline(obj1);
}

void FigWriter::WriteText(const FigObject &obj)
{
  const double tx = X(obj.iPos.iX), ty = Y(obj.iPos.iY);
  fprintf(iXml, "<text size=\"%g\" pos=\"%g %g\"",
	  iMagnification * obj.iFontSize, tx, ty );
  WriteStroke(obj);
  // 0: Left justified; 1: Center justified; 2: Right justified
  if (obj.iSubtype == 1)
    fprintf(iXml, " halign=\"center\"");
  else if (obj.iSubtype == 2)
    fprintf(iXml, " halign=\"right\"");
  if (!(obj.iFontFlags & 1) || obj.iAngle != 0.0) {
    if( ipe7 )
      fprintf(iXml, " transformations=\"affine\"");
    else
      fprintf(iXml, " transformable=\"yes\"");
  }
  if (obj.iAngle != 0.0) {
    double ca = 0, sa = 0;
    if( obj.iAngle == 1.5708 )
      sa = 1;
    else if( obj.iAngle == -1.5708 )
      sa = -1;
    else {
      ca = cos(obj.iAngle);
      sa = sin(obj.iAngle);
    }
    const double mtx = -sa*ty + ca*tx - tx, mty = ca*ty - ty + sa*tx;
    fprintf(iXml, " matrix=\"%f %f %f %f %f %f\"", ca, sa, -sa, ca, -mtx, -mty);
  }
  fprintf(iXml, " type=\"label\">");
  int font = obj.iFont;
  if (obj.iFontFlags & 2) {
    // "special" Latex text
    font = 0; // needs no special treatment
  } else if (obj.iFontFlags & 4) {
    // Postscript font: set font to default
    font = 0;
    fprintf(stderr, "WARNING: postscript font ignored.\n");
  }
  switch (font) {
  case 0: // Default font
    fprintf(iXml, "%s", &obj.iString[0]);
    break;
  case 1: // Roman
    fprintf(iXml, "\\textrm{%s}", &obj.iString[0]);
    break;
  case 2: // Bold
    fprintf(iXml, "\\textbf{%s}", &obj.iString[0]);
    break;
  case 3: // Italic
    fprintf(iXml, "\\emph{%s}", &obj.iString[0]);
    break;
  case 4: // Sans Serif
    fprintf(iXml, "\\textsf{%s}", &obj.iString[0]);
    break;
  case 5: // Typewriter
    fprintf(iXml, "\\texttt{%s}", &obj.iString[0]);
    break;
  }
  fprintf(iXml, "</text>\n");
}

void FigWriter::WriteArc(const FigObject &obj)
{
  if (obj.iThickness == 0 && obj.iAreaFill==-1 ) {
      fprintf(stderr, "WARNING: arc with neither fill nor line ignored.\n");
      return;
  }
  // 0: pie-wedge (closed); 1: open ended arc
  fprintf(iXml, "<path ");
  WriteStroke(obj);
  WriteFill(obj);
  WriteLineStyle(obj);
  fprintf(iXml, ">\n");
  Point beg = (obj.iDirection == 0) ? obj.iArc3 : obj.iArc1;
  Point end = (obj.iDirection == 0) ? obj.iArc1 : obj.iArc3;
  fprintf(iXml, "%g %g m\n", X(beg.iX), Y(beg.iY));
  double dx = obj.iArc1.iX - obj.iCenterX;
  double dy = obj.iArc1.iY - obj.iCenterY;
  double radius = sqrt(dx*dx + dy*dy);
  fprintf(iXml, "%g 0 0 %g %g %g %g %g a\n</path>\n",
	  X(radius), X(radius),
	  X(obj.iCenterX), Y(obj.iCenterY),
	  X(end.iX), Y(end.iY));
}

// --------------------------------------------------------------------

static void print_help_message()
{
  fprintf(stderr, "figtoipe is part of the extensible drawing editor Ipe.\n"
	  "  Copyright (C) 1993-2008 Otfried Cheong <otfried@ipe.airpost.net>\n"
	  "  This is free software with ABSOLUTELY NO WARRANTY.\n"
	  "\n"
	  "Use: figtoipe [-g] [-c] [-p preamble] <figfile> <xmlfile>\n"
	  "  converts a file in FIG format to Ipe's XML format\n"
	  "  -g          -- puts the produced figure into a group\n"
          "  -c          -- use cropbox for size of figure\n"
          "  -6          -- write in ipe 6 format instead of ipe 7 format\n"
	  "  -p preamble -- inserts a preamble (e.g. '\\usepackage{amsmath}')\n"
	  );
  exit(9);
}

// --------------------------------------------------------------------

static bool simple_getopt( const char* option, bool has_arg, const char* &value, int &argc, char** argv )
{
    bool found = false;
    for( int a=1; a<argc; a++ ) {
        if( strcmp( option, argv[a] ) == 0 && (!has_arg || a+1 < argc) ) {
            const int shift = has_arg ? 2 : 1;
            value = has_arg ? argv[a+1] : 0;
            for( int aa=a; aa<argc-shift; aa++ )
                argv[aa] = argv[aa+shift];
            argc -= shift;
            a--;
            found = true;
        }
    }
    return found;
}

// --------------------------------------------------------------------

int main(int argc, char **argv)
{
  bool group = false, cropbox = false;
  std::string preamble = "";
  const char* arg;

  if( simple_getopt("-6", false, arg, argc, argv) )
      ipe7 = false;
  if( simple_getopt("-g", false, arg, argc, argv) )
      group = true;
  if( simple_getopt("-c", false, arg, argc, argv) )
      cropbox = true;
  if( simple_getopt("-p", true, arg, argc, argv) )
      preamble = arg;
  if( argc != 3 )
      print_help_message();

  const char *figname = argv[1];
  const char *xmlname = argv[2];

  FILE *fig = fopen(figname, "r");
  if (!fig) {
    fprintf(stderr,"figtoipe: cannot open '%s'\n", figname);
    exit(-1);
  }

  FigReader fr(fig);
  if (!fr.ReadHeader()) {
    fprintf(stderr, "figtoipe: cannot parse header of '%s'\n", figname);
    exit(-1);
  }

  fprintf(stderr,
	  "Converting at %g FIG units per point, magnification %g.\n",
	  fr.UnitsPerPoint(), fr.Magnification());

  if (!fr.ReadObjects()) {
    fprintf(stderr, "Error reading FIG file.\n");
    exit(9);
  }
  fclose(fig);

  FILE *xml = fopen(xmlname, "w");
  if (!xml) {
    fprintf(stderr, "figtoipe: cannot open '%s'\n", xmlname);
    exit(-1);
  }

  FigWriter fw(xml, figname, fr.Magnification(), fr.UnitsPerPoint(), fr.UserColors());

  if( ipe7 ) {
      fprintf(xml, "<?xml version=\"1.0\"?>\n"
              "<!DOCTYPE ipe SYSTEM \"ipe.dtd\">\n");
  }
  fprintf(xml, "<ipe version=\"%s\" creator=\"%s\">\n",
          ipe7 ? "70000" : "60028",
          FIGTOIPE_VERSION);
  if( ipe7 ) {
      fprintf(xml, "<info/>\n");
  } else {
      fprintf(xml, "<info media=\"%d %d %d %d\"%s/>\n",
              0, 0, MEDIABOX_WIDTH, MEDIABOX_HEIGHT,
              cropbox ? " bbox=\"cropbox\"" : "");
  }

  if( !preamble.empty() )
    fprintf(xml, "<preamble>%s\n</preamble>\n", preamble.c_str());

  if( ipe7 ) {
      fprintf(xml, "<ipestyle name=\"ipe6colors\">\n"
              "<color name=\"red\" value=\"1 0 0\"/>\n"
              "<color name=\"green\" value=\"0 1 0\"/>\n"
              "<color name=\"blue\" value=\"0 0 1\"/>\n"
              "<color name=\"yellow\" value=\"1 1 0\"/>\n"
              "<color name=\"gray1\" value=\"0.125\"/>\n"
              "<color name=\"gray2\" value=\"0.25\"/>\n"
              "<color name=\"gray3\" value=\"0.375\"/>\n"
              "<color name=\"gray4\" value=\"0.5\"/>\n"
              "<color name=\"gray5\" value=\"0.625\"/>\n"
              "<color name=\"gray6\" value=\"0.75\"/>\n"
              "<color name=\"gray7\" value=\"0.875\"/>\n"
              "</ipestyle>\n");

      fprintf(xml, "<ipestyle>\n<layout paper=\"%d %d\" origin=\"0 0\" frame=\"%d %d\"%s/>\n</ipestyle>\n",
              MEDIABOX_WIDTH, MEDIABOX_HEIGHT,
              MEDIABOX_WIDTH, MEDIABOX_HEIGHT,
              cropbox ? "" : " crop=\"no\"");
  }
  fprintf(xml, "<page>\n");

  if( group )
    fprintf(xml, "<group>\n");

  fw.WriteObjects(fr.Objects(), 0, fr.Objects().size());

  if( group )
    fprintf(xml, "</group>\n");

  fprintf(xml, "</page>\n");
  fprintf(xml, "</ipe>\n");

  fclose(xml);
  return 0;
}

// --------------------------------------------------------------------
