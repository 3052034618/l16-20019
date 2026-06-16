"""
量纲分析与单位换算引擎 v2.0 — 完整测试
========================================
测试覆盖:
- 复合单位指数解析 (m/s^2, m^3/kg/s^2, N*m, (m/s)^2)
- 自定义单位与别名 API
- 表达式语法增强 (负数、负指数、隐式乘法)
- 量纲一致性校验
- 单位自动简化 (自动转 N, J, W)
- 命令行单次模式
"""

import math
import sys

sys.path.insert(0, ".")

from dimensional_engine import (
    DIMENSIONLESS,
    Dimension,
    DimensionError,
    ParseError,
    Quantity,
    UnitDefinitionError,
    UnitRegistry,
    parse,
    parse_unit_symbol,
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
# 1. 复合单位指数解析
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("1. 复合单位指数解析")
print("=" * 60)

reg = UnitRegistry()

# 清除默认注册的 km/h, m/s 等以测试动态解析
test_reg = UnitRegistry()

print("\n  --- 解析单位符号 ---")
for sym, expected_dim, expected_desc in [
    ("m/s^2", Dimension(length=1, time=-2), "加速度"),
    ("kg*m/s^2", Dimension(mass=1, length=1, time=-2), "力"),
    ("m^3/kg/s^2", Dimension(length=3, mass=-1, time=-2), "引力常数单位"),
    ("N*m", Dimension(mass=1, length=2, time=-2), "功=牛顿×米"),
    ("(m/s)^2", Dimension(length=2, time=-2), "速度平方"),
    ("s^-2", Dimension(time=-2), "频率平方"),
    ("kg^-1*m^3*s^-2", Dimension(length=3, mass=-1, time=-2), "引力常数单位(负指数)"),
    ("kg*m^2/s^3", Dimension(mass=1, length=2, time=-3), "功率"),
]:
    u = parse_unit_symbol(sym, test_reg)
    ok = u is not None and u.dimension == expected_dim
    check(f"parse_unit('{sym}') → {expected_desc}", ok,
          f"得 {u.dimension if u else None}")

print("\n  --- 表达式中使用复合单位 ---")
r1 = parse("5 kg * 9.8 m/s^2", test_reg)
check("5 kg * 9.8 m/s^2 = 49 N",
      r1.dimension == Dimension(mass=1, length=1, time=-2)
      and approx(r1.to_value("N"), 49))

r2 = parse("1 N*m", test_reg)
check("1 N*m = 1 J",
      r2.dimension == Dimension(mass=1, length=2, time=-2)
      and approx(r2.to_value("J"), 1))

r3 = parse("6.674e-11 m^3/kg/s^2", test_reg)
check("6.674e-11 m^3/kg/s^2 量纲正确",
      r3.dimension == Dimension(length=3, mass=-1, time=-2))

r4 = parse("1000 kg/m^3", test_reg)
check("1000 kg/m^3 = 1 g/cm^3 (密度)",
      r4.dimension == Dimension(mass=1, length=-3)
      and approx(r4.to_value("g/cm^3"), 1))

r5 = parse("10 m/s^2 * 5 s", test_reg)
check("10 m/s^2 * 5 s = 50 m/s",
      r5.dimension == Dimension(length=1, time=-1)
      and approx(r5.value_base, 50))

# ═══════════════════════════════════════════════════════
# 2. 自定义单位与别名 API
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("2. 自定义单位与别名 API")
print("=" * 60)

reg2 = UnitRegistry()

print("\n  --- 表达式方式定义 ---")
u1 = reg2.define_unit("furlong", definition="220 yd")
check("define furlong = 220 yd", u1.dimension == Dimension(length=1))
check("1 furlong = 201.168 m", approx(Quantity(1, "furlong", reg2).to_value("m"), 201.168))

u2 = reg2.define_unit("day", definition="24 h")
check("define day = 24 h", u2.dimension == Dimension(time=1))
check("1 day = 86400 s", approx(Quantity(1, "day", reg2).to_value("s"), 86400))

u3 = reg2.define_unit("mph", definition="mi/h")
check("define mph = mi/h", u3.dimension == Dimension(length=1, time=-1))
check("60 mph ≈ 26.82 m/s", approx(Quantity(60, "mph", reg2).to_value("m/s"), 26.8224, rel=1e-4))

print("\n  --- 量纲+因子方式定义 ---")
u4 = reg2.define_unit("fortnight", name="两星期",
                      dimension=Dimension(time=1), factor=14 * 86400)
check("define fortnight", u4.dimension == Dimension(time=1))
check("1 fortnight = 14 day",
      approx(Quantity(1, "fortnight", reg2).to_value("day"), 14))

print("\n  --- 别名 ---")
reg2.alias("fur", "furlong")
check("alias fur → furlong", "fur" in reg2)
check("1 fur = 1 furlong",
      Quantity(1, "fur", reg2) == Quantity(1, "furlong", reg2))

print("\n  --- 重名检测 ---")
try:
    reg2.define_unit("m", definition="100 cm")
    check("重名应报错", False)
except UnitDefinitionError as e:
    check("重名报错 ✓", True, str(e)[:50])

print("\n  --- 别名重名检测 ---")
try:
    reg2.alias("km", "m")
    check("别名重名应报错", False)
except UnitDefinitionError as e:
    check("别名重名报错 ✓", True, str(e)[:50])

print("\n  --- 错误定义检测 ---")
try:
    reg2.define_unit("bad1", dimension=Dimension(length=1))  # 缺 factor
    check("缺 factor 应报错", False)
except UnitDefinitionError as e:
    check("缺 factor 报错 ✓", True, str(e)[:50])

print("\n  --- 删除单位 ---")
check("unregister('furlong')", reg2.unregister("furlong"))
check("'furlong' 已删除", "furlong" not in reg2)
check("别名 'fur' 也被删除", "fur" not in reg2)

print("\n  --- 定义后在表达式中使用 ---")
r_day = parse("3 day * 24 h/day", reg2)
check("3 day * 24 h/day = 72 h (运算后单位简化)",
      approx(r_day.value_base, 72 * 3600) and r_day.dimension == Dimension(time=1))

# ═══════════════════════════════════════════════════════
# 3. 表达式语法增强
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("3. 表达式语法增强")
print("=" * 60)

reg3 = UnitRegistry()

print("\n  --- 负数 ---")
n1 = parse("-5 m", reg3)
check("-5 m = -5 m", approx(n1.value_base, -5))

n2 = parse("-3.14 * 2 m", reg3)
check("-3.14 * 2 m = -6.28 m", approx(n2.value_base, -6.28))

print("\n  --- 负指数 ---")
ne1 = parse("m^-2", reg3)
check("m^-2 量纲 = L⁻²", ne1.dimension == Dimension(length=-2))

ne2 = parse("s^-1", reg3)
check("s^-1 量纲 = T⁻¹", ne2.dimension == Dimension(time=-1))

ne3 = parse("kg^-1 * m^3 * s^-2", reg3)
check("kg^-1*m^3*s^-2 量纲 = L³·M⁻¹·T⁻²",
      ne3.dimension == Dimension(length=3, mass=-1, time=-2))

print("\n  --- 括号里的单位幂 ---")
p1 = parse("(2 m)^3", reg3)
check("(2 m)^3 = 8 m³", approx(p1.value_base, 8) and p1.dimension == Dimension(length=3))

p2 = parse("(m/s)^2", reg3)
check("(m/s)^2 量纲 = L²·T⁻²", p2.dimension == Dimension(length=2, time=-2))

p3 = parse("2*(m/s)", reg3)
check("2*(m/s) = 2 m/s", approx(p3.value_base, 2) and p3.dimension == Dimension(length=1, time=-1))

print("\n  --- 隐式乘法 ---")
im1 = parse("2m", reg3)
check("2m = 2 m", approx(im1.value_base, 2) and im1.dimension == Dimension(length=1))

im2 = parse("3 kg m/s^2", reg3)
check("3 kg m/s^2 = 3 N",
      approx(im2.to_value("N"), 3) and im2.dimension == Dimension(mass=1, length=1, time=-2))

im3 = parse("10 kg 9.8 m/s^2", reg3)
check("10 kg 9.8 m/s^2 = 98 N", approx(im3.to_value("N"), 98))

im4 = parse("(1+2)m", reg3)
check("(1+2)m = 3 m", approx(im4.value_base, 3))

im5 = parse("2 (3 m)", reg3)
check("2 (3 m) = 6 m", approx(im5.value_base, 6))

# ═══════════════════════════════════════════════════════
# 4. 单位自动简化 (自动转 N, J, W)
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("4. 单位自动简化")
print("=" * 60)

reg4 = UnitRegistry()

s1 = parse("1 kg * 1 m / 1 s^2", reg4)
print(f"  1 kg * 1 m / 1 s^2 → {s1}")
check("kg·m/s² 自动简化为 N", "N" in repr(s1))

s2 = parse("1 N * 1 m", reg4)
print(f"  1 N * 1 m → {s2}")
check("N·m 自动简化为 J", "J" in repr(s2))

s3 = parse("1 J / 1 s", reg4)
print(f"  1 J / 1 s → {s3}")
check("J/s 自动简化为 W", "W" in repr(s3))

s4 = parse("1 N / 1 m^2", reg4)
print(f"  1 N / 1 m^2 → {s4}")
check("N/m² 自动简化为 Pa", "Pa" in repr(s4))

# ═══════════════════════════════════════════════════════
# 5. 量纲一致性校验增强
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("5. 量纲一致性校验")
print("=" * 60)

try:
    parse("5 m + 3 s")
    check("长度+时间 应报错", False)
except DimensionError as e:
    check("长度+时间 报错 ✓", True, "量纲不一致" in str(e))

try:
    parse("5 m to kg")
    check("长度→质量 应报错", False)
except DimensionError as e:
    check("长度→质量 报错 ✓", True, "量纲不一致" in str(e))

try:
    a = parse("10 m", reg)
    b = parse("5 s", reg)
    if a > b:
        pass
    check("长度>时间 比较应报错", False)
except DimensionError as e:
    check("长度>时间 比较报错 ✓", True)

try:
    parse("5 kg ^ 2 m")
    check("有量纲指数应报错", False)
except (DimensionError, ParseError) as e:
    check("有量纲指数 报错 ✓", True)

# ═══════════════════════════════════════════════════════
# 6. 错误提示友好性
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("6. 错误提示友好性")
print("=" * 60)

try:
    parse("5 m + ")
    check("表达式不完整 应报错", False)
except ParseError as e:
    check("表达式不完整 报错 ✓", True, "意外" in str(e))

try:
    parse("5 kg * 9.8 m/s^2 to foo")
    check("未知目标单位 应报错", False)
except KeyError as e:
    check("未知目标单位 报错 ✓", True, "foo" in str(e))

# ═══════════════════════════════════════════════════════
# 7. CLI 单次调用模式
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("7. CLI 单次调用模式")
print("=" * 60)

import subprocess
import os

os.environ["PYTHONIOENCODING"] = "utf-8"

test_cases = [
    ("5 kg * 9.8 m/s^2", "N", 49.0),
    ("100 C to K", "K", 373.15),
    ("100 km/h to m/s", "m/s", 100 / 3.6),
]

for expr, expected_unit, expected_val in test_cases:
    cmd = [sys.executable, "dimensional_engine.py", expr]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10,
                              encoding='utf-8', errors='replace')
        ok = result.returncode == 0 and "数值:" in result.stdout
        check(f"CLI: '{expr}' → exit={result.returncode}", ok,
              result.stderr if result.stderr else "")
        if ok and expected_val:
            try:
                output_val = float(result.stdout.split("数值:")[1].split()[0])
                check(f"  → 值 ≈ {expected_val}", approx(output_val, expected_val, rel=1e-4))
            except (IndexError, ValueError) as e:
                check(f"  → 值 ≈ {expected_val}", False, f"解析输出失败: {e}")
    except Exception as e:
        check(f"CLI: '{expr}' → 执行失败", False, str(e)[:50])

