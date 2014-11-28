#
# Makefile for ipe5toxml
#

ifdef COMSPEC
TARGET = ipe5toxml.exe
LDFLAGS = -mconsole
else
TARGET = ipe5toxml
endif

LIBS = -lm

all: $(TARGET)

sources	= ipe5toxml.c

objects = ipe5toxml.o

$(TARGET): $(objects)
	$(CC) $(LDFLAGS) -o $(TARGET) $(objects) $(LIBS)

.PHONY: clean
clean:
	@-rm -f $(objects) $(TARGET) 

