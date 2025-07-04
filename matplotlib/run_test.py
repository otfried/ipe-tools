from glob import glob
from os.path import exists
from subprocess import run


if not exists(outdir := "test_outputs"):
    run(f"mkdir {outdir}", shell=True)

if exists(f"tests/{outdir}"):
    run(f"rm -rf tests/{outdir}", shell=True)

for f in (files := glob('tests/*.py')):
    print(f"python {f}")
    run(["python", f"{f}"])
run(f"mv *.ipe {outdir}", shell=True)
run(f"mv {outdir} tests", shell=True)
