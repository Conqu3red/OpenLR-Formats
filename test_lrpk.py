from open_lr_formats.lrpk.track import *
from open_lr_formats.pretty_print import pretty_print

file1 = "a.lrpk"
file2 = "b.lrpk"

with open(file1, "rb") as f:
    t1 = LRPK_Reader(f).read()
    pretty_print(t1)

with open(file2, "wb") as f:
    LRPK_Writer(f, t1).write()

with open(file2, "rb") as f:
    t2 = LRPK_Reader(f).read()
    pretty_print(t2)

assert t1 == t2