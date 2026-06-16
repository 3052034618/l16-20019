"""
量纲分析与单位换算引擎 — 完整演示与测试
========================================
"""

import math
import sys
import traceback

sys.path.insert(0, ".")

from dimensional_engine import (
    DIMENSIONLESS,
    Dimension,
    DimensionError,
    Quantity,
    UnitRegistry,
    parse,
    q,
)

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}  {detail}")


def approx(a, b, rel=1e-6):
    if a == 0 and b == 0:
        return True
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-12)


# ═══════════════════════════════════════════════════════
# 1. 量纲的指数向量表示
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("1. 量纲的指数向量表示")
print("=" * 60)

length = Dimension(length=1)
mass = Dimension(mass=1)
time_dim = Dimension(time=1)
velocity = Dimension(length=1, time=-1)
force = Dimension(mass=1, length=1, time=-2)
energy = Dimension(mass=1, length=2, time=-2)
pressure = Dimension(mass=1, length=-1, time=-2)

print(f"\n  长度  → {length}  指数向量: {length.exponents}")
print(f"  质量  → {mass}  指数向量: {mass.exponents}")
print(f"  时间  → {time_dim}  指数向量: {time_dim.exponents}")
print(f"  速度  → {velocity}  指数向量: {velocity.exponents}")
print(f"  力    → {force}  指数向量: {force.exponents}")
print(f"  能量  → {energy}  指数向量: {energy.exponents}")
print(f"  压强  → {pressure}  指数向量: {pressure.exponents}")

check("速度量纲 = [1,0,-1,0,0,0,0]", velocity.exponents == (1, 0, -1, 0, 0, 0, 0))
check("力量纲 = [1,1,-2,0,0,0,0]", force.exponents == (1, 1, -2, 0, 0, 0, 0))

# ═══════════════════════════════════════════════════════
# 2. 乘除法 → 量纲指数相加减
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("2. 乘除法: 量纲指数相加减")
print("=" * 60)

vel_dim = length / time_dim
print(f"\n  长度 / 时间 = {vel_dim}  (速度)")
check("速度 = 长度/时间", vel_dim == velocity)

acc_dim = velocity / time_dim
print(f"  速度 / 时间 = {acc_dim}  (加速度)")
check("加速度 = 长度·时间⁻²", acc_dim == Dimension(length=1, time=-2))

f_dim = mass * acc_dim
print(f"  质量 × 加速度 = {f_dim}  (力)")
check("力 = 质量×加速度", f_dim == force)

e_dim = force * length
print(f"  力 × 长度 = {e_dim}  (能量/功)")
check("能量 = 力×长度", e_dim == energy)

p_dim = force / (length ** 2)
print(f"  力 / 长度² = {p_dim}  (压强)")
check("压强 = 力/面积", p_dim == Dimension(mass=1, length=-1, time=-2))

ratio_dim = energy / energy
print(f"  能量 / 能量 = {ratio_dim}  (无量纲)")
check("同量纲相除 = 无量纲", ratio_dim.is_dimensionless())

# ═══════════════════════════════════════════════════════
# 3. 加减法 → 量纲必须一致，否则报错
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("3. 加减法: 量纲一致性校验")
print("=" * 60)

print("\n  合法: 5 m + 3 m")
sum_q = q(5, "m") + q(3, "m")
check("5m + 3m = 8m", approx(sum_q.value_base, 8))

print("  合法: 1 km + 500 m (不同单位但同量纲)")
sum_q2 = q(1, "km") + q(500, "m")
check("1km + 500m = 1500m (基本单位)", approx(sum_q2.value_base, 1500))

print("  非法: 5 m + 3 s (不同量纲)")
try:
    _ = q(5, "m") + q(3, "s")
    check("长度+时间 应报错", False)
except DimensionError as e:
    check("长度+时间 报错 ✓", True, str(e))

print("  非法: 10 kg - 2 m")
try:
    _ = q(10, "kg") - q(2, "m")
    check("质量-长度 应报错", False)
