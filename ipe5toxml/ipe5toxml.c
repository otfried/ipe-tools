/*
 * ipe5toxml.c
 * 
 * This program converts files in Ipe format (as used by Ipe up to
 * version 5.0) to XML format as used by Ipe 6.0.
 */

#define IPE5TOXML_VERSION "ipe5toxml 2015/04/04"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>

/* Ipe Object Types */

#define IPE_LINE       0
#define IPE_TEXT       1
#define IPE_CIRCLE     2
#define IPE_MARK       3
#define IPE_ARC        4
#define IPE_BITMAP     5
#define IPE_SPLINE     6
#define IPE_BEGINGROUP 7
#define IPE_ENDGROUP   8
#define IPE_SEGMENTS   9

const double SPLINE_MULTI_THRESHOLD_SQUARED = 0.01;

const double IpePi = 3.1415926535897932385;

/* Ipe Color Type
   the empty color has entry -1 for red */

typedef struct _IpeColor {
  double red, green, blue;
} IpeColor;

/* Ipe Font Type */

#define IPE_ROMAN   0
#define IPE_ITALIC  1
#define IPE_BOLD    2
#define IPE_MATH    3

typedef struct { double x, y; } vertex;
typedef struct { double xmin, xmax, ymin, ymax; } bbox;

/* the Environment where the IUM is called */

typedef struct _IpeEnvironment {
  IpeColor stroke, fill;	/* current stroke and fill colors  */
  unsigned short linestyle;     /* solid, dashed etc. as 16 bits   */
  double linewidth;		/* linewidth of stroke             */
  short arrow;			/* two bits for two arrows         */
  double arsize;                 /* size of arrows                  */
  double marksize;               /* size of marks                   */
  double gridsize;               /* grid size                       */
  double snapangle;              /* snap angle                      */
  short marktype;               /* type of mark (1 .. 5)           */
  short font;                   /* font of text object             */
  double fontsize;               /* fontsize                        */
  bool  axisset;                /* is an axis system defined ?     */
  vertex origin;                /* if so, this is the origin       */
  double axisdir;                /*    and this the base direction  */
} IpeEnvironment;

typedef struct _Line {		/* also used for splines	   */
  bool closed;		        /* true if closed curve (polygon)  */
  short arrow;			/* two bits for two arrows         */
  double arsize;                 /* size of arrows                  */
  int n;                        /* number of vertices              */
  vertex *v;                    /* pointer to array of vertices    */
  char *vtype;                  /* pointer to array of vertex type */
                                /* indicators N L E C              */
} Line;

typedef struct _Circle {
  vertex center;                /* center of circle                */
  double radius;                 /* radius of circle                */
  bool  ellipse;                /* is object an ellipse ?          */
  double tfm[4];                 /* tfm values from file            */
} Circle;

typedef struct _Mark {
  vertex pos;                   /* position                        */
  short type;                   /* type of mark (1 .. 5)           */
  double size;                   /* size of mark                    */
} Mark;

typedef struct _Arc {
  short arrow;			/* two bits for two arrows         */
  double arsize;                 /* size of arrows                  */
  vertex center;                /* center of arc                   */
  double radius;                 /* radius of arc                   */
  double begangle, endangle;     /* two angles in radians           */
} Arc;

typedef struct _Text {
  char *str;                    /* the string                      */
  short font;                   /* font                            */
  double fontsize;               /* LaTeX fontsize                  */
  vertex pos;                   /* position of text                */
  bool minipage;                /* true if text is minipage        */
  vertex ll, ur;                /* ll and ur vertex of bounding box*/
} Text;

typedef struct _Bitmap {
  vertex ll, ur;      		/* lower left, upper right corner  */
  short width, height;          /* no of bits in bitmap            */
  unsigned long *words;         /* pointer to width*height pixels  */
  bool in_color;                /* color bitmap ?                  */
} Bitmap;

typedef struct _IpeObject {
  int type;                     /* type of this object             */
  IpeColor stroke, fill;        /* stroke and fill color of object */
  unsigned short linestyle;	/* solid, dashed etc. as 16 bits   */
  double linewidth;		/* linewidth of stroke             */
  struct _IpeObject *next;      /* pointer to next object          */

  union W {
    Line   *line;
    Circle *circle;
    Mark   *mark;
    Text   *text;
    Arc    *arc;
    Bitmap *bitmap;
  } w ;

} IpeObject;

/* the current Ipe environment when IUM is called */

extern IpeEnvironment ipe_environment;

/* input and output for IUM */

extern IpeObject *ium_input;     /* selected objects from Ipe       */
extern IpeObject *ium_output;    /* IUM generated things to Ipe     */

#define MAX_LINE_LENGTH 1024

#define FALSE 0
#define TRUE 1

#ifdef __cplusplus
#define NEWOBJECT(Type) (new Type)
#define NEWARRAY(Type, Size) (new Type[Size])
#define FREEARRAY(Ptr) delete [] Ptr
#else
#define NEWOBJECT(Type) ((Type *) malloc(sizeof(Type)))
#define NEWARRAY(Type, Size) ((Type *) malloc(Size * sizeof(Type)))
#define FREEARRAY(Ptr) free(Ptr)
#endif

#ifdef sun
#define BITS char
#else
#define BITS void
#endif

#define SETXY(v, x, y) v.x = x; v.y = y
#define XCOORD x
#define YCOORD y

/* the current Ipe environment when IUM is called */

IpeEnvironment ipe_environment;

/* IUM input and output */

