"""
量纲分析与单位换算引擎
======================
支持基本量纲(长度/质量/时间/温度/电流/物质的量/发光强度)及其组合，
换算时校验量纲一致性，解析带单位的表达式并计算结果含单位。

核心设计
--------
1. 每个量纲用 7 维指数向量表示，对应 SI 七个基本量纲:
   [长度, 质量, 时间, 温度, 电流, 物质的量, 发光强度]
   例: 速度 = 长度¹·时间⁻¹ → [1, 0, -1, 0, 0, 0, 0]
       力   = 质量¹·长度¹·时间⁻² → [1, 1, -2, 0, 0, 0, 0]

2. 乘法 → 指数相加; 除法 → 指数相减
3. 加减法 → 强制要求量纲完全一致，否则抛出 DimensionError
4. 单位换算 → 每个单位记录相对基本单位的换算因子(factor)和偏移(offset)
5. 温度偏移 → 摄氏/华氏等换算带 offset，convert 时用 value * factor + offset
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional, Sequence, Tuple, Union

BASE_DIM_NAMES = ("length", "mass", "time", "temperature", "current", "amount", "luminosity")
BASE_DIM_SYMBOLS = ("L", "M", "T", "Θ", "I", "N", "J")
_DIM_INDEX = {name: i for i, name in enumerate(BASE_DIM_NAMES)}


class DimensionError(Exception):
    """量纲不一致时抛出的异常。"""
    pass


class Dimension:
    """
    用指数向量表示物理量纲。

    每个分量是一个 Fraction，保证精确运算。
    例: 速度  → Dimension(length=1, time=-1)
        无量纲 → Dimension()  (全零向量)
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
        """乘法 → 指数相加"""
        return Dimension.from_vector(a + b for a, b in zip(self._exponents, other._exponents))

    def __truediv__(self, other: "Dimension") -> "Dimension":
        """除法 → 指数相减"""
        return Dimension.from_vector(a - b for a, b in zip(self._exponents, other._exponents))

    def __pow__(self, n: Union[int, float, Fraction]) -> "Dimension":
        """幂运算 → 指数乘以 n"""
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


