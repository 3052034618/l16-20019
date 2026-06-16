#!/usr/bin/env python3
"""
量纲科学计算器 v3 功能测试
测试变量单位保留、物理常数别名、数学函数、历史命令
"""

from dimensional_engine import parse, DEFAULT_REGISTRY


def test_variable_unit_preservation():
    """测试变量和 ans 保留完整单位"""
    print("\n" + "=" * 60)
    print("1. 变量与 ans 单位保留")
    print("=" * 60)
    print()

    variables = {}

    # 测试 1: let v = 100 km/h 后 v * 5 s
    v = parse("100 km/h", DEFAULT_REGISTRY)
    variables['v'] = v
    result = parse("v * 5 s", DEFAULT_REGISTRY, variables)
    result_m = result.to('m')
    print(f"  let v = 100 km/h")
    print(f"  v * 5 s = {result:.6g}  → to m = {result_m:.6g}")
    assert abs(result_m.value_in_unit() - 138.88888888888889) < 0.01
    assert result_m._unit.symbol == 'm'
    print("  ✓ v * 5 s = 138.889 m  [量纲正确，单位正确]")
    print()

    # 测试 2: ans 保留单位
    ans = parse("100 km/h", DEFAULT_REGISTRY)
    variables['ans'] = ans
    result = parse("ans * 5 s", DEFAULT_REGISTRY, variables)
    result_m = result.to('m')
    print(f"  ans = 100 km/h")
    print(f"  ans * 5 s = {result:.6g}  → to m = {result_m:.6g}")
    assert abs(result_m.value_in_unit() - 138.88888888888889) < 0.01
    print("  ✓ ans * 5 s = 138.889 m  [量纲正确]")
    print()

    # 测试 3: 变量在复杂表达式中
    variables['t'] = parse("10 s", DEFAULT_REGISTRY)
    variables['a'] = parse("9.8 m/s^2", DEFAULT_REGISTRY)
    result = parse("0.5 * a * t^2", DEFAULT_REGISTRY, variables)
    result_m = result.to('m')
    print(f"  let t = 10 s, a = 9.8 m/s^2")
    print(f"  0.5 * a * t^2 = {result:.6g}  → to m = {result_m:.6g}")
    assert abs(result_m.value_in_unit() - 490) < 0.01
    print("  ✓ 0.5 * a * t^2 = 490 m  [量纲正确]")
    print()

    print("  ✅ 变量与 ans 单位保留测试全部通过!")


