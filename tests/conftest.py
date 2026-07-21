"""Common test fixtures for the skills project."""
from __future__ import annotations

import pytest


@pytest.fixture
def sample_markdown() -> str:
    return """---
title: Test Article
slug: test-article
categories: [Tech]
tags: [test, python]
halo:
  name: abc123
---
# Test Article

## 一、Introduction

This is a test paragraph with some content.

### 背景

Background information here.

### 目的

Purpose of this article.

## 二、Main Content

The main body of the article.

### 步骤一

Step one description.

### 步骤二

Step two description.
"""


@pytest.fixture
def sample_x_content() -> str:
    return """---
title: "X 上的 用户：测试推文"
slug: x-test
---
X 上的 用户发布了他的想法。

## 一、观点

发布你的回复
由 AI 生成
查看更多

![图像](https://pbs.twimg.com/media/test.jpg)
"""