# ═══════════════════════════════════════════════════════
# 8. 综合物理计算
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("8. 综合物理计算")
print("=" * 60)

reg5 = UnitRegistry()

# 万有引力: F = G * m1 * m2 / r^2
G_expr = "6.674e-11 m^3/kg/s^2"
F_expr = f"({G_expr}) * 5.972e24 kg * 1 kg / (6.371e6 m)^2"
F = parse(F_expr, reg5)
print(f"  地表重力 = {F.to('N')}")
check("地表重力 ≈ 9.8 N", approx(F.to_value("N"), 9.8, rel=0.02))

# 动能: E = 1/2 m v^2
E = parse("0.5 * 1000 kg * (100 km/h)^2", reg5)
print(f"  1t 车以 100km/h 行驶的动能 = {E.to('J'):.6g}")
check("动能计算 量纲=能量", E.dimension == Dimension(mass=1, length=2, time=-2))

# 理想气体: PV = nRT → P = nRT/V
# 用 1 mol 理想气体在 0°C、22.4 L 下的压强
# 直接使用复合单位 J/(mol*K)，不需要额外定义
P_expr = "1 mol * 8.314 J/(mol*K) * 273.15 K / 0.0224 m^3"
P = parse(P_expr, reg5)
print(f"  标准状态理想气体压强 = {P.to('Pa'):.6g}")
check("理想气体压强 ≈ 1.01e5 Pa", approx(P.to_value("Pa"), 1.01325e5, rel=0.02))