IpeObject *ium_input;
IpeObject *ium_output;

static char *ipename;
static char *xmlname;
static FILE *fh;
static char linebuf[MAX_LINE_LENGTH];
static int grouplevel = 0;
static int firstpage = 0;
static bool in_settings = TRUE;

/******************** reading ******************************************/

static void assert_n(int n_expected, int n_actual)
{
  if (n_expected != n_actual)  {
    fprintf(stderr, "Fatal error: failed to parse input\n");
    exit(9);
  }
  return;
}

static void assert_fgets(char* s, int size, FILE* stream)
{
  if (fgets(s, size, stream) != s) {
    fprintf(stderr, "Fatal error: failed to read input\n");
    exit(9);
  }
  return;
}

static char *read_next(void)
{
  int ch2, ch1, ch;
  char *p;
  
  /* read words until we find a sole "%" */
  ch2 = ch1 = ch = ' ';
  
  while ((ch = fgetc(fh)) != EOF &&
	 !(ch1 == '%' && isspace(ch2) && isspace(ch))) {
    ch2 = ch1;
    ch1 = ch;
  }

  if (ch == EOF) {
    /* read error (could be EOF, then it's a format error) */
    fprintf(stderr, "Error reading IPE file %s\n", ipename);
    exit(9);
  }

  /* next word is keyword */
  
  p = linebuf;
  while ((*p = fgetc(fh)), *p != EOF && (p < (linebuf + sizeof(linebuf) -1)) && !isspace(*p))
    p++;
  *p = '\0';

  /* fprintf(stderr, " %s ", linebuf);*/
  return linebuf;
}

/* temporary storage for read_env and read_entry */

static struct {
  bool closed;
  vertex xy;
  bool minipage;
  double wd, ht, dp;
  double radius;
  double begangle, endangle;
  char *str;
  int n;
  vertex *v;
  char *vtype;
  bool ellipse;
  double tfm[4];
  unsigned long *words;
  int xbits, ybits;
  bool bmcolor;
} rd;

