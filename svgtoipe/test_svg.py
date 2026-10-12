#
# Test svgtoipe.py on a few examples
#
# More tests:
# SVG Test suite with PNG reference: https://www.w3.org/Graphics/SVG/Test/20110816/
#


import html
import os
import re
import subprocess
import sys
import urllib.request
from urllib.parse import quote

assert sys.hexversion >= 0x3000000, "Please run using Python 3"

ignore = {"photos.svg", "videos.svg", "oscon.svg"}


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
        sys.stderr.write(f"Downloading '{fname}'\n")
        req1 = urllib.request.Request(url + fname)
        ex = urllib.request.urlopen(req1).read()
        with open("test/" + fname, "wb") as out:
            out.write(ex)


def writeOverview(results):
    with open("overview.html", "w", encoding="UTF-8") as out:
        out.write("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SVG conversion overview</title>
<style>
body { margin: 16px; font-family: sans-serif; color: #222; }
table { width: 100%; table-layout: fixed; border-collapse: collapse; }
th, td { width: 50%; border: 1px solid #bbb; padding: 8px; vertical-align: top; }
th { background: #eee; }
a { overflow-wrap: anywhere; }
object { display: block; width: 100%; height: 360px; margin-top: 8px; }
.error { color: #a00; }
@media (max-width: 600px) { body { margin: 4px; } object { height: 240px; } }
</style>
</head>
<body>
<h1>SVG conversion overview</h1>
<table>
<thead><tr><th scope="col">Original SVG</th><th scope="col">SVG &rarr; Ipe &rarr; SVG</th></tr></thead>
<tbody>
""")
        for original, rendered, log, error in results:
            original_url = html.escape(quote(original))
            rendered_url = html.escape(quote(rendered))
            log_url = html.escape(quote(log))
            out.write(
                f'<tr><td><a href="{original_url}">{html.escape(os.path.basename(original))}</a>'
            )
            out.write(
                f'<object type="image/svg+xml" data="{original_url}"></object></td><td>'
            )
            if error:
                out.write(f'<p class="error">{html.escape(error)}</p>')
            else:
                out.write(
                    f'<a href="{rendered_url}">{html.escape(os.path.basename(rendered))}</a> '
                )
            if os.path.getsize(log) > 0:
                out.write(
                    f'<a href="{log_url}" target="_blank" rel="noopener">Diagnostics</a>'
                )
            if not error:
                out.write(
                    f'<object type="image/svg+xml" data="{rendered_url}"></object>'
                )
            out.write("</td></tr>\n")
        out.write("</tbody>\n</table>\n</body>\n</html>\n")


def testSamples():
    files = sorted(os.listdir("./test"))
    results = []
    for f in files:
        if not f.endswith(".svg") or f.endswith(".ipe.svg"):
            continue
        original = os.path.join("test", f)
        ipe = original[:-4] + ".ipe"
        rendered = ipe + ".svg"
        log = os.path.join("test", "results-" + f[:-4] + ".txt")
        error = None
        with open(log, "w", encoding="UTF-8") as diagnostics:
            try:
                status = subprocess.run(
                    [sys.executable, "svgtoipe.py", original],
                    stderr=diagnostics,
                    check=False,
                ).returncode
                if status != 0:
                    error = f"Error converting '{f}'"
                else:
                    status = subprocess.run(
                        ["iperender", "-svg", "-nocrop", ipe, rendered],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    ).returncode
                    if status != 0:
                        error = f"Error rendering '{ipe}'"
                    elif not os.path.isfile(rendered) or os.path.getsize(rendered) == 0:
                        error = f"Renderer produced no SVG for '{ipe}'"
            except OSError as exception:
                error = str(exception)
        sys.stderr.write((error or f"Converted and rendered '{f}'") + "\n")
        results.append((original, rendered, log, error))
    writeOverview(results)
    sys.stderr.write("Wrote overview.html\n")


if __name__ == "__main__":
    getSamples()
    testSamples()
