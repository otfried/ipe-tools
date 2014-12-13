#
# Run all the tests in tests subdirectory
# and save plots in ipe and svg format
# 

import os, sys

def fix_file(f):
  data = open("tests/%s" % f, "rb").readlines()
  os.rename("tests/%s" % f, "tests/%s.bak" % f)
  out = open("tests/%s" % f, "wb")
  for l in data:
    ll = l.strip()
    if ll == "import matplotlib as mpl": continue
    if ll == "print mpl.__file__": continue
    if ll == "mpl.use('module://backend_ipe')": continue
    if ll == "#mpl.use('module://backend_ipe')": continue    
    if ll == "#plt.show()" or ll == "plt.show()": continue
    if ll[:12] == "#plt.savefig": continue
    if ll[:11] == "plt.savefig": continue
    out.write(l)
  out.close()

def runall(form):
  tests = [f[:-3] for f in os.listdir("tests") if f[-3:] == ".py"]
  for f in tests:
    # doesn't work on my matplotlib version
    if f == "power_norm_demo": continue
    run(form, f)

def run(form, f):
  sys.stderr.write("# %s\n" % f)
  t = open("tmp.py", "wb")
  t.write("""# %s
import matplotlib as mpl
""" % f)
  if form=="ipe":
    t.write("mpl.use('module://backend_ipe')\n")
  t.write(open("tests/%s.py" % f, "rb").read())
  t.write("plt.savefig('out/%s.%s', format='%s')\n" % (f, form, form))
  t.close()
  os.system("python tmp.py")

if len(sys.argv) != 3:
  sys.stderr.write("Usage: run_test.py <format> <test>\n")
  sys.exit(9)

form = sys.argv[1]
test = sys.argv[2]
if test == 'all':
  runall(form)
else:
  run(form, test)