static void read_env(IpeEnvironment *ienv)
{
  char *wk;
  double x, y;
  int i;
  
  ienv->stroke.red = ienv->stroke.green = ienv->stroke.blue = -1;
  ienv->fill.red = ienv->fill.green = ienv->fill.blue = -1;
  ienv->linestyle = 0;
  ienv->linewidth = 0.4;
  ienv->arrow = 0;
  ienv->axisset = FALSE;
  rd.closed = FALSE;
  /* init transformation to identity */
  rd.tfm[0] = rd.tfm[3] = 1.0;
  rd.tfm[1] = rd.tfm[2] = 0.0;
  rd.minipage = FALSE;
  rd.ellipse = FALSE;
  rd.str = NULL;
  rd.v = NULL;
  rd.vtype = NULL;
  
  while (TRUE) {
    wk = read_next();
    if (!strcmp(wk, "sk")) {
      assert_n(1, fscanf(fh, "%lf", &ienv->stroke.red));
      ienv->stroke.blue = ienv->stroke.green = ienv->stroke.red;
    } else if (!strcmp(wk, "fi")) {
      assert_n(1, fscanf(fh, "%lf", &ienv->fill.red));
      ienv->fill.blue = ienv->fill.green = ienv->fill.red;
    } else if (!strcmp(wk, "skc")) {
      assert_n(3, fscanf(fh, "%lf%lf%lf",
              &ienv->stroke.red, &ienv->stroke.green, &ienv->stroke.blue));
    } else if (!strcmp(wk, "fic")) {
      assert_n(3, fscanf(fh, "%lf%lf%lf",
              &ienv->fill.red, &ienv->fill.green, &ienv->fill.blue));
    } else if (!strcmp(wk, "ss")) {
      assert_n(2, fscanf(fh, "%hu%lf", &ienv->linestyle, &ienv->linewidth));
    } else if (!strcmp(wk, "ar")) {
      assert_n(2, fscanf(fh, "%hu%lf", &ienv->arrow, &ienv->arsize));
    } else if (!strcmp(wk, "cl")) {
      rd.closed = TRUE;
    } else if (!strcmp(wk, "f")) {
      assert_n(2, fscanf(fh, "%hu%lf", &ienv->font, &ienv->fontsize));
    } else if (!strcmp(wk, "grid")) {
      assert_n(2, fscanf(fh, "%lf%lf", &ienv->gridsize, &ienv->snapangle));
    } else if (!strcmp(wk, "ty")) {
      assert_n(1, fscanf(fh, "%hu", &ienv->marktype));
    } else if (!strcmp(wk, "sz")) {
      assert_n(1, fscanf(fh, "%lf",  &ienv->marksize));
    } else if (!strcmp(wk, "xy")) {
      assert_n(2, fscanf(fh, "%lf%lf", &x, &y));
      SETXY(rd.xy, x, y);
    } else if (!strcmp(wk, "px")) {
      assert_n(2, fscanf(fh, "%d%d", &rd.xbits, &rd.ybits));
    } else if (!strcmp(wk, "bb")) {
      rd.minipage = TRUE;
      assert_n(2, fscanf(fh, "%lf%lf", &rd.wd, &rd.ht));
      rd.dp = rd.ht;
    } else if (!strcmp(wk, "tbb")) {
      rd.minipage = FALSE;
      assert_n(2, fscanf(fh, "%lf%lf%lf", &rd.wd, &rd.ht, &rd.dp));
    } else if (!strcmp(wk, "ang")) {
      assert_n(2, fscanf(fh, "%lf%lf", &rd.begangle, &rd.endangle));
    } else if (!strcmp(wk, "r")) {
      assert_n(1, fscanf(fh, "%lf", &rd.radius));
    } else if (!strcmp(wk, "tfm")) {
      rd.ellipse = TRUE;
      assert_n(4, fscanf(fh, "%lf%lf%lf%lf", &rd.tfm[0], &rd.tfm[1], &rd.tfm[2], &rd.tfm[3]));
    } else if (!strcmp(wk, "axis")) {
      ienv->axisset = TRUE;
      assert_n(3, fscanf(fh, "%lf%lf%lf", &x, &y, &ienv->axisdir));
      SETXY(ienv->origin, x, y);
    } else if (!strcmp(wk, "#")) {
      /* vertices of a polyline */
      int ch;
      assert_n(1, fscanf(fh, "%d", &rd.n));
      rd.v = NEWARRAY(vertex, rd.n);
      rd.vtype = NEWARRAY(char, rd.n);
      for (i = 0; i < rd.n; i++ ) {
	assert_n(2, fscanf(fh, "%lf%lf", &x, &y));
	SETXY(rd.v[i], x, y);
	/* find character */
	do {
	  ch = fgetc(fh);
	} while (ch != EOF && isspace(ch) && ch != '\n');
	if (ch == '\n') {
	  rd.vtype[i] = ' ';
	} else {
	  rd.vtype[i] = (char) (ch & 0xff);
	  /* skip to next line */
	  while ((ch = fgetc(fh)) != EOF && ch != '\n')
	    ;
	}
      }
    } else if (!strcmp(wk, "s")) {
      /* get string */
      assert_fgets(linebuf, MAX_LINE_LENGTH, fh);
      linebuf[strlen(linebuf) - 1] = '\0';
      if (!rd.str) {
	/* first string */
	rd.str = strdup(linebuf);
      } else {
	char *ns = NEWARRAY(char, (strlen(rd.str) + strlen(linebuf) + 2));
	strcpy(ns, rd.str);
	strcat(ns, "\n");
	strcat(ns, linebuf);
	free(rd.str);
	rd.str = ns;
      }
    } else if (!strcmp(wk, "bits")) {
      /* get bitmap */
      unsigned long nwords;
      long i, incolor, nchars;
      int ch, mode;
      char *p, *strbits, buf[3];
      short red, green, blue;
      
      assert_n(2, fscanf(fh, "%ld%d", &nwords, &mode));
      incolor = mode & 1;
      if (mode & 0x8) {
	/* read RAW bitmap */
	do {
	  if ((ch = fgetc(fh)) == EOF) {
	    fprintf(stderr, "EOF while reading RAW bitmap\n");
	    exit(9);
	  }
	} while (ch != '\n');
	rd.bmcolor = incolor ? TRUE : FALSE;
	rd.words = NEWARRAY(unsigned long, nwords);
	if (mode & 0x01) {
	  /* color bitmap: 32 bits per pixel */
	  if (fread((BITS *) rd.words, sizeof(unsigned long),
		    ((unsigned int) nwords), fh)
	      != nwords) {
	    fprintf(stderr, "Error reading RAW bitmap\n");
	    exit(9);
	  }
	} else {
	  /* gray bitmap: 8 bits per pixel */
	  register char *inp, *end;
	  register unsigned long *out;
	  char *pix = NEWARRAY(char, nwords);
	  if (fread((BITS *) pix, sizeof(char), ((unsigned int) nwords), fh)
	      != nwords) {
	    fprintf(stderr, "Error reading RAW bitmap\n");
	    exit(9);
	  }
	  /* convert to unsigned longs */
	  inp = pix;
	  end = pix + nwords;
	  out = rd.words;
	  while (inp < end) {
	    *out++ = (*inp << 16) | (*inp << 8) | (*inp);
	    inp++;
	  }
	  FREEARRAY(pix);
	}	  
      } else {
	/* read Postscript style bitmap */
	nchars = (incolor ? 6 : 2) * nwords;
	p = strbits = NEWARRAY(char, nchars);
	for (i = 0; i < nchars; i++) {
	  do {
	    if ((ch = fgetc(fh)) == EOF) {
	      fprintf(stderr, "EOF while reading bitmap\n");
	      exit(9);
	    }
	  } while (!(('0' <= ch && ch <= '9') || ('a' <= ch && ch <= 'f')));
	  *p++ = ch;
	}
	p = strbits;
	rd.words = NEWARRAY(unsigned long, nwords);
	rd.bmcolor = incolor ? TRUE : FALSE;
	buf[2] = '\0';
	for (i = 0; i < ((int) nwords); ) {
	  buf[0] = *p++;
	  buf[1] = *p++;
	  red = ((short) strtol(buf, NULL, 16));
	  if (incolor) {
	    buf[0] = *p++;
	    buf[1] = *p++;
	    green = ((short) strtol(buf, NULL, 16));
	    buf[0] = *p++;
	    buf[1] = *p++;
	    blue = ((short) strtol(buf, NULL, 16));
	    rd.words[i++] = (blue * 0x10000) | (green * 0x100) | red;
	  } else {
	    rd.words[i++] = (red * 0x10000) | (red * 0x100) | red;
	  }
	}
	free(strbits);
      }
    } else if (!strcmp(wk, "End")) {
      return;
    } else {
      if (in_settings) {
	/* unknown keyword in settings: ignore this line */
	assert_fgets(linebuf, MAX_LINE_LENGTH, fh);
      } else {
	/* unknown keyword in an object: this is serious */
	fprintf(stderr, "Illegal keyword %s in IPE file %s\n",
		wk, ipename);
	exit(9);
      }
    }
  }
}

