<!-- markdownlint-disable MD033 && MD041 && MD045 && MD001-->
<div align="center">
  <h1>✨Re-灵初bot✨</h1>
  
  <a name="readme-top"><img src="https://socialify.git.ci/xinvxueyuan/lingchu-bot/image?custom_description=%E7%94%B1Nonebot2%E9%A9%B1%E5%8A%A8%E7%9A%84QQ%E7%AE%A1%E7%90%86%E6%9C%BA%E5%99%A8%E4%BA%BA&description=1&font=Inter&forks=1&issues=1&language=1&name=1&owner=1&pattern=Overlapping+Hexagons&pulls=1&theme=Auto" alt="lingchu-bot" width="640" height="320" /></a>
  
[![][license-shield]][license-link] [![][docs-shield]][docs-link] [![][github-release-shield]][github-release-link] [![][github-stars-shield]][github-stars-link]
![CodeRabbit Pull Request Reviews][CodeRabbit-link]

![ide-link]

</div>
<br/>
<div>

# 如何开始

<div class="alert alert-warning" role="alert" align="center">
<h2>🚧开发阶段，文档更新落后🚧</h2>
<h2>⚠️包管理器未定，暂时使用pdm，注意兼容问题⚠️</h2>
</div>

## 前置条件

我们使用激进的推送策略，因此请确保您的本地仓库与远程仓库保持同步。

- [git](https://git-scm.com/downloads)最新版本
- [python](https://www.python.org/downloads/)>=3.12, <4.0版本
- [pdm](https://pdm-project.org/zh-cn/latest/)最新版本

</div>
<div>

## 开启项目

[项目文档]([docs-link])

#### 以下操作需在终端执行，且目录无中文字符

克隆项目到本地

```bash
git clone https://github.com/xinvxueyuan/lingchu-bot.git
```

进入项目目录

```bash
cd lingchu-bot
```

安装项目依赖

```bash
pdm install --prod # 安装生产依赖
pdm install  # 或安装全部依赖(包含开发依赖)
```

启动项目

```bash
pdm run bot.py # 启动项目(生产环境)
pdm run bot.py --reload # 自动重载(开发环境)
```

</div>
<div>

## 注意事项

- 项目使用ruff进行代码检查，建议在开发过程中使用ruff进行代码检查。
- 项目使用pdm进行依赖管理，建议在开发过程中使用pdm进行依赖管理。
- 项目使用black进行代码格式化，建议在开发过程中使用black进行代码格式化。
- 项目使用isort进行导入排序，建议在开发过程中使用isort进行导入排序。

## 感谢

[Nonebot2](https://nonebot.dev/)
[onebot11](https://11.onebot.dev/)
[go-cqhttp](https://go-cqhttp.org/)
[nonebot-plugin-apscheduler](https://github.com/nonebot/plugin-apscheduler)
[nonebot-plugin-orm](https://github.com/nonebot/plugin-orm)
[httpx](https://www.python-httpx.org/)
[websockets](https://websockets.readthedocs.io/)
[nicegui](https://nicegui.io/)

<!-- official link -->
[docs-link]: https://lingchu.zone.id/

<!-- Other link-->
[license-link]: https://www.gnu.org/licenses/gpl-3.0.html
[github-release-link]: https://github.com/xinvxueyuan/lingchu-bot/releases/latest
[github-stars-link]: https://github.com/xinvxueyuan/lingchu-bot

<!-- Shield link-->
[docs-shield]: https://img.shields.io/badge/documentation-148F76
[github-release-shield]: https://img.shields.io/github/v/release/xinvxueyuan/lingchu-bot
[github-stars-shield]: https://img.shields.io/github/stars/xinvxueyuan/lingchu-bot?color=%231890FF&style=flat-square
[license-shield]: https://img.shields.io/github/license/xinvxueyuan/lingchu-bot
[CodeRabbit-link]: https://img.shields.io/coderabbit/prs/github/xinvxueyuan/lingchu-bot?utm_source=oss&utm_medium=github&utm_campaign=xinvxueyuan%2Flingchu-bot&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews
[ide-link]: https://img.shields.io/badge/IDE-Visual%20Studio%20Code-blue?style=flat&logo=data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBzdGFuZGFsb25lPSJubyI/PjwhRE9DVFlQRSBzdmcgUFVCTElDICItLy9XM0MvL0RURCBTVkcgMS4xLy9FTiIgImh0dHA6Ly93d3cudzMub3JnL0dyYXBoaWNzL1NWRy8xLjEvRFREL3N2ZzExLmR0ZCI+PHN2ZyB0PSIxNzI4MTA5NDQzMzg2IiBjbGFzcz0iaWNvbiIgdmlld0JveD0iMCAwIDEwMjQgMTAyNCIgdmVyc2lvbj0iMS4xIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHAtaWQ9IjU5OTAiIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIiB3aWR0aD0iMjQiIGhlaWdodD0iMjQiPjxwYXRoIGQ9Ik03MjUuMzMzMzMzIDcwMi43MlYzMTUuMzA2NjY3bC0yNTYgMTkzLjcwNjY2Nk05NC43MiAzOTIuMTA2NjY3YTM2LjYwOCAzNi42MDggMCAwIDEtMC44NTMzMzMtNDkuMDY2NjY3bDUxLjItNDcuMzZjOC41MzMzMzMtNy42OCAyOS40NC0xMS4wOTMzMzMgNDQuOCAwbDE0NS45MiAxMTEuMzYgMzM4LjM0NjY2Ni0zMDkuMzMzMzMzYzEzLjY1MzMzMy0xMy42NTMzMzMgMzcuMTItMTkuMiA2NC01LjEybDE3MC42NjY2NjcgODEuNDkzMzMzYzE1LjM2IDguOTYgMjkuODY2NjY3IDIzLjA0IDI5Ljg2NjY2NyA0OS4wNjY2Njd2NTc2YzAgMTcuMDY2NjY3LTEyLjM3MzMzMyAzNS40MTMzMzMtMjUuNiA0Mi42NjY2NjZsLTE4Ny43MzMzMzQgODkuNmMtMTMuNjUzMzMzIDUuNTQ2NjY3LTM5LjI1MzMzMyAwLjQyNjY2Ny00OC4yMTMzMzMtOC41MzMzMzNsLTM0Mi4xODY2NjctMzExLjQ2NjY2Ny0xNDUuMDY2NjY2IDExMC45MzMzMzRjLTE2LjIxMzMzMyAxMS4wOTMzMzMtMzYuMjY2NjY3IDguMTA2NjY3LTQ0LjggMGwtNTEuMi00Ni45MzMzMzRjLTEzLjY1MzMzMy0xNC4wOC0xMS45NDY2NjctMzcuMTIgMi4xMzMzMzMtNTEuMmwxMjgtMTE1LjIiIGZpbGw9IiNmZmZmZmYiIHAtaWQ9IjU5OTEiPjwvcGF0aD48L3N2Zz4=

</div>
