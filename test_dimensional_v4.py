#!/usr/bin/env python3
"""
量纲科学计算器 v4 功能测试
测试多参数函数、非基本单位函数结果、变量赋值修复、表达式保存
"""

import math
from dimensional_engine import parse, DEFAULT_REGISTRY, DimensionError


def test_multi_arg_functions():
    print("\n" + "=" * 60)
    print("1. 多参数函数 (min, max, pow, hypot)")
    print("=" * 60)
    print()

    # min/max 同量纲
    result = parse("min(3 m, 5 m)", DEFAULT_REGISTRY)
    print(f"  min(3 m, 5 m) = {result:.6g}")
    assert abs(result.value_in_unit() - 3.0) < 1e-10
    print("  ✓ min(3 m, 5 m) = 3 m")

    result = parse("max(3 m, 5 m)", DEFAULT_REGISTRY)
    print(f"  max(3 m, 5 m) = {result:.6g}")
    assert abs(result.value_in_unit() - 5.0) < 1e-10
    print("  ✓ max(3 m, 5 m) = 5 m")
    print()

    # min/max 不同量纲应该报错
    try:
        parse("min(3 m, 5 s)", DEFAULT_REGISTRY)
        assert False, "min(3 m, 5 s) 应该报错"
    except DimensionError as e:
        print(f"  min(3 m, 5 s) → 错误: {e}")
        print("  ✓ 不同量纲比较正确报错")
    print()

    # min/max 混合单位 (km vs m)
    result = parse("max(1 km, 500 m)", DEFAULT_REGISTRY)
    result_m = result.to('m')
    print(f"  max(1 km, 500 m) = {result:.6g}  → to m = {result_m:.6g}")
    assert abs(result_m.value_in_unit() - 1000) < 0.01
    print("  ✓ max(1 km, 500 m) = 1000 m")
    print()

    # pow(base, exp)
    result = parse("pow(2, 3)", DEFAULT_REGISTRY)
    print(f"  pow(2, 3) = {result:.6g}")
    assert abs(result.value_in_unit() - 8.0) < 1e-10
    print("  ✓ pow(2, 3) = 8")

    result = parse("pow(2 m, 3)", DEFAULT_REGISTRY)
    print(f"  pow(2 m, 3) = {result:.6g}")
    assert abs(result.value_in_unit() - 8.0) < 1e-10
    print("  ✓ pow(2 m, 3) = 8 m^3")
    print()

    # pow 带量纲指数应该报错
    try:
        parse("pow(2, 3 m)", DEFAULT_REGISTRY)
        assert False, "pow(2, 3 m) 应该报错"
    except DimensionError as e:
        print(f"  pow(2, 3 m) → 错误: {e}")
        print("  ✓ pow 指数带单位正确报错")
    print()

    # hypot
    result = parse("hypot(3 m, 4 m)", DEFAULT_REGISTRY)
    print(f"  hypot(3 m, 4 m) = {result:.6g}")
    assert abs(result.value_in_unit() - 5.0) < 1e-10
    print("  ✓ hypot(3 m, 4 m) = 5 m")

    result = parse("hypot(3 km, 4 km)", DEFAULT_REGISTRY)
    result_m = result.to('m')
    print(f"  hypot(3 km, 4 km) = {result:.6g}  → to m = {result_m:.6g}")
    assert abs(result_m.value_in_unit() - 5000) < 0.01
    print("  ✓ hypot(3 km, 4 km) = 5000 m")
    print()

    # hypot 不同量纲应该报错
    try:
        parse("hypot(3 m, 4 s)", DEFAULT_REGISTRY)
        assert False, "hypot(3 m, 4 s) 应该报错"
    except DimensionError as e:
        print(f"  hypot(3 m, 4 s) → 错误: {e}")
        print("  ✓ hypot 不同量纲正确报错")
    print()

    print("  ✅ 多参数函数测试全部通过!")


