# Halo 外部图片迁移流程

当文章引用了外部 CDN 图片（如 `pbs.twimg.com`、`sspai.com` 等），这些图片在 Halo 上可能因防盗链返回 403/404。解决方案：下载 → 上传到 Halo → 替换本地 URL。

## 标准流程

### 第一步：扫描+下载

```bash
python ~/.hermes/scripts/halo-migrate-images.py "<文件绝对路径>"
```

脚本会：扫描所有外部图片 URL → 下载到临时目录 → 生成 `upload.sh`。

### 第二步：上传到 Halo

`halo attachment upload` 输出格式为表格，`metadata.name` 字段是 UUID：

```bash
halo attachment upload --file "<图片路径>" 2>&1 | grep "metadata.name" | awk '{print $2}'
# 输出示例: ffdc71fa-16f7-475b-86f7-740dc60f9914
```

### 第三步：获取 permalink

用 `--json` 输出读取 `status.permalink`：

```bash
halo attachment get <UUID> --json | python3 -c "import sys,json;d=json.load(sys.stdin);print('https://jia.baoyu2023.top'+d['status']['permalink'])"
# 输出示例: https://jia.baoyu2023.top/upload/0_HL-h9mcb0AALFN0-ktxt
```

### 第四步：批量上传

循环上传所有图片：

```bash
for f in /c/Users/zhaid/AppData/Local/Temp/halo_images_*/[0-9]_*; do
  halo attachment upload --file "$f" 2>&1 | grep "metadata.name" | awk '{print $2}'
done
```

### 第五步：应用映射

将 `mapping.txt`（格式 `图片ID|Halo_URL`）应用到 markdown 文件：

```bash
python ~/.hermes/scripts/halo-migrate-images.py "<文件路径>" --apply "<映射文件路径>"
```

## 已知问题

### `upload.sh` 的 grep 模式错误

`halo-migrate-images.py` 生成的 `upload.sh` 用 `grep "thumbnails.L"` 提取 URL，但 `halo attachment upload` 的输出中**不存在**该字段（thumbnails 为 `{}`）。**不要直接运行 upload.sh**——它会收集空 URL。

### `halo` 是 shell 脚本，Python subprocess 不可调用

在 Windows 上，`halo` 是 npm 包装的 shell 脚本，Python 的 `subprocess.run(['halo', ...])` 会 `FileNotFoundError`。必须通过 `terminal` 工具（git-bash）调用。

### 重复上传

`halo attachment upload` 每次调用都会创建新附件（即使文件相同）。检查 `halo attachment list` 确认没有冗余附件。清理多余附件用：

```bash
halo attachment delete <UUID> --force
```