static void addtobox(bbox *bb, double x, double y)
{
  if (x < bb->xmin)
    bb->xmin = x;
  if (x > bb->xmax)
    bb->xmax = x;
  if (y < bb->ymin)
    bb->ymin = y;
  if (y > bb->ymax)
    bb->ymax = y;
}

static IpeObject *read_entry(bbox *bb)
{
  char *wk;
  int i;
  IpeObject *iobj;
  IpeEnvironment ienv;

  iobj = NEWOBJECT(IpeObject);
  
  iobj->next = NULL;

  wk = read_next();
  
  if (!strcmp(wk, "Group")) {
    iobj->type = IPE_BEGINGROUP;
    grouplevel++;
    return iobj;
  } else if (!strcmp(wk, "End")) {
    iobj->type = IPE_ENDGROUP;
    grouplevel--;
    return ((grouplevel >= 0) ? iobj : NULL);
  } else if (!strcmp(wk, "Line")) {
    iobj->type = IPE_LINE;
  } else if (!strcmp(wk, "Segments")) {
    iobj->type = IPE_SEGMENTS;
  } else if (!strcmp(wk, "Spline")) {
    iobj->type = IPE_SPLINE;
  } else if (!strcmp(wk, "Text")) {
    iobj->type = IPE_TEXT;
  } else if (!strcmp(wk, "Circle")) {
    iobj->type = IPE_CIRCLE;
  } else if (!strcmp(wk, "Arc")) {
    iobj->type = IPE_ARC;
  } else if (!strcmp(wk, "Mark")) {
    iobj->type = IPE_MARK;
  } else if (!strcmp(wk, "Bitmap")) {
    iobj->type = IPE_BITMAP;
  } else {
    fprintf(stderr, "Illegal keyword %s in IPE file %s\n",
	    wk, ipename);
    exit(9);
  }

  /* read header, now read data */
  read_env(&ienv);

  /* read data, now fill in object */
  iobj->stroke = ienv.stroke;
  iobj->fill = ienv.fill;
  iobj->linestyle = ienv.linestyle;
  iobj->linewidth = ienv.linewidth;
  
  switch (iobj->type) {
    /* we treat polylines and splines alike */
  case IPE_LINE:
  case IPE_SEGMENTS:
  case IPE_SPLINE:
    iobj->w.line = NEWOBJECT(Line);
    iobj->w.line->closed = rd.closed;
    iobj->w.line->arrow = ienv.arrow;
    iobj->w.line->arsize = ienv.arsize;
    iobj->w.line->n = rd.n;
    iobj->w.line->v = rd.v;
    {
      int k;
      for (k = 0; k < rd.n; k++)
	addtobox(bb, rd.v[k].x, rd.v[k].y);
    }
    iobj->w.line->vtype = rd.vtype;
    if (iobj->type == IPE_SEGMENTS) {
      /* check keys */
      int i;
      for (i = 0; i < rd.n; i++) {
	switch (rd.vtype[i]) {
	case 'N': case 'E': case 'L': case 'C':
	  /* good */
	  break;
	default:
	  fprintf(stderr, "Illegal code '%c' in Segments object\n", 
		  rd.vtype[i]);
	  exit(9);
	}
      }
    }
    break;

  case IPE_ARC:
    iobj->w.arc = NEWOBJECT(Arc);
    iobj->w.arc->arrow = ienv.arrow;
    iobj->w.arc->arsize = ienv.arsize;
    iobj->w.arc->center = rd.xy;
    iobj->w.arc->radius = rd.radius;
    iobj->w.arc->begangle = rd.begangle;
    iobj->w.arc->endangle = rd.endangle;
    /* ignore in bbox computation */
    break;

  case IPE_CIRCLE:
    iobj->w.circle = NEWOBJECT(Circle);
    iobj->w.circle->center = rd.xy;
    iobj->w.circle->radius = rd.radius;
    iobj->w.circle->ellipse = rd.ellipse;
    for (i = 0; i < 4; i++) {
      iobj->w.circle->tfm[i] = rd.tfm[i];
    }
    /* just use bounding box of circle, ignoring tfm */
    addtobox(bb, rd.xy.x - rd.radius, rd.xy.y - rd.radius);
    addtobox(bb, rd.xy.x + rd.radius, rd.xy.y + rd.radius);
    break;
    
  case IPE_MARK:
    iobj->w.mark = NEWOBJECT(Mark);
    iobj->w.mark->pos = rd.xy;
    iobj->w.mark->type = ienv.marktype;
    iobj->w.mark->size = ienv.marksize;
    addtobox(bb, rd.xy.x, rd.xy.y);
    break;

  case IPE_BITMAP:
    iobj->w.bitmap = NEWOBJECT(Bitmap);
    iobj->w.bitmap->ll = rd.xy;
    iobj->w.bitmap->width = rd.xbits;
    iobj->w.bitmap->height = rd.ybits;
    iobj->w.bitmap->words = rd.words;
    iobj->w.bitmap->in_color = rd.bmcolor;
    iobj->w.bitmap->ur.x = rd.xy.x + rd.wd;
    iobj->w.bitmap->ur.y = rd.xy.y + rd.ht;
    addtobox(bb, rd.xy.x, rd.xy.y);
    addtobox(bb, rd.xy.x + rd.wd, rd.xy.y + rd.ht);
    break;
    
  case IPE_TEXT:
    iobj->w.text = NEWOBJECT(Text);
    iobj->w.text->pos = rd.xy;
    iobj->w.text->font = ienv.font;
    iobj->w.text->fontsize = ienv.fontsize;
    iobj->w.text->minipage = rd.minipage;
    iobj->w.text->ll = rd.xy;
    iobj->w.text->ll.y -= rd.dp;
    iobj->w.text->ur = iobj->w.text->ll;
    iobj->w.text->ur.x += rd.wd;
    iobj->w.text->ur.y += rd.ht;
    iobj->w.text->str = rd.str;
    addtobox(bb, rd.xy.x, rd.xy.y - rd.dp);
    addtobox(bb, rd.xy.x + rd.wd, rd.xy.y + rd.ht - rd.dp);
    break;
  }

  /* now set all values in IpeObject, return it */
  return iobj;
}

