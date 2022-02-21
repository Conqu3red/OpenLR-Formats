from track import *
from pretty_print import pretty_print

file1 = "a.trk"
file2 = "b.trk"

with open(file1, "rb") as f:
    t1 = TRK_Reader(f).read()
    pretty_print(t1)

with open(file2, "wb") as f:
    TRK_Writer(f, t1).write()

with open(file2, "rb") as f:
    t2 = TRK_Reader(f).read()
    pretty_print(t2)

assert t1 == t2