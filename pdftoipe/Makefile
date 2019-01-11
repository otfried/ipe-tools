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
  CXX=$(IPECROSS)-w64-mingw32-g++
  CPPFLAGS += -I/sw/mingwlibs-$(IPECROSS)/include/poppler
  LIBS += -L/sw/mingwlibs-$(IPECROSS)/lib -lpoppler
  LDFLAGS += -static
  TARGET = pdftoipe.exe	
else
  POPPLER_CFLAGS ?= $(shell pkg-config --cflags poppler)
  POPPLER_LIBS   ?= $(shell pkg-config --libs poppler)
  CPPFLAGS += $(POPPLER_CFLAGS)
  LIBS += $(POPPLER_LIBS)
  TARGET   = pdftoipe
endif

CXXFLAGS += -Wno-write-strings -std=c++11

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