/******************** writing ******************************************/

static void write_color(IpeColor *color)
{
  if (color->red == color->green && color->red == color->blue) {
    if (color->red == 0.0)
      fprintf(fh, "black");
    else if (color->red == 1.0)
      fprintf(fh, "white");
    else 
      fprintf(fh, "%g", color->red);
  } else if (color->red == 1.0 && color->green == 0.0 && color->blue == 0.0)
    fprintf(fh, "red");
  else if (color->red == 0.0 && color->green == 1.0 && color->blue == 0.0)
    fprintf(fh, "green");
  else if (color->red == 0.0 && color->green == 0.0 && color->blue == 1.0)
    fprintf(fh, "blue");
  else 
    fprintf(fh, "%g %g %g", color->red, color->green, color->blue);
}

static void write_colors(IpeObject *iobj)
{
  if (iobj->stroke.red != -1) {
    fprintf(fh, " stroke=\"");
    write_color(&iobj->stroke);
    fprintf(fh, "\"");
  }
  if (iobj->fill.red != -1) {
    fprintf(fh, " fill=\"");
    write_color(&iobj->fill);
    fprintf(fh, "\"");
  }
}

static void write_dashes(short dash)
{
  static int p[32];
  int len = 0;
  unsigned int onoff = 1;
  unsigned int rot = dash;
  int count = 0;
  int good;
  int i;
  int k = 0;

  if (!(rot & 0x0001))
    rot = 0xffff ^ rot;
  for (i = 0; i < 16; i++) {
    if (onoff != (rot & 1)) {
      p[len++] = count;
      count = 0;
      onoff = 1 - onoff;
    }
    rot >>= 1;
    count++;
  }
  p[len++] = count;
  if (onoff)
    p[len++] = 0;
  for (i = 0; i < len; i++)
    p[i+len] = p[i];
  // now determine period
  do {
    k++;
    good = TRUE;
    for (i = 0; i < len; i++)
      if (p[i] != p[i+k]) {
	good = FALSE;
      }
  } while (!good);
  // k is period of what we want
  fprintf(fh, "[%d", p[0]);
  for (i = 1; i < k; i++)
    fprintf(fh, " %d", p[i]);
  fprintf(fh, "] 0");
}

static void write_linestyle(IpeObject *iobj)
{
  if (iobj->stroke.red == -1) {
    fprintf(fh, " dash=\"void\"");
  } else if (iobj->linestyle != 0 && iobj->linestyle != 0xffff) {
    fprintf(fh, " dash=\"");
    write_dashes(iobj->linestyle);
    fprintf(fh, "\"");
  }
  fprintf(fh, " pen=\"%g\"", iobj->linewidth);
}

static int cmp_spl_vtx(vertex *v0, vertex *v1) 
{
  double dx = v1->x - v0->x;
  double dy = v1->y - v0->y;
  return (dx*dx + dy*dy < SPLINE_MULTI_THRESHOLD_SQUARED);
}

static void midpoint(vertex *res, vertex *u, vertex *v)
{
  res->x = 0.5 * (u->x + v->x);
  res->y = 0.5 * (u->y + v->y);
}

static void thirdpoint(vertex *res, vertex *u, vertex *v)
{
  res->x = (1.0/3.0) * ((2 * u->x) + v->x);
  res->y = (1.0/3.0) * ((2 * u->y) + v->y);
}

static void convert_spline_to_bezier(FILE *fh, int n, vertex *v)
{
  int i;
  vertex q0, q1, q2, q3;
  vertex u, w;

  for (i = 0; i < n - 3; i++ ) {
    thirdpoint(&q1, &v[i+1], &v[i+2]);
    thirdpoint(&q2, &v[i+2], &v[i+1]);
    thirdpoint(&u, &v[i+1], &v[i]);
    midpoint(&q0, &u, &q1);
    thirdpoint(&w, &v[i+2], &v[i+3]);
    midpoint(&q3, &w, &q2);
    if (i == 0)
      fprintf(fh, "\n%g %g m\n", q0.x, q0.y);
    fprintf(fh, "%g %g %g %g %g %g c\n", q1.x, q1.y, q2.x, q2.y, q3.x, q3.y);
  }
}

