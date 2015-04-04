#############################################################################
# Makefile for building figtoipe
#############################################################################

CXX           = g++
CXXFLAGS      += -O2 -Wall -W
RM            = rm -f
LIBS          = -lz

TARGET = figtoipe
SOURCES = $(TARGET).cpp 
SRCDISTFILES = $(TARGET).1 $(SOURCES) README Makefile GPL-2

all: $(TARGET)

clean:
	-$(RM) $(TARGET)

$(TARGET): $(SOURCES)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS) $(LIBS)

dist:
	DATE=`date  +"%Y%m%d"`; D=/tmp/$(TARGET)-$$DATE; \
	rm -rf $$D; mkdir $$D; \
	cp $(SRCDISTFILES) $$D; \
	tar czvf $$D.tar.gz -C /tmp $(TARGET)-$$DATE

.PHONY: all
