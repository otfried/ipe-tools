#
# Access Ipe document from Python
#

import sys, os
import math

assert sys.hexversion >= 0x3060000

import ipe as Ipe
ipe = Ipe.ipe()

print("Some quick tests of the Lua bridge:")
print("1 + 1 in Lua: ", Ipe.eval("1 + 1"))
Ipe.execute("print('Hello World' .. ' from Lua')")
g = Ipe.globals()
print("sqrt(2) from Lua: ", g.math.sqrt(2))
print("Global variable config: ", g.config.latexdir, g.config.platform)

print("Testing ipe.Vector and ipe.Matrix:")
v1 = ipe.Vector()
v2 = ipe.Vector(3, 2)
v3 = ipe.Direction(math.pi/4.0)
print(v1, v2, v3)
print(v1 + v2, v2 + v3, v3 - v2)
print(v2.len(), v3.len(), v2.angle(), v3.angle())
print(v2 == v1 + v2, v2 == v2 + v3)
print("Dot products: ", v1 ^ v2, v2 ^ v3)
print(3 * v2, v3 * 7)
print(-v2, -v3)

m1 = ipe.Matrix(1.0, 0, 0, 2.0, 5, 8)
m2 = ipe.Matrix(1.0, 2, 3, -1.0, 0, 0)
print(m1, m2)
print(m1 * m2)
print(m1 * v2, m1 * v3, m2 * v3)

if len(sys.argv) == 2:
  ipename = sys.argv[1]
else:
  ipename = "../poweripe/demo-presentation.ipe"
  
doc = ipe.Document(ipename)
print("Document has ", len(doc), "pages and ", doc.countTotalViews(), "views")

props = doc.properties()
print("Some document properties: ", props.title, props.created, props.creator)
print("All document properties:")
for k in props:
  print(" -", k, props[k])
  
for pageNo in range(1, len(doc) + 1):
  print("Page %d has %d objects" % (pageNo, len(doc[pageNo])))