static void write_entry(IpeObject *iobj)
/*  write a single Ipe Object to output file */
{
  int i;
  char *p;
  
  switch (iobj->type) {
  case IPE_BEGINGROUP:
    if (grouplevel > 0)
      fprintf(fh, "<group>\n");
    else {
      if (firstpage) {
	fprintf(fh, "<ipestyle>\n<template name=\"Background\">\n<group>\n");
      } else {
	fprintf(fh, "<page>\n");
      }
    }
    grouplevel++;
    return;
  case IPE_ENDGROUP:
    grouplevel--;
    if (grouplevel > 0)
      fprintf(fh, "</group>\n");
    else { 
      if (firstpage) {
	fprintf(fh, "</group>\n</template>\n</ipestyle>\n");
	firstpage = 0;
      } else {
	fprintf(fh, "</page>\n");
      }
    }
    break;

  case IPE_SPLINE:
    fprintf(fh, "<path");
    write_colors(iobj);
    write_linestyle(iobj);
    if (iobj->w.line->arrow & 2)
      fprintf(fh, " arrow=\"%g\"", iobj->w.line->arsize);
    if (iobj->w.line->arrow & 1)
      fprintf(fh, " backarrow=\"%g\"", iobj->w.line->arsize);
    fprintf(fh, ">");
    if (iobj->w.line->n == 2) {
      /* line segment */
      fprintf(fh, "\n%g %g m\n", iobj->w.line->v[0].x, iobj->w.line->v[0].y);
      fprintf(fh, "%g %g l\n", iobj->w.line->v[1].x, iobj->w.line->v[1].y);
    } else if (iobj->w.line->n == 3) {
      /* quadratic B-spline */
      if (iobj->w.line->closed) {
	/* closed quadratic B-spline */
	int i;
	for (i = 0; i < 3; ++i) {
	  vertex q0, q2;
	  midpoint(&q0, &iobj->w.line->v[i], &iobj->w.line->v[(i+1) % 3]);
	  midpoint(&q2, &iobj->w.line->v[(i+1) % 3], 
		   &iobj->w.line->v[(i+2) % 3]);
	  if (i == 0)
	    fprintf(fh, "\n%g %g m", q0.x, q0.y);
	  fprintf(fh, "\n%g %g ", iobj->w.line->v[(i+1) % 3].x, 
		  iobj->w.line->v[(i+1) % 3].y);
	  fprintf(fh, "%g %g q", q2.x, q2.y);
	}
	fprintf(fh, " h\n");
      } else {
	/* open quadratic B-spline */
	vertex q0, q2;
	midpoint(&q0, &iobj->w.line->v[0], &iobj->w.line->v[1]);
	midpoint(&q2, &iobj->w.line->v[1], &iobj->w.line->v[2]);
	fprintf(fh, "\n%g %g m\n", q0.x, q0.y);
	fprintf(fh, "%g %g ", iobj->w.line->v[1].x, iobj->w.line->v[1].y);
	fprintf(fh, "%g %g q\n", q2.x, q2.y);
      }
    } else if (iobj->w.line->closed) {
      /* Closed cubic B-spline */
      for (i = 0; i < iobj->w.line->n; i++ )
	fprintf(fh, "\n%g %g", iobj->w.line->v[i].x, iobj->w.line->v[i].y);
      fprintf(fh, " u\n");
    } else {
      /* Check whether first and last point have multiplicity 3 */
      int n = iobj->w.line->n;
      if (n >= 8 && 
	  cmp_spl_vtx(&iobj->w.line->v[0], &iobj->w.line->v[1]) &&
	  cmp_spl_vtx(&iobj->w.line->v[0], &iobj->w.line->v[2]) &&
	  cmp_spl_vtx(&iobj->w.line->v[n-1], &iobj->w.line->v[n-2]) &&
	  cmp_spl_vtx(&iobj->w.line->v[n-1], &iobj->w.line->v[n-3])) {
	/* Yes, can convert to Ipe 6 B-Spline object */
	fprintf(fh, "\n%g %g m", iobj->w.line->v[2].x, iobj->w.line->v[2].y);
	for (i = 3; i < iobj->w.line->n - 2; i++ )
	  fprintf(fh, "\n%g %g", iobj->w.line->v[i].x, iobj->w.line->v[i].y);
	fprintf(fh, " s\n");
      } else {
	/* Have to convert to Ipe 6 Bezier path */
	convert_spline_to_bezier(fh, n, iobj->w.line->v);
      }
    }
    fprintf(fh, "</path>\n");
    break;

  case IPE_LINE:
  case IPE_SEGMENTS:
    fprintf(fh, "<path");
    write_colors(iobj);
    write_linestyle(iobj);
    if (iobj->w.line->arrow & 2)
      fprintf(fh, " arrow=\"%g\"", iobj->w.line->arsize);
    if (iobj->w.line->arrow & 1)
      fprintf(fh, " backarrow=\"%g\"", iobj->w.line->arsize);
    fprintf(fh, ">\n");
    for (i = 0; i < iobj->w.line->n; i++ ) {
      fprintf(fh, "%g %g ", (iobj->w.line->v[i].x), (iobj->w.line->v[i].y) );
      if (iobj->type == IPE_SEGMENTS) {
	switch (iobj->w.line->vtype[i]) {
	case 'N':
	  fprintf(fh, "m\n");
	  break;
	case 'L':
	case 'E':
	  fprintf(fh, "l\n");
	  break;
	case 'C':
	  fprintf(fh, "l h\n");
	  break;
	}
      } else {
	if (i == 0) {
	  fprintf(fh, "m\n");
	} else if (i + 1 == iobj->w.line->n) {
	  if (iobj->w.line->closed)
	    fprintf(fh, "l h\n");
	  else 
	    fprintf(fh, "l\n");
	} else {
	  fprintf(fh, "l\n");
	}
      }
    }
    fprintf(fh, "</path>\n");
    break;

  case IPE_MARK:
    fprintf(fh, "<mark");
    iobj->fill.red = -1;
    write_colors(iobj);
    fprintf(fh, " pos=\"%g %g\"",
	    (iobj->w.mark->pos.XCOORD), (iobj->w.mark->pos.YCOORD));
    fprintf(fh, " shape=\"%d\"", iobj->w.mark->type);
    fprintf(fh, " size=\"%g\"/>\n", (iobj->w.mark->size));
    break;
   
  case IPE_CIRCLE:
    fprintf(fh, "<path");
    write_colors(iobj);
    write_linestyle(iobj);
    fprintf(fh, ">\n");
    if (iobj->w.circle->ellipse) {
      double r = (iobj->w.circle->radius);
      fprintf(fh, "%g %g %g %g %g %g e\n",
	      r * iobj->w.circle->tfm[0], r * iobj->w.circle->tfm[1],
	      r * iobj->w.circle->tfm[2], r * iobj->w.circle->tfm[3],
	      (iobj->w.circle->center.XCOORD),
	      (iobj->w.circle->center.YCOORD));
    } else {
      fprintf(fh, "%g 0 0 %g %g %g e\n",
	      (iobj->w.circle->radius),
	      (iobj->w.circle->radius),
	      (iobj->w.circle->center.XCOORD),
	      (iobj->w.circle->center.YCOORD));
    }
    fprintf(fh, "</path>\n");
    break;
    
  case IPE_ARC:
    // ignore zero radius arcs
    if (iobj->w.arc->radius != 0.0) {
      fprintf(fh, "<path");
      write_colors(iobj);
      write_linestyle(iobj);
      if (iobj->w.arc->arrow & 2)
	fprintf(fh, " arrow=\"%g\"", (iobj->w.arc->arsize));
      if (iobj->w.arc->arrow & 1)
	fprintf(fh, " backarrow=\"%g\"", (iobj->w.arc->arsize));
      fprintf(fh, ">\n");
      {
	double alpha = (iobj->w.arc->begangle * IpePi / 180.0 );
	double beta = (iobj->w.arc->endangle * IpePi / 180.0 );
	double radius = iobj->w.arc->radius;
	double x = (iobj->w.arc->center.x);
	double y = (iobj->w.arc->center.y);
	while (beta <= alpha)
	  beta += IpePi + IpePi;
	fprintf(fh, "%g %g m\n", x + radius * cos(alpha), 
		y + radius * sin(alpha));
	fprintf(fh, "%g 0 0 %g %g %g ", radius, radius, x, y);
	fprintf(fh, "%g %g a\n", x + radius * cos(beta), 
		y + radius * sin(beta));
	
      }
      fprintf(fh, "</path>\n");
    }
    break;

  case IPE_TEXT:
    fprintf(fh, "<text");
    iobj->fill.red = -1;
    write_colors(iobj);
    fprintf(fh, " pos=\"%g %g\"",
	    (iobj->w.text->pos.XCOORD), (iobj->w.text->pos.YCOORD));
    fprintf(fh, " size=\"%.2g\"", iobj->w.text->fontsize);
    if (iobj->w.text->minipage) {
      fprintf(fh, " type=\"minipage\" valign=\"top\" width=\"%g\"",
	      (iobj->w.text->ur.XCOORD - iobj->w.text->ll.XCOORD));
    } else {
      fprintf(fh, " type=\"label\" valign=\"bottom\"");
    }
    fprintf(fh, ">");
    switch (iobj->w.text->font) {
    case IPE_ROMAN:
    default:
      break;
    case IPE_ITALIC:
      fprintf(fh, "\\textit{");
      break;
    case IPE_BOLD:
      fprintf(fh, "\\textbf{");
      break;
    case IPE_MATH:
      fprintf(fh, "$");
      break;
    }
    for (p = iobj->w.text->str; *p; p++) {
      switch (*p) {
      case '<':
	fprintf(fh, "&lt;");
	break;
      case '>':
	fprintf(fh, "&gt;");
	break;
      case '&':
	fprintf(fh, "&amp;");
	break;
      case '\r': /* skip CR */ 
	break;
      default:
	fputc(*p, fh);
	break;
      }
    }
    switch (iobj->w.text->font) {
    case IPE_ROMAN:
    default:
      break;
    case IPE_ITALIC:
    case IPE_BOLD:
      fprintf(fh, "}");
      break;
    case IPE_MATH:
      fprintf(fh, "$");
      break;
    }
    fprintf(fh, "</text>\n");
    break;

  case IPE_BITMAP:
    fprintf(fh, "<image");
    fprintf(fh, " rect=\"%g %g %g %g\"",
	    iobj->w.bitmap->ll.XCOORD, iobj->w.bitmap->ll.YCOORD,
	    iobj->w.bitmap->ur.XCOORD, iobj->w.bitmap->ur.YCOORD); 
    fprintf(fh, " width=\"%d\" height=\"%d\"",
	    iobj->w.bitmap->width, iobj->w.bitmap->height);
    if (iobj->w.bitmap->in_color)
      fprintf(fh, " ColorSpace=\"DeviceRGB\"");
    else 
      fprintf(fh, " ColorSpace=\"DeviceGray\"");
    fprintf(fh, " BitsPerComponent=\"8\">\n");
    /* write bitmap in hex */
    if (iobj->w.bitmap->in_color) {
      int nwords = iobj->w.bitmap->width * iobj->w.bitmap->height;
      int i;
      /* write a color bitmap: 32 bits per pixel */
      for (i = 0; i < nwords; ++i) {
	int val = iobj->w.bitmap->words[i] & 0x00ffffff;
	fprintf(fh, "%06x", val);
      }
    } else {
      int nwords = iobj->w.bitmap->width * iobj->w.bitmap->height;
      int i;
      /* write a color bitmap: 32 bits per pixel */
      for (i = 0; i < nwords; ++i) {
	int val = iobj->w.bitmap->words[i] & 0x000000ff;
	fprintf(fh, "%02x", val );
      }
    }
    fprintf(fh, "\n</image>\n");
    break;
    
  default:
    /* this should never happen */
    fprintf(stderr, "Fatal error: trying to write unknown type %d\n",
	    iobj->type);
    exit(1);
  }
  return;
}

