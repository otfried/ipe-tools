# --------------------------------------------------------------------
# Makefile for pdftoipe
# --------------------------------------------------------------------

ifdef COMSPEC
  # compiling on Windows?
  CPPFLAGS += -I/minglibs/include/poppler
  LIBS += -L/minglibs/lib -lpoppler
  LDFLAGS += -static
  TARGET = pdftoipe.exe	
else ifdef IPECROSS
  # cross-compiling for Windows?
  CXX=i686-w64-mingw32-g++
  CPPFLAGS += -I/sw/mingwlibs/include/poppler
  LIBS += -L/sw/mingwlibs/lib -lpoppler
  LDFLAGS += -static
  TARGET = pdftoipe.exe	
else
  CPPFLAGS += $(shell pkg-config --cflags poppler) 
  LIBS += $(shell pkg-config --libs poppler)
  TARGET = pdftoipe
endif

CXXFLAGS += -Wno-write-strings

all: $(TARGET)

objects = parseargs.o xmloutputdev.o pdftoipe.o 

$(TARGET): $(objects)
	$(CXX) $(LDFLAGS) -o $@ $^ $(LIBS)

clean:
	@-rm -f $(objects) $(TARGET)

xmloutputdev.o: xmloutputdev.h
pdftoipe.o: xmloutputdev.h parseargs.h
parseargs.o: parseargs.h

# --------------------------------------------------------------------
