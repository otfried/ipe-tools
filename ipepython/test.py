#
# Access Ipe document from Python
#

import sys, os
assert sys.hexversion >= 0x3060000

import ipe as Ipe
ipe = Ipe.ipe()

print("Some quick tests of the Lua bridge:")
print("1 + 1 in Lua: ", Ipe.eval("1 + 1"))
Ipe.execute("print('Hello World' .. ' from Lua')")
g = Ipe.globals()
print("sqrt(2) from Lua: ", g.math.sqrt(2))
print("Global variable config: ", g.config.latexdir, g.config.platform)

if len(sys.argv) == 2:
  ipename = sys.argv[1]
  
  doc = ipe.Document(ipename)
  print("Document has ", len(doc), "pages and ", doc.countTotalViews(doc), "views")

  props = doc.properties(doc)
  print("Some document properties: ", props.title, props.created, props.creator)
  print("All document properties:")
  for k in props:
    print(" -", k, props[k])

  for pageNo in range(1, len(doc) + 1):
    print("Page %d has %d objects" % (pageNo, len(doc[pageNo])))

