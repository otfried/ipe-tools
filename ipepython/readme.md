# Ipe Python module

This is an extension module that will let you read and write Ipe
documents from Python 3.

It makes the Ipe Lua-bindings available using a Python-Lua bridge
based on code written by [Gustavo
Niemeyer](http://labix.org/lunatic-python).

## Installation

You'll need to fill in the arguments to find the Lua and Ipe header
files and library in `setup.py`.  Then say
```
python3 setup.py build
sudo python3 setup.py install
```

## Documentation

After loading the module:

```
import ipe
```

you can use the functions documented in the [Lua
bindings](http://ipe.otfried.org/manual/lua.html). For instance, load
an Ipe document by saying:

```
doc = ipe.Document("filename.pdf")
```

Have a look at `test.py` for an example.


**Tables:** Several methods in the module return *Lua tables*.  These
are similar to Python dictionaries, but are a distinct type.

For instance,

```
props = doc.properties()
```

will set `props` to be a table with keys such as `author`, `title`,
`created`, etc.  

You can access the elements of a table using either
attribute syntax (`props.title`) or dictionary syntax
(`props['title']`).  You can also can iterate over the elements of a
table in a `for` loop:

```
for k in props:
  print(k, props[k])
```

**Sequences:** A document is a sequence of pages, a page is a sequence
of graphical objects.  In Lua, indices **start with one**, not zero!
You can use Python's `len` function to determine the length of a
sequence.  For instance, loop over the pages of a document like this:

```
for pageNo in range(1, len(doc) + 1):
  print("Page %d has %d objects" % (pageNo, len(doc[pageNo])))
```

**Iterators:** The Lua documentation shows loops using
`page:objects()` and `document:pages()`.  This does not work from
Python.  You should use a loop over the indices instead.