def test_non_base_unit_functions():
    print("\n" + "=" * 60)
    print("2. 非基本单位函数结果")
    print("=" * 60)
    print()

    # sqrt(100 cm^2) → 10 cm → to m = 0.1 m
    result = parse("sqrt(100 cm^2)", DEFAULT_REGISTRY)
    result_m = result.to('m')
    print(f"  sqrt(100 cm^2) = {result:.6g}  → to m = {result_m:.6g}")
    assert abs(result_m.value_in_unit() - 0.1) < 0.001
    print("  ✓ sqrt(100 cm²) = 10 cm = 0.1 m")
    print()

    # abs(-5 cm) → 5 cm
    result = parse("abs(-5 cm)", DEFAULT_REGISTRY)
    print(f"  abs(-5 cm) = {result:.6g}")
    assert abs(result.value_in_unit() - 5.0) < 1e-10
    result_m = result.to('m')
    assert abs(result_m.value_in_unit() - 0.05) < 0.0001
    print(f"  abs(-5 cm) → to m = {result_m:.6g}")
    print("  ✓ abs(-5 cm) = 5 cm, to m = 0.05 m")
    print()

    # floor(3.7 km)
    result = parse("floor(3.7 km)", DEFAULT_REGISTRY)
    print(f"  floor(3.7 km) = {result:.6g}")
    assert abs(result.value_in_unit() - 3.0) < 1e-10
    result_m = result.to('m')
    assert abs(result_m.value_in_unit() - 3000) < 0.01
    print(f"  floor(3.7 km) → to m = {result_m:.6g}")
    print("  ✓ floor(3.7 km) = 3 km = 3000 m")
    print()

    # ceil(3.2 ms) → 4 ms
    result = parse("ceil(3.2 ms)", DEFAULT_REGISTRY)
    print(f"  ceil(3.2 ms) = {result:.6g}")
    assert abs(result.value_in_unit() - 4.0) < 1e-10
    result_s = result.to('s')
    assert abs(result_s.value_in_unit() - 0.004) < 0.00001
    print(f"  ceil(3.2 ms) → to s = {result_s:.6g}")
    print("  ✓ ceil(3.2 ms) = 4 ms = 0.004 s")
    print()

    # min/max with non-base units
    result = parse("min(2 km, 3000 m)", DEFAULT_REGISTRY)
    result_m = result.to('m')
    print(f"  min(2 km, 3000 m) = {result:.6g}  → to m = {result_m:.6g}")
    assert abs(result_m.value_in_unit() - 2000) < 0.01
    print("  ✓ min(2 km, 3000 m) = 2000 m")
    print()

    print("  ✅ 非基本单位函数结果测试全部通过!")


def test_sqrt_unit_derivation():
    print("\n" + "=" * 60)
    print("3. sqrt 单位推导")
    print("=" * 60)
    print()

    # sqrt(4 m^2) → 2 m
    result = parse("sqrt(4 m^2)", DEFAULT_REGISTRY)
    print(f"  sqrt(4 m^2) = {result:.6g}")
    assert abs(result.value_in_unit() - 2.0) < 1e-10
    print("  ✓ sqrt(4 m²) = 2 m")

    # sqrt(10000 m^2) → 100 m → to km = 0.1 km
    result = parse("sqrt(10000 m^2)", DEFAULT_REGISTRY)
    result_km = result.to('km')
    print(f"  sqrt(10000 m^2) = {result:.6g}  → to km = {result_km:.6g}")
    assert abs(result_km.value_in_unit() - 0.1) < 0.001
    print("  ✓ sqrt(10000 m²) = 100 m = 0.1 km")

    # sqrt(9 s^2) → 3 s
    result = parse("sqrt(9 s^2)", DEFAULT_REGISTRY)
    print(f"  sqrt(9 s^2) = {result:.6g}")
    assert abs(result.value_in_unit() - 3.0) < 1e-10
    print("  ✓ sqrt(9 s²) = 3 s")

    # sqrt(16 N^2) → 4 N
    result = parse("sqrt(16 N^2)", DEFAULT_REGISTRY)
    print(f"  sqrt(16 N^2) = {result:.6g}")
    assert abs(result.value_in_unit() - 4.0) < 1e-10
    print("  ✓ sqrt(16 N²) = 4 N")
    print()

    print("  ✅ sqrt 单位推导测试全部通过!")


def test_variable_assignment_smooth():
    print("\n" + "=" * 60)
    print("4. 变量赋值顺滑性")
    print("=" * 60)
    print()

    # let v = 100 km/h
    variables = {}
    v = parse("100 km/h", DEFAULT_REGISTRY, variables)
    variables['v'] = v
    result = parse("v * 5 s", DEFAULT_REGISTRY, variables)
    result_m = result.to('m')
    print(f"  let v = 100 km/h → v * 5 s to m = {result_m:.6g}")
    assert abs(result_m.value_in_unit() - 138.889) < 0.01
    print("  ✓ v * 5 s = 138.889 m")
    print()

    # v = 200 km/h (重新赋值)
    v2 = parse("200 km/h", DEFAULT_REGISTRY, variables)
    variables['v'] = v2
    result = parse("v * 5 s", DEFAULT_REGISTRY, variables)
    result_m = result.to('m')
    print(f"  v = 200 km/h → v * 5 s to m = {result_m:.6g}")
    assert abs(result_m.value_in_unit() - 277.778) < 0.01
    print("  ✓ 变量重新赋值后正确更新")
    print()

    # ans 在表达式中
    ans = parse("50 km/h", DEFAULT_REGISTRY)
    variables['ans'] = ans
    result = parse("ans * 2", DEFAULT_REGISTRY, variables)
    print(f"  ans = 50 km/h → ans * 2 = {result:.6g}")
    result_kmh = result.to('km/h')
    assert abs(result_kmh.value_in_unit() - 100) < 0.01
    print("  ✓ ans 在表达式中可用")
    print()

    print("  ✅ 变量赋值顺滑性测试全部通过!")