except DimensionError as e:
    check("质量-长度 报错 ✓", True, str(e))

# ═══════════════════════════════════════════════════════
# 4. 不同单位间换算 — 换算因子
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("4. 单位换算 — 通过换算因子")
print("=" * 60)

print("\n  --- 长度 ---")
r1 = q(1, "km").to("m")
print(f"  1 km = {r1}")
check("1 km = 1000 m", approx(r1.value_in_unit(), 1000))

r2 = q(1, "mi").to("km")
print(f"  1 mi = {r2}")
check("1 mi ≈ 1.60934 km", approx(r2.value_in_unit(), 1.609344))

r3 = q(12, "in").to("cm")
print(f"  12 in = {r3}")
check("12 in = 30.48 cm", approx(r3.value_in_unit(), 30.48))

print("\n  --- 速度 ---")
r4 = q(100, "km/h").to("m/s")
print(f"  100 km/h = {r4}")
check("100 km/h ≈ 27.78 m/s", approx(r4.value_in_unit(), 100 / 3.6))

r5 = q(1, "kn").to("km/h")
print(f"  1 kn = {r5}")
check("1 kn ≈ 1.852 km/h", approx(r5.value_in_unit(), 1.852))

print("\n  --- 质量 ---")
r6 = q(1, "lb").to("kg")
print(f"  1 lb = {r6}")
check("1 lb ≈ 0.453592 kg", approx(r6.value_in_unit(), 0.45359237))

print("\n  --- 量纲不一致换算应报错 ---")
try:
    q(100, "km/h").to("kg")
    check("速度→质量 应报错", False)
except DimensionError:
    check("速度→质量 报错 ✓", True)

# ═══════════════════════════════════════════════════════
# 5. 温度换算 — 带偏移的非线性换算
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("5. 温度换算 — 带偏移的非比例换算")
print("=" * 60)

print("\n  摄氏→开尔文:")
t1 = q(0, "C").to("K")
print(f"  0 °C = {t1}")
check("0°C = 273.15 K", approx(t1.value_in_unit(), 273.15))

t2 = q(100, "C").to("K")
print(f"  100 °C = {t2}")
check("100°C = 373.15 K", approx(t2.value_in_unit(), 373.15))

print("\n  开尔文→摄氏:")
t3 = q(300, "K").to("C")
print(f"  300 K = {t3}")
check("300 K = 26.85°C", approx(t3.value_in_unit(), 26.85))

print("\n  华氏→摄氏:")
t4 = q(32, "F").to("C")
print(f"  32 °F = {t4}")
check("32°F = 0°C", approx(t4.value_in_unit(), 0))

t5 = q(212, "F").to("C")
print(f"  212 °F = {t5}")
check("212°F = 100°C", approx(t5.value_in_unit(), 100))

print("\n  摄氏→华氏:")
t6 = q(37, "C").to("F")
print(f"  37 °C = {t6}")
check("37°C = 98.6°F", approx(t6.value_in_unit(), 98.6))

print("\n  华氏→开尔文:")
t7 = q(-40, "F").to("K")
print(f"  -40 °F = {t7}")
check("-40°F = 233.15 K", approx(t7.value_in_unit(), 233.15))

# ═══════════════════════════════════════════════════════
# 6. 复合量纲运算 — 力、功、功率
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("6. 复合量纲运算")
print("=" * 60)

G_val = 6.674e-11
G_q = G_val * q(1, "m") ** 3 / (q(1, "kg") * q(1, "s") ** 2)
print(f"  G (引力常数) 的量纲: {G_q.dimension}")
check("G 量纲 = L³·M⁻¹·T⁻²", G_q.dimension == Dimension(length=3, mass=-1, time=-2))

F_gravity = G_q * q(5.972e24, "kg") * q(1, "kg") / (q(6.371e6, "m") ** 2)
print(f"  地表引力 (每kg): {F_gravity.to('N')}")
check("地表引力≈9.8N", approx(F_gravity.to_value("N"), 9.8, rel=0.01))

