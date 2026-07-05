#!/usr/bin/env python3
"""
halo-migrate-images.py — 扫描 markdown 中的外部图片，下载并生成 Halo 上传命令
用法:
  python halo-migrate-images.py <markdown文件> [--referer <域名>]

流程:
  1. 扫描文件中所有外部图片 URL
  2. 下载到临时目录（自动加 Referer 头）
  3. 输出 `halo attachment upload --file <path>` 命令列表（agent 执行）
  4. 上传完成后再次运行: python halo-migrate-images.py <文件> --apply <mapping_file>
     会自动替换文件中的 URL 为 Halo 地址

Agent 使用流程:
  python halo-migrate-images.py "D:/1-obsidian/Clippings/文章.md"
  → 下载图片到临时目录，输出命令列表
  → agent 逐条执行命令，输出重定向到 mapping 文件
  → python halo-migrate-images.py "文章.md" --apply <mapping_file>
  → 替换 URL，完成
"""

import re, os, sys, subprocess, json, tempfile, shutil
from urllib.parse import urlparse

# 常见防盗链 CDN 域名（默认处理这些）
KNOWN_CDN_DOMAINS = [
    'cdnfile.sspai.com',     # 少数派
    'cdn.vox-cdn.com',       # 
    'images.unsplash.com',
    'miro.medium.com',
    'cdn-images-1.medium.com',
]

def scan_images(filepath):
    """扫描 markdown 文件中所有图片 URL"""
    text = open(filepath, encoding='utf-8').read()
    # Markdown 图片: ![alt](url) 和 HTML <img src="url">
    urls = set()
    for m in re.finditer(r'!\[.*?\]\(([^)]+)\)', text):
        urls.add(m.group(1))
    for m in re.finditer(r'<img[^>]*src=["\']([^"\']+)["\']', text):
        urls.add(m.group(1))
    # 过滤出外部 URL
    external = []
    for url in sorted(urls):
        if url.startswith('http'):
            external.append(url)
    return text, external

def download_images(urls, referer=None):
    """下载图片到临时目录，返回 {filename: local_path} 映射"""
    tmpdir = tempfile.mkdtemp(prefix='halo_images_')
    mapping = {}
    for i, url in enumerate(urls):
        parsed = urlparse(url)
        fname = os.path.basename(parsed.path)
        if not fname:
            fname = f'image_{i}'
        local = os.path.join(tmpdir, f'{i}_{fname}')
        
        cmd = ['curl', '-sL', '-o', local]
        if referer:
            cmd += ['-H', f'Referer: {referer}']
        cmd.append(url)
        
        ret = subprocess.run(cmd, capture_output=True)
        if ret.returncode == 0 and os.path.exists(local) and os.path.getsize(local) > 0:
            mapping[url] = local
            print(f'  ✅ {i+1}/{len(urls)} {fname[:40]}')
        else:
            print(f'  ❌ {i+1}/{len(urls)} {fname[:40]} (下载失败)')
    
    return tmpdir, mapping

def generate_upload_commands(mapping, tmpdir):
    """生成 halo 上传命令列表"""
    commands = []
    # 写一个批处理脚本
    script_path = os.path.join(tmpdir, 'upload.sh')
    with open(script_path, 'w') as f:
        f.write('#!/bin/bash\n')
        f.write(f'HALO_TMPDIR="{tmpdir}"\n')
        f.write(f'MAPPING_FILE="{tmpdir}/mapping.txt"\n')
        f.write('> "$MAPPING_FILE"\n')
        for url, local in mapping.items():
            win_path = local.replace('/', '\\')
            f.write(f'URL=$(halo attachment upload --file "{win_path}" 2>&1 | grep "thumbnails.L" | awk \'{{print $2}}\')\n')
            # 用 URL 的 hash 做 key
            key = urlparse(url).path.split('/')[-1]
            f.write(f'echo "{key}|$URL" >> "$MAPPING_FILE"\n')
    os.chmod(script_path, 0o755)
    return script_path

def apply_mapping(filepath, mapping_file):
    """用 mapping 替换文件中的 URL"""
    # 读取 mapping
    url_map = {}
    with open(mapping_file) as f:
        for line in f:
            parts = line.strip().split('|', 1)
            if len(parts) == 2 and parts[1]:
                key, halo_path = parts
                if halo_path.startswith('/'):
                    halo_path = f'https://jia.baoyu2023.top{halo_path}'
                url_map[key] = halo_path
    
    text = open(filepath, encoding='utf-8').read()
    count = 0
    for key, new_url in url_map.items():
        pattern = r'https?://[^\s"\'\)]*' + re.escape(key) + r'[^\s"\'\)]*'
        text, n = re.subn(pattern, new_url, text)
        count += n
    
    open(filepath, 'w', encoding='utf-8').write(text)
    print(f'替换了 {count} 张图片')
    return count

def main():
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
    
    # 普通模式: 扫描、下载、生成命令
    referer = None
    if '--referer' in sys.argv:
        idx = sys.argv.index('--referer')
        if idx + 1 < len(sys.argv):
            referer = sys.argv[idx + 1]
    
    text, urls = scan_images(filepath)
    
    if not urls:
        print('未发现外部图片 URL')
        return
    
    # 过滤出看起来像 CDN 的外部图片
    # 排除已知安全域名
    safe = ['jia.baoyu2023.top', 'localhost', '127.0.0.1']
    external = [u for u in urls if all(s not in u for s in safe)]
    
    print(f'发现 {len(external)} 张外部图片:')
    for u in external:
        print(f'  {u[:80]}')
    print()
    
    # 下载
    print('下载中...')
    tmpdir, mapping = download_images(external, referer)
    
    if not mapping:
        print('没有成功下载的图片')
        return
    
    # 生成上传脚本
    script = generate_upload_commands(mapping, tmpdir)
    
    print(f'\n✅ 下载完成: {len(mapping)}/{len(external)} 张')
    print(f'\n📋 下一步: agent 执行以下脚本上传到 Halo:')
    print(f'   bash {script}')
    print(f'\n📋 上传完成后:')
    print(f'   python3 "{__file__}" "{filepath}" --apply "{tmpdir}/mapping.txt"')
    print(f'\n📋 或手动逐条执行:')
    for url, local in mapping.items():
        print(f'   halo attachment upload --file "{local}"')

if __name__ == '__main__':
    main()
