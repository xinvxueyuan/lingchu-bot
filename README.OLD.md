<!-- markdownlint-disable MD033 MD013 -->
<h1><img src="docs/assets/images/logo-clr.svg" width = "415" height = "460"
    alt="lingchu-bot" align="right" id="top-image"/></h1>
<div align="center" id="top-rt-shield">

<h1>✨Re-灵初bot✨</h1>

_Modern application-side framework implemented based on NoneBot2._

<blockquote>おはうと、皆さん！今日もよろしくお願いします！</blockquote>

<!-- 核心信息 -->
[![许可证][license-shield]][license-link]
[![最新发行版][github-release-shield]][github-release-link]
[![GitHub 星标][github-stars-shield]][github-stars-link]
[![总下载量][downloads-shield]][downloads-link]

<!-- 代码/依赖相关 -->
[![主语言][top-language-shield]][top-language-link]
[![代码体积][code-size-shield]][code-size-link]
[![仓库大小][repo-size-shield]][repo-size-link]
[![CodeRabbit 评审][CodeRabbit-link]][CodeRabbit-link]

<!-- 平台/支持 -->
[![VS Code 支持][ide-link-1]][ide-link-1]
[![PyCharm 支持][ide-link-2]][ide-link-2]
[![托管状态][managed-link]][managed-link]

<!-- 文档/社区 -->
[![文档][docs-shield]][docs-link]
[![文档状态][deployments-shield]][deployments-link]
[![Zread 问答][zread-shield]][zread-link]
[![DeepWiki 问答][deepwiki-shield]][deepwiki-link]

</div>

---

## Introduction

灵初bot是一款基于 NoneBot2 框架开发的应用侧机器人项目。当前仓库以
`nonebot-plugin-lingchu-bot` 插件包为核心，已经实现并测试覆盖的业务能力
主要集中在 Milky 群管理命令；项目结构仍保留多适配器和非群管理功能的后续
迭代空间。

## Quick Start

> [!WARNING]
> 🚧Pre-alpha / development 阶段🚧
>
> 当前接口、命令行为和运行方式仍可能调整。请以源码、测试和新版
> [README.md](README.md) / 在线文档为准。

当前工作树没有提交根目录 `bot.py`。本仓库以 NoneBot 插件包和
`pyproject.toml` 的 `[tool.nonebot]` 配置为主；Docker 构建流程会通过
`nb-cli` 生成运行用 `/tmp/bot.py`。

| [![GitHub.Pages][docs-shield]][docs-link] | [![文档状态][deployments-shield]][deployments-link] |
| :---: | :---: |

## Compatibility issues

- unknown

## License

本项目使用复合许可证，包含 LGPL-3.0 和 GNU FDL。

- 详细说明请参见 -> [存储库策略](Repository-Policy.md)
- 许可证文本参见 -> [许可证-代码](LICENSE-code) & [许可证-文档](./LICENSE-docs)

## Acknowledgments

> 除所有者外，当前未有做出重大贡献的开发人员，欢迎加入我们！

[![贡献者数量][contributors-shield]][contributors-link]

## Credits