# ═══════════════════════════════════════════════════════
# 9. 物理常数
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("9. 物理常数")
print("=" * 60)

reg6 = UnitRegistry()

# 检查常数已注册
consts = reg6.all_constants()
check(f"已注册 {len(consts)} 个物理常数", len(consts) >= 9)

# 测试万有引力常数
G = reg6.get_constant('G')
check(f"G 已注册: {G}", G is not None)
check("G 量纲正确", G.dimension == Dimension(length=3, mass=-1, time=-2))

# 测试光速
c = reg6.get_constant('c')
check(f"c 已注册: {c}", c is not None)
check("c 量纲正确", c.dimension == Dimension(length=1, time=-1))

# 测试在表达式中使用常数
F2 = parse("G * 5.972e24 kg * 1 kg / (6.371e6 m)^2", reg6)
check(f"G 在表达式中可用: {F2.to('N'):.4g} N", 
      approx(F2.to_value("N"), 9.8, rel=0.02))

# 测试 5 G 这种写法
result = parse("5 G", reg6)
check("5 G = 5 * G", approx(result.value_base, 5 * G.value_base, rel=1e-10))

# 测试质能方程
E2 = parse("1 kg * c^2", reg6)
check("E = mc² 量纲正确", E2.dimension == Dimension(mass=1, length=2, time=-2))
check("E = mc² 数值正确", approx(E2.to_value("J"), 8.98755e16, rel=0.01))

