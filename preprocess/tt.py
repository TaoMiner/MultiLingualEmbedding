import codecs
import re
import struct
import pandas as pd

RE = re.compile(r'^([+-])(.*):(en|zh|es)$')

s = '+w:ew2'

m = RE.match(s)
if m:
    print m.group(1)
    print m.group(2)
    print m.group(3)