F_weight = q(10, "kg") * (q(9.8, "m") / q(1, "s") ** 2)
print(f"  10kg 物体重力: {F_weight.to('N')}")
check("10kg 重力=98N", approx(F_weight.to_value("N"), 98))

work = F_weight * q(5, "m")
print(f"  提升5m 做功: {work.to('J')}")
check("做功=490J", approx(work.to_value("J"), 490))

power = work / q(2, "s")
print(f"  2秒完成 功率: {power.to('W')}")
check("功率=245W", approx(power.to_value("W"), 245))

# ═══════════════════════════════════════════════════════
# 7. 表达式解析器
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("7. 表达式解析器")
print("=" * 60)

r_parse1 = parse("100 km/h + 20 m/s")
print(f"  100 km/h + 20 m/s = {r_parse1.to('m/s')}")
check("100km/h+20m/s≈47.78m/s", approx(r_parse1.to_value("m/s"), 100 / 3.6 + 20))

r_parse2 = parse("5 kg * 9.8 m/s")
print(f"  5 kg * 9.8 m/s = {r_parse2}")
check("5kg × 9.8m/s 量纲=动量", r_parse2.dimension == Dimension(mass=1, length=1, time=-1))

r_parse3 = parse("0 C to K")
print(f"  0 °C → K = {r_parse3}")
check("0°C → 273.15 K", approx(r_parse3.value_in_unit(), 273.15))

r_parse4 = parse("32 F to C")
print(f"  32 °F → °C = {r_parse4}")
check("32°F → 0°C", approx(r_parse4.value_in_unit(), 0))

r_parse5 = parse("1 km + 500 m")
print(f"  1 km + 500 m = {r_parse5.to('m')}")

r_parse6 = parse("100 km/h to m/s")
print(f"  100 km/h → m/s = {r_parse6}")

print("\n  --- 表达式中量纲不一致应报错 ---")
try:
    parse("5 m + 3 s")
    check("5m + 3s 应报错", False)
except DimensionError:
    check("5m + 3s 报错 ✓", True)

# ═══════════════════════════════════════════════════════
# 8. 比较运算 — 量纲一致性要求
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("8. 比较运算")
print("=" * 60)

check("1 km > 500 m", q(1, "km") > q(500, "m"))
check("1 km == 1000 m", q(1, "km") == q(1000, "m"))
check("100 km/h < 30 m/s", q(100, "km/h") < q(30, "m/s"))

try:
    _ = q(5, "m") > q(3, "s")
    check("长度>时间 应报错", False)
except DimensionError:
    check("长度>时间 报错 ✓", True)

# ═══════════════════════════════════════════════════════
# 9. 幂运算
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("9. 幂运算 — 量纲指数乘以幂次")
print("=" * 60)

area = q(3, "m") ** 2
print(f"  (3 m)² = {area}  量纲: {area.dimension}")
check("面积量纲 = L²", area.dimension == Dimension(length=2))

volume = q(2, "m") ** 3
print(f"  (2 m)³ = {volume}  量纲: {volume.dimension}")
check("体积量纲 = L³", volume.dimension == Dimension(length=3))

# ═══════════════════════════════════════════════════════
# 10. 无量纲量
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("10. 无量纲量")
print("=" * 60)

ratio = q(1, "km") / q(1000, "m")
print(f"  1 km / 1000 m = {ratio.value_base}  量纲: {ratio.dimension}")
check("1km/1000m = 1 (无量纲)", approx(ratio.value_base, 1) and ratio.dimension.is_dimensionless())

# ═══════════════════════════════════════════════════════
# 汇总
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
total = PASS + FAIL
print(f"测试结果: {PASS}/{total} 通过", end="")
if FAIL > 0:
    print(f"  ⚠ {FAIL} 失败")
else:
    print("  🎉 全部通过!")
print("=" * 60)
