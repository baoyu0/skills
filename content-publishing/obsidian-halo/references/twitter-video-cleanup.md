# Twitter 剪藏视频嵌入清理

## 问题

Twitter/X 剪藏文章常包含 raw `<video>` HTML 标签，如：

```html
<video preload="none" tabindex="-1" playsinline=""
  aria-label="嵌入式视频"
  poster="https://pbs.twimg.com/amplify_video_thumb/xxx/img/xxx.jpg"
  style="width: 100%; height: 100%; position: absolute; background-color: black; top: 0%; left: 0%; transform: rotate(0deg) scale(1.005);">
  <source type="video/mp4" src="blob:https://x.com/xxx">
</video>
```

## 症状

在 Halo 页面：
- `position: absolute; width:100%; height:100%` 撑破页面布局
- `blob:` URL 只在 X/Twitter 站内有效，其他页面无法播放
- 视频时间戳文字（如 `0:03 / 0:08`）成为孤立文本

## 自动修复（推荐）

脚本 `cleanup` 模式自动完成所有替换：

```bash
python ~/.hermes/scripts/halo-publish.py cleanup "<文件路径>"
```

自动处理：
1. 扫描 `<video>`/`<audio>` 标签 → 提取 `poster` URL
2. 替换为 `[![视频截图](poster)](原文链接)`（从 frontmatter `source` 取原文 URL）
3. 删除附件的视频时间戳行（如 `0:02 / 0:32`）
4. 检测残留的 `<iframe>`/`<embed>`/`<object>` 标签并警告
5. 幂等，可重复执行

## 手动修复（边缘情况）

当 `cleanup` 无法处理时（如 poster URL 需要登录/CDN 鉴权），手动操作：

1. 从 `poster` 属性中提取视频截图 URL
2. 替换为 Markdown 图片链接到原文 Twitter 帖子
   ```markdown
   [![视频截图](<poster_url>)](<原文链接>)
   ```
3. 删除时间戳文字行（如 `0:03 / 0:08`）
4. **关键：替换后务必重新读取前后段落**，确认没有意外删除原文内容。多行替换（multi-line match）容易误删相邻段落。
5. 同时检查其他 raw HTML 标签
