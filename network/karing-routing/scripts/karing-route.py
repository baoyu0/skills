#!/usr/bin/env python3
"""
karing-route — Karing 路由规则管理 CLI
为指定路由组添加域名白名单，无需手动改 JSON。

用法:
  karing-route add <路由组名> <域名1> [域名2 ...]
  karing-route list [--all]
  karing-route restart
  karing-route check <域名>
  karing-route help

示例:
  karing-route add "🎯 国内直连" rsshub.app
  karing-route list
  karing-route check objects.githubusercontent.com
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


KARING_PORT: int = 3067
KARING_PORT_STR: str = f":{KARING_PORT} "

# Karing 配置路径（可通过环境变量 KARING_CONFIG 覆盖）
CONFIG_PATH: Path = Path(
    os.environ.get(
        "KARING_CONFIG",
        r"C:\Users\zhaid\AppData\Roaming\Karing\karing\service_core.json",
    )
)

# 系统内部规则名前缀（list 命令中默认隐藏）
SYSTEM_RULE_PREFIXES: Tuple[str, ...] = ("direct[", "proxy[", "current[", "cn[", "ip_is_")
# 用户关心的自定义路由组（含 [自定义] 后缀的）
CUSTOM_RULE_NAMES: List[str] = [
    "🛑 广告拦截[自定义]", "🛑 恶意软件[自定义]", "🍃 应用净化[自定义]",
    "🎶 网易音乐[自定义]", "📺 哔哩哔哩[自定义]",
    "🎯 国内直连[自定义]", "📹 油管视频[自定义]", "🐱 GitHub[自定义]",
    "🌏 Google Play[自定义]", "🌏 Google[自定义]", "♊️ Google Gemini[自定义]",
    "📢 Google FCM[自定义]", "🎧 TikTok[自定义]", "📸 Instagram[自定义]",
    "🎥 奈飞视频[自定义]", "📲 电报消息[自定义]",
    "🌐 Reddit[自定义]", "🌐 Skywork[自定义]",
    "🐦 X/Twitter[自定义]", "💬 Discord[自定义]", "💬 Claude[自定义]",
    "💬 OpenAI[自定义]", "🤖 DeepSeek[自定义]",
    "Ⓜ️ 微软Bing[自定义]", "Ⓜ️ 微软云盘[自定义]", "Ⓜ️ 微软服务[自定义]",
    "🎮 游戏平台[自定义]", "🍎 苹果服务[自定义]", "🌏 国外穿墙[自定义]",
]


# ══════════════════════════════════════════════
# 配置读写（原子写入）
# ══════════════════════════════════════════════


def load_config() -> dict:
    """加载 Karing 配置，失败时退出。"""
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Karing 配置文件不存在: {CONFIG_PATH}")
        print("请确认 Karing 已安装并运行过至少一次")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"配置文件解析失败: {e}")
        sys.exit(1)
    except PermissionError:
        print(f"无权限读取配置文件: {CONFIG_PATH}")
        sys.exit(1)


def save_config(cfg: dict) -> None:
    """原子写入配置（tmp 文件 → rename，防止中断损坏）。"""
    tmp: str = str(CONFIG_PATH) + ".tmp"
    try:
        Path(tmp).write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, str(CONFIG_PATH))
    except IOError as e:
        print(f"写入配置文件失败: {e}")
        sys.exit(1)


# ══════════════════════════════════════════════
# 路由规则工具函数
# ══════════════════════════════════════════════


def is_system_rule(rule: dict) -> bool:
    """判断是否为系统内部规则（不展示给用户）。"""
    name: str = rule.get("name", "")
    if not name:
        return True  # 无 name 的规则（inbound sniff 等）
    return name.startswith(SYSTEM_RULE_PREFIXES) or name.startswith("[rule ")


def get_rule_domains(rule: dict) -> List[str]:
    """从路由规则中提取 domain_suffix 列表。"""
    domains: List[str] = []
    for sub in rule.get("rules", []):
        if "domain_suffix" in sub:
            domains.extend(sub["domain_suffix"])
    return domains


def find_custom_rule(cfg: dict, name: str) -> Optional[dict]:
    """精确查找自定义路由组。"""
    for rule in cfg.get("route", {}).get("rules", []):
        if rule.get("name") == name and "[自定义]" in rule.get("name", ""):
            return rule
    return None


def get_custom_rule_names(cfg: Optional[dict] = None) -> List[str]:
    """从配置动态提取自定义路由组名称，回退到静态列表。"""
    if cfg is None:
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return CUSTOM_RULE_NAMES
    names: List[str] = []
    for rule in cfg.get("route", {}).get("rules", []):
        if not is_system_rule(rule):
            name: str = rule.get("name", "")
            if name:
                names.append(name)
    return names if names else CUSTOM_RULE_NAMES


# ══════════════════════════════════════════════
# 命令实现
# ══════════════════════════════════════════════


def cmd_list(show_all: bool = False) -> None:
    """列出路由规则。"""
    cfg: dict = load_config()
    rules: list = cfg.get("route", {}).get("rules", [])
    custom: list = [r for r in rules if not is_system_rule(r)]
    system: list = [r for r in rules if is_system_rule(r)]

    print(f"Karing 路由规则 — {len(custom)} 自定义 + {len(system)} 系统\n")

    for i, rule in enumerate(custom):
        name: str = rule.get("name", "?")
        outbound: str = rule.get("outbound", "N/A")
        domains: List[str] = get_rule_domains(rule)
        domain_str: str = f" ({', '.join(domains[:5])})" if domains else ""
        out_str: str = f" → {outbound}" if outbound else ""
        print(f"  [{i}] {name}{out_str}{domain_str}")

    if show_all and system:
        print(f"\n  系统规则 ({len(system)} 条):")
        for rule in system:
            print(f"      {rule.get('name', '?')}")
    elif system:
        print(f"\n  系统规则 ({len(system)} 条，已隐藏，加 --all 显示)")


def cmd_add(route_name: str, *domains: str) -> None:
    """添加域名到指定路由组。"""
    cfg: dict = load_config()
    rule: Optional[dict] = find_custom_rule(cfg, route_name)

    if not rule:
        # 尝试模糊匹配
        matches: list = [
            r for r in cfg.get("route", {}).get("rules", [])
            if route_name.lower() in r.get("name", "").lower()
        ]
        if len(matches) == 1:
            rule = matches[0]
            print(f"模糊匹配到: {rule['name']}")
        elif len(matches) > 1:
            print(f"找到多个匹配，请指定完整路由组名:")
            for m in matches:
                print(f"  {m['name']}")
            rule_names: List[str] = get_custom_rule_names(cfg)
            print(f"\n可用路由组: {', '.join(rule_names)}")
            return
        else:
            print(f"未找到路由组 '{route_name}'")
            rule_names = get_custom_rule_names(cfg)
            print(f"可用路由组:\n  " + "\n  ".join(rule_names))
            return

    # 查找或创建 domain_suffix 子规则
    found: bool = False
    for sub in rule.get("rules", []):
        if "domain_suffix" in sub:
            existing: Set[str] = set(sub["domain_suffix"])
            added: List[str] = sorted(d for d in domains if d not in existing)
            if not added:
                print("✅ 全部域名已存在，无需添加")
                return
            sub["domain_suffix"].extend(added)
            found = True
            print(f"已添加 → {rule['name']}: {added}")
            break

    if not found:
        rule.setdefault("rules", []).insert(0, {"domain_suffix": sorted(domains)})
        print(f"已创建 domain_suffix → {rule['name']}: {list(domains)}")

    save_config(cfg)


def cmd_restart() -> None:
    """重启 karingService.exe。"""
    print("重启 karingService.exe...")
    try:
        r: subprocess.CompletedProcess = subprocess.run(
            ["taskkill", "/F", "/IM", "karingService.exe"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            print("✅ 已停止")
        else:
            print(f"⚠️ 停止进程: {r.stderr.strip() or '进程不存在'}")
            print("等待 GUI 自动拉起服务...")
    except subprocess.TimeoutExpired:
        print("⚠️ 停止进程超时")
        return
    except FileNotFoundError:
        print("⚠️ taskkill 命令不存在（非 Windows 系统？）")
        return

    # 用原生 Python 检查端口（替代 findstr 管道）
    print(f"等待 {KARING_PORT} 端口恢复...", end=" ", flush=True)
    for _ in range(10):
        time.sleep(1)
        if _check_port_listening(KARING_PORT):
            print("✅ 已恢复!")
            return
        print(".", end="", flush=True)

    print(f"⚠️ 超时，{KARING_PORT} 端口未恢复。请检查 Karing GUI 是否运行。")


def _check_port_listening(port: int) -> bool:
    """检查指定端口是否处于 LISTENING 状态（纯 Python，无需 findstr）。"""
    try:
        result: subprocess.CompletedProcess = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if f":{port} " in line and "LISTENING" in line:
                return True
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def cmd_check(domain: str) -> None:
    """检查域名当前被哪个路由组匹配。"""
    cfg: dict = load_config()
    rules: list = cfg.get("route", {}).get("rules", [])

    # 第一轮：精确 domain_suffix 匹配
    for i, rule in enumerate(rules):
        for sub in rule.get("rules", []):
            if "domain_suffix" in sub:
                for suffix in sub["domain_suffix"]:
                    if domain == suffix or domain.endswith("." + suffix):
                        print(f"  ✅ [{i}] {rule['name']} → {rule.get('outbound', 'N/A')}")
                        print(f"     规则: domain_suffix {suffix}")
                        return

    # 第二轮：rule_set / domain_keyword 模糊匹配
    for i, rule in enumerate(rules):
        for sub in rule.get("rules", []):
            if "rule_set" in sub:
                for rs in sub["rule_set"]:
                    tld: str = domain.rsplit(".", 1)[-1] if "." in domain else domain
                    if tld in rs or domain.split(".")[0] in rs:
                        print(f"  ℹ️ [{i}] {rule['name']} (rule_set: {rs}) → {rule.get('outbound', 'N/A')}")

            if "domain_keyword" in sub:
                for kw in sub["domain_keyword"]:
                    if kw.lower() in domain.lower():
                        print(f"  ℹ️ [{i}] {rule['name']} (domain_keyword: {kw}) → {rule.get('outbound', 'N/A')}")

    print(f"  ⚠️ 未找到精确 domain_suffix 匹配 (上方为模糊匹配结果)")


def print_help() -> None:
    """打印帮助信息。"""
    print(__doc__)


# ══════════════════════════════════════════════
# 入口
# ══════════════════════════════════════════════


def main() -> None:
    """CLI 入口。"""
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print_help()
        return

    cmd: str = sys.argv[1]

    if cmd == "list":
        show_all: bool = "--all" in sys.argv
        cmd_list(show_all)
    elif cmd == "add" and len(sys.argv) >= 4:
        cmd_add(sys.argv[2], *sys.argv[3:])
    elif cmd == "restart":
        cmd_restart()
    elif cmd == "check" and len(sys.argv) >= 3:
        cmd_check(sys.argv[2])
    else:
        print(f"karing-route: 未知命令或参数不足 '{cmd}'")
        print_help()


if __name__ == "__main__":
    main()