static void ipetoxml(void)
{
  IpeObject *last, *iobj;
  char *wk;
  char preamble[MAX_LINE_LENGTH];
  char pspreamble[MAX_LINE_LENGTH];
  int no_pages = 0;
  bbox bb = { 99999.0, -99999.0, 99999.0, -99999.0 };

  ium_input = NULL;

  /* read IPE file */

  if (!(fh = fopen(ipename, "rb"))) {
    fprintf(stderr, "Cannot open IPE file %s\n", ipename);
    exit(9);
  }
  
  grouplevel = 0;
  preamble[0] = '\0';
  pspreamble[0] = '\0';
  
  wk = read_next();
  if (!strcmp(wk, "Preamble")) {
    int nlines;
    int ch;
    char *p = preamble;
    assert_n(1, fscanf(fh, "%d", &nlines));
    /* skip to next line */
    while ((ch = fgetc(fh)) != '\n' && ch != EOF)
      ;
    while (nlines > 0 && ch != EOF && (p < (preamble + sizeof(preamble) - 1))) {
      ch = fgetc(fh);
      if (ch == EOF) {
        fprintf(stderr, "EOF while reading preamble\n");
        exit(9);
      }
      if (ch != '%')
	*p++ = ch;
      if (ch == '\n')
	nlines--;
    }
    *p = '\0';
    wk = read_next();
  }

  if (!strcmp(wk, "PSpreamble")) {
    int nlines;
    int ch;
    char *p = pspreamble;
    assert_n(1, fscanf(fh, "%d", &nlines));
    /* skip to next line */
    while ((ch = fgetc(fh)) != '\n' && ch != EOF)
      ;
    while (nlines > 0 && ch != EOF && (p < (pspreamble + sizeof(pspreamble) -1 ))) {
      ch = fgetc(fh);
      if (ch == EOF) {
        fprintf(stderr, "EOF while reading PSpreamble\n");
        exit(9);
      }
      *p++ = ch;
      if (ch == '\n')
	nlines--;
    }
    *p = '\0';
    wk = read_next();
  }

  if (!strcmp(wk, "Pages")) {
    assert_n(1, fscanf(fh, "%d", &no_pages));
  } else if (strcmp(wk, "Group")) {
    fprintf(stderr, "Not an IPE file: %s\n", ipename);
    exit(9);
  }
  
  last = NULL;
  while ((iobj = read_entry(&bb)) != NULL) {
    if (last)
      last->next = iobj;
    else
      ium_input = iobj;
    last = iobj;
  }
  fclose(fh);

  /* testing only? */
  if (xmlname == 0)
    return;

  /* write file in XML format */

  if (!(fh = fopen(xmlname, "wb"))) {
    fprintf(stderr, "Cannot open XML file %s for writing\n", xmlname);
    exit(9);
  }

  fprintf(fh, "<ipe creator=\"%s\">\n", IPE5TOXML_VERSION);
  {
    char *p = preamble;
    while (*p && *p != '}')
      p++;
    if (*p)
      p++;
    while (*p && (*p == ' ' || *p == '\n' || *p == '\r'))
      p++;
    if (*p) {
      fprintf(fh, "<preamble>");
      while (*p) {
	char *q = strstr(p, "\\usepackage{ipe}");
	if (q) {
	  while (p < q)
	    fputc(*p++, fh);
	  p = q + 16;
	} else {
	  while (*p)
	    fputc(*p++, fh);
	}
      }
      fprintf(fh, "</preamble>\n");
    }
  }
  /*
  if (pspreamble[0]) {
    fprintf(fh, "<pspreamble>%s</pspreamble>\n", pspreamble);
  }
  */
  if (no_pages > 0) {
    firstpage = 1;
    grouplevel = 0;
  } else {
    fprintf(fh, "<page>\n");
    grouplevel = 1;
  }
  for (iobj = ium_input; iobj; iobj = iobj->next) {
    write_entry(iobj);
  }
  if (no_pages == 0)
    fprintf(fh, "</page>\n");
  fprintf(fh, "</ipe>\n");
  
  if (fclose(fh) == EOF) {
    fprintf(stderr, "Write error on XML file %s\n", xmlname);
    exit(9);
  }
}

int main(int argc, char **argv)
{
  if (argc >= 3 && !strcmp(argv[1], "-test")) {
    /* test mode */
    int i;
    for (i = 2; i < argc; i++) {
      ipename = argv[i];
      xmlname = 0;
      fprintf(stderr, "Testing %s\n", ipename);
      ipetoxml();
    }
  } else {
    if (argc != 3) {
      /* something is wrong here, we should have exactly two arguments */
      fprintf(stderr, "Usage: %s file.ipe file.xml\n", argv[0]);
      exit(9);
    }
    ipename = argv[1];
    xmlname = argv[2];
    ipetoxml();
  }
  return 0;
}

