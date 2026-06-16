import subprocess
import sys

print('=== 测试 CLI 错误处理 ===')
print()

# 测试 1: 无效字符
print('测试 1: 无效字符')
result = subprocess.run(
    [sys.executable, 'dimensional_engine.py', '1 m @ 2 s'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print(f'  命令: python dimensional_engine.py "1 m @ 2 s"')
print(f'  退出码: {result.returncode}')
print(f'  输出: {result.stdout.strip() if result.stdout else ""}{result.stderr.strip() if result.stderr else ""}')
print(f'  有 traceback: {"Traceback" in result.stdout or "Traceback" in result.stderr}')
print()

# 测试 2: 未知单位
print('测试 2: 未知单位')
result = subprocess.run(
    [sys.executable, 'dimensional_engine.py', '5 xyz'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print(f'  命令: python dimensional_engine.py "5 xyz"')
print(f'  退出码: {result.returncode}')
print(f'  输出: {result.stdout.strip() if result.stdout else ""}{result.stderr.strip() if result.stderr else ""}')
print(f'  有 traceback: {"Traceback" in result.stdout or "Traceback" in result.stderr}')
print()

# 测试 3: 未知转换目标
print('测试 3: 未知转换目标')
result = subprocess.run(
    [sys.executable, 'dimensional_engine.py', '1 m to xyz'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print(f'  命令: python dimensional_engine.py "1 m to xyz"')
print(f'  退出码: {result.returncode}')
print(f'  输出: {result.stdout.strip() if result.stdout else ""}{result.stderr.strip() if result.stderr else ""}')
print(f'  有 traceback: {"Traceback" in result.stdout or "Traceback" in result.stderr}')
print()

# 测试 4: 量纲不匹配
print('测试 4: 量纲不匹配转换')
result = subprocess.run(
    [sys.executable, 'dimensional_engine.py', '1 m to kg'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print(f'  命令: python dimensional_engine.py "1 m to kg"')
print(f'  退出码: {result.returncode}')
print(f'  输出: {result.stdout.strip() if result.stdout else ""}{result.stderr.strip() if result.stderr else ""}')
print(f'  有 traceback: {"Traceback" in result.stdout or "Traceback" in result.stderr}')
print()

# 测试 5: 正确表达式（验证正常工作）
print('测试 5: 正确表达式（验证正常工作）')
result = subprocess.run(
    [sys.executable, 'dimensional_engine.py', 'G * 5.972e24 kg * 1 kg / (6.371e6 m)^2 to N'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print(f'  命令: python dimensional_engine.py "G * 5.972e24 kg * 1 kg / (6.371e6 m)^2 to N"')
print(f'  退出码: {result.returncode}')
print(f'  输出: {result.stdout.strip() if result.stdout else ""}{result.stderr.strip() if result.stderr else ""}')
print(f'  有 traceback: {"Traceback" in result.stdout or "Traceback" in result.stderr}')
print()

# 测试 6: SI 前缀
print('测试 6: SI 前缀')
result = subprocess.run(
    [sys.executable, 'dimensional_engine.py', '1 ms to s'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print(f'  命令: python dimensional_engine.py "1 ms to s"')
print(f'  退出码: {result.returncode}')
print(f'  输出: {result.stdout.strip() if result.stdout else ""}{result.stderr.strip() if result.stderr else ""}')
print()

# 测试 7: 夹杂奇怪符号
print('测试 7: 夹杂奇怪符号')
result = subprocess.run(
    [sys.executable, 'dimensional_engine.py', '1 m # 2 s'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
print(f'  命令: python dimensional_engine.py "1 m # 2 s"')
print(f'  退出码: {result.returncode}')
print(f'  输出: {result.stdout.strip() if result.stdout else ""}{result.stderr.strip() if result.stderr else ""}')
print(f'  有 traceback: {"Traceback" in result.stdout or "Traceback" in result.stderr}')
