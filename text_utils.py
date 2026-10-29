import re
import jieba

def tokens(s):
    return [x.strip() for x in jieba.cut(s) if x.strip() and not re.fullmatch(r'\W+', x)]