class UnitDef:
    """
    单位定义。

    Attributes
    ----------
    name : str       单位全名 (如 "meter")
    symbol : str     单位符号 (如 "m")
    dimension : Dimension  对应量纲
    factor : float   相对基本单位的换算因子 (1 此单位 = factor 个基本单位)
    offset : float   偏移量 (用于温度等非线性换算)
                     含义: value_base = (value_this + offset) * factor
                     对于绝对单位 (m, kg, s) offset=0

    换算公式
    --------
    value_base = (value_this + offset) * factor
    value_this = value_base / factor - offset
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
        """将此单位的值转换为基本单位的值。"""
        return (value + self.offset) * self.factor

    def from_base(self, value_base: float) -> float:
        """将基本单位的值转换为此单位的值。"""
        return value_base / self.factor - self.offset

    def __repr__(self) -> str:
        return f"UnitDef({self.symbol!r}, {self.dimension})"


class UnitRegistry:
    """
    单位注册表，管理所有已知单位。

    每个单位通过符号(symbol)索引。复合单位(如 m/s)在运算时
    动态构造，不需要预注册。
    """

    def __init__(self):
        self._units: Dict[str, UnitDef] = {}
        self._init_si()
        self._init_imperial()
        self._init_temperature()
        self._init_derived()

    def register(self, unit: UnitDef) -> None:
        if unit.symbol in self._units:
            raise ValueError(f"单位符号冲突: {unit.symbol}")
        self._units[unit.symbol] = unit

    def get(self, symbol: str) -> Optional[UnitDef]:
        return self._units.get(symbol)

    def __getitem__(self, symbol: str) -> UnitDef:
        u = self._units.get(symbol)
        if u is None:
            raise KeyError(f"未知单位: {symbol}")
        return u

    def __contains__(self, symbol: str) -> bool:
        return symbol in self._units

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
        """
        温度换算 (带偏移)
        -----------------
        基本单位为开尔文(K)。
        factor 的含义: 1 K = factor 个此单位
        offset 的含义: 此单位的零点比 K 的零点低 offset 个此单位

        摄氏度: T_K = T_C + 273.15,  1 K = 1 °C  → factor=1, offset=273.15
        华氏度: T_K = (T_F + 459.67) × 5/9, 1 K = 9/5 °F → factor=9/5, offset=459.67

        验证:
          to_base(0°C) = (0 + 273.15) * 1 = 273.15 K  ✓
          from_base(273.15) = 273.15 / 1 - 273.15 = 0 °C  ✓
          to_base(32°F) = (32 + 459.67) * (9/5) = 491.67 * 1.8 = ... 
          等等，我需要重新推导。

        通用公式: value_base = (value_this + offset) * factor
        其中 value_base 是基本单位(K)的值

        对于摄氏度: T_K = T_C + 273.15
          → value_base = value_C + 273.15 = (value_C + 273.15) * 1
          → factor = 1, offset = 273.15  ✓

        对于华氏度: T_K = (T_F + 459.67) * 5/9
          → value_base = (value_F + 459.67) * 5/9
          → factor = 5/9, offset = 459.67

        验证: to_base(32°F) = (32 + 459.67) * 5/9 = 491.67 * 5/9 = 273.15 K ✓
        验证: from_base(373.15) = 373.15 / (5/9) - 459.67 = 373.15 * 9/5 - 459.67 = 671.67 - 459.67 = 212°F ✓
        """
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
        self.register(UnitDef("km/h", "km/h", Dimension(length=1, time=-1), factor=(1 / 3.6)))
        self.register(UnitDef("m/s", "m/s", Dimension(length=1, time=-1)))
        self.register(UnitDef("g_per_cm3", "g/cm3", Dimension(mass=1, length=-3), factor=1000))
        self.register(UnitDef("knot", "kn", Dimension(length=1, time=-1), factor=0.514444))


DEFAULT_REGISTRY = UnitRegistry()


class Quantity:
    """
    带量纲和单位的物理量。

    内部始终以基本单位的值存储(value_base)，同时记录
    当前显示单位(unit)以便格式化输出。

    算术规则
    --------
    - 乘法: 值相乘，量纲指数相加
    - 除法: 值相除，量纲指数相减
    - 加法: 值相加，量纲必须完全一致
    - 减法: 值相减，量纲必须完全一致
    - 幂运算: 值取幂，量纲指数乘以指数
    """

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
        """
        转换到目标单位。

        量纲必须一致；否则抛出 DimensionError。
        """
        if isinstance(target_unit, str):
            target = self._registry[target_unit]
        else:
            target = target_unit
        if self._dimension != target.dimension:
            raise DimensionError(
                f"量纲不一致: 当前={self._dimension}, 目标={target.dimension}"
            )
        new_value = target.from_base(self._value_base)
        return Quantity(new_value, target, self._registry)

    def to_value(self, target_unit: Union[str, UnitDef]) -> float:
        """转换到目标单位并返回纯数值。"""
        return self.to(target_unit).value_in_unit()

    def value_in_unit(self) -> float:
        """返回当前单位下的数值。"""
        if self._unit is None:
            return self._value_base
        return self._unit.from_base(self._value_base)

    def __mul__(self, other: Union["Quantity", float, int]) -> "Quantity":
        if isinstance(other, (int, float)):
            return Quantity.from_base(
                self._value_base * other, self._dimension, self._unit, self._registry
            )
        if isinstance(other, Quantity):
            new_dim = self._dimension * other._dimension
            new_val = self._value_base * other._value_base
            return Quantity.from_base(new_val, new_dim, registry=self._registry)
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
            return Quantity.from_base(new_val, new_dim, registry=self._registry)
        return NotImplemented

    def __rtruediv__(self, other: Union[float, int]) -> "Quantity":
        if isinstance(other, (int, float)):
            new_dim = DIMENSIONLESS / self._dimension
            new_val = other / self._value_base
            return Quantity.from_base(new_val, new_dim, registry=self._registry)
        return NotImplemented

    def __add__(self, other: "Quantity") -> "Quantity":
        if not isinstance(other, Quantity):
            return NotImplemented
        if self._dimension != other._dimension:
            raise DimensionError(
                f"不能将 {self._dimension} 加到 {other._dimension} 上"
            )
        return Quantity.from_base(
            self._value_base + other._value_base, self._dimension, self._unit, self._registry
        )

    def __sub__(self, other: "Quantity") -> "Quantity":
        if not isinstance(other, Quantity):
            return NotImplemented
        if self._dimension != other._dimension:
            raise DimensionError(
                f"不能从 {self._dimension} 减去 {other._dimension}"
            )
        return Quantity.from_base(
            self._value_base - other._value_base, self._dimension, self._unit, self._registry
        )

    def __pow__(self, n: Union[int, float]) -> "Quantity":
        new_dim = self._dimension ** n
        new_val = self._value_base ** n
        return Quantity.from_base(new_val, new_dim, registry=self._registry)

    def __neg__(self) -> "Quantity":
        return Quantity.from_base(-self._value_base, self._dimension, self._unit, self._registry)

    def __abs__(self) -> "Quantity":
        return Quantity.from_base(abs(self._value_base), self._dimension, self._unit, self._registry)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Quantity):
            return NotImplemented
        if self._dimension != other._dimension:
            return False
        return math.isclose(self._value_base, other._value_base, rel_tol=1e-9)

    def __lt__(self, other: "Quantity") -> bool:
        if not isinstance(other, Quantity):
            return NotImplemented
        if self._dimension != other._dimension:
            raise DimensionError(
                f"不能比较 {self._dimension} 与 {other._dimension}"
            )
        return self._value_base < other._value_base

    def __le__(self, other: "Quantity") -> bool:
        return self == other or self < other

    def __gt__(self, other: "Quantity") -> bool:
        if not isinstance(other, Quantity):
            return NotImplemented
        if self._dimension != other._dimension:
            raise DimensionError(
                f"不能比较 {self._dimension} 与 {other._dimension}"
            )
        return self._value_base > other._value_base

    def __ge__(self, other: "Quantity") -> bool:
        return self == other or self > other

    def __repr__(self) -> str:
        if self._unit:
            val = self._unit.from_base(self._value_base)
            return f"{val:.6g} {self._unit.symbol}"
        return f"{self._value_base:.6g} [{self._dimension}]"

    def __str__(self) -> str:
        return self.__repr__()


# ─────────────────────────────────────────────
# 表达式解析器
# ─────────────────────────────────────────────

_TOKEN_PATTERNS = [
    ("NUMBER", r"\d+\.?\d*(?:[eE][+-]?\d+)?"),
    ("UNIT", r"[a-zA-Z][a-zA-Z0-9_/°]*"),
    ("OP", r"[+\-*/^()]"),
    ("WS", r"\s+"),
]
_TOKEN_RE = re.compile("|".join(f"(?P<{name}>{pat})" for name, pat in _TOKEN_PATTERNS))


def _tokenize(expr: str) -> List[Tuple[str, str]]:
    tokens = []
    for m in _TOKEN_RE.finditer(expr):
        kind = m.lastgroup
        value = m.group()
        if kind == "WS":
            continue
        tokens.append((kind, value))
    return tokens


class _Parser:
    """
    递归下降解析器，支持:
      - 数字 + 单位 (如 100 km/h)
      - 加减乘除幂运算
      - 括号分组

    文法 (简化):
      expr   = term (('+' | '-') term)*
      term   = factor (('*' | '/') factor)*
      factor = atom ('^' number)?
      atom   = NUMBER [UNIT] | '(' expr ')'
    """

    def __init__(self, tokens: List[Tuple[str, str]], registry: UnitRegistry):
        self.tokens = tokens
        self.pos = 0
        self.registry = registry

    def peek(self) -> Optional[Tuple[str, str]]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected_kind: Optional[str] = None) -> Tuple[str, str]:
        tok = self.peek()
        if tok is None:
            raise SyntaxError("意外的表达式结尾")
        if expected_kind and tok[0] != expected_kind:
            raise SyntaxError(f"期望 {expected_kind}，得到 {tok[0]}({tok[1]})")
        self.pos += 1
        return tok

    def parse(self) -> Quantity:
        result = self.expr()
        if self.pos < len(self.tokens):
            raise SyntaxError(f"多余的标记: {self.tokens[self.pos:]}")
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
        base = self.atom()
        tok = self.peek()
        if tok and tok[0] == "OP" and tok[1] == "^":
            self.consume()
            exp_tok = self.consume("NUMBER")
            exp = float(exp_tok[1])
            base = base ** exp
        return base

    def atom(self) -> Quantity:
        tok = self.peek()
        if tok is None:
            raise SyntaxError("意外的表达式结尾")

        if tok[0] == "OP" and tok[1] == "(":
            self.consume()
            result = self.expr()
            self.consume("OP")  # ')'
            return result

        if tok[0] == "NUMBER":
            self.consume()
            value = float(tok[1])
            next_tok = self.peek()
            if next_tok and next_tok[0] == "UNIT":
                unit_tok = self.consume()
                symbol = unit_tok[1]
                unit_def = self.registry.get(symbol)
                if unit_def is None:
                    unit_def = self._try_parse_compound_unit(symbol)
                    if unit_def is None:
                        raise KeyError(f"未知单位: {symbol}")
                return Quantity(value, unit_def, self.registry)
            else:
                dimless = UnitDef("dimensionless", "1", DIMENSIONLESS)
                return Quantity(value, dimless, self.registry)

        if tok[0] == "UNIT":
            unit_tok = self.consume()
            symbol = unit_tok[1]
            unit_def = self.registry.get(symbol)
            if unit_def is None:
                raise KeyError(f"未知单位: {symbol}")
            dimless = UnitDef("dimensionless", "1", DIMENSIONLESS)
            return Quantity(1.0, unit_def, self.registry)

        raise SyntaxError(f"意外的标记: {tok}")

    def _try_parse_compound_unit(self, symbol: str) -> Optional[UnitDef]:
        """
        尝试解析复合单位符号，如 m/s, kg*m/s^2 等。
        仅处理简单的 A/B 或 A*B/C 形式。
        """
        if "/" in symbol:
            parts = symbol.split("/", 1)
            num_part = parts[0].strip()
            den_part = parts[1].strip()

            num_unit = self.registry.get(num_part)
            den_unit = self.registry.get(den_part)
            if num_unit and den_unit:
                combined_dim = num_unit.dimension / den_unit.dimension
                combined_factor = num_unit.factor / den_unit.factor
                return UnitDef(symbol, symbol, combined_dim, factor=combined_factor)

        if "*" in symbol:
            parts = symbol.split("*")
            combined_dim = Dimension()
            combined_factor = Fraction(1)
            for p in parts:
                u = self.registry.get(p.strip())
                if not u:
                    return None
                combined_dim = combined_dim * u.dimension
                combined_factor = combined_factor * Fraction(u.factor).limit_denominator(10**12)
            return UnitDef(symbol, symbol, combined_dim, factor=float(combined_factor))

        return None


def parse(expr: str, registry: Optional[UnitRegistry] = None) -> Quantity:
    """
    解析带单位的表达式并返回 Quantity。

    示例
    ----
    >>> parse("100 km/h + 20 m/s")
    >>> parse("5 kg * 9.8 m/s^2")
    >>> parse("100 C to K")
    """
    reg = registry or DEFAULT_REGISTRY

    to_target = None
    if " to " in expr:
        expr, to_target = expr.split(" to ", 1)
        to_target = to_target.strip()

    tokens = _tokenize(expr.strip())
    parser = _Parser(tokens, reg)
    result = parser.parse()

    if to_target:
        result = result.to(to_target)

    return result


def q(value: float, unit: str, registry: Optional[UnitRegistry] = None) -> Quantity:
    """快速构造 Quantity 的简写。"""
    return Quantity(value, unit, registry or DEFAULT_REGISTRY)
