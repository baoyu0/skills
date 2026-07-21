#!/usr/bin/env python3
"""
halo-migrate-images.py — 扫描 markdown 中的外部图片，下载并生成 Halo 上传映射

用法:
  python halo-migrate-images.py <markdown文件> [--referer <域名>]

流程:
  1. 扫描文件中所有外部图片 URL
  2. 下载到临时目录（自动设置 User-Agent，可选 Referer）
  3. 输出 URL → 本地路径的 JSON 映射文件（mapping.json）
  4. agent 读取 mapping.json，逐条执行 `halo attachment upload --file <path>`，
     将上传结果记录为 URL → Halo URL 的新 JSON 映射文件
  5. 上传完成后再次运行:
     python halo-migrate-images.py <文件> --apply <new_mapping.json>
     自动替换文件中的原始图片 URL 为 Halo 地址

注意: 临时目录不会被自动清理，agent 需在读取 mapping 后自行清理。
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# 常见防盗链 CDN 域名（默认处理这些）
KNOWN_CDN_DOMAINS: list[str] = [
    'cdnfile.sspai.com',
    'cdn.vox-cdn.com',
    'images.unsplash.com',
    'miro.medium.com',
    'cdn-images-1.medium.com',
]

# 默认请求头，模拟浏览器行为绕过基础防盗链
HEADERS: dict[str, str] = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
}


def scan_images(filepath: str) -> tuple[str, list[str]]:
    """扫描 markdown 文件中所有外部图片 URL，返回 (全文, 外部 URL 列表)"""
    try:
        text = Path(filepath).read_text(encoding='utf-8')
    except FileNotFoundError:
        print(f'文件不存在: {filepath}')
        sys.exit(1)
    except OSError as e:
        print(f'读取文件失败: {e}')
        sys.exit(1)

    urls: set[str] = set()
    # Markdown 图片: ![alt](url)
    for m in re.finditer(r'!\[.*?\]\(([^)]+)\)', text):
        urls.add(m.group(1))
    # HTML <img src="url">
    for m in re.finditer(r'<img[^>]*src=["\']([^"\']+)["\']', text):
        urls.add(m.group(1))

    external = sorted(u for u in urls if u.startswith('http'))
    return text, external


def download_images(
    urls: list[str],
    referer: str | None = None,
) -> tuple[str, dict[str, str]]:
    """下载图片到临时目录，返回 (tmpdir, {url: local_path} 映射)

    使用 urllib.request 替代 curl subprocess，支持自定义 Referer。
    """
    tmpdir = tempfile.mkdtemp(prefix='halo_images_')
    mapping: dict[str, str] = {}

    headers = dict(HEADERS)
    if referer:
        headers['Referer'] = referer

    for i, url in enumerate(urls):
        parsed = urlparse(url)
        fname = os.path.basename(parsed.path) or f'image_{i}'
        # 移除 URL 查询参数和片段，确保文件名安全
        safe_name = f'{i}_{fname.split("?")[0].split("#")[0]}'
        local = os.path.join(tmpdir, safe_name)

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = response.read()
            Path(local).write_bytes(data)
            if os.path.getsize(local) > 0:
                mapping[url] = local
                print(f'  ✅ {i+1}/{len(urls)} {fname[:40]}')
            else:
                print(f'  ❌ {i+1}/{len(urls)} {fname[:40]} (文件为空)')
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            print(f'  ❌ {i+1}/{len(urls)} {fname[:40]} (下载失败: {e})')

    return tmpdir, mapping


def generate_mapping(mapping: dict[str, str], output_path: str) -> str:
    """将 {url: local_path} 映射写入 JSON 文件"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        print(f'映射文件已生成: {output_path}')
    except OSError as e:
        print(f'写入映射文件失败: {e}')
        sys.exit(1)
    return output_path


def apply_mapping(filepath: str, mapping_file: str) -> int:
    """用 JSON mapping ({original_url: halo_url}) 替换文件中的图片 URL"""
    try:
        with open(mapping_file, encoding='utf-8') as f:
            url_map: dict[str, str] = json.load(f)
    except FileNotFoundError:
        print(f'映射文件不存在: {mapping_file}')
        return 0
    except json.JSONDecodeError as e:
        print(f'映射文件格式错误: {e}')
        return 0

    # 补全相对路径为完整 URL（Halo API 可能返回相对路径）
    resolved: dict[str, str] = {}
    for key, value in url_map.items():
        if value.startswith('/'):
            value = f'https://jia.baoyu2023.top{value}'
        resolved[key] = value

    try:
        text = Path(filepath).read_text(encoding='utf-8')
    except OSError as e:
        print(f'读取文件失败: {e}')
        return 0

    count = 0
    for original_url, new_url in resolved.items():
        escaped = re.escape(original_url)
        text, n = re.subn(escaped, new_url, text)
        count += n

    try:
        Path(filepath).write_text(text, encoding='utf-8')
    except OSError as e:
        print(f'写入文件失败: {e}')
        return 0

    print(f'替换了 {count} 张图片')
    return count


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f'文件不存在: {filepath}')
        sys.exit(1)

    # --apply 模式: 应用 mapping
    if '--apply' in sys.argv:
        idx = sys.argv.index('--apply')
        if idx + 1 < len(sys.argv):
            apply_mapping(filepath, sys.argv[idx + 1])
        return

    # 普通模式: 扫描、下载、生成 JSON mapping
    referer: str | None = None
    if '--referer' in sys.argv:
        idx = sys.argv.index('--referer')
        if idx + 1 < len(sys.argv):
            referer = sys.argv[idx + 1]

    text, urls = scan_images(filepath)

    if not urls:
        print('未发现外部图片 URL')
        return

    # 排除已知安全域名
    safe: list[str] = ['jia.baoyu2023.top', 'localhost', '127.0.0.1']
    external = [u for u in urls if all(s not in u for s in safe)]

    print(f'发现 {len(external)} 张外部图片:')
    for u in external:
        print(f'  {u[:80]}')
    print()

    print('下载中...')
    tmpdir, mapping = download_images(external, referer)

    if not mapping:
        print('没有成功下载的图片')
        return

    # 生成 JSON 映射
    mapping_path = os.path.join(tmpdir, 'mapping.json')
    generate_mapping(mapping, mapping_path)

    print(f'\n✅ 下载完成: {len(mapping)}/{len(external)} 张')
    print(f'\n📋 下一步: 读取 {mapping_path}，逐条执行 halo attachment upload:')
    for url, local in mapping.items():
        print(f'   halo attachment upload --file "{local}"')
    print()
    print('将每条命令的返回结果中提取的 Halo URL 记录为新 JSON，格式:')
    print(f'  {{"original_url": "https://halo-host/upload/path"}}')
    print(f'然后运行:')
    print(f'   python "{__file__}" "{filepath}" --apply <新 mapping.json>')


if __name__ == '__main__':
    main()
