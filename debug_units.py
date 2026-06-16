from dimensional_engine import parse, UnitRegistry

reg = UnitRegistry()

# 测试单位保留
r1 = parse('sqrt(4 m^2)', reg)
print(f'sqrt(4 m^2) = {r1}')

r2 = parse('abs(-5 m)', reg)
print(f'abs(-5 m) = {r2}')

r3 = parse('floor(3.7 m)', reg)
print(f'floor(3.7 m) = {r3}')

r4 = parse('ceil(3.2 m)', reg)
print(f'ceil(3.2 m) = {r4}')

r5 = parse('round(3.5 m)', reg)
print(f'round(3.5 m) = {r5}')

# 测试更复杂的
r6 = parse('sqrt(100 cm^2)', reg)
print(f'sqrt(100 cm^2) = {r6}')
print(f'  to m: {r6.to("m")}')

# 测试变量保留单位后参与运算
variables = {'v': parse('100 km/h', reg)}
r7 = parse('v * 5 s to m', reg, variables)
print(f'v * 5 s to m = {r7}')

# 测试 ans 保留单位
variables2 = {'ans': parse('100 km/h', reg)}
r8 = parse('ans * 5 s to m', reg, variables2)
print(f'ans * 5 s to m = {r8}')

print('测试完成!')