# 测试理想气体常数
P2 = parse("1 mol * R * 273.15 K / 0.0224 m^3", reg6)
check("R 在表达式中可用", approx(P2.to_value("Pa"), 1.01325e5, rel=0.02))

# ═══════════════════════════════════════════════════════
# 10. SI 前缀和新单位
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("10. SI 前缀和新单位")
print("=" * 60)

reg7 = UnitRegistry()

# 测试 SI 前缀
prefix_tests = [
    ("1 mm to m", 0.001),
    ("1 km to m", 1000),
    ("1 cm to m", 0.01),
    ("1 um to m", 1e-6),
    ("1 nm to m", 1e-9),
    ("1 ms to s", 0.001),
    ("1 us to s", 1e-6),
    ("1 ns to s", 1e-9),
    ("1 MHz to Hz", 1e6),
    ("1 GHz to Hz", 1e9),
    ("1 kW to W", 1000),
    ("1 MeV to eV", 1e6),
    ("1 GPa to Pa", 1e9),
]

for expr, expected in prefix_tests:
    try:
        result = parse(expr, reg7)
        val = result.value_base if '/' not in expr.split(' to ')[1] else result.value_base
        # 解析目标单位并转换
        target = expr.split(' to ')[1]
        converted = result.to_value(target)
        check(f"{expr} = {converted:.4g} {target}", approx(converted, expected, rel=1e-4))
    except Exception as e:
        check(f"{expr}", False, str(e)[:60])

