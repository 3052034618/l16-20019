from dimensional_engine import parse, DEFAULT_REGISTRY

print('=== 测试 SI 前缀自动识别 ===')
# 测试前缀
tests = [
    ('1 mm', '0.001 m'),
    ('1 km', '1000 m'),
    ('1 cm', '0.01 m'),
    ('1 um', '1e-06 m'),
    ('1 nm', '1e-09 m'),
    ('1 kg', '1000 g'),
    ('1 ms', '0.001 s'),
    ('1 us', '1e-06 s'),
    ('1 ns', '1e-09 s'),
    ('1 MHz', '1000000 Hz'),
    ('1 GHz', '1e+09 Hz'),
    ('1 kW', '1000 W'),
    ('1 MeV', '1.60218e-13 J'),
    ('1 GPa', '1e+09 Pa'),
]

for expr, expected in tests:
    try:
        result = parse(expr)
        print(f'{expr} = {result}')
    except Exception as e:
        print(f'{expr} 错误: {e}')

print()
print('=== 测试新单位 ===')
# 测试压力单位
tests2 = [
    ('1 atm to Pa', '101325 Pa'),
    ('1 bar to Pa', '100000 Pa'),
    ('1 mmHg to Pa', '133.322 Pa'),
    ('1 torr to Pa', '133.322 Pa'),
    ('1 psi to Pa', '6894.76 Pa'),
]

for expr, expected in tests2:
    try:
        result = parse(expr)
        print(f'{expr} = {result}')
    except Exception as e:
        print(f'{expr} 错误: {e}')

print()
print('=== 测试能量单位 ===')
tests3 = [
    ('1 eV to J', '1.60218e-19 J'),
    ('1 keV to eV', '1000 eV'),
    ('1 cal to J', '4.184 J'),
    ('1 kcal to J', '4184 J'),
    ('1 kWh to J', '3.6e+06 J'),
]

for expr, expected in tests3:
    try:
        result = parse(expr)
        print(f'{expr} = {result}')
    except Exception as e:
        print(f'{expr} 错误: {e}')

print()
print('=== 测试天文单位 ===')
tests4 = [
    ('1 AU to km', '1.49598e+08 km'),
    ('1 ly to km', '9.46073e+12 km'),
    ('1 pc to ly', '3.26156 ly'),
]

for expr, expected in tests4:
    try:
        result = parse(expr)
        print(f'{expr} = {result}')
    except Exception as e:
        print(f'{expr} 错误: {e}')

print()
print('=== 测试量纲不匹配转换 ===')
try:
    result = parse('1 m to kg')
    print(f'1 m to kg = {result}')
except Exception as e:
    print(f'1 m to kg 错误: {e}')
