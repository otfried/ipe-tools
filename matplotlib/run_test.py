from glob import glob
from subprocess import run


for f in (files := glob('tests/*.py')):
    print(f"python {f}")
    run(["python", f"{f}"])
run("mv *.ipe tests", shell=True)
