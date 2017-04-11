import re
tagRE = re.compile(r'(.*?)<(/?\w+)[^>]*?>(?:([^<]*)(<.*?>)?)?')
quotaRE = re.compile(r'(\d{1,}):(\d{1,}):(.*)')

ss = '635:24:Arquitectura'

m = quotaRE.search(ss)

print m.group(1)
print m.group(2)
print m.group(3)