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

import json, subprocess, sys, os, time

CONFIG_PATH = r"C:\Users\zhaid\AppData\Roaming\Karing\karing\service_core.json"

# 系统内部规则名前缀（list 命令中默认隐藏）
SYSTEM_RULE_PREFIXES = ("direct[", "proxy[", "current[", "cn[", "ip_is_")
# 用户关心的自定义路由组（含 [自定义] 后缀的）
CUSTOM_RULE_NAMES = [
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


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def is_system_rule(rule):
    """判断是否为系统内部规则（不展示给用户）"""
    name = rule.get("name", "")
    if not name:
        return True  # 无 name 的规则（inbound sniff 等）
    return name.startswith(SYSTEM_RULE_PREFIXES) or name.startswith("[rule ")


def get_rule_domains(rule):
    """从路由规则中提取 domain_suffix 列表"""
    domains = []
    for sub in rule.get("rules", []):
        if "domain_suffix" in sub:
            domains.extend(sub["domain_suffix"])
    return domains


def find_custom_rule(cfg, name):
    """精确查找自定义路由组"""
    for rule in cfg.get("route", {}).get("rules", []):
        if rule.get("name") == name and "[自定义]" in rule.get("name", ""):
            return rule
    return None


def cmd_list(show_all=False):
    cfg = load_config()
    rules = cfg.get("route", {}).get("rules", [])
    custom = [r for r in rules if not is_system_rule(r)]
    system = [r for r in rules if is_system_rule(r)]

    print(f"Karing 路由规则 — {len(custom)} 自定义 + {len(system)} 系统\n")

    for i, rule in enumerate(custom):
        name = rule.get("name", "?")
        outbound = rule.get("outbound", "N/A")
        domains = get_rule_domains(rule)
        domain_str = f" ({', '.join(domains[:5])})" if domains else ""
        out_str = f" → {outbound}" if outbound else ""
        print(f"  [{i}] {name}{out_str}{domain_str}")

    if show_all and system:
        print(f"\n  系统规则 ({len(system)} 条，已隐藏，加 --all 显示):")
        for rule in system:
            print(f"      {rule.get('name', '?')}")


def cmd_add(route_name, *domains):
    cfg = load_config()
    rule = find_custom_rule(cfg, route_name)

    if not rule:
        # 尝试模糊匹配
        matches = [r for r in cfg.get("route", {}).get("rules", [])
                   if route_name.lower() in r.get("name", "").lower()]
        if len(matches) == 1:
            rule = matches[0]
            print(f"模糊匹配到: {rule['name']}")
        elif len(matches) > 1:
            print(f"找到多个匹配，请指定完整路由组名:")
            for m in matches:
                print(f"  {m['name']}")
            print(f"\n可用路由组: {', '.join(CUSTOM_RULE_NAMES)}")
            return
        else:
            print(f"未找到路由组 '{route_name}'")
            print(f"可用路由组:\n  " + "\n  ".join(CUSTOM_RULE_NAMES))
            return

    # 查找或创建 domain_suffix 子规则
    found = False
    for sub in rule.get("rules", []):
        if "domain_suffix" in sub:
            existing = set(sub["domain_suffix"])
            added = sorted(d for d in domains if d not in existing)
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


def cmd_restart():
    print("重启 karingService.exe...")
    r = subprocess.run(["taskkill", "/F", "/IM", "karingService.exe"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        print("✅ 已停止")
    else:
        print(f"⚠️ 停止进程返回: {r.stderr.strip()}")
        print("等待 GUI 自动拉起服务...")

    # 验证端口恢复（最多等 10 秒）
    print("等待 3067 端口恢复...", end=" ", flush=True)
    for attempt in range(10):
        time.sleep(1)
        check = subprocess.run(
            "netstat -ano | findstr \":3067 \"",
            shell=True, capture_output=True, text=True
        )
        if "LISTENING" in check.stdout:
            print("✅ 已恢复!")
            return
        print(".", end="", flush=True)

    print("⚠️ 超时，3067 端口未恢复。请检查 Karing GUI 是否运行。")


def cmd_check(domain):
    """检查域名当前被哪个路由组匹配"""
    cfg = load_config()
    rules = cfg.get("route", {}).get("rules", [])

    # 第一轮：精确 domain_suffix 匹配
    for i, rule in enumerate(rules):
        for sub in rule.get("rules", []):
            if "domain_suffix" in sub:
                # 精确匹配（域名本身或子域名）
                for suffix in sub["domain_suffix"]:
                    if domain == suffix or domain.endswith("." + suffix):
                        print(f"  ✅ [{i}] {rule['name']} → {rule.get('outbound', 'N/A')}")
                        print(f"     规则: domain_suffix {suffix}")
                        return

    # 第二轮：rule_set / domain_keyword / name 模糊匹配
    for i, rule in enumerate(rules):
        for sub in rule.get("rules", []):
            if "rule_set" in sub:
                for rs in sub["rule_set"]:
                    tld = domain.rsplit(".", 1)[-1] if "." in domain else domain
                    if tld in rs or domain.split(".")[0] in rs:
                        print(f"  ℹ️ [{i}] {rule['name']} (rule_set: {rs}) → {rule.get('outbound', 'N/A')}")

            if "domain_keyword" in sub:
                for kw in sub["domain_keyword"]:
                    if kw.lower() in domain.lower():
                        print(f"  ℹ️ [{i}] {rule['name']} (domain_keyword: {kw}) → {rule.get('outbound', 'N/A')}")

    print(f"  ⚠️ 未找到精确 domain_suffix 匹配 — 可能被兜底规则选中")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "list":
        show_all = "--all" in sys.argv
        cmd_list(show_all)
    elif cmd == "add" and len(sys.argv) >= 4:
        cmd_add(sys.argv[2], *sys.argv[3:])
    elif cmd == "restart":
        cmd_restart()
    elif cmd == "check" and len(sys.argv) >= 3:
        cmd_check(sys.argv[2])
    else:
        print(f"karing-route: 未知命令或参数不足 '{cmd}'")
        print(__doc__)


if __name__ == "__main__":
    main()
