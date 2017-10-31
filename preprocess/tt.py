import codecs
import re
import struct
import pandas as pd

vec = [2,1,4,0,1]

a = -pd.Series(vec)

ranks = a.rank(method='min')
print ranks