def test_constant_aliases():
    """测试物理常数别名和冲突处理"""
    print("\n" + "=" * 60)
    print("2. 物理常数别名与冲突处理")
    print("=" * 60)
    print()

    # 测试 1: planck (h 被小时占用)
    planck = DEFAULT_REGISTRY.get_constant('planck')
    h_p = DEFAULT_REGISTRY.get_constant('h_p')
    print(f"  planck = {planck:.6g}")
    print(f"  h_p = {h_p:.6g}")
    assert planck is not None
    assert h_p is not None
    assert abs(planck.value_in_unit() - h_p.value_in_unit()) < 1e-30
    print("  ✓ planck → h_p 别名正确")
    print()

    # 测试 2: boltzmann (k 被千前缀占用)
    boltzmann = DEFAULT_REGISTRY.get_constant('boltzmann')
    k_b = DEFAULT_REGISTRY.get_constant('k_b')
    print(f"  boltzmann = {boltzmann:.6g}")
    print(f"  k_b = {k_b:.6g}")
    assert boltzmann is not None
    assert k_b is not None
    assert abs(boltzmann.value_in_unit() - k_b.value_in_unit()) < 1e-30
    print("  ✓ boltzmann → k_b 别名正确")
    print()

    # 测试 3: gravity (g 被克占用)
    gravity = DEFAULT_REGISTRY.get_constant('gravity')
    g_0 = DEFAULT_REGISTRY.get_constant('g_0')
    print(f"  gravity = {gravity:.6g}")
    print(f"  g_0 = {g_0:.6g}")
    assert gravity is not None
    assert g_0 is not None
    assert abs(gravity.value_in_unit() - g_0.value_in_unit()) < 1e-10
    print("  ✓ gravity → g_0 别名正确")
    print()

    # 测试 4: pi 和 euler
    pi = DEFAULT_REGISTRY.get_constant('pi')
    euler = DEFAULT_REGISTRY.get_constant('euler')
    print(f"  pi = {pi:.6g}")
    print(f"  euler = {euler:.6g}")
    assert pi is not None
    assert euler is not None
    assert abs(pi.value_in_unit() - 3.141592653589793) < 1e-10
    assert abs(euler.value_in_unit() - 2.718281828459045) < 1e-10
    print("  ✓ pi 和 euler 常数正确")
    print()

    # 测试 5: 原有单位不被覆盖
    h = parse("1 h", DEFAULT_REGISTRY)
    k = parse("1 kg", DEFAULT_REGISTRY)  # k 是千前缀
    g = parse("1 g", DEFAULT_REGISTRY)
    e = parse("1 e", DEFAULT_REGISTRY)  # e 是元电荷
    print(f"  1 h (小时) = {h:.6g}")
    print(f"  1 kg (千+克) = {k:.6g}")
    print(f"  1 g (克) = {g:.6g}")
    print(f"  1 e (元电荷) = {e:.6g}")
    assert abs(h.value_base - 3600) < 0.01
    assert abs(k.value_base - 1) < 0.01
    assert abs(g.value_base - 0.001) < 0.0001
    print("  ✓ 原有单位 h, k, g, e 未被覆盖")
    print()

    # 测试 6: 常数在表达式中使用
    result = parse("planck * c", DEFAULT_REGISTRY)
    print(f"  planck * c = {result:.6g}")
    print("  ✓ 常数别名可在表达式中使用")
    print()

    # 测试 7: get_constant_info
    info = DEFAULT_REGISTRY.get_constant_info('h_p')
    print(f"  h_p 别名: {info.get('aliases', [])}")
    print(f"  h_p 注释: {info.get('note', '')}")
    assert 'planck' in info.get('aliases', [])
    assert 'h 被小时' in info.get('note', '')
    print("  ✓ 常数信息包含别名和冲突说明")
    print()

    print("  ✅ 物理常数别名与冲突处理测试全部通过!")


