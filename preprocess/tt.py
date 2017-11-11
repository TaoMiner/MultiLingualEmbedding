import codecs
import re

a = [0,5,8,12,5,67]

s = sum(a)
b = [float(x)/s for x in a]
print b

rho = 0.1
c = [(x+rho)/(rho+1) for x in b]
print c

s = sum(c)
d = [x/s for x in c]
print d