# -*- coding: utf-8 -*-
"""Export every slide to PNG using WPS's own renderer (identical to what the user sees), for checking connector arrows."""
import os, sys
import win32com.client as win32

src = os.path.abspath(sys.argv[1])
outdir = os.path.abspath(sys.argv[2])
os.makedirs(outdir, exist_ok=True)
app = win32.DispatchEx("Kwpp.Application")
app.Visible = True
doc = app.Presentations.Open(src, WithWindow=False)
for i in range(1, doc.Slides.Count + 1):
    p = os.path.join(outdir, "s%d.png" % i)
    doc.Slides.Item(i).Export(p, "PNG", 2400, 1350)
    print(p)
doc.Close(); app.Quit()
