import re
tagRE = re.compile(r'(.*?)<(/?\w+)[^>]*?>(?:([^<]*)(<.*?>)?)?')
quotaRE = re.compile(r'redirect title=\"(.*?)\"')

ss = '    <redirect title="History of Afghanistan" />asdfwef"wef"'

m = quotaRE.search(ss)

print m.group(1)