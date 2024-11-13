import re
pattern = re.compile('label (%[\w.]+)')
str = 'br i1 %10, label %39, label %11'
print(pattern.findall(str))