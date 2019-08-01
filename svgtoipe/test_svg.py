#!/usr/bin/env python3

#
# Test svgtoipe.py on a few examples
#
# More tests:
# SVG Test suite with PNG reference: https://www.w3.org/Graphics/SVG/Test/20110816/
#


import os, sys, re
import urllib.request

assert sys.hexversion >= 0x3000000, "Please run using Python 3"

ignore = set(["photos.svg", "videos.svg"])

def getSamples():
  url = "https://dev.w3.org/SVG/tools/svgweb/samples/svg-files/"
  req = urllib.request.Request(url)
  f = urllib.request.urlopen(req)
  index = f.read()
  fpat = re.compile(b'href="([-_a-zA-Z0-9]+\\.svg)"')
  for m in fpat.finditer(index):
    fname = m.group(1).decode("UTF-8")
    if fname in ignore:
      continue
    if os.path.exists("test/" + fname):
      continue
    sys.stderr.write("Downloading '%s'\n" % fname)
    req1 = urllib.request.Request(url + fname)
    ex = urllib.request.urlopen(req1).read()
    out = open("test/" + fname, "wb")
    out.write(ex)
    out.close()

def testSamples():
  files = os.listdir("./test")
  for f in files:
    if not f.endswith(".svg"):
      continue
    status = os.system("python3 svgtoipe.py test/%s 2> test/results-%s.txt" % (f, f))
    if status != 0:
      sys.stderr.write("Error converting '%s'\n" % f)
    else:
      sys.stderr.write("Converted '%s'\n" % f)
  
if __name__ == "__main__":
  getSamples()
  testSamples()
