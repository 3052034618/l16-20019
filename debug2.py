from dimensional_engine import _expr_tokenize, _EXPR_TOKEN_RE

# 调试 tokenizer
test_expr = '1 m @ 2 s'
print(f'表达式: {repr(test_expr)}')
print()

# 看看正则表达式匹配了什么
print('正则表达式匹配结果:')
for m in _EXPR_TOKEN_RE.finditer(test_expr):
    print(f'  match: {repr(m.group())}, start={m.start()}, end={m.end()}, group={m.lastgroup}')

print()

# 试试 tokenize
try:
    tokens = _expr_tokenize(test_expr)
    print(f'tokenize 结果: {tokens}')
except Exception as e:
    print(f'tokenize 错误: {e}')

print()

# 再试试另一个
test_expr2 = '1 m # 2 s'
print(f'表达式: {repr(test_expr2)}')
print('正则表达式匹配结果:')
for m in _EXPR_TOKEN_RE.finditer(test_expr2):
    print(f'  match: {repr(m.group())}, start={m.start()}, end={m.end()}, group={m.lastgroup}')
