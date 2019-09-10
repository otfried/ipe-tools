# Ipe Python module

This is an extension module that will let you read and write Ipe
documents from Python 3.

It makes use of the Ipe Lua-bindings, through a [Python-Lua
bridge](http://labix.org/lunatic-python) written by Gustavo Niemeyer.

## Compiling

You'll need to fill in the arguments to find the Lua and Ipe header
files and library in `setup.py`.  Then say
```
python3 setup.py build
sudo python3 setup.py install
```

## Using

The `ipe` module makes available Ipe's [Lua
bindings](http://ipe.otfried.org/manual/lua.html) in Python, so you
can now write scripts working with Ipe files in Python.

Load the module like so:
```
import ipe as Ipe
ipe = Ipe.ipe()
```

You can now use the members of the `ipe` table just like in Lua. For
instance, load an Ipe document by saying:
```
doc = ipe.Document("filename.pdf")
```

Have a look at `test.py` for an example.

**Methods:** In Lua, methods of an object are called using the
"colon-syntax". For instance, you write `obj:get("stroke")` to obtain
the stroke color of an Ipe object.  In Python, you will have to
provide the object **again** as the first argument of the method, like
this: `obj.get(obj, "stroke")`.  (Lua doesn't automatically fill in
the `self` argument.)

**Tables:** Many functions return Lua tables.  For instance,
```
props = doc.properties(doc)
```
will set `props` to be a table with keys such as `author`,
`title`, `created`, etc.   You can access the elements of a table
using attribute syntax `props.title`, using dictionary syntax
`props['title']`, and you can iterate over its keys in a for loop:
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

