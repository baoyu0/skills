#!/usr/bin/env python3
"""
karing-route — Karing 路由规则管理 CLI
为指定路由组添加域名白名单，无需手动改 JSON。

用法:
  python karing-route.py add <路由组名> <域名1> [域名2 ...]
  python karing-route.py list
  python karing-route.py restart
  python karing-route.py check <域名>

示例:
  python karing-route.py add "🎯 国内直连" rsshub.app
  python karing-route.py list
  python karing-route.py check objects.githubusercontent.com
"""

import json, subprocess, sys, os

CONFIG_PATH = r"C:\Users\zhaid\AppData\Roaming\Karing\karing\service_core.json"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def find_route_rule(cfg, name):
    """按 name 查找路由规则"""
    for rule in cfg.get("route", {}).get("rules", []):
        if rule.get("name") == name:
            return rule
    return None


def cmd_list():
    cfg = load_config()
    rules = cfg.get("route", {}).get("rules", [])
    print(f"Karing 路由规则 ({len(rules)} 条)\n")
    for i, rule in enumerate(rules):
        name = rule.get("name", f"[rule {i}]")
        outbound = rule.get("outbound", "N/A")
        domains = []
        if "rules" in rule:
            for sub in rule["rules"]:
                if "domain_suffix" in sub:
                    domains.extend(sub["domain_suffix"])
        domain_str = ""
        if domains:
            domain_str = f" ({', '.join(domains[:5])})"
        print(f"  [{i}] {name} → {outbound}{domain_str}")


def cmd_add(route_name, *domains):
    cfg = load_config()
    rule = find_route_rule(cfg, route_name)
    if not rule:
        # 模糊匹配
        matches = [r for r in cfg.get("route", {}).get("rules", [])
                   if route_name in r.get("name", "")]
        if len(matches) == 1:
            rule = matches[0]
            print(f"模糊匹配到: {rule['name']}")
        elif len(matches) > 1:
            print(f"找到多个匹配: {[m['name'] for m in matches]}")
            return
        else:
            print(f"未找到路由组 '{route_name}'")
            return

    # 查找或创建 domain_suffix 子规则
    found = False
    for sub in rule.get("rules", []):
        if "domain_suffix" in sub:
            existing = set(sub["domain_suffix"])
            added = [d for d in domains if d not in existing]
            if not added:
                print("✅ 全部域名已存在，无需添加")
                return
            sub["domain_suffix"].extend(added)
            found = True
            print(f"已添加 {added} → {rule['name']}")
            break

    if not found:
        rule.setdefault("rules", []).insert(0, {"domain_suffix": list(domains)})
        print(f"已创建 domain_suffix 规则: {domains} → {rule['name']}")

    save_config(cfg)


def cmd_restart():
    print("重启 karingService.exe...")
    r = subprocess.run(["taskkill", "/F", "/IM", "karingService.exe"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        print("✅ 已停止，Karing GUI 会自动重启服务（等待 3 秒）")
    else:
        print(f"⚠️ 停止失败: {r.stderr.strip()}")
        print("可能已经停止，等 GUI 自动拉起...")


def cmd_check(domain):
    """检查域名当前被哪个路由组匹配"""
    cfg = load_config()
    rules = cfg.get("route", {}).get("rules", [])
    for i, rule in enumerate(rules):
        # 检查 domain_suffix
        for sub in rule.get("rules", []):
            if "domain_suffix" in sub and any(d in domain for d in sub["domain_suffix"]):
                print(f"  ✅ [{i}] {rule['name']} → {rule.get('outbound','N/A')}")
                return
        # 检查 rule_set (geosite)
        for sub in rule.get("rules", []):
            if "rule_set" in sub:
                for rs in sub["rule_set"]:
                    if domain.split(".")[-2] in rs or any(d in rs for d in domain.split(".")):
                        print(f"  ℹ️ [{i}] {rule['name']} (rule_set: {rs}) → {rule.get('outbound','N/A')}")
        # 检查 domain in route_name
        if domain.split(".")[0].lower() in rule.get("name", "").lower():
            print(f"  ℹ️ [{i}] {rule['name']} (name match) → {rule.get('outbound','N/A')}")

    print(f"  ⚠️ 未找到精确规则 — 可能被兜底 '🌏 国外穿墙' 或 'cn[geosite]' 匹配")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return

    cmd = sys.argv[1]
    if cmd == "list":
        cmd_list()
    elif cmd == "add" and len(sys.argv) >= 4:
        route_name = sys.argv[2]
        domains = sys.argv[3:]
        cmd_add(route_name, *domains)
    elif cmd == "restart":
        cmd_restart()
    elif cmd == "check" and len(sys.argv) >= 3:
        cmd_check(sys.argv[2])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
