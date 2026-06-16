"""
量纲分析与单位换算引擎 (增强版)
================================
支持基本量纲及其组合、量纲一致性校验、带单位的表达式解析。

核心改进
--------
- 完整的复合单位解析: m/s^2, m^3/kg/s^2, N*m, (m/s)^2, s^-2
- 自定义单位与别名注册 API，带详细错误提示
- 表达式语法增强: 负数、负指数、隐式乘法(2m, 3 kg m/s^2)
- 命令行交互界面
"""

from __future__ import annotations

import math
import re
import sys
from fractions import Fraction
from typing import Dict, List, Optional, Sequence, Tuple, Union

BASE_DIM_NAMES = ("length", "mass", "time", "temperature", "current", "amount", "luminosity")
BASE_DIM_SYMBOLS = ("L", "M", "T", "Θ", "I", "N", "J")
_DIM_INDEX = {name: i for i, name in enumerate(BASE_DIM_NAMES)}


# ─────────────────────────────────────────────
# 异常类型
# ─────────────────────────────────────────────
class DimensionError(Exception):
    """量纲不一致时抛出的异常。"""
    pass


class UnitDefinitionError(Exception):
    """单位定义错误时抛出的异常。"""
    pass


class ParseError(Exception):
    """表达式解析错误时抛出的异常。"""
    pass


# ─────────────────────────────────────────────
# Dimension - 量纲的指数向量表示
# ─────────────────────────────────────────────
class Dimension:
    """
    用 7 维指数向量表示物理量纲，分量为 Fraction 保证精确运算。
    """
    __slots__ = ("_exponents",)

    def __init__(self, **powers: Union[int, float, Fraction, str]):
        exps = [Fraction(0)] * len(BASE_DIM_NAMES)
        for name, power in powers.items():
            if name not in _DIM_INDEX:
                raise ValueError(f"未知量纲: {name}")
            exps[_DIM_INDEX[name]] = Fraction(power)
        self._exponents = tuple(exps)

    @classmethod
    def from_vector(cls, vector: Sequence) -> "Dimension":
        obj = object.__new__(cls)
        obj._exponents = tuple(Fraction(v) for v in vector)
        return obj

    @property
    def exponents(self) -> Tuple[Fraction, ...]:
        return self._exponents

    def is_dimensionless(self) -> bool:
        return all(e == 0 for e in self._exponents)

    def __mul__(self, other: "Dimension") -> "Dimension":
        return Dimension.from_vector(a + b for a, b in zip(self._exponents, other._exponents))

    def __truediv__(self, other: "Dimension") -> "Dimension":
        return Dimension.from_vector(a - b for a, b in zip(self._exponents, other._exponents))

    def __pow__(self, n: Union[int, float, Fraction]) -> "Dimension":
        n = Fraction(n)
        return Dimension.from_vector(e * n for e in self._exponents)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Dimension):
            return NotImplemented
        return self._exponents == other._exponents

    def __hash__(self) -> int:
        return hash(self._exponents)

    def __repr__(self) -> str:
        parts = []
        for sym, exp in zip(BASE_DIM_SYMBOLS, self._exponents):
            if exp != 0:
                if exp == 1:
                    parts.append(sym)
                else:
                    parts.append(f"{sym}^{exp}")
        return "·".join(parts) if parts else "1"

    def __str__(self) -> str:
        return self.__repr__()


DIMENSIONLESS = Dimension()


# ─────────────────────────────────────────────
# UnitDef - 单位定义
# ─────────────────────────────────────────────
class UnitDef:
    """
    单位定义。

    Attributes
    ----------
    name : str       单位全名 (如 "meter")
    symbol : str     单位符号 (如 "m")
    dimension : Dimension  对应量纲
    factor : float   换算因子: 1 此单位 = factor 个基本单位
    offset : float   偏移量: value_base = (value_this + offset) * factor
                     用于摄氏/华氏等带零点偏移的换算
    """
    __slots__ = ("name", "symbol", "dimension", "factor", "offset")

    def __init__(
        self,
        name: str,
        symbol: str,
        dimension: Dimension,
        factor: float = 1.0,
        offset: float = 0.0,
    ):
        self.name = name
        self.symbol = symbol
        self.dimension = dimension
        self.factor = factor
        self.offset = offset

    def to_base(self, value: float) -> float:
        return (value + self.offset) * self.factor

    def from_base(self, value_base: float) -> float:
        return value_base / self.factor - self.offset

    def __repr__(self) -> str:
        return f"UnitDef({self.symbol!r}, {self.dimension})"


# ─────────────────────────────────────────────
# UnitSymbolParser - 解析复合单位符号 (m/s^2, kg*m/s^2 等)
# ─────────────────────────────────────────────
_UNIT_TOKEN_RE = re.compile(r"""
    (?P<UNIT>[a-zA-Z][a-zA-Z0-9_°]*) |
    (?P<OP>[*/^()]) |
    (?P<NUMBER>-?\d+\.?\d*(?:[eE][+-]?\d+)?) |
    (?P<WS>\s+)
""", re.VERBOSE)


class UnitSymbolParser:
    """
    专用的单位符号解析器。

    文法:
      unit_expr = unit_term (('*' | '/') unit_term)*
      unit_term = unit_atom ('^' number)?
      unit_atom = IDENT | '(' unit_expr ')'

    支持:
      m/s^2, kg*m/s^2, m^3/kg/s^2, (m/s)^2, s^-2, N*m, kg^-1*m^3*s^-2
    """

    def __init__(self, input_data: Union[str, List[Tuple[str, str]]], registry: "UnitRegistry"):
        self.registry = registry
        if isinstance(input_data, str):
            self.text = input_data
            self.tokens = self._tokenize(input_data)
        else:
            # 直接接受 token list，用于从表达式解析器中调用
            self.text = "".join(v for _, v in input_data)
            self.tokens = input_data
        self.pos = 0

    def _tokenize(self, text: str) -> List[Tuple[str, str]]:
        tokens = []
        for m in _UNIT_TOKEN_RE.finditer(text):
            kind = m.lastgroup
            value = m.group()
            if kind == "WS":
                continue
            tokens.append((kind, value))
        return tokens

    def peek(self) -> Optional[Tuple[str, str]]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self) -> Tuple[str, str]:
        tok = self.peek()
        if tok is None:
            raise ParseError(f"单位表达式 '{self.text}' 意外结束")
        self.pos += 1
        return tok

    def parse(self) -> UnitDef:
        dim, factor = self._unit_expr()
        if self.pos < len(self.tokens):
            raise ParseError(f"单位表达式 '{self.text}' 中多余的字符: {self.tokens[self.pos:]}")
        if dim is None:
            dim = DIMENSIONLESS
        return UnitDef(self.text, self.text, dim, factor=factor)

    def _unit_expr(self) -> Tuple[Optional[Dimension], float]:
        dim, factor = self._unit_term()
        while True:
            tok = self.peek()
            if tok and tok[0] == "OP" and tok[1] in ("*", "/"):
                op = self.consume()[1]
                rdim, rfactor = self._unit_term()
                if rdim is None:
                    rdim = DIMENSIONLESS
                if dim is None:
                    dim = DIMENSIONLESS
                if op == "*":
                    dim = dim * rdim
                    factor *= rfactor
                else:
                    dim = dim / rdim
                    factor /= rfactor
            else:
                break
        return dim, factor

    def _unit_term(self) -> Tuple[Optional[Dimension], float]:
        dim, factor = self._unit_atom()
        tok = self.peek()
        if tok and tok[0] == "OP" and tok[1] == "^":
            self.consume()
            exp_tok = self.peek()
            if exp_tok is None or exp_tok[0] != "NUMBER":
                raise ParseError(f"单位表达式 '{self.text}' 中 '^' 后面需要数字")
            self.consume()
            exp = float(exp_tok[1])
            if dim is not None:
                dim = dim ** exp
            factor = factor ** exp
        return dim, factor

    def _unit_atom(self) -> Tuple[Optional[Dimension], float]:
        tok = self.peek()
        if tok is None:
            raise ParseError(f"单位表达式 '{self.text}' 意外结束")

        if tok[0] == "OP" and tok[1] == "(":
            self.consume()
            dim, factor = self._unit_expr()
            close = self.peek()
            if close is None or close[0] != "OP" or close[1] != ")":
                raise ParseError(f"单位表达式 '{self.text}' 缺少右括号")
            self.consume()
            return dim, factor

        if tok[0] == "UNIT":
            self.consume()
            symbol = tok[1]
            # 直接访问注册表内部字典，避免无限递归调用 get()
            unit = self.registry._units.get(symbol)
            if unit is None:
                alias = self.registry._aliases.get(symbol)
                if alias is not None:
                    unit = self.registry._units.get(alias)
            if unit is None:
                raise ParseError(f"未知单位符号: '{symbol}' 在表达式 '{self.text}' 中")
            return unit.dimension, unit.factor

        if tok[0] == "NUMBER":
            self.consume()
            val = float(tok[1])
            return None, val

        raise ParseError(f"单位表达式 '{self.text}' 中意外的标记: {tok}")


def parse_unit_symbol(symbol: str, registry: "UnitRegistry") -> Optional[UnitDef]:
    """解析复合单位符号，如 m/s^2、kg*m/s^2 等。"""
    if not symbol or not symbol.strip():
        return None
    
    # 先尝试直接查找（不带前缀解析，避免无限递归）
    if symbol in registry._units:
        return registry._units[symbol]
    if symbol in registry._aliases:
        return registry._units[registry._aliases[symbol]]
    
    # 尝试 SI 前缀解析（手动实现，不调用 registry.get 避免递归）
    for prefix in sorted(registry._SI_PREFIXES.keys(), key=len, reverse=True):
        if symbol.startswith(prefix) and len(symbol) > len(prefix):
            base_symbol = symbol[len(prefix):]
            # 只查找基本单位，不递归
            base_unit = None
            if base_symbol in registry._units:
                base_unit = registry._units[base_symbol]
            elif base_symbol in registry._aliases:
                base_unit = registry._units[registry._aliases[base_symbol]]
            
            if base_unit is not None:
                # 对于带 offset 的温度单位，不支持前缀
                if base_unit.offset != 0:
                    continue
                exp, prefix_name = registry._SI_PREFIXES[prefix]
                factor = 10 ** exp
                new_symbol = f"{prefix}{base_symbol}"
                new_name = f"{prefix_name}{base_unit.name}"
                new_unit = UnitDef(new_name, new_symbol, base_unit.dimension, factor * base_unit.factor, 0.0)
                registry._units[new_symbol] = new_unit
                return new_unit
    
    # 最后尝试用 UnitSymbolParser 解析复合单位
    try:
        parser = UnitSymbolParser(symbol, registry)
        return parser.parse()
    except ParseError:
        return None


