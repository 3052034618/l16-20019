from dimensional_engine import parse, DEFAULT_REGISTRY, UnitRegistry, q

# 测试变量保留单位
registry = UnitRegistry()
v = parse('100 km/h', registry)
print(f'v = {v}')
print(f'v.dimension = {v.dimension}')

# 测试变量在表达式中保留单位
variables = {'v': v}
result = parse('v * 5 s', registry, variables)
print(f'v * 5 s = {result}')
print(f'to m: {result.to("m")}')

# 测试 ans
variables2 = {'ans': v}
result2 = parse('ans * 2', registry, variables2)
print(f'ans * 2 = {result2}')

# 测试更复杂的例子
variables3 = {
    'v': parse('100 km/h', registry),
    't': parse('5 s', registry)
}
result3 = parse('v * t to m', registry, variables3)
print(f'v * t to m = {result3}')

# 测试 ans * 5 s to m
variables4 = {'ans': parse('100 km/h', registry)}
result4 = parse('ans * 5 s to m', registry, variables4)
print(f'ans * 5 s to m = {result4}')

print('\n所有测试完成!')