> 特别感谢 [NoneBot](https://github.com/nonebot) 组织的开发人员以及
> 社区开发者提供的一系列优秀工具

- [nonebot-plugin-apscheduler](https://github.com/nonebot/plugin-apscheduler)

- [nonebot-plugin-localstore](https://github.com/nonebot/plugin-localstore)

- [nonebot-plugin-orm](https://github.com/nonebot/plugin-orm)

- 以及更多... -> [pyproject项目配置文件](./pyproject.toml)

> 这些工具使得项目变得更好

Lint & Format

- [Ruff](https://docs.astral.sh/ruff/)
- [Pyright (Pylance)](https://microsoft.github.io/pyright/#/)
- [Ty](https://docs.astral.sh/ty/)
- [MyPy](https://mypy.readthedocs.io/en/stable/)

Document service

- [Zensical](https://zensical.org/)

其余未列出的 -> [依赖列表](
https://github.com/xinvxueyuan/xinvxueyuan/network/dependencies)

## About

[![创建时间][created-shield]][created-link]

<!--
  <div align="center">
    <a name="readme-top"><img src="https://socialify.git.ci/xinvxueyuan/lingchu-bot/image?custom_description=%E7%94%B1Nonebot2%E9%A9%B1%E5%8A%A8%E7%9A%84QQ%E7%AE%A1%E7%90%86%E6%9C%BA%E5%99%A8%E4%BA%BA&description=1&font=Inter&forks=1&issues=1&language=1&name=1&owner=1&pattern=Overlapping+Hexagons&pulls=1&theme=Auto" alt="lingchu-bot" width="640" height="320" /></a>
    <a name="readme-banner"><img width="899" height="567" alt="banner" src="https://github.com/user-attachments/assets/db779db0-e2b1-493b-9fa3-0efcac22a2ac" /></a>
  </div>
-->
<div id="links">

<!-- 核心信息 -->
[license-link]: https://www.gnu.org/licenses/lgpl-3.0.html
[github-release-link]: https://github.com/xinvxueyuan/xinvxueyuan/releases/latest?label=发行版
[github-stars-link]: https://github.com/xinvxueyuan/lingchu-bot
[downloads-link]: https://github.com/xinvxueyuan/xinvxueyuan/releases
[contributors-link]: https://github.com/xinvxueyuan/lingchu-bot
[created-link]: https://github.com/xinvxueyuan/lingchu-bot

<!-- 代码/依赖相关 -->
[top-language-link]: https://github.com/xinvxueyuan/lingchu-bot
[code-size-link]: https://github.com/xinvxueyuan/lingchu-bot
[repo-size-link]: https://github.com/xinvxueyuan/lingchu-bot
[CodeRabbit-link]: https://img.shields.io/coderabbit/prs/github/xinvxueyuan/lingchu-bot?utm_source=oss&utm_medium=github&utm_campaign=lingchu-bot%2Flingchu-bot&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+评审

<!-- 平台/支持 -->
[ide-link-1]: https://img.shields.io/badge/IDE-Visual%20Studio%20Code-blue?style=flat&logo=data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBzdGFuZGFsb25lPSJubyI/PjwhRE9DVFlQRSBzdmcgUFVCTElDICItLy9XM0MvL0RURCBTVkcgMS4xLy9FTiIgImh0dHA6Ly93d3cudzMub3JnL0dyYXBoaWNzL1NWRy8xLjEvRFREL3N2ZzExLmR0ZCI+PHN2ZyB0PSIxNzI4MTA5NDQzMzg2IiBjbGFzcz0iaWNvbiIgdmlld0JveD0iMCAwIDEwMjQgMTAyNCIgdmVyc2lvbj0iMS4xIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHAtaWQ9IjU5OTAiIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIiB3aWR0aD0iMjQiIGhlaWdodD0iMjQiPjxwYXRoIGQ9Ik03MjUuMzMzMzMzIDcwMi43MlYzMTUuMzA2NjY3bC0yNTYgMTkzLjcwNjY2Nk05NC43MiAzOTIuMTA2NjY3YTM2LjYwOCAzNi42MDggMCAwIDEtMC44NTMzMzMtNDkuMDY2NjY3bDUxLjItNDcuMzZjOC41MzMzMzMtNy42OCAyOS40NC0xMS4wOTMzMzMgNDQuOCAwbDE0NS45MiAxMTEuMzYgMzM4LjM0NjY2Ni0zMDkuMzMzMzMzYzEzLjY1MzMzMy0xMy42NTMzMzMgMzcuMTItMTkuMiA2NC01LjEybDE3MC42NjY2NjcgODEuNDkzMzMzYzE1LjM2IDguOTYgMjkuODY2NjY3IDIzLjA0IDI5Ljg2NjY2NyA0OS4wNjY2Njd2NTc2YzAgMTcuMDY2NjY3LTEyLjM3MzMzMyAzNS40MTMzMzMtMjUuNiA0Mi42NjY2NjZsLTE4Ny43MzMzMzQgODkuNmMtMTMuNjUzMzMzIDUuNTQ2NjY3LTM5LjI1MzMzMyAwLjQyNjY2Ny00OC4yMTMzMzMtOC41MzMzMzNsLTM0Mi4xODY2NjctMzExLjQ2NjY2Ny0xNDUuMDY2NjY2IDExMC45MzMzMzRjLTE2LjIxMzMzMyAxMS4wOTMzMzMtMzYuMjY2NjY3IDguMTA2NjY3LTQ0LjggMGwtNTEuMi00Ni45MzMzMzRjLTEzLjY1MzMzMy0xNC4wOC0xMS45NDY2NjctMzcuMTIgMi4xMzMzMzMtNTEuMmwxMjgtMTE1LjIiIGZpbGw9IiNmZmZmZmYiIHAtaWQ9IjU5OTEiPjwvcGF0aD48L3N2Zz4=
[ide-link-2]: https://img.shields.io/badge/IDE-PyCharm-green?style=flat&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNmZmYiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cGF0aCBkPSJNMjEgMTVjMCAxLjY1Ny0xLjM0MyAzLTMgM3MtMy0xLjM0My0zLTNzMS4zNDMtMyAzLTNzMyAxLjM0MyAzIDN6TTMgMTVjMCAxLjY1NyAxLjM0MyAzIDMgM3MzLTEuMzQzIDMtM3MtMS4zNDMtMy0zLTNzLTMgMS4zNDMtMyAzem0xMy42LTguOGwtLjQgMi40LTYuNC02LjQgMi40LS40IDQuOCA0LjggNC44LTQuOHoiPjwvcGF0aD48L3N2Zz4=
[managed-link]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json

<!-- 文档/社区 -->
[docs-link]: https://lingchu.zone.id/
[deployments-link]: https://github.com/xinvxueyuan/lingchu-bot
[zread-link]: https://zread.ai/xinvxueyuan/lingchu-bot
[deepwiki-link]: https://deepwiki.com/xinvxueyuan/lingchu-bot

<!-- Shield link -->
[license-shield]: https://img.shields.io/github/license/xinvxueyuan/lingchu-bot
[github-release-shield]: https://img.shields.io/github/v/release/xinvxueyuan/lingchu-bot
[github-stars-shield]: https://img.shields.io/github/stars/xinvxueyuan/lingchu-bot?color=%231890FF&style=flat-square
[downloads-shield]: https://img.shields.io/github/downloads/xinvxueyuan/lingchu-bot/total?label=总下载量
[contributors-shield]: https://img.shields.io/github/contributors-anon/xinvxueyuan/lingchu-bot?label=贡献者数量
[created-shield]: https://img.shields.io/github/created-at/xinvxueyuan/lingchu-bot?label=创建自
[top-language-shield]: https://img.shields.io/github/languages/top/xinvxueyuan/lingchu-bot
[code-size-shield]: https://img.shields.io/github/languages/code-size/xinvxueyuan/lingchu-bot?label=代码大小
[repo-size-shield]: https://img.shields.io/github/repo-size/xinvxueyuan/lingchu-bot?label=仓库大小
[docs-shield]: https://img.shields.io/badge/Docs%20on-Github.Pages-orange
[deployments-shield]: https://img.shields.io/github/deployments/xinvxueyuan/lingchu-bot/github-pages?label=文档状态
[zread-shield]: https://img.shields.io/badge/Ask_Zread-_.svg?color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff
[deepwiki-shield]: https://deepwiki.com/badge.svg

</div>
