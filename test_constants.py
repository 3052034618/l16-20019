from dimensional_engine import parse, DEFAULT_REGISTRY

print('=== 已注册的物理常数 ===')
for name, q in DEFAULT_REGISTRY.all_constants().items():
    print(f'{name} = {q}')

print()
print('=== 测试表达式中使用常数 ===')
# 万有引力计算
F = parse('G * 5.972e24 kg * 1 kg / (6.371e6 m)^2')
print(f'重力 F = {F}')
print(f'转成 N: {F.to("N")}')

print()
# 质能方程
E = parse('1 kg * c^2')
print(f'E = mc^2 = {E}')
print(f'转成 J: {E.to("J")}')

print()
# 理想气体
P = parse('1 mol * R * 273.15 K / 0.0224 m^3')
print(f'P = nRT/V = {P}')
print(f'转成 Pa: {P.to("Pa")}')

print()
# 5 G 这种写法（数字后面跟常数）
result = parse('5 G')
print(f'5 G = {result}')

print()
# 测试小时 h 仍然可用
result2 = parse('2 h to s')
print(f'2 h = {result2}')
