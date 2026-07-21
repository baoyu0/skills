# HTTP 请求/响应示例排版规范

> 在文章中使用 `①②③④` 编号 + 完整 HTTP 头 + 可选的 JSON body，一个 ` ```text ` 代码块呈现完整请求-响应流程。

## 格式定义

### 核心规则

一条 HTTP 请求/响应示例占用一个 ` ```text ` 代码块，内部用 `①②③④` 编号区分步骤：

```text
① <HTTP方法> <路径> HTTP/1.1
Host: <域名>
Authorization: Bearer <token>
Content-Type: application/json

② <JSON body（可选）>

③ HTTP/1.1 <状态码> <状态描述>
Content-Type: application/json

④ <JSON body（可选）>
```

### 编号含义

| 编号 | 代表 | 出现位置 |
|------|------|---------|
| `①` | **请求行 + 请求头** | 每个示例的第一组 |
| `②` | **请求体**（可选） | 请求头之后的 JSON |
| `③` | **状态行 + 响应头** | 请求部分之后的响应 |
| `④` | **响应体**（可选） | 响应头之后的 JSON |

## 完整示例

### 示例 1：GET 请求（无请求体、有响应体）

```text
① GET /apis/content.halo.run/v1alpha1/categories HTTP/1.1
Host: jia.baoyu2023.top
Authorization: Bearer pat_xxxxx

③ HTTP/1.1 200 OK
Content-Type: application/json

④ {
  "items": [
    { "metadata": { "name": "cat-001" }, "spec": { "displayName": "技术" } },
    { "metadata": { "name": "cat-002" }, "spec": { "displayName": "产品" } }
  ],
  "total": 2
}
```

### 示例 2：POST 请求（有请求体、有响应体）

```text
① POST /apis/uc.api.content.halo.run/v1alpha1/posts HTTP/1.1
Host: jia.baoyu2023.top
Authorization: Bearer pat_xxxxx
Content-Type: application/json

② {
  "post": {
    "title": "文章标题",
    "slug": "article-slug"
  }
}

③ HTTP/1.1 201 Created
Content-Type: application/json

④ {
  "metadata": { "name": "uuid-xxxx" },
  "spec": { "title": "文章标题", "slug": "article-slug", "publish": false }
}
```

### 示例 3：PUT 请求（有请求体、简单响应）

```text
① PUT /api/v1alpha1/configmaps/system HTTP/1.1
Host: jia.baoyu2023.top
Authorization: Bearer pat_xxxxx
Content-Type: application/json

② {
  "apiVersion": "v1alpha1",
  "kind": "ConfigMap",
  "data": { "codeInjection": "{...}" }
}

③ HTTP/1.1 200 OK
```

## 使用场景

| 场景 | 适用 | 不适用 |
|------|------|--------|
| API 调用演示 | ✅ 一个代码块看全貌 | ❌ 换行/分步打断理解 |
| 请求-响应对照 | ✅ ①③ 步骤天然分 request/response | ❌ 跨代码块对照 |
| curl 操作说明 | ✅ 可嵌入 curl 参数解析 | ❌ 实际可执行的 curl 命令 |

## 特殊变体

### 只有请求（无响应）

当不需要展示响应时，省略 `③④`：

```text
① POST /apis/uc.api.content.halo.run/v1alpha1/posts HTTP/1.1
Host: jia.baoyu2023.top
Authorization: Bearer pat_xxxxx
Content-Type: application/json

② {
  "title": "测试文章",
  "slug": "test-post"
}
```

### 无 body 的请求

当 GET/DELETE 不需要请求体时，省略 `②`：

```text
① DELETE /apis/content.halo.run/v1alpha1/posts/uuid-xxxx HTTP/1.1
Host: jia.baoyu2023.top
Authorization: Bearer pat_xxxxx

③ HTTP/1.1 204 No Content
```

## 为什么不拆成多个代码块

| 方案 | 问题 |
|------|------|
| 请求 ` ```bash ` + 响应 ` ```json ` 拆两个块 | ① 读者需要在两个代码块之间来回滚动对照；② 编号 step 和请求/响应的对应关系被视觉打断 |
| 用 `curl` 实际命令 + ` ```json ` 响应 | ① curl 命令含 -H 和 -d 参数，正文中已解释过；② 读者关心的是**协议层面的数据流**而非 shell 命令本身 |
| 纯文本描述 | ① 缺少视觉结构；② Header 和 body 的边界不清晰 |

**一个代码块的优势**：读者从上到下依次看到「谁发了什么请求 → 服务器回了什么状态 → 数据长什么样」，阅读顺序与 HTTP 交互时序一致。

## 与 curl 命令的配合

当正文需要实际可执行的 `curl` 命令时，用 ` ```bash ` 独立提 cell：

```bash
curl -s -X GET \
  -H "Authorization: Bearer ${PAT}" \
  "https://jia.baoyu2023.top/apis/content.halo.run/v1alpha1/categories"
```

然后用 ` ```text ` 的编号格式解释请求/响应结构。两者不互相替代。

## 对比：URL 参数说明

当需要说明 URL 参数含义（非全 HTTP 流程）时，用 ` ```text ` 但不用编号：

```text
GET /apis/content.halo.run/v1alpha1/posts/{name}
  {name} : 文章 UUID
  ?page  : 页码（可选，默认 1）
  ?size  : 每页条数（可选，默认 10）
```

这种简化格式不使用 `①②③④` 编号，因为不涉及请求和响应的完整数据流。
