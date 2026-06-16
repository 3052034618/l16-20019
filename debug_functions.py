from dimensional_engine import parse, UnitRegistry
import math

reg = UnitRegistry()

print("=== 测试三角函数 ===")
# 弧度
r1 = parse('sin(0)', reg)
print(f'sin(0) = {r1} (期望 0)')

r2 = parse('sin(pi/2)', reg)
print(f'sin(pi/2) = {r2.value_base:.6f} (期望 1)')

# 角度
r3 = parse('sin(90 deg)', reg)
print(f'sin(90 deg) = {r3.value_base:.6f} (期望 1)')

r4 = parse('cos(0 deg)', reg)
print(f'cos(0 deg) = {r4.value_base:.6f} (期望 1)')

r5 = parse('tan(45 deg)', reg)
print(f'tan(45 deg) = {r5.value_base:.6f} (期望 1)')

# 弧度转换
r6 = parse('cos(pi)', reg)
print(f'cos(pi) = {r6.value_base:.6f} (期望 -1)')

print("\n=== 测试反三角函数 ===")
r7 = parse('asin(1)', reg)
print(f'asin(1) = {r7.value_base:.6f} rad (期望 pi/2 ≈ 1.5708)')

r8 = parse('acos(0)', reg)
print(f'acos(0) = {r8.value_base:.6f} rad (期望 pi/2 ≈ 1.5708)')

print("\n=== 测试双曲函数 ===")
r9 = parse('sinh(0)', reg)
print(f'sinh(0) = {r9.value_base:.6f} (期望 0)')

r10 = parse('cosh(0)', reg)
print(f'cosh(0) = {r10.value_base:.6f} (期望 1)')

print("\n=== 测试指数对数 ===")
r11 = parse('exp(0)', reg)
print(f'exp(0) = {r11.value_base:.6f} (期望 1)')

r12 = parse('exp(1)', reg)
print(f'exp(1) = {r12.value_base:.6f} (期望 e ≈ 2.71828)')

r13 = parse('ln(1)', reg)
print(f'ln(1) = {r13.value_base:.6f} (期望 0)')

r14 = parse('log(10)', reg)
print(f'log(10) = {r14.value_base:.6f} (期望 ln(10) ≈ 2.30259)')

r15 = parse('log10(100)', reg)
print(f'log10(100) = {r15.value_base:.6f} (期望 2)')

r16 = parse('log2(8)', reg)
print(f'log2(8) = {r16.value_base:.6f} (期望 3)')

print("\n=== 测试平方根 ===")
r17 = parse('sqrt(4)', reg)
print(f'sqrt(4) = {r17.value_base:.6f} (期望 2)')

# 量纲保持
r18 = parse('sqrt(4 m^2)', reg)
print(f'sqrt(4 m^2) = {r18} (期望 2 m)')
print(f'  量纲: {r18.dimension}')

r19 = parse('sqrt(9 m^2)', reg)
print(f'sqrt(9 m^2) = {r19} (期望 3 m)')

print("\n=== 测试取整和绝对值 ===")
r20 = parse('abs(-5.2)', reg)
print(f'abs(-5.2) = {r20.value_base:.6f} (期望 5.2)')

r21 = parse('floor(3.7)', reg)
print(f'floor(3.7) = {r21.value_base:.6f} (期望 3)')

r22 = parse('ceil(3.2)', reg)
print(f'ceil(3.2) = {r22.value_base:.6f} (期望 4)')

r23 = parse('round(3.5)', reg)
print(f'round(3.5) = {r23.value_base:.6f} (期望 4)')

# 量纲保持
r24 = parse('abs(-5 m)', reg)
print(f'abs(-5 m) = {r24} (期望 5 m)')

print("\n=== 测试量纲错误 ===")
try:
    r = parse('sin(5 m)', reg)
    print(f'sin(5 m) 应该报错，实际得到: {r}')
except Exception as e:
    print(f'sin(5 m) 正确报错: {type(e).__name__}')

try:
    r = parse('log(10 m)', reg)
    print(f'log(10 m) 应该报错，实际得到: {r}')
except Exception as e:
    print(f'log(10 m) 正确报错: {type(e).__name__}')

print("\n=== 测试隐式乘法 ===")
r25 = parse('2 sin(90 deg)', reg)
print(f'2 sin(90 deg) = {r25.value_base:.6f} (期望 2)')

r26 = parse('(1+2) cos(0)', reg)
print(f'(1+2) cos(0) = {r26.value_base:.6f} (期望 3)')

print("\n=== 测试复合表达式 ===")
r27 = parse('sin(30 deg)^2 + cos(30 deg)^2', reg)
print(f'sin²(30°) + cos²(30°) = {r27.value_base:.6f} (期望 1)')

r28 = parse('sqrt(2) * sin(45 deg)', reg)
print(f'sqrt(2) * sin(45 deg) = {r28.value_base:.6f} (期望 1)')

print("\n=== 测试变量在函数中使用 ===")
variables = {'theta': parse('90 deg', reg)}
r29 = parse('sin(theta)', reg, variables)
print(f'sin(theta) where theta=90 deg = {r29.value_base:.6f} (期望 1)')

print("\n所有测试完成!")