def test_comma_in_expressions():
    print("\n" + "=" * 60)
    print("5. 逗号分隔参数解析")
    print("=" * 60)
    print()

    # 基本逗号分隔
    result = parse("min(1, 2)", DEFAULT_REGISTRY)
    print(f"  min(1, 2) = {result:.6g}")
    assert abs(result.value_in_unit() - 1.0) < 1e-10
    print("  ✓ min(1, 2) = 1")

    # 嵌套函数
    result = parse("max(sin(0), cos(0))", DEFAULT_REGISTRY)
    print(f"  max(sin(0), cos(0)) = {result:.6g}")
    assert abs(result.value_in_unit() - 1.0) < 1e-10
    print("  ✓ max(sin(0), cos(0)) = 1")

    # 表达式参数
    result = parse("min(2 * 3 m, 5 m + 2 m)", DEFAULT_REGISTRY)
    print(f"  min(2*3 m, 5m+2m) = {result:.6g}")
    assert abs(result.value_in_unit() - 6.0) < 1e-10
    print("  ✓ min(6 m, 7 m) = 6 m")
    print()

    print("  ✅ 逗号分隔参数解析测试全部通过!")


def test_pow_function():
    print("\n" + "=" * 60)
    print("6. pow 函数详细测试")
    print("=" * 60)
    print()

    # pow(2, 10) = 1024
    result = parse("pow(2, 10)", DEFAULT_REGISTRY)
    print(f"  pow(2, 10) = {result:.6g}")
    assert abs(result.value_in_unit() - 1024) < 0.01
    print("  ✓ pow(2, 10) = 1024")

    # pow(10, -2) = 0.01
    result = parse("pow(10, -2)", DEFAULT_REGISTRY)
    print(f"  pow(10, -2) = {result:.6g}")
    assert abs(result.value_in_unit() - 0.01) < 1e-10
    print("  ✓ pow(10, -2) = 0.01")

    # pow(3 m, 2) = 9 m^2
    result = parse("pow(3 m, 2)", DEFAULT_REGISTRY)
    print(f"  pow(3 m, 2) = {result:.6g}")
    assert abs(result.value_in_unit() - 9.0) < 1e-10
    print("  ✓ pow(3 m, 2) = 9 m²")

    # pow(2 m, 0.5) ≈ sqrt(2) m^0.5
    result = parse("pow(4 m, 0.5)", DEFAULT_REGISTRY)
    print(f"  pow(4 m, 0.5) = {result:.6g}")
    assert abs(result.value_in_unit() - 2.0) < 1e-10
    print("  ✓ pow(4 m, 0.5) = 2 m^0.5")
    print()

    print("  ✅ pow 函数测试全部通过!")


def test_simplify_no_false_match():
    print("\n" + "=" * 60)
    print("7. simplify() 不再乱匹配单位")
    print("=" * 60)
    print()

    # 100 km/h * 5 s 不应变成 kn
    v = parse("100 km/h", DEFAULT_REGISTRY)
    variables = {'v': v}
    result = parse("v * 5 s", DEFAULT_REGISTRY, variables)
    result_m = result.to('m')
    print(f"  100 km/h * 5 s = {result:.6g}  → to m = {result_m:.6g}")
    assert abs(result_m.value_in_unit() - 138.889) < 0.01
    print("  ✓ km/h * s 结果正确转为 m")

    # sin(30 deg) * 10 m/s 不应变成 kn
    variables2 = {'theta': parse("30 deg", DEFAULT_REGISTRY)}
    result = parse("10 m/s * sin(theta)", DEFAULT_REGISTRY, variables2)
    result_mps = result.to('m/s')
    print(f"  10 m/s * sin(30 deg) = {result:.6g}  → to m/s = {result_mps:.6g}")
    assert abs(result_mps.value_in_unit() - 5.0) < 0.01
    print("  ✓ sin 结果 * 速度 正确转为 m/s")
    print()

    print("  ✅ simplify 不乱匹配测试全部通过!")


def main():
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "量纲科学计算器 v4 功能测试" + " " * 20 + "║")
    print("╚" + "═" * 58 + "╝")

    all_passed = True

    tests = [
        test_multi_arg_functions,
        test_non_base_unit_functions,
        test_sqrt_unit_derivation,
        test_variable_assignment_smooth,
        test_comma_in_expressions,
        test_pow_function,
        test_simplify_no_false_match,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            import traceback
            print(f"  ✗ 测试失败: {e}")
            traceback.print_exc()
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("  🎉 所有 v4 功能测试通过!")
    else:
        print("  💔 部分测试失败")
    print("=" * 60)
    print()

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