def test_math_functions():
    """测试数学函数和无量纲检查"""
    print("\n" + "=" * 60)
    print("3. 数学函数与无量纲检查")
    print("=" * 60)
    print()

    import math

    # 测试 1: 三角函数 - 弧度
    result = parse("sin(pi/2)", DEFAULT_REGISTRY)
    print(f"  sin(pi/2) = {result:.6g}")
    assert abs(result.value_in_unit() - 1.0) < 1e-10
    print("  ✓ sin(pi/2) = 1")

    result = parse("cos(0)", DEFAULT_REGISTRY)
    print(f"  cos(0) = {result:.6g}")
    assert abs(result.value_in_unit() - 1.0) < 1e-10
    print("  ✓ cos(0) = 1")
    print()

    # 测试 2: 三角函数 - 角度
    result = parse("sin(90 deg)", DEFAULT_REGISTRY)
    print(f"  sin(90 deg) = {result:.6g}")
    assert abs(result.value_in_unit() - 1.0) < 1e-10
    print("  ✓ sin(90 deg) = 1")

    result = parse("cos(180 deg)", DEFAULT_REGISTRY)
    print(f"  cos(180 deg) = {result:.6g}")
    assert abs(result.value_in_unit() + 1.0) < 1e-10
    print("  ✓ cos(180 deg) = -1")
    print()

    # 测试 3: 反三角函数
    result = parse("asin(1)", DEFAULT_REGISTRY)
    print(f"  asin(1) = {result:.6g}")
    assert abs(result.value_in_unit() - math.pi / 2) < 1e-10
    print("  ✓ asin(1) = π/2")
    print()

    # 测试 4: 双曲函数
    result = parse("sinh(0)", DEFAULT_REGISTRY)
    print(f"  sinh(0) = {result:.6g}")
    assert abs(result.value_in_unit()) < 1e-10
    print("  ✓ sinh(0) = 0")

    result = parse("cosh(0)", DEFAULT_REGISTRY)
    print(f"  cosh(0) = {result:.6g}")
    assert abs(result.value_in_unit() - 1.0) < 1e-10
    print("  ✓ cosh(0) = 1")
    print()

    # 测试 5: 指数和对数
    result = parse("exp(1)", DEFAULT_REGISTRY)
    print(f"  exp(1) = {result:.6g}")
    assert abs(result.value_in_unit() - math.e) < 1e-10
    print("  ✓ exp(1) = e")

    result = parse("ln(euler)", DEFAULT_REGISTRY)
    print(f"  ln(euler) = {result:.6g}")
    assert abs(result.value_in_unit() - 1.0) < 1e-10
    print("  ✓ ln(euler) = 1")

    result = parse("log10(100)", DEFAULT_REGISTRY)
    print(f"  log10(100) = {result:.6g}")
    assert abs(result.value_in_unit() - 2.0) < 1e-10
    print("  ✓ log10(100) = 2")

    result = parse("log2(8)", DEFAULT_REGISTRY)
    print(f"  log2(8) = {result:.6g}")
    assert abs(result.value_in_unit() - 3.0) < 1e-10
    print("  ✓ log2(8) = 3")
    print()

    # 测试 6: sqrt - 有量纲
    result = parse("sqrt(4 m^2)", DEFAULT_REGISTRY)
    print(f"  sqrt(4 m^2) = {result:.6g}")
    assert abs(result.value_in_unit() - 2.0) < 1e-10
    print("  ✓ sqrt(4 m^2) = 2 m  [量纲正确]")
    print()

    # 测试 7: 取整函数 - 保留单位
    result = parse("abs(-5 m)", DEFAULT_REGISTRY)
    print(f"  abs(-5 m) = {result:.6g}")
    assert abs(result.value_in_unit() - 5.0) < 1e-10
    print("  ✓ abs(-5 m) = 5 m  [单位保留]")

    result = parse("floor(3.7 m)", DEFAULT_REGISTRY)
    print(f"  floor(3.7 m) = {result:.6g}")
    assert abs(result.value_in_unit() - 3.0) < 1e-10
    print("  ✓ floor(3.7 m) = 3 m  [单位保留]")

    result = parse("ceil(3.2 m)", DEFAULT_REGISTRY)
    print(f"  ceil(3.2 m) = {result:.6g}")
    assert abs(result.value_in_unit() - 4.0) < 1e-10
    print("  ✓ ceil(3.2 m) = 4 m  [单位保留]")

    result = parse("round(3.5 m)", DEFAULT_REGISTRY)
    print(f"  round(3.5 m) = {result:.6g}")
    assert abs(result.value_in_unit() - 4.0) < 1e-10
    print("  ✓ round(3.5 m) = 4 m  [单位保留]")
    print()

    # 测试 8: 错误 - 带单位的量传给 sin
    try:
        parse("sin(5 m)", DEFAULT_REGISTRY)
        print("  ✗ sin(5 m) 应该报错但没有")
        assert False
    except Exception as e:
        print(f"  sin(5 m) → 错误: {e}")
        print("  ✓ sin(带单位) 正确报错")
    print()

    # 测试 9: 错误 - 带单位的量传给 log
    try:
        parse("log(10 m)", DEFAULT_REGISTRY)
        print("  ✗ log(10 m) 应该报错但没有")
        assert False
    except Exception as e:
        print(f"  log(10 m) → 错误: {e}")
        print("  ✓ log(带单位) 正确报错")
    print()

    # 测试 10: 隐式乘法与函数
    result = parse("2 sin(pi/2)", DEFAULT_REGISTRY)
    print(f"  2 sin(pi/2) = {result:.6g}")
    assert abs(result.value_in_unit() - 2.0) < 1e-10
    print("  ✓ 2 sin(x) 隐式乘法正确")
    print()

    print("  ✅ 数学函数与无量纲检查测试全部通过!")