# 测试新单位
new_unit_tests = [
    ("1 atm to Pa", 101325),
    ("1 bar to Pa", 1e5),
    ("1 mmHg to Pa", 133.322),
    ("1 torr to Pa", 133.322),
    ("1 psi to Pa", 6894.76),
    ("1 eV to J", 1.60218e-19),
    ("1 cal to J", 4.184),
    ("1 kcal to J", 4184),
    ("1 kWh to J", 3.6e6),
    ("1 AU to km", 1.49598e8),
    ("1 ly to km", 9.46073e12),
    ("1 pc to ly", 3.26156),
]

for expr, expected in new_unit_tests:
    try:
        target = expr.split(' to ')[1]
        result = parse(expr, reg7)
        converted = result.to_value(target)
        check(f"{expr} = {converted:.4g} {target}", approx(converted, expected, rel=1e-3))
    except Exception as e:
        check(f"{expr}", False, str(e)[:60])

# ═══════════════════════════════════════════════════════
# 11. 错误处理收紧
# ═══════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("11. 错误处理收紧")
print("=" * 60)

# 测试无效字符
try:
    parse("1 m @ 2 s", reg7)
    check("无效字符 @ 应报错", False, "没有报错")
except ParseError as e:
    check(f"无效字符 @ 报错: {e}", "无效字符" in str(e) or "@" in str(e))
except Exception as e:
    check(f"无效字符 @ 报错类型错误", False, str(e)[:60])

# 测试未知单位
try:
    parse("5 xyz", reg7)
    check("未知单位 xyz 应报错", False, "没有报错")
except (ParseError, KeyError) as e:
    check(f"未知单位 xyz 报错: {str(e)[:50]}", "xyz" in str(e))
except Exception as e:
    check(f"未知单位 xyz 报错类型错误", False, str(e)[:60])

# 测试夹杂奇怪符号
try:
    parse("1 m # 2 s", reg7)
    check("无效字符 # 应报错", False, "没有报错")
except ParseError as e:
    check(f"无效字符 # 报错: {e}", "无效字符" in str(e) or "#" in str(e))
except Exception as e:
    check(f"无效字符 # 报错类型错误", False, str(e)[:60])

# 测试 CLI 退出码
import subprocess
import sys

cli_tests = [
    ("1 m @ 2 s", 1),  # 无效字符，应返回 1
    ("5 xyz", 1),      # 未知单位，应返回 1
    ("1 m to kg", 1),  # 量纲不匹配，应返回 1
    ("1 m to xyz", 1), # 未知目标单位，应返回 1
    ("1 m", 0),        # 正确，应返回 0
]

for expr, expected_exit in cli_tests:
    try:
        result = subprocess.run(
            [sys.executable, 'dimensional_engine.py', expr],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=10
        )
        has_tb = "Traceback" in result.stdout or "Traceback" in result.stderr
        check(f"CLI: '{expr}' → exit={result.returncode}, tb={has_tb}",
              result.returncode == expected_exit and not has_tb)
    except Exception as e:
        check(f"CLI: '{expr}' 执行失败", False, str(e)[:60])

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

sys.exit(0 if FAIL == 0 else 1)
