import re

disRE = re.compile("{{disambig(uation)?(\|[^}]*)?}}")

ss = 'ca:weo'

if ':' in ss:
    print 1
else:
    print 2
