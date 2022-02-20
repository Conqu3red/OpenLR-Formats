from track import *
from pretty_print import pretty_print

with open("3 a.trk", "rb") as f:
    t = TRK_Reader(f).read()
    pretty_print(t)