---
icon: simple/markdown
---

# 快速开始

完整文档请访问 [zensical.org](https://zensical.org/docs/)。

## 命令

- [`zensical new`][new] - 创建新项目
- [`zensical serve`][serve] - 启动本地 Web 服务器
- [`zensical build`][build] - 构建站点

  [new]: https://zensical.org/docs/usage/new/
  [serve]: https://zensical.org/docs/usage/preview/
  [build]: https://zensical.org/docs/usage/build/

## 示例

### 提示块

> 前往 [文档](https://zensical.org/docs/authoring/admonitions/)

!!! note

    这是一个**注记**提示块。用它来提供有用的信息。

!!! warning

    这是一个**警告**提示块。请小心！

### 详情

> 前往 [文档](https://zensical.org/docs/authoring/admonitions/#collapsible-blocks)

??? info "点击展开以获取更多信息"

    该内容在你点击展开之前是隐藏的。
    非常适合常见问题或较长的说明。

## 代码块

> 前往 [文档](https://zensical.org/docs/authoring/code-blocks/)

``` python hl_lines="2" title="代码块"
def greet(name):
    print(f"Hello, {name}!") # (1)!

greet("Python")
```

1. > 前往 [文档](https://zensical.org/docs/authoring/code-blocks/#code-annotations)

    代码注释允许为代码行附加说明。

代码也可以内联高亮：`#!python print("Hello, Python!")`。

## 内容选项卡

> 前往 [文档](https://zensical.org/docs/authoring/content-tabs/)

=== "Python"

    ``` python
    print("Hello from Python!")
    ```

=== "Rust"

    ``` rs
    println!("Hello from Rust!");
    ```

## 图表

> 前往 [文档](https://zensical.org/docs/authoring/diagrams/)

``` mermaid
graph LR
  A[Start] --> B{Error?};
  B -->|Yes| C[Hmm...];
  C --> D[Debug];
  D --> B;
  B ---->|No| E[Yay!];
```

## 脚注

> 前往 [文档](https://zensical.org/docs/authoring/footnotes/)

这是一句带有脚注的句子。[^1]

将鼠标悬停其上以查看提示。

[^1]: 这是脚注。

## 格式化

> 前往 [文档](https://zensical.org/docs/authoring/formatting/)

- ==这是高亮内容==
- ^^这是插入的内容（下划线）^^
- ~~这是删除的内容（删除线）~~
- H~2~O
- A^T^A
- ++ctrl+alt+del++

## 图标与表情

> 前往 [文档](https://zensical.org/docs/authoring/icons-emojis/)

- :sparkles: `:sparkles:`
- :rocket: `:rocket:`
- :tada: `:tada:`
- :memo: `:memo:`
- :eyes: `:eyes:`

## 数学

> 前往 [文档](https://zensical.org/docs/authoring/math/)

$$
\cos x=\sum_{k=0}^{\infty}\frac{(-1)^k}{(2k)!}x^{2k}
$$

!!! warning "需要配置"
    请注意，本页通过 `script` 标签引入了 MathJax，
    并未在生成的默认配置中启用，以避免在不需要的页面中包含它。
    如果你的站点对数学公式的需求较多，请参阅文档了解如何
    在所有页面上进行配置。

<script id="MathJax-script" async src="https://unpkg.com/mathjax@3/es5/tex-mml-chtml.js"></script>
<script>
  window.MathJax = {
    tex: {
      inlineMath: [["\\(", "\\)"]],
      displayMath: [["\\[", "\\]"]],
      processEscapes: true,
      processEnvironments: true
    },
    options: {
      ignoreHtmlClass: ".*|",
      processHtmlClass: "arithmatex"
    }
  };
</script>

## 任务清单

> 前往 [文档](https://zensical.org/docs/authoring/lists/#using-task-lists)

- [x] 安装 Zensical
- [x] 配置 `zensical.toml`
- [x] 撰写出色的文档
- [ ] 部署到任意平台

## 气泡提示

> 前往 [文档](https://zensical.org/docs/authoring/tooltips/)

[将鼠标悬停我][example]

  [example]: https://example.com "我是一个提示！"
