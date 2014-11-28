# --------------------------------------------------------------------
# Makefile for pdftoipe
# --------------------------------------------------------------------

ifdef COMSPEC
  # compiling on Windows?
  CPPFLAGS += -I/c/Home/poppler-0.16.5/poppler \
	-I/c/Home/poppler-0.16.5
  LIBS += -L/c/MinGW/lib -lpoppler
  TARGET = pdftoipe.exe	
else ifdef IPEMXE
  # cross-compiling for Windows?
  CXX=i686-pc-mingw32-g++
  CPPFLAGS += -I/sw/mingw/include/poppler
  LIBS += /sw/mingw/bin/libpoppler-35.dll
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