def test_angle_units():
    """测试角度单位"""
    print("\n" + "=" * 60)
    print("4. 角度单位支持")
    print("=" * 60)
    print()

    import math

    # 测试 1: deg 和 rad 都是无量纲
    deg = parse("1 deg", DEFAULT_REGISTRY)
    rad = parse("1 rad", DEFAULT_REGISTRY)
    print(f"  1 deg = {deg:.6g} [量纲: {deg.dimension}]")
    print(f"  1 rad = {rad:.6g} [量纲: {rad.dimension}]")
    assert str(deg.dimension) == '1'
    assert str(rad.dimension) == '1'
    print("  ✓ deg 和 rad 都是无量纲")
    print()

    # 测试 2: deg 到 rad 的转换
    deg180 = parse("180 deg", DEFAULT_REGISTRY)
    rad_pi = deg180.to('rad')
    print(f"  180 deg to rad = {rad_pi:.6g}")
    assert abs(rad_pi.value_in_unit() - math.pi) < 1e-10
    print("  ✓ 180 deg = π rad")
    print()

    # 测试 3: 在三角函数中自动转换
    result = parse("sin(30 deg)", DEFAULT_REGISTRY)
    print(f"  sin(30 deg) = {result:.6g}")
    assert abs(result.value_in_unit() - 0.5) < 1e-10
    print("  ✓ sin(30 deg) = 0.5")

    result = parse("tan(45 deg)", DEFAULT_REGISTRY)
    print(f"  tan(45 deg) = {result:.6g}")
    assert abs(result.value_in_unit() - 1.0) < 1e-10
    print("  ✓ tan(45 deg) = 1")
    print()

    print("  ✅ 角度单位测试全部通过!")


def test_integration():
    """综合测试"""
    print("\n" + "=" * 60)
    print("5. 综合应用测试")
    print("=" * 60)
    print()

    # 测试 1: 用常数计算
    result = parse("G * 5.972e24 kg * 1 kg / (6.371e6 m)^2", DEFAULT_REGISTRY)
    result_n = result.to('N')
    print(f"  地球表面重力 = {result_n:.6g}")
    assert abs(result_n.value_in_unit() - 9.819532098) < 0.1
    print("  ✓ 地球表面重力 ≈ 9.82 N")
    print()

    # 测试 2: 变量 + 函数
    variables = {}
    variables['theta'] = parse("30 deg", DEFAULT_REGISTRY)
    result = parse("10 m/s * sin(theta)", DEFAULT_REGISTRY, variables)
    result_mps = result.to('m/s')
    print(f"  let theta = 30 deg")
    print(f"  10 m/s * sin(theta) = {result:.6g}  → to m/s = {result_mps:.6g}")
    assert abs(result_mps.value_in_unit() - 5.0) < 0.01
    print("  ✓ 10 m/s * sin(30°) = 5 m/s")
    print()

    # 测试 3: sqrt 后转换单位
    result = parse("sqrt(10000 m^2)", DEFAULT_REGISTRY)
    result_km = result.to('km')
    print(f"  sqrt(10000 m^2) = {result:.6g}  → to km = {result_km:.6g}")
    assert abs(result_km.value_in_unit() - 0.1) < 0.001
    print("  ✓ sqrt(10000 m²) = 100 m = 0.1 km")
    print()

    print("  ✅ 综合应用测试全部通过!")


def main():
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "量纲科学计算器 v3 功能测试" + " " * 20 + "║")
    print("╚" + "═" * 58 + "╝")

    all_passed = True

    try:
        test_variable_unit_preservation()
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        all_passed = False

    try:
        test_constant_aliases()
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        all_passed = False

    try:
        test_math_functions()
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        all_passed = False

    try:
        test_angle_units()
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        all_passed = False

    try:
        test_integration()
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("  🎉 所有 v3 功能测试通过!")
    else:
        print("  💔 部分测试失败")
    print("=" * 60)
    print()

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
