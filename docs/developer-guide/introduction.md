---
icon: lucide/rocket
title: 开发指南
---



### 项目原则

为了方便维护和扩展，我们遵循以下原则：

- 选择Type时，依据最小兼容性优先原则，在满足所有当前及可预见未来需求的前提下，选择列表中最靠左（兼容性最小）的类型
- 所有内容统一采用 [UTF-8](https://www.iso.org/standard/76835.html) 编码
- 严格遵守 PEP8 代码规范，为遵循周围代码风格或组织提案时允许破坏
- 使用 [git-flow](https://git-flow.sh/) 工具进行迭代控制

### 准备阶段

> 以下软件为必须

- IDE   集成开发环境
  - (推荐 [VS code](https://code.visualstudio.com/) 或者 [PyCharm](https://www.jetbrains.com/pycharm/))
- [git](https://git-scm.com/)         版本控制工具
- [Python](https://www.python.org/)   编程语言 3.13 版
  - Python 包管理工具(必选其一)
    - [uv](https://docs.astral.sh/uv/)      🔥官方支持
    - [Poetry](https://python-poetry.org/)  🚧接受报告
    - [PDM](https://pdm-project.org/)       🚧接受报告
    - ...                                   🚫不受维护

> 以下软件为可选

- [nb-cli](https://cli.nonebot.dev/)    nonebot 脚手架  🥰原生推荐
  - ```uv tool install nb-cli@latest```
