from dimensional_engine import DEFAULT_REGISTRY, parse_unit_symbol

# 手动调试
print('=== 调试 ms ===')
print(f's 在 _units 中: {"s" in DEFAULT_REGISTRY._units}')
print(f'm 在 _SI_PREFIXES 中: {"m" in DEFAULT_REGISTRY._SI_PREFIXES}')
print(f'前缀 m 的值: {DEFAULT_REGISTRY._SI_PREFIXES.get("m")}')

# 手动调用 parse_unit_symbol
result = parse_unit_symbol('ms', DEFAULT_REGISTRY)
print(f'parse_unit_symbol("ms") 返回: {result}')

if result:
    print(f'  name: {result.name}')
    print(f'  symbol: {result.symbol}')
    print(f'  factor: {result.factor}')

# 看看 ms 是否被解析为 m*s
print()
print('=== 看看 UnitSymbolParser 如何解析 ms ===')
from dimensional_engine import UnitSymbolParser
parser = UnitSymbolParser('ms', DEFAULT_REGISTRY)
try:
    result2 = parser.parse()
    print(f'UnitSymbolParser 解析结果: {result2}')
except Exception as e:
    print(f'UnitSymbolParser 错误: {e}')

# 现在试试在 parse_unit_symbol 中先打印一些调试信息
print()
print('=== 测试 registry.get("ms") ===')
result3 = DEFAULT_REGISTRY.get('ms')
print(f'get("ms") 返回: {result3}')
