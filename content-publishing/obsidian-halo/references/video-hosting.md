# 免费视频托管方案（Blog 嵌入用）

当文章含有 blob: 或 MSE 视频（如 X Article 嵌入），cleanup 脚本会降级为 poster 截图。
如果用户手动下载了原始视频，需要找一个免费公开的托管平台获取直链用于 `<video>` 标签。

## 方案对比

| 平台 | 容量 | 直链 | Range请求 | 持久性 | 上传方式 |
|------|------|------|-----------|--------|----------|
| **GitHub Releases** ⭐ | 2GB/release | ✅ 301→CDN | ✅ 206 | 永久 | `gh release create` |
| catbox.moe | 200MB/文件 | ✅ 直链 | — | 不限时 | `curl -F` API |
| gofile.io | 5GB/文件 | ✅ 302 | ❌ 不支持 | 不限时 | `curl -F` API |
| 0x0.st | 300MB | ✅ | — | 30天 | 已关闭 |
| ImgBB | 64MB | ✅ | — | 图片为主 | API |

## 推荐方案：GitHub Releases

用用户已有的 GitHub 帐号，上传到任意仓库的 Releases 附件：

```bash
# 创建 release 并上传视频
gh release create <tag> <视频路径> --repo <owner/repo> --title "<标题>" --notes ""

# 直链格式
# https://github.com/<owner>/<repo>/releases/download/<tag>/<filename>
```

**优点：**
- 不占仓库存储空间（Release 附件独立计费）
- CDN 加速，支持 range request（视频可拖动进度条）
- 永久有效，无广告
- `gh` CLI 已认证时一行命令搞定

**注意事项：**
- GitHub CDN 返回 `Content-Type: application/octet-stream`，但浏览器在 `<video>` 标签中能正确识别 MP4
- tag 名不能重复，可用 `video-assets` 或按内容命名