# ─────────────────────────────────────────────
# UnitRegistry - 单位注册表 (支持自定义单位与别名)
# ─────────────────────────────────────────────
class UnitRegistry:
    """单位注册表，管理所有已知单位及其别名。"""

    # SI 前缀 (前缀符号 -> (10的指数, 前缀名称))
    _SI_PREFIXES = {
        'Y': (24, 'yotta'),
        'Z': (21, 'zetta'),
        'E': (18, 'exa'),
        'P': (15, 'peta'),
        'T': (12, 'tera'),
        'G': (9, 'giga'),
        'M': (6, 'mega'),
        'k': (3, 'kilo'),
        'h': (2, 'hecto'),
        'da': (1, 'deca'),
        'd': (-1, 'deci'),
        'c': (-2, 'centi'),
        'm': (-3, 'milli'),
        'μ': (-6, 'micro'),
        'u': (-6, 'micro'),
        'n': (-9, 'nano'),
        'p': (-12, 'pico'),
        'f': (-15, 'femto'),
        'a': (-18, 'atto'),
        'z': (-21, 'zepto'),
        'y': (-24, 'yocto'),
    }

    def __init__(self):
        self._units: Dict[str, UnitDef] = {}
        self._aliases: Dict[str, str] = {}
        self._constants: Dict[str, Quantity] = {}
        self._constant_aliases: Dict[str, str] = {}
        self._constant_notes: Dict[str, str] = {}
        self._constants_initialized = False
        self._init_all()

    # ─── 公共 API ───────────────────────────
    def define_unit(
        self,
        symbol: str,
        *,
        name: Optional[str] = None,
        dimension: Optional[Union[Dimension, str]] = None,
        factor: Optional[float] = None,
        offset: float = 0.0,
        definition: Optional[str] = None,
    ) -> UnitDef:
        """
        定义一个新的单位。有两种方式：

        方式1: 通过量纲和换算因子
            define_unit("furlong", name="furlong", dimension=Dimension(length=1), factor=201.168)

        方式2: 通过表达式
            define_unit("day", definition="24 h")
            define_unit("mph", definition="mi/h")
            define_unit("furlong", definition="220 yd")

        参数
        ----
        symbol : str          单位符号
        name : str            单位全名 (可选，默认等于 symbol)
        dimension : Dimension 量纲 (方式1)
        factor : float        换算因子 (方式1，1 此单位 = factor 基本单位)
        offset : float        偏移量 (方式1，默认 0)
        definition : str      定义表达式 (方式2，如 "24 h" 或 "mi/h")
        """
        if symbol in self._units or symbol in self._aliases:
            raise UnitDefinitionError(
                f"符号 '{symbol}' 已存在。请先调用 unregister('{symbol}') 删除后再注册。"
            )

        if definition is not None:
            # 方式2: 通过表达式定义
            if dimension is not None or factor is not None:
                raise UnitDefinitionError(
                    f"定义 '{symbol}' 时不能同时使用 definition 和 dimension/factor。"
                )
            unit = self._define_from_expression(symbol, name, definition, offset)
        else:
            # 方式1: 通过量纲和因子
            if dimension is None or factor is None:
                raise UnitDefinitionError(
                    f"定义 '{symbol}' 时必须提供 definition，或同时提供 dimension 和 factor。"
                )
            if isinstance(dimension, str):
                raise UnitDefinitionError(
                    f"dimension 必须是 Dimension 对象，不是字符串。"
                    f"试试用 parse_unit('{dimension}') 获取量纲？"
                )
            unit = UnitDef(name or symbol, symbol, dimension, factor, offset)

        self._units[symbol] = unit
        return unit

    def alias(self, new_symbol: str, existing_symbol: str, *, name: Optional[str] = None) -> None:
        """
        为现有单位添加别名。

        示例:
            alias("metre", "m")
            alias("千米", "km", name="千米")
        """
        if new_symbol in self._units or new_symbol in self._aliases:
            raise UnitDefinitionError(
                f"符号 '{new_symbol}' 已存在。请先删除后再注册。"
            )
        # 解析 existing_symbol (可能是别名链)
        real_symbol = self._resolve_alias(existing_symbol)
        if real_symbol not in self._units:
            raise UnitDefinitionError(f"未知单位: '{existing_symbol}'")

        self._aliases[new_symbol] = real_symbol
        # 如果提供了 name，更新主单位的 name（可选）
        if name is not None:
            self._units[real_symbol].name = name

    def unregister(self, symbol: str) -> bool:
        """删除单位或别名。成功返回 True，未找到返回 False。"""
        if symbol in self._units:
            # 删除主单位时，也删除所有指向它的别名
            aliases_to_del = [a for a, t in self._aliases.items() if t == symbol]
            for a in aliases_to_del:
                del self._aliases[a]
            del self._units[symbol]
            return True
        if symbol in self._aliases:
            del self._aliases[symbol]
            return True
        return False

    def get(self, symbol: str) -> Optional[UnitDef]:
        """获取单位，自动解析复合单位、别名和 SI 前缀。"""
        if symbol in self._units:
            return self._units[symbol]
        if symbol in self._aliases:
            return self._units[self._aliases[symbol]]
        # parse_unit_symbol 会处理 SI 前缀和复合单位解析
        return parse_unit_symbol(symbol, self)

    def _get_base_unit(self, symbol: str) -> Optional[UnitDef]:
        """获取基本单位（不带前缀的），仅用于前缀解析。"""
        if symbol in self._units:
            return self._units[symbol]
        if symbol in self._aliases:
            return self._units[self._aliases[symbol]]
        return None

    def __getitem__(self, symbol: str) -> UnitDef:
        u = self.get(symbol)
        if u is None:
            raise KeyError(f"未知单位: '{symbol}'")
        return u

    def __contains__(self, symbol: str) -> bool:
        return self.get(symbol) is not None or symbol in self._constants

    def all_units(self) -> Dict[str, UnitDef]:
        """返回所有已注册主单位的副本。"""
        return dict(self._units)

    def all_aliases(self) -> Dict[str, str]:
        """返回所有别名映射。"""
        return dict(self._aliases)

    def register_constant(
        self,
        symbol: str,
        quantity: Quantity,
        aliases: Optional[List[str]] = None,
        note: Optional[str] = None
    ) -> None:
        """
        注册物理常数。

        参数
        ----
        symbol : str       常数符号 (如 'G', 'c', 'h_p')
        quantity : Quantity  常数值（带单位）
        aliases : List[str]  可选别名列表 (如 ['planck', 'h'] 用于 h_p)
        note : str         可选备注说明 (如 'h 被小时占用，推荐使用 h_p')

        示例:
            register_constant('G', parse('6.67430e-11 m^3/kg/s^2'))
            register_constant('h_p', parse('6.62607015e-34 J*s'),
                            aliases=['planck', 'h_const'],
                            note='h 被小时单位占用，推荐使用 h_p')
        """
        if symbol in self._constants:
            raise UnitDefinitionError(
                f"常数 '{symbol}' 已存在。"
            )
        if symbol in self._units or symbol in self._aliases:
            raise UnitDefinitionError(
                f"符号 '{symbol}' 已被单位占用，请使用其他符号。"
            )
        self._constants[symbol] = quantity
        
        # 注册别名（只注册不与现有符号冲突的别名）
        if aliases:
            for alias in aliases:
                if alias not in self._units and alias not in self._aliases \
                        and alias not in self._constants and alias not in self._constant_aliases:
                    self._constant_aliases[alias] = symbol
        
        # 注册备注
        if note:
            self._constant_notes[symbol] = note

    def _ensure_constants_initialized(self) -> None:
        """确保常数已初始化（延迟初始化）。"""
        if self._constants_initialized:
            return
        # 检查 Quantity 是否已定义
        if 'Quantity' in globals():
            self._init_constants()
            self._constants_initialized = True

    def get_constant(self, symbol: str) -> Optional[Quantity]:
        """获取物理常数，支持别名查找，不存在返回 None。"""
        self._ensure_constants_initialized()
        if symbol in self._constants:
            return self._constants[symbol]
        if symbol in self._constant_aliases:
            return self._constants[self._constant_aliases[symbol]]
        return None

    def get_constant_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取物理常数的完整信息（符号、数值、别名、备注等）。"""
        self._ensure_constants_initialized()
        actual_symbol = symbol
        if symbol in self._constant_aliases:
            actual_symbol = self._constant_aliases[symbol]
        if actual_symbol not in self._constants:
            return None
        aliases = [k for k, v in self._constant_aliases.items() if v == actual_symbol]
        return {
            'symbol': actual_symbol,
            'quantity': self._constants[actual_symbol],
            'aliases': aliases,
            'note': self._constant_notes.get(actual_symbol, '')
        }

    def get_all_constants_info(self) -> List[Dict[str, Any]]:
        """获取所有物理常数的完整信息列表。"""
        self._ensure_constants_initialized()
        result = []
        for symbol, qty in self._constants.items():
            aliases = [k for k, v in self._constant_aliases.items() if v == symbol]
            result.append({
                'symbol': symbol,
                'quantity': qty,
                'aliases': aliases,
                'note': self._constant_notes.get(symbol, '')
            })
        return result

    def all_constants(self) -> Dict[str, Quantity]:
        """返回所有已注册物理常数的副本。"""
        self._ensure_constants_initialized()
        return dict(self._constants)

    # ─── 内部方法 ───────────────────────────
    def _resolve_alias(self, symbol: str) -> str:
        """递归解析别名到最终主单位符号。"""
        visited = set()
        current = symbol
        while current in self._aliases:
            if current in visited:
                raise UnitDefinitionError(f"检测到别名循环: {symbol}")
            visited.add(current)
            current = self._aliases[current]
        return current

    def _define_from_expression(
        self, symbol: str, name: Optional[str], definition: str, offset: float
    ) -> UnitDef:
        """通过表达式定义单位。"""
        # 解析表达式，得到 Quantity，然后提取其 dimension 和 factor
        try:
            qty = parse(definition, self)
        except Exception as e:
            raise UnitDefinitionError(
                f"定义 '{symbol}' 时解析表达式 '{definition}' 失败: {e}"
            ) from e

        if offset != 0 and qty.dimension != Dimension(temperature=1):
            raise UnitDefinitionError(
                f"定义 '{symbol}' 时 offset 只能用于温度量纲单位。"
            )

        if not math.isclose(qty.value_base, 0) or qty.dimension.is_dimensionless():
            dim = qty.dimension
            # 计算 factor: expression_value_base = factor * 1
            # 即 expression_value_base 个基本单位 = 1 个新单位
            # 所以 factor = expression_value_base
            factor = qty.value_base
        else:
            # 如果表达式值为 0 且不是无量纲，则有问题
            dim = qty.dimension
            factor = 1.0

        if offset != 0 and dim != Dimension(temperature=1):
            raise UnitDefinitionError(
                f"offset 参数只能用于温度量纲的单位。当前量纲: {dim}"
            )

        return UnitDef(name or symbol, symbol, dim, factor=factor, offset=offset)

    def register(self, unit: UnitDef) -> None:
        """低级 API，直接注册 UnitDef 对象。"""
        if unit.symbol in self._units or unit.symbol in self._aliases:
            raise UnitDefinitionError(
                f"单位符号冲突: '{unit.symbol}' 已存在。"
            )
        self._units[unit.symbol] = unit

    # ─── 预定义单位 ─────────────────────────
    def _init_all(self):
        self._init_si()
        self._init_imperial()
        self._init_temperature()
        self._init_derived()
        self._init_pressure()
        self._init_energy()
        self._init_astronomical()
        self._init_aliases()

    def _init_si(self):
        self.register(UnitDef("meter", "m", Dimension(length=1)))
        self.register(UnitDef("kilometer", "km", Dimension(length=1), factor=1000))
        self.register(UnitDef("centimeter", "cm", Dimension(length=1), factor=0.01))
        self.register(UnitDef("millimeter", "mm", Dimension(length=1), factor=0.001))
        self.register(UnitDef("micrometer", "um", Dimension(length=1), factor=1e-6))
        self.register(UnitDef("nanometer", "nm", Dimension(length=1), factor=1e-9))
        self.register(UnitDef("kilogram", "kg", Dimension(mass=1)))
        self.register(UnitDef("gram", "g", Dimension(mass=1), factor=0.001))
        self.register(UnitDef("milligram", "mg", Dimension(mass=1), factor=1e-6))
        self.register(UnitDef("second", "s", Dimension(time=1)))
        self.register(UnitDef("minute", "min", Dimension(time=1), factor=60))
        self.register(UnitDef("hour", "h", Dimension(time=1), factor=3600))
        self.register(UnitDef("ampere", "A", Dimension(current=1)))
        self.register(UnitDef("mole", "mol", Dimension(amount=1)))
        self.register(UnitDef("candela", "cd", Dimension(luminosity=1)))

    def _init_imperial(self):
        self.register(UnitDef("inch", "in", Dimension(length=1), factor=0.0254))
        self.register(UnitDef("foot", "ft", Dimension(length=1), factor=0.3048))
        self.register(UnitDef("yard", "yd", Dimension(length=1), factor=0.9144))
        self.register(UnitDef("mile", "mi", Dimension(length=1), factor=1609.344))
        self.register(UnitDef("pound", "lb", Dimension(mass=1), factor=0.45359237))
        self.register(UnitDef("ounce", "oz", Dimension(mass=1), factor=0.028349523125))

    def _init_temperature(self):
        self.register(UnitDef("kelvin", "K", Dimension(temperature=1)))
        self.register(UnitDef("celsius", "C", Dimension(temperature=1), factor=1.0, offset=273.15))
        self.register(UnitDef("fahrenheit", "F", Dimension(temperature=1), factor=5.0 / 9.0, offset=459.67))

    def _init_derived(self):
        self.register(UnitDef("newton", "N", Dimension(mass=1, length=1, time=-2)))
        self.register(UnitDef("joule", "J", Dimension(mass=1, length=2, time=-2)))
        self.register(UnitDef("watt", "W", Dimension(mass=1, length=2, time=-3)))
        self.register(UnitDef("pascal", "Pa", Dimension(mass=1, length=-1, time=-2)))
        self.register(UnitDef("hertz", "Hz", Dimension(time=-1)))
        self.register(UnitDef("liter", "L", Dimension(length=3), factor=0.001))
        self.register(UnitDef("m/s", "m/s", Dimension(length=1, time=-1)))
        self.register(UnitDef("km/h", "km/h", Dimension(length=1, time=-1), factor=1 / 3.6))
        self.register(UnitDef("knot", "kn", Dimension(length=1, time=-1), factor=0.514444))
        # 纯数字单位（用于无量纲常数）
        self.register(UnitDef("unity", "1", DIMENSIONLESS, factor=1.0))
        # 角度单位（无量纲，但有换算因子）
        import math
        self.register(UnitDef("radian", "rad", DIMENSIONLESS, factor=1.0))
        self.register(UnitDef("degree", "deg", DIMENSIONLESS, factor=math.pi / 180.0))

    def _init_aliases(self):
        self.alias("metre", "m", name="metre")
        self.alias("metres", "m")
        self.alias("meters", "m")
        self.alias("kilometers", "km")
        self.alias("kilometres", "km")
        self.alias("sec", "s")
        self.alias("secs", "s")
        self.alias("seconds", "s")
        self.alias("minutes", "min")
        self.alias("hours", "h")
        self.alias("grams", "g")
        self.alias("kilograms", "kg")
        self.alias("pounds", "lb")
        self.alias("ounces", "oz")
        self.alias("inches", "in")
        self.alias("feet", "ft")
        self.alias("yards", "yd")
        self.alias("miles", "mi")
        self.alias("degC", "C")
        self.alias("degF", "F")
        self.alias("degK", "K")
        self.alias("°C", "C")
        self.alias("°F", "F")
        self.alias("°K", "K")

    def _init_pressure(self):
        """初始化压强单位。"""
        self.register(UnitDef("bar", "bar", Dimension(mass=1, length=-1, time=-2), factor=1e5))
        self.register(UnitDef("millibar", "mbar", Dimension(mass=1, length=-1, time=-2), factor=100))
        self.register(UnitDef("mmHg", "mmHg", Dimension(mass=1, length=-1, time=-2), factor=133.3223684))
        self.register(UnitDef("torr", "torr", Dimension(mass=1, length=-1, time=-2), factor=133.3223684))
        self.register(UnitDef("atmosphere", "atm", Dimension(mass=1, length=-1, time=-2), factor=101325))
        self.register(UnitDef("psi", "psi", Dimension(mass=1, length=-1, time=-2), factor=6894.75729))

    def _init_energy(self):
        """初始化能量单位。"""
        self.register(UnitDef("electronvolt", "eV", Dimension(mass=1, length=2, time=-2), factor=1.602176634e-19))
        self.register(UnitDef("calorie", "cal", Dimension(mass=1, length=2, time=-2), factor=4.184))
        self.register(UnitDef("kilocalorie", "kcal", Dimension(mass=1, length=2, time=-2), factor=4184))
        self.register(UnitDef("watt_hour", "Wh", Dimension(mass=1, length=2, time=-2), factor=3600))
        self.register(UnitDef("kilowatt_hour", "kWh", Dimension(mass=1, length=2, time=-2), factor=3.6e6))

    def _init_astronomical(self):
        """初始化天文单位。"""
        self.register(UnitDef("astronomical_unit", "AU", Dimension(length=1), factor=1.495978707e11))
        self.register(UnitDef("light_year", "ly", Dimension(length=1), factor=9.4607304725808e15))
        self.register(UnitDef("parsec", "pc", Dimension(length=1), factor=3.0856775814913673e16))
        self.register(UnitDef("solar_mass", "M_sun", Dimension(mass=1), factor=1.98847e30))
        self.register(UnitDef("earth_mass", "M_earth", Dimension(mass=1), factor=5.9722e24))

    def _init_constants(self):
        """初始化常用物理常数。"""
        if self._constants_initialized:
            return
        import math
        
        # 万有引力常数
        self.register_constant(
            'G',
            Quantity.from_base(
                6.67430e-11,
                Dimension(length=3, mass=-1, time=-2),
                registry=self
            ),
            aliases=['grav', 'gravitational'],
            note='万有引力常数'
        )
        # 光速
        self.register_constant(
            'c',
            Quantity.from_base(
                299792458.0,
                Dimension(length=1, time=-1),
                registry=self
            ),
            aliases=['light', 'c0'],
            note='真空中光速'
        )
        # 普朗克常数 (h 被小时占用，使用 h_p)
        self.register_constant(
            'h_p',
            Quantity.from_base(
                6.62607015e-34,
                Dimension(mass=1, length=2, time=-1),
                registry=self
            ),
            aliases=['planck', 'h_const', 'plank'],
            note='h 被小时单位占用，推荐使用 h_p 或 planck'
        )
        # 约化普朗克常数
        self.register_constant(
            'hbar',
            Quantity.from_base(
                6.62607015e-34 / (2 * math.pi),
                Dimension(mass=1, length=2, time=-1),
                registry=self
            ),
            aliases=['h_bar', 'reduced_planck'],
            note='约化普朗克常数 = h / 2π'
        )
        # 玻尔兹曼常数 (k 被千前缀占用，使用 k_b)
        self.register_constant(
            'k_b',
            Quantity.from_base(
                1.380649e-23,
                Dimension(mass=1, length=2, time=-2, temperature=-1),
                registry=self
            ),
            aliases=['boltzmann', 'k_const', 'boltzman'],
            note='k 被千前缀 (k=10^3) 占用，推荐使用 k_b 或 boltzmann'
        )
        # 理想气体常数
        self.register_constant(
            'R',
            Quantity.from_base(
                8.314462618,
                Dimension(mass=1, length=2, time=-2, temperature=-1, amount=-1),
                registry=self
            ),
            aliases=['gas_constant', 'ideal_gas'],
            note='理想气体常数 = k_b * N_A'
        )
        # 元电荷
        self.register_constant(
            'e',
            Quantity.from_base(
                1.602176634e-19,
                Dimension(current=1, time=1),
                registry=self
            ),
            aliases=['electron_charge', 'elementary_charge'],
            note='元电荷（电子电荷量）'
        )
        # 阿伏伽德罗常数
        self.register_constant(
            'N_A',
            Quantity.from_base(
                6.02214076e23,
                Dimension(amount=-1),
                registry=self
            ),
            aliases=['avogadro', 'avogadro_constant'],
            note='阿伏伽德罗常数'
        )
        # 标准重力加速度 (g 被克占用，使用 g_0)
        self.register_constant(
            'g_0',
            Quantity.from_base(
                9.80665,
                Dimension(length=1, time=-2),
                registry=self
            ),
            aliases=['gravity', 'standard_gravity', 'g_const'],
            note='g 被克单位占用，推荐使用 g_0 或 gravity'
        )
        # 圆周率 π
        self.register_constant(
            'pi',
            Quantity.from_base(
                math.pi,
                DIMENSIONLESS,
                unit=self['1'],
                registry=self
            ),
            aliases=['π', 'pi_const'],
            note='圆周率 π ≈ 3.1415926535'
        )
        # 自然对数的底 e
        self.register_constant(
            'euler',
            Quantity.from_base(
                math.e,
                DIMENSIONLESS,
                unit=self['1'],
                registry=self
            ),
            aliases=['e_const', 'napier'],
            note='e 被元电荷占用，推荐使用 euler 或 e_const (e ≈ 2.71828)'
        )
        # 标准大气压 (已作为单位注册，不再作为常数)
        # self.register_constant(
        #     'atm',
        #     Quantity.from_base(
        #         101325.0,
        #         Dimension(mass=1, length=-1, time=-2),
        #         registry=self
        #     )
        # )
        # 电子伏特 (已作为单位注册，不再作为常数)
        # self.register_constant(
        #     'eV',
        #     Quantity.from_base(
        #         1.602176634e-19,
        #         Dimension(mass=1, length=2, time=-2),
        #         registry=self
        #     )
        # )
        self._constants_initialized = True


DEFAULT_REGISTRY = UnitRegistry()


# ─────────────────────────────────────────────
# Quantity - 带单位的物理量
# ─────────────────────────────────────────────
class Quantity:
    """带量纲和单位的物理量，内部以基本单位值存储。"""

    __slots__ = ("_value_base", "_dimension", "_unit", "_registry")

    def __init__(
        self,
        value: float,
        unit: Union[str, UnitDef],
        registry: Optional[UnitRegistry] = None,
    ):
        self._registry = registry or DEFAULT_REGISTRY
        if isinstance(unit, str):
            unit_def = self._registry[unit]
        else:
            unit_def = unit
        self._value_base = unit_def.to_base(value)
        self._dimension = unit_def.dimension
        self._unit = unit_def

    @classmethod
    def from_base(
        cls,
        value_base: float,
        dimension: Dimension,
        unit: Optional[UnitDef] = None,
        registry: Optional[UnitRegistry] = None,
    ) -> "Quantity":
        obj = object.__new__(cls)
        obj._registry = registry or DEFAULT_REGISTRY
        obj._value_base = value_base
        obj._dimension = dimension
        obj._unit = unit
        return obj

    @property
    def value_base(self) -> float:
        return self._value_base

    @property
    def dimension(self) -> Dimension:
        return self._dimension

    @property
    def unit(self) -> Optional[UnitDef]:
        return self._unit

    def to(self, target_unit: Union[str, UnitDef]) -> "Quantity":
        """转换到目标单位，量纲必须一致。"""
        if isinstance(target_unit, str):
            target = self._registry[target_unit]
        else:
            target = target_unit
        if self._dimension != target.dimension:
            raise DimensionError(
                f"量纲不一致: 当前={self._dimension}, 目标={target.dimension}\n"
                f"  详细: 你试图把 {self._dimension} 的量转换为 {target.dimension} 的量，"
                f"这在物理上没有意义。"
            )
        new_value = target.from_base(self._value_base)
        return Quantity(new_value, target, self._registry)

    def to_value(self, target_unit: Union[str, UnitDef]) -> float:
        return self.to(target_unit).value_in_unit()

    def value_in_unit(self) -> float:
        if self._unit is None:
            return self._value_base
        return self._unit.from_base(self._value_base)

    def simplify(self) -> "Quantity":
        """尝试匹配一个有名字的导出单位（N, J, W 等）来替换复合量纲。"""
        reg = self._registry
        candidates = []
        for sym, u in reg.all_units().items():
            if u.dimension == self._dimension and u.offset == 0:
                value = u.from_base(self._value_base)
                if abs(value) >= 1:
                    candidates.append((value, sym, u))
        if candidates:
            # 选择数值最接近 1 的（或有名字的优先）
            named = [c for c in candidates if len(c[1]) <= 2]
            if named:
                candidates = named
            candidates.sort(key=lambda c: abs(math.log10(abs(c[0]))))
            best = candidates[0]
            return Quantity(best[0], best[2], self._registry)
        return self

    def __mul__(self, other: Union["Quantity", float, int]) -> "Quantity":
        if isinstance(other, (int, float)):
            return Quantity.from_base(
                self._value_base * other, self._dimension, self._unit, self._registry
            )
        if isinstance(other, Quantity):
            new_dim = self._dimension * other._dimension
            new_val = self._value_base * other._value_base
            result = Quantity.from_base(new_val, new_dim, registry=self._registry)
            return result.simplify()
        return NotImplemented

    def __rmul__(self, other: Union[float, int]) -> "Quantity":
        if isinstance(other, (int, float)):
            return Quantity.from_base(
                self._value_base * other, self._dimension, self._unit, self._registry
            )
        return NotImplemented

    def __truediv__(self, other: Union["Quantity", float, int]) -> "Quantity":
        if isinstance(other, (int, float)):
            return Quantity.from_base(
                self._value_base / other, self._dimension, self._unit, self._registry
            )
        if isinstance(other, Quantity):
            new_dim = self._dimension / other._dimension
            new_val = self._value_base / other._value_base
            result = Quantity.from_base(new_val, new_dim, registry=self._registry)
            return result.simplify()
        return NotImplemented

    def __rtruediv__(self, other: Union[float, int]) -> "Quantity":
        if isinstance(other, (int, float)):
            new_dim = DIMENSIONLESS / self._dimension
            new_val = other / self._value_base
            result = Quantity.from_base(new_val, new_dim, registry=self._registry)
            return result.simplify()
        return NotImplemented

    def __add__(self, other: "Quantity") -> "Quantity":
        if not isinstance(other, Quantity):
            return NotImplemented
        if self._dimension != other._dimension:
            raise DimensionError(
                f"不能将 {self._dimension} 加到 {other._dimension} 上。\n"
                f"  详细: 加法要求两个量的量纲完全一致，请检查单位是否匹配。"
            )
        return Quantity.from_base(
            self._value_base + other._value_base, self._dimension, self._unit, self._registry
        )

    def __sub__(self, other: "Quantity") -> "Quantity":
        if not isinstance(other, Quantity):
            return NotImplemented
        if self._dimension != other._dimension:
            raise DimensionError(
                f"不能从 {self._dimension} 减去 {other._dimension}。\n"
                f"  详细: 减法要求两个量的量纲完全一致，请检查单位是否匹配。"
            )
        return Quantity.from_base(
            self._value_base - other._value_base, self._dimension, self._unit, self._registry
        )

    def __pow__(self, n: Union[int, float, "Quantity"]) -> "Quantity":
        exp: Union[int, float]
        if isinstance(n, Quantity):
            if n._dimension != DIMENSIONLESS:
                raise DimensionError(
                    f"指数必须是无量纲的，但收到 {n._dimension}\n"
                    f"  详细: 指数运算要求指数为纯数字，不能是带单位的物理量。"
                )
            exp = n._value_base
        else:
            exp = n
        new_dim = self._dimension ** exp
        new_val = self._value_base ** exp
        result = Quantity.from_base(new_val, new_dim, registry=self._registry)
        return result.simplify()

    def __neg__(self) -> "Quantity":
        return Quantity.from_base(-self._value_base, self._dimension, self._unit, self._registry)

    def __abs__(self) -> "Quantity":
        return Quantity.from_base(abs(self._value_base), self._dimension, self._unit, self._registry)

    def __eq__(self, other: object) -> bool:
        other_q: Optional[Quantity] = None
        if isinstance(other, Quantity):
            other_q = other
        elif isinstance(other, (int, float)):
            if self._dimension == DIMENSIONLESS:
                other_q = Quantity.from_base(float(other), DIMENSIONLESS, registry=self._registry)
            else:
                raise DimensionError(
                    f"不能比较有量纲量 [{self._dimension}] 与纯数字\n"
                    f"  详细: 比较有量纲量时，必须使用相同量纲的量，不能直接与纯数字比较。"
                )

        if other_q is None:
            return NotImplemented

        if self._dimension != other_q._dimension:
            raise DimensionError(
                f"不能比较 {self._dimension} 与 {other_q._dimension}\n"
                f"  详细: 相等比较要求两个量的量纲完全一致，请检查单位是否匹配。"
            )
        return math.isclose(self._value_base, other_q._value_base, rel_tol=1e-9)

    def __lt__(self, other: Union["Quantity", int, float]) -> bool:
        other_q: Optional[Quantity] = None
        if isinstance(other, Quantity):
            other_q = other
        elif isinstance(other, (int, float)):
            if self._dimension == DIMENSIONLESS:
                other_q = Quantity.from_base(float(other), DIMENSIONLESS, registry=self._registry)
            else:
                raise DimensionError(
                    f"不能比较有量纲量 [{self._dimension}] 与纯数字\n"
                    f"  详细: 比较有量纲量时，必须使用相同量纲的量，不能直接与纯数字比较。"
                )

        if other_q is None:
            return NotImplemented

        if self._dimension != other_q._dimension:
            raise DimensionError(
                f"不能比较 {self._dimension} 与 {other_q._dimension}\n"
                f"  详细: 大小比较要求两个量的量纲完全一致，请检查单位是否匹配。"
            )
        return self._value_base < other_q._value_base

    def __le__(self, other: Union["Quantity", int, float]) -> bool:
        return self == other or self < other

    def __gt__(self, other: Union["Quantity", int, float]) -> bool:
        other_q: Optional[Quantity] = None
        if isinstance(other, Quantity):
            other_q = other
        elif isinstance(other, (int, float)):
            if self._dimension == DIMENSIONLESS:
                other_q = Quantity.from_base(float(other), DIMENSIONLESS, registry=self._registry)
            else:
                raise DimensionError(
                    f"不能比较有量纲量 [{self._dimension}] 与纯数字\n"
                    f"  详细: 比较有量纲量时，必须使用相同量纲的量，不能直接与纯数字比较。"
                )

        if other_q is None:
            return NotImplemented

        if self._dimension != other_q._dimension:
            raise DimensionError(
                f"不能比较 {self._dimension} 与 {other_q._dimension}\n"
                f"  详细: 大小比较要求两个量的量纲完全一致，请检查单位是否匹配。"
            )
        return self._value_base > other_q._value_base

    def __ge__(self, other: Union["Quantity", int, float]) -> bool:
        return self == other or self > other

    def format(self, target_unit: Optional[str] = None) -> str:
        """格式化输出。"""
        if target_unit:
            q = self.to(target_unit)
            val = q.value_in_unit()
            sym = target_unit
        elif self._unit:
            val = self._unit.from_base(self._value_base)
            sym = self._unit.symbol
        else:
            val = self._value_base
            sym = ""
        return f"{val:.6g} {sym}".rstrip()

    def __repr__(self) -> str:
        if self._unit:
            # 如果有明确指定的单位，直接使用，不自动简化
            val = self._unit.from_base(self._value_base)
            return f"{val:.6g} {self._unit.symbol}"
        # 没有明确单位，尝试自动简化为有名字的导出单位
        simplified = self.simplify()
        if simplified._unit and simplified._unit.offset == 0:
            val = simplified._unit.from_base(self._value_base)
            return f"{val:.6g} {simplified._unit.symbol}"
        return f"{self._value_base:.6g} [{self._dimension}]"

    def __str__(self) -> str:
        return self.__repr__()

    def __format__(self, format_spec: str) -> str:
        if not format_spec:
            return self.__repr__()
        if self._unit:
            # 如果有明确指定的单位，直接使用，不自动简化
            val = self._unit.from_base(self._value_base)
            return f"{val:{format_spec}} {self._unit.symbol}"
        # 没有明确单位，尝试自动简化为有名字的导出单位
        simplified = self.simplify()
        if simplified._unit and simplified._unit.offset == 0:
            val = simplified._unit.from_base(self._value_base)
            return f"{val:{format_spec}} {simplified._unit.symbol}"
        return f"{self._value_base:{format_spec}} [{self._dimension}]"


# ─────────────────────────────────────────────
# 表达式解析器 (增强版)
# ─────────────────────────────────────────────
_MATH_FUNCTIONS = {
    # 三角函数 (支持角度: 默认弧度，可指定 deg/rad)
    'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
    # 双曲函数
    'sinh', 'cosh', 'tanh',
    # 指数对数
    'sqrt', 'exp', 'log', 'ln', 'log10', 'log2',
    # 其他
    'abs', 'floor', 'ceil', 'round',
}

_EXPR_TOKEN_RE = re.compile(r"""
    (?P<NUMBER>-?\d+\.?\d*(?:[eE][+-]?\d+)?) |
    (?P<FUNC>[a-zA-Z][a-zA-Z0-9_]*)(?=\s*\() |
    (?P<UNIT>[a-zA-Z][a-zA-Z0-9_°\u00B0]*) |
    (?P<OP>[+\-*/^()]) |
    (?P<TO>\s+to\s+) |
    (?P<WS>\s+)
""", re.VERBOSE)


# 初始化物理常数（必须在 Quantity 类定义完成之后）
DEFAULT_REGISTRY._init_constants()


def _expr_tokenize(expr: str) -> List[Tuple[str, str]]:
    """
    表达式分词。分词后会插入隐式乘号，例如:
      "2m"       → NUMBER(2), OP(*), UNIT(m)
      "3 kg m"   → NUMBER(3), OP(*), UNIT(kg), OP(*), UNIT(m)
      "(1+2)m"   → OP((), NUMBER(1), OP(+), NUMBER(2), OP()), OP(*), UNIT(m)
    """
    raw_tokens: List[Tuple[str, str]] = []
    last_end = 0
    for m in _EXPR_TOKEN_RE.finditer(expr):
        kind = m.lastgroup
        value = m.group()
        
        # 先检查是否有未匹配的字符（无效字符）
        if m.start() > last_end:
            invalid = expr[last_end:m.start()]
            if invalid.strip():
                raise ParseError(f"表达式中包含无效字符: '{invalid}'")
        
        # 然后更新 last_end
        last_end = m.end()
        
        if kind == "WS":
            continue
        if kind == "TO":
            raw_tokens.append(("TO", "to"))
            continue
        if kind == "FUNC":
            # 验证是否是有效的数学函数
            if value not in _MATH_FUNCTIONS:
                # 如果不是已知函数，当作普通 UNIT 处理
                raw_tokens.append(("UNIT", value))
            else:
                raw_tokens.append((kind, value))
            continue
        raw_tokens.append((kind, value))
    
    # 检查表达式末尾是否有未匹配的字符
    if last_end < len(expr):
        invalid = expr[last_end:]
        if invalid.strip():
            raise ParseError(f"表达式末尾包含无效字符: '{invalid}'")

    # 插入隐式乘号
    tokens: List[Tuple[str, str]] = []
    for i, (kind, value) in enumerate(raw_tokens):
        tokens.append((kind, value))
        if i >= len(raw_tokens) - 1:
            continue
        next_kind, next_val = raw_tokens[i + 1]

        need_implicit_mul = False

        # 注意: NUMBER 后面跟 UNIT 不插入 *，让 atom() 处理 NUMBER+UNIT 组合
        # 这是为了保证 1 s^2 作为整体 (1 s)^2 而不是 1 * s^2

        # 数字后面跟左括号: 2 (3+4) → 2 * (3+4)
        if kind == "NUMBER" and next_kind == "OP" and next_val == "(":
            need_implicit_mul = True

        # 数字后面跟函数: 2 sin(x) → 2 * sin(x)
        elif kind == "NUMBER" and next_kind == "FUNC":
            need_implicit_mul = True

        # 右括号后面跟数字或单位或函数: (3+4) 2 → (3+4)*2; (3+4)m → (3+4)*m; (3+4) sin(x) → (3+4)*sin(x)
        elif kind == "OP" and value == ")" and next_kind in ("NUMBER", "UNIT", "FUNC"):
            need_implicit_mul = True

        # 单位后面跟数字或单位或左括号或函数:
        #   m 2 → m*2; m s → m*s; m (3+4) → m*(3+4); m sin(x) → m*sin(x)
        elif kind == "UNIT" and next_kind in ("NUMBER", "UNIT", "FUNC"):
            need_implicit_mul = True
        elif kind == "UNIT" and next_kind == "OP" and next_val == "(":
            need_implicit_mul = True

        # 函数后面跟单位或数字: sin(x) 2 → sin(x)*2; sin(x) m → sin(x)*m
        elif kind == "FUNC" and next_kind in ("NUMBER", "UNIT"):
            need_implicit_mul = True

        if need_implicit_mul:
            tokens.append(("OP", "*"))

    return tokens


class _ExprParser:
    """
    增强版递归下降解析器。

    文法:
      expr   = term (('+' | '-') term)*
      term   = factor (('*' | '/') factor)*
      factor = unary ('^' expr_power)?
      unary  = '-' atom | '+' atom | atom
      expr_power = unary
      atom   = NUMBER [UNIT] | UNIT | '(' expr ')'

    支持:
      - 负数: -5 m, -3.14
      - 负指数: m^-2, s^-1
      - 隐式乘法: 2m, 3 kg m/s^2
      - 括号: (2 m)^3, 2*(m/s)
    """

    def __init__(
        self,
        tokens: List[Tuple[str, str]],
        registry: UnitRegistry,
        variables: Optional[Dict[str, Quantity]] = None
    ):
        self.tokens = tokens
        self.pos = 0
        self.registry = registry
        self.variables = variables or {}

    def peek(self, offset: int = 0) -> Optional[Tuple[str, str]]:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else None

    def consume(self, expected_kind: Optional[str] = None) -> Tuple[str, str]:
        tok = self.peek()
        if tok is None:
            raise ParseError("表达式意外结束")
        if expected_kind and tok[0] != expected_kind:
            raise ParseError(f"期望 {expected_kind}，得到 {tok[0]}('{tok[1]}')")
        self.pos += 1
        return tok

    def parse(self) -> Quantity:
        result = self.expr()
        if self.pos < len(self.tokens):
            remaining = " ".join(f"'{v}'" for _, v in self.tokens[self.pos:])
            raise ParseError(f"表达式有多余的字符: {remaining}")
        return result

    def expr(self) -> Quantity:
        left = self.term()
        while True:
            tok = self.peek()
            if tok and tok[0] == "OP" and tok[1] in ("+", "-"):
                self.consume()
                right = self.term()
                if tok[1] == "+":
                    left = left + right
                else:
                    left = left - right
            else:
                break
        return left

    def term(self) -> Quantity:
        left = self.factor()
        while True:
            tok = self.peek()
            if tok and tok[0] == "OP" and tok[1] in ("*", "/"):
                self.consume()
                right = self.factor()
                if tok[1] == "*":
                    left = left * right
                else:
                    left = left / right
            else:
                break
        return left

    def factor(self) -> Quantity:
        base = self.unary()
        tok = self.peek()
        if tok and tok[0] == "OP" and tok[1] == "^":
            self.consume()
            # 幂运算右边可以是一元表达式（支持负指数）
            exp = self.unary()
            if not exp.dimension.is_dimensionless():
                raise ParseError(f"指数必须是无量纲的，不能是 {exp.dimension}")
            base = base ** exp.value_base
        return base

    def unary(self) -> Quantity:
        tok = self.peek()
        if tok and tok[0] == "OP" and tok[1] in ("+", "-"):
            self.consume()
            atom = self.atom()
            if tok[1] == "-":
                return -atom
            return atom
        return self.atom()

    def _apply_function(self, func_name: str, arg: Quantity) -> Quantity:
        """
        应用数学函数到 Quantity，并处理量纲检查。

        参数:
            func_name: 函数名 (sin, cos, sqrt, etc.)
            arg: 参数 Quantity

        返回:
            计算结果 Quantity
        """
        import math

        # 检查是否是角度单位（用于三角函数）
        is_trig = func_name in ('sin', 'cos', 'tan')
        is_inverse_trig = func_name in ('asin', 'acos', 'atan')
        is_hyperbolic = func_name in ('sinh', 'cosh', 'tanh')
        is_exponential = func_name in ('exp', 'log', 'ln', 'log10', 'log2')
        is_power = func_name in ('sqrt',)
        is_rounding = func_name in ('abs', 'floor', 'ceil', 'round')

        # 获取纯数值（处理角度单位转换）
        if is_trig or is_hyperbolic:
            # 三角函数和双曲函数: 参数必须是无量纲或角度单位
            if arg.dimension.is_dimensionless():
                # 无量纲，默认弧度
                value = arg.value_base
            else:
                # 检查是否是角度单位
                try:
                    # 尝试转换为弧度
                    rad_value = arg.to_value('rad')
                    value = rad_value
                except (DimensionError, KeyError):
                    try:
                        # 尝试转换为度再转弧度
                        deg_value = arg.to_value('deg')
                        value = math.radians(deg_value)
                    except (DimensionError, KeyError):
                        raise DimensionError(
                            f"函数 '{func_name}' 需要无量纲参数或角度单位 (deg/rad)，"
                            f"但得到的量纲是 {arg.dimension}\n"
                            f"  详细: 请使用 sin(90 deg) 或 sin(pi/2 rad) 或 sin(1.57) 的形式。"
                        )
        elif is_inverse_trig:
            # 反三角函数: 参数必须是无量纲，结果是弧度（无量纲）
            if not arg.dimension.is_dimensionless():
                raise DimensionError(
                    f"函数 '{func_name}' 需要无量纲参数，"
                    f"但得到的量纲是 {arg.dimension}\n"
                    f"  详细: 反三角函数的输入必须是 -1 到 1 之间的纯数字。"
                )
            value = arg.value_base
        elif is_exponential:
            # 指数和对数: 参数必须是无量纲
            if not arg.dimension.is_dimensionless():
                raise DimensionError(
                    f"函数 '{func_name}' 需要无量纲参数，"
                    f"但得到的量纲是 {arg.dimension}\n"
                    f"  详细: 指数和对数函数只能作用于纯数字。"
                )
            value = arg.value_base
        else:
            # 其他函数（sqrt, abs, floor, ceil, round）: 可以是任何量纲
            value = arg.value_base

        # 执行计算
        if func_name == 'sin':
            result_value = math.sin(value)
        elif func_name == 'cos':
            result_value = math.cos(value)
        elif func_name == 'tan':
            result_value = math.tan(value)
        elif func_name == 'asin':
            result_value = math.asin(value)
        elif func_name == 'acos':
            result_value = math.acos(value)
        elif func_name == 'atan':
            result_value = math.atan(value)
        elif func_name == 'sinh':
            result_value = math.sinh(value)
        elif func_name == 'cosh':
            result_value = math.cosh(value)
        elif func_name == 'tanh':
            result_value = math.tanh(value)
        elif func_name == 'sqrt':
            result_value = math.sqrt(value)
        elif func_name == 'exp':
            result_value = math.exp(value)
        elif func_name == 'log' or func_name == 'ln':
            result_value = math.log(value)
        elif func_name == 'log10':
            result_value = math.log10(value)
        elif func_name == 'log2':
            result_value = math.log2(value)
        elif func_name == 'abs':
            result_value = abs(value)
        elif func_name == 'floor':
            result_value = math.floor(value)
        elif func_name == 'ceil':
            result_value = math.ceil(value)
        elif func_name == 'round':
            result_value = round(value)
        else:
            raise ParseError(f"未知函数: {func_name}")

        # 确定结果的量纲和单位
        if is_trig or is_inverse_trig or is_hyperbolic or is_exponential:
            # 三角函数、反三角函数、双曲函数、指数对数: 结果无量纲
            result_dim = DIMENSIONLESS
            result_unit = UnitDef("dimensionless", "1", result_dim)
            return Quantity(result_value, result_unit, self.registry)
        elif is_power:
            # sqrt: 量纲指数除以 2
            result_dim = arg.dimension ** Fraction(1, 2)
            # 尝试从原单位推导新单位
            if arg._unit and arg._unit.offset == 0:
                # 简单处理：如果原单位是 m^2，结果单位是 m
                old_sym = arg._unit.symbol
                # 尝试创建一个简化的单位符号
                new_sym = f"sqrt({old_sym})" if '^' in old_sym else old_sym
                try:
                    result_unit = UnitDef(f"sqrt_{old_sym}", new_sym, result_dim, factor=math.sqrt(arg._unit.factor))
                    return Quantity(result_value, result_unit, self.registry)
                except:
                    pass
            result_unit = UnitDef("dimensionless", "1", result_dim)
            return Quantity(result_value, result_unit, self.registry)
        else:
            # abs, floor, ceil, round: 保持原有量纲和单位
            result_dim = arg.dimension
            if arg._unit:
                # 保留原单位
                return Quantity(result_value, arg._unit, self.registry)
            result_unit = UnitDef("dimensionless", "1", result_dim)
            return Quantity(result_value, result_unit, self.registry)

    def atom(self) -> Quantity:
        tok = self.peek()
        if tok is None:
            raise ParseError("表达式意外结束")

        # 函数调用: func(expr)
        if tok[0] == "FUNC":
            func_name = tok[1]
            self.consume()
            # 期望左括号
            lparen = self.peek()
            if lparen is None or lparen[0] != "OP" or lparen[1] != "(":
                raise ParseError(f"函数 '{func_name}' 后缺少 '('")
            self.consume()
            # 解析参数
            arg = self.expr()
            # 期望右括号
            rparen = self.peek()
            if rparen is None or rparen[0] != "OP" or rparen[1] != ")":
                raise ParseError(f"函数 '{func_name}' 的参数缺少 ')'")
            self.consume()
            # 应用函数
            return self._apply_function(func_name, arg)

        # 括号
        if tok[0] == "OP" and tok[1] == "(":
            self.consume()
            result = self.expr()
            close = self.peek()
            if close is None or close[0] != "OP" or close[1] != ")":
                raise ParseError("缺少右括号 ')'")
            self.consume()
            return result

        # 数字 [复合单位]
        if tok[0] == "NUMBER":
            self.consume()
            value = float(tok[1])
            next_tok = self.peek()
            if next_tok and next_tok[0] == "UNIT":
                # 数字后面跟单位: 解析为 系数 × 复合单位
                unit_def = self._parse_compound_unit()
                if unit_def is None:
                    # 返回 None 表示后面是常数，不是单位，处理为 数字 * 常数
                    const = self.atom()
                    dimless = UnitDef("dimensionless", "1", DIMENSIONLESS)
                    num_qty = Quantity(value, dimless, self.registry)
                    return num_qty * const
                return Quantity(value, unit_def, self.registry)
            else:
                # 只是一个纯数字
                dimless = UnitDef("dimensionless", "1", DIMENSIONLESS)
                return Quantity(value, dimless, self.registry)

        # 独立单位 (如 m, kg, s, 或复合单位 m^2/s)
        if tok[0] == "UNIT":
            # 先检查是否是变量（优先级最高）
            if tok[1] in self.variables:
                self.consume()
                return self.variables[tok[1]]
            # 再检查是否是物理常数
            const = self.registry.get_constant(tok[1])
            if const is not None:
                self.consume()
                return const
            # 否则解析为单位
            unit_def = self._parse_compound_unit()
            if unit_def is None:
                raise ParseError(f"无法解析单位符号: '{tok[1]}'")
            return Quantity(1.0, unit_def, self.registry)

        raise ParseError(f"意外的标记: {tok}")

    def _parse_compound_unit(self) -> UnitDef:
        """
        从当前位置开始智能解析复合单位符号。

        规则:
        - 遇到 UNIT: 属于单位符号
        - 遇到 ^: 属于单位符号（指数运算符），后面必须跟 NUMBER（指数）
        - 遇到 * 或 /: 只有当后面跟 UNIT 时才属于单位符号，否则是表达式运算符
        - 遇到 NUMBER: 只有当前面是 ^ 时才属于单位符号（指数值）
        - 其他情况: 停止解析

        示例:
        - `m^3/kg/s^2` → 完整解析为 m³·kg⁻¹·s⁻²
        - `s^2` → 解析为 s²
        - `kg * m` 中，`kg` 后面的 `*` 后面是 NUMBER，所以只解析 `kg`，`*` 留给表达式
        """
        collected: List[Tuple[str, str]] = []

        while self.pos < len(self.tokens):
            kind, value = self.tokens[self.pos]

            if kind == "UNIT":
                # 先检查是否是物理常数，如果是，停止解析
                if self.registry.get_constant(value) is not None:
                    break
                # 单位符号，直接收集
                collected.append(("UNIT", value))
                self.pos += 1

            elif kind == "OP" and value == "^":
                # 指数运算符，总是单位符号的一部分
                collected.append(("OP", value))
                self.pos += 1
                # 后面必须跟指数（可以是带符号的数字）
                if self.pos >= len(self.tokens):
                    raise ParseError("指数运算符 '^' 后面缺少指数值")
                exp_kind, exp_val = self.tokens[self.pos]
                if exp_kind != "NUMBER":
                    raise ParseError(f"指数必须是数字，得到 '{exp_val}'")
                collected.append(("NUMBER", exp_val))
                self.pos += 1

            elif kind == "OP" and value in ("*", "/"):
                # 乘除运算符：只有下一个 token 是 UNIT 且不是常数时才属于单位符号
                if self.pos + 1 < len(self.tokens):
                    next_kind, next_val = self.tokens[self.pos + 1]
                    if next_kind == "UNIT" and self.registry.get_constant(next_val) is None:
                        collected.append(("OP", value))
                        self.pos += 1
                    else:
                        # 下一个不是 UNIT 或是常数，停止解析，这个运算符留给表达式
                        break
                else:
                    break

            else:
                # 其他 token (NUMBER 但不是指数, OP 但不是 ^/*/, 括号等)，停止解析
                break

        if not collected:
            # 返回 None 表示没有解析到任何单位符号，调用者需要处理
            return None

        # 特殊情况: 如果只解析到单个单位符号，先尝试通过 registry.get() 获取
        # 这样可以触发 SI 前缀的动态解析
        if len(collected) == 1 and collected[0][0] == "UNIT":
            symbol = collected[0][1]
            # 先检查是否是物理常数，如果是，不消耗 token，让表达式层面处理
            if self.registry.get_constant(symbol) is not None:
                self.pos -= 1
                return None
            # 调用 registry.get() 触发前缀解析
            unit = self.registry.get(symbol)
            if unit is not None:
                return unit

        # 调用 UnitSymbolParser 解析收集到的单位 token
        usp = UnitSymbolParser(collected, self.registry)
        unit = usp.parse()
        if unit is None:
            # 尝试给出更友好的错误信息
            symbols = "".join(v for _, v in collected)
            raise ParseError(f"无法解析单位符号: '{symbols}'")

        return unit


def parse(
    expr: str,
    registry: Optional[UnitRegistry] = None,
    variables: Optional[Dict[str, Quantity]] = None
) -> Quantity:
    """
    解析带单位的表达式并返回 Quantity。

    语法增强:
      - 负数: -5 m, -3.14
      - 负指数: m^-2, s^-1
      - 隐式乘法: 2m, 3 kg m/s^2
      - 括号: (2 m)^3, (m/s)^2
      - 单位换算: 100 C to K, 100 km/h to m/s
      - 变量: 支持在表达式中使用预定义变量（如 ans, v, t 等）

    示例:
      parse("5 kg * 9.8 m/s^2")       → 49 N
      parse("1 N*m")                  → 1 J
      parse("6.674e-11 m^3/kg/s^2")   → 6.674e-11 m³·kg⁻¹·s⁻²
      parse("2m")                     → 2 m
      parse("3 kg m/s^2")             → 3 N
      parse("(2 m)^3")                → 8 m³
      parse("100 km/h to m/s")        → 27.78 m/s
    """
    reg = registry or DEFAULT_REGISTRY
    vars_dict = variables or {}

    # 先处理 " ... to ..." 语法
    to_target = None
    to_idx = None
    tokens = _expr_tokenize(expr.strip())
    for i, (kind, value) in enumerate(tokens):
        if kind == "TO":
            to_idx = i
            break

    if to_idx is not None:
        to_target = "".join(v for _, v in tokens[to_idx + 1:])
        tokens = tokens[:to_idx]

    parser = _ExprParser(tokens, reg, vars_dict)
    try:
        result = parser.parse()
    except ParseError as e:
        raise ParseError(f"解析表达式 '{expr}' 失败: {e}") from e

    if to_target:
        to_target = to_target.strip()
        try:
            result = result.to(to_target)
        except DimensionError as e:
            raise DimensionError(
                f"转换 '{expr}' 失败: {e}"
            ) from e

    return result


def q(value: float, unit: str, registry: Optional[UnitRegistry] = None) -> Quantity:
    """快速构造 Quantity。"""
    return Quantity(value, unit, registry or DEFAULT_REGISTRY)


# ─────────────────────────────────────────────
# 命令行界面
# ─────────────────────────────────────────────
_BANNER = """
╔══════════════════════════════════════════════════════════════╗
║         量纲科学计算器 (交互式) v3.0                         ║
╠══════════════════════════════════════════════════════════════╣
║  输入表达式进行计算，支持:                                   ║
║    • 基本运算: 5 kg * 9.8 m/s^2                             ║
║    • 隐式乘法: 2m, 3 kg m/s^2                               ║
║    • 单位换算: 100 C to K, 100 km/h to m/s                  ║
║    • 幂运算: (2 m)^3, m^-2                                  ║
║    • 数学函数: sin, cos, sqrt, log, exp 等                  ║
║    • 物理常数: G, c, planck, boltzmann, pi 等               ║
║    • 变量赋值: let v = 100 km/h  或  v = 100 km/h           ║
║    • 历史命令: :history 查看, !n 或 !-n 重执行              ║
║    • 定义单位: :def 符号 = 表达式   (例如 :def day = 24 h)  ║
║    • 定义别名: :alias 新符号 = 原符号                        ║
║    • 删除单位: :del 符号                                    ║
║    • 列出单位: :list [:search 关键字]                       ║
║    • 显示帮助: :help                                        ║
║    • 退出    : :q 或 :quit 或 Ctrl+C                        ║
╚══════════════════════════════════════════════════════════════╝
"""


def _print_result(qty: Quantity) -> None:
    """格式化输出 Quantity 结果。"""
    display_qty = qty
    offset = 0.0

    # 如果已经有明确的单位（如用户通过 to() 指定），就用它，不自动简化
    if qty._unit:
        val = qty.value_in_unit()
        sym = qty._unit.symbol
        dim = qty.dimension
        offset = qty._unit.offset
    else:
        # 没有明确单位，尝试简化
        simplified = qty.simplify()
        display_qty = simplified
        val = simplified.value_in_unit()
        sym = simplified._unit.symbol if simplified._unit else ""
        dim = simplified.dimension
        if simplified._unit:
            offset = simplified._unit.offset

    dim_vec = ", ".join(str(e) for e in dim.exponents)

    print(f"  数值: {val:.6g} {sym}")
    print(f"  量纲: {dim}")
    print(f"  向量: [{dim_vec}]")
    if offset != 0:
        print(f"  提示: 此单位包含零点偏移 (offset = {offset})")


def _cli_define(cmd: str, registry: UnitRegistry) -> bool:
    """处理 :def 命令。"""
    if "=" not in cmd:
        print("  错误: :def 命令格式应为 :def 符号 = 表达式")
        return False
    symbol_part, def_part = cmd.split("=", 1)
    symbol = symbol_part.strip()
    definition = def_part.strip()
    if not symbol:
        print("  错误: 单位符号不能为空")
        return False
    try:
        unit = registry.define_unit(symbol, definition=definition)
        print(f"  ✓ 已定义单位: {symbol} = {definition}")
        print(f"    量纲: {unit.dimension}, 因子: {unit.factor}")
        return True
    except (UnitDefinitionError, ParseError, DimensionError) as e:
        print(f"  错误: {e}")
        return False


def _cli_alias(cmd: str, registry: UnitRegistry) -> bool:
    """处理 :alias 命令。"""
    if "=" not in cmd:
        print("  错误: :alias 命令格式应为 :alias 新符号 = 原符号")
        return False
    new_part, old_part = cmd.split("=", 1)
    new_sym = new_part.strip()
    old_sym = old_part.strip()
    if not new_sym or not old_sym:
        print("  错误: 符号不能为空")
        return False
    try:
        registry.alias(new_sym, old_sym)
        print(f"  ✓ 已定义别名: {new_sym} → {old_sym}")
        return True
    except UnitDefinitionError as e:
        print(f"  错误: {e}")
        return False


def _cli_delete(cmd: str, registry: UnitRegistry) -> bool:
    """处理 :del 命令。"""
    symbol = cmd.strip()
    if not symbol:
        print("  错误: 请指定要删除的符号")
        return False
    if registry.unregister(symbol):
        print(f"  ✓ 已删除: {symbol}")
        return True
    print(f"  警告: 未找到符号 '{symbol}'")
    return False


def _cli_list(cmd: str, registry: UnitRegistry) -> None:
    """处理 :list 命令。"""
    search = None
    if cmd.startswith(":search"):
        search = cmd[len(":search"):].strip().lower()

    units = registry.all_units()
    aliases = registry.all_aliases()

    # 反向查找别名
    alias_for: Dict[str, List[str]] = {}
    for a, t in aliases.items():
        alias_for.setdefault(t, []).append(a)

    rows = []
    for sym, u in sorted(units.items()):
        if search and search not in sym.lower() and search not in u.name.lower():
            continue
        aliases_str = ", ".join(alias_for.get(sym, []))
        rows.append((sym, u.name, str(u.dimension), aliases_str))

    if not rows:
        print("  (无匹配项)")
        return

    # 打印表格
    sym_w = max(len(r[0]) for r in rows)
    name_w = max(len(r[1]) for r in rows)
    dim_w = max(len(r[2]) for r in rows)

    print(f"  {'符号':<{sym_w}}  {'名称':<{name_w}}  {'量纲':<{dim_w}}  别名")
    print(f"  {'─'*sym_w}  {'─'*name_w}  {'─'*dim_w}  {'─'*20}")
    for sym, name, dim, ali in rows:
        print(f"  {sym:<{sym_w}}  {name:<{name_w}}  {dim:<{dim_w}}  {ali}")

    if aliases and not search:
        print(f"\n  另有 {len(aliases)}个别名未显示，使用 :list :search 关键字 过滤")


_HELP = """
  命令列表:
    :def 符号 = 表达式      定义新单位 (例: :def day = 24 h)
    :alias 新 = 原          定义别名 (例: :alias 米 = m)
    :del 符号               删除单位或别名
    :list [:search 关键字]  列出所有单位
    :vars                   列出所有变量
    :consts                 列出所有物理常数
    :history                列出计算历史
    :help                   显示此帮助
    :q / :quit              退出

  历史命令:
    !n                      重新执行第 n 条历史命令
    !-n                     重新执行倒数第 n 条命令
    !!                      重新执行上一条命令 (同 !-1)

  变量赋值:
    let v = 100 km/h        定义变量 v
    var v = 100 km/h        同上
    v = 100 km/h            同上
    ans                     上一次计算结果

  数学函数:
    sin, cos, tan           三角函数 (支持 deg/rad)
    asin, acos, atan        反三角函数
    sinh, cosh, tanh        双曲函数
    sqrt, exp               平方根、自然指数
    log, ln, log10, log2    对数函数
    abs, floor, ceil, round 取整函数

  物理常数 (部分常用别名):
    G, c, R, e              万有引力、光速、气体常数、元电荷
    planck, boltzmann       h_p (h 被小时占用), k_b (k 被千前缀占用)
    pi, euler               圆周率 π, 自然对数底 e (e 被元电荷占用)
    gravity, avogadro       g_0 (g 被克占用), N_A
"""


def cli() -> int:
    """
    交互式命令行界面入口。

    用法: python dimensional_engine.py            → 交互式
          python dimensional_engine.py "表达式"   → 单次计算
          python dimensional_engine.py -e "表达式" -t "目标单位"
    """
    args = sys.argv[1:]

    # 单次运行模式
    if args and args[0] not in ("-h", "--help", "-i", "--interactive"):
        if args[0] == "-e":
            expr = args[1] if len(args) > 1 else ""
            target = None
            if "-t" in args:
                idx = args.index("-t")
                if idx + 1 < len(args):
                    target = args[idx + 1]
            if target:
                expr = f"{expr} to {target}"
        else:
            expr = " ".join(args)

        if not expr:
            print("错误: 请提供表达式。使用 -h 查看帮助。")
            return 1

        try:
            result = parse(expr)
            _print_result(result)
            return 0
        except (ParseError, DimensionError, UnitDefinitionError) as e:
            print(f"错误: {e}")
            return 1
        except Exception as e:
            # 捕获所有其他异常，不输出 traceback
            print(f"错误: 处理表达式时发生未知错误 - {e}")
            return 1

    # 帮助模式
    if args and args[0] in ("-h", "--help"):
        print("量纲分析与单位换算引擎")
        print()
        print("用法:")
        print(f"  {sys.argv[0]}                      启动交互式界面")
        print(f"  {sys.argv[0]} \"表达式\"             单次计算")
        print(f"  {sys.argv[0]} -e \"表达式\" [-t 目标单位]  指定表达式和目标单位")
        print(f"  {sys.argv[0]} -h                   显示此帮助")
        return 0

    # 交互式模式
    print(_BANNER)
    registry = DEFAULT_REGISTRY
    variables: Dict[str, Quantity] = {}
    last_result: Optional[Quantity] = None
    history: List[Tuple[str, Optional[Quantity]]] = []  # (expression, result)

    def _add_to_history(expr: str, result: Optional[Quantity]) -> None:
        """添加到历史记录。"""
        history.append((expr, result))

    def _get_history_entry(n: int) -> Optional[Tuple[str, Optional[Quantity]]]:
        """获取历史记录条目，支持负数索引。"""
        if n == 0:
            return None
        if n > 0:
            idx = n - 1
        else:
            idx = len(history) + n
        if 0 <= idx < len(history):
            return history[idx]
        return None

    try:
        while True:
            try:
                line = input("→ ").strip()
            except EOFError:
                print()
                break
            if not line:
                continue

            # 检查历史命令: !n, !-n, !!
            if line.startswith('!'):
                if line == '!!':
                    # 上一条命令
                    entry = _get_history_entry(-1)
                else:
                    try:
                        n = int(line[1:])
                        entry = _get_history_entry(n)
                    except ValueError:
                        print(f"  错误: 无效的历史命令 '{line}'")
                        continue
                
                if entry is None:
                    print(f"  错误: 历史记录中没有该条目")
                    continue
                
                expr, _ = entry
                print(f"  重执行: {expr}")
                line = expr

            # 检查变量赋值: let v = expr 或 var v = expr 或 v = expr
            assignment_match = re.match(r'^(?:let\s+|var\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)$', line)
            if assignment_match:
                var_name = assignment_match.group(1)
                var_expr = assignment_match.group(2)
                try:
                    # 构建包含 ans 的变量字典
                    parse_vars = dict(variables)
                    if last_result is not None:
                        parse_vars['ans'] = last_result
                    value = parse(var_expr, registry, parse_vars)
                    variables[var_name] = value
                    last_result = value
                    print(f"  已定义变量: {var_name} = {value}")
                    _print_result(value, indent="  ")
                    _add_to_history(line, value)
                except (ParseError, DimensionError, UnitDefinitionError) as e:
                    print(f"  错误: {e}")
                except Exception as e:
                    print(f"  错误: 定义变量时发生未知错误 - {e}")
                continue

            if line.startswith(":"):
                if line in (":q", ":quit", ":exit"):
                    break
                if line == ":help":
                    print(_HELP)
                    continue
                if line.startswith(":def"):
                    try:
                        _cli_define(line[4:], registry)
                    except Exception as e:
                        print(f"  错误: {e}")
                    continue
                if line.startswith(":alias"):
                    try:
                        _cli_alias(line[6:], registry)
                    except Exception as e:
                        print(f"  错误: {e}")
                    continue
                if line.startswith(":del"):
                    try:
                        _cli_delete(line[4:], registry)
                    except Exception as e:
                        print(f"  错误: {e}")
                    continue
                if line.startswith(":list"):
                    try:
                        _cli_list(line[5:], registry)
                    except Exception as e:
                        print(f"  错误: {e}")
                    continue
                if line == ":vars":
                    if variables:
                        print("  已定义变量:")
                        for name, val in variables.items():
                            print(f"    {name} = {val}")
                    else:
                        print("  没有已定义的变量。")
                    continue
                if line == ":consts":
                    consts_info = registry.get_all_constants_info()
                    if consts_info:
                        print("  物理常数:")
                        print()
                        # 找到最大宽度
                        sym_w = max(len(info['symbol']) for info in consts_info)
                        alias_w = max(len(", ".join(info['aliases'])) if info['aliases'] else 0 for info in consts_info)
                        alias_w = max(alias_w, 10)
                        
                        # 打印表头
                        header = f"  {'符号':<{sym_w}}  {'别名':<{alias_w}}  描述"
                        print(header)
                        print(f"  {'─' * sym_w}  {'─' * alias_w}  {'─' * 30}")
                        
                        for info in consts_info:
                            sym = info['symbol']
                            qty = info['quantity']
                            aliases = ", ".join(info['aliases']) if info['aliases'] else "-"
                            note = info['note']
                            
                            # 第一行：符号、别名、描述
                            print(f"  {sym:<{sym_w}}  {aliases:<{alias_w}}  {note}")
                            # 第二行：数值和量纲
                            val_str = f"    = {qty.value_in_unit():.6g} {qty._unit.symbol if qty._unit else ''}  [{qty.dimension}]"
                            print(val_str)
                            print()
                        
                        # 显示冲突提示
                        conflicts = [info for info in consts_info if '被' in info.get('note', '')]
                        if conflicts:
                            print("  💡 提示: 以下常用符号与现有单位冲突，已提供别名:")
                            for info in conflicts:
                                print(f"     • {info['note']}")
                            print()
                    else:
                        print("  没有已注册的物理常数。")
                    continue
                if line == ":history":
                    if not history:
                        print("  暂无历史记录。")
                    else:
                        print("  历史记录:")
                        print()
                        print(f"  {'#':>3}  {'表达式':<40}  结果")
                        print(f"  {'─'*3}  {'─'*40}  {'─'*20}")
                        for i, (expr, result) in enumerate(history, 1):
                            result_str = f"{result:.6g}" if result else "(错误)"
                            expr_display = expr if len(expr) <= 38 else expr[:36] + "..."
                            print(f"  {i:>3}  {expr_display:<40}  {result_str}")
                        print()
                        print("  使用 !n 重执行第 n 条，!-n 重执行倒数第 n 条，!! 重执行上一条")
                        print()
                    continue
                print(f"  未知命令: {line}。输入 :help 查看命令列表。")
                continue

            try:
                # 构建包含 ans 的变量字典
                parse_vars = dict(variables)
                if last_result is not None:
                    parse_vars['ans'] = last_result
                
                result = parse(line, registry, parse_vars)
                last_result = result
                _print_result(result)
                _add_to_history(line, result)
            except (ParseError, DimensionError, UnitDefinitionError, KeyError) as e:
                print(f"  错误: {e}")
            except Exception as e:
                print(f"  错误: 计算时发生未知错误 - {e}")

    except KeyboardInterrupt:
        print("\n\n再见!")

    print("退出。")
    return 0


if __name__ == "__main__":
    sys.exit(cli())
