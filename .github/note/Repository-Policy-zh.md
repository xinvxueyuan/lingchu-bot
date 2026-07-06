# 仓库策略 — 许可证合规

> [English](../../Repository-Policy.md) | 中文

本项目采用**分阶段开源许可证栈**，在两个阶段之间设有自动切换。切换规则
详见 [许可证栈与切换](#许可证栈与切换) 一节，其法律可行性由
[`CLA.md`](../../CLA.md) 中的再许可授权条款保障。

## 许可证栈与切换

### 当前阶段（自项目创立起生效）

| 标的 | 许可证 | SPDX 标识符 |
| --- | --- | --- |
| 软件代码 | GNU Lesser General Public License v3.0 或后续版本 | `LGPL-3.0-or-later` |
| 文档 | GNU Free Documentation License v1.3 或后续版本 | `GFDL-1.3-or-later` |
| 视觉元素 | CC0 1.0 通用公共领域贡献许可证 | `CC0-1.0` |

### 未来阶段

| 标的 | 许可证 | SPDX 标识符 |
| --- | --- | --- |
| 软件代码 | MIT 许可证或后续版本，**或** Apache 许可证 2.0 或后续版本（用户自选双许可证） | `MIT-or-later OR Apache-2.0-or-later` |
| 文档 | Creative Commons Attribution-ShareAlike 4.0 国际或后续版本 | `CC-BY-SA-4.0-or-later` |
| 视觉元素 | Creative Commons Attribution-ShareAlike 4.0 国际或后续版本 | `CC-BY-SA-4.0-or-later` |

> 注：`pyproject.toml` 使用规范 SPDX 形式（`MIT OR Apache-2.0`、`CC-BY-SA-4.0`）以满足 PEP 639 / `uv build` 校验；上表的 `-or-later` 形式表达项目"或后续版本"的意图。

### 切换规则

- **切换触发点**取以下两者中的较早者：
  1. 本项目**首次公开发行后一年**（即首个非预发布版本发布日，如
     `1.0.0`，不含 `0.x` 或 `rc` / `alpha` / `beta`）；或
  2. 本项目的**首次主版本变更**（SemVer `x.0.0` 发布）。
- 切换**仅作用于触发日（含）之后提交的贡献**。触发日之前提交的贡献
  继续适用其提交当时生效的许可证。
- 切换是**单向**的：一旦进入未来阶段，本项目不会回退到当前阶段栈。
- 切换在**法律上可执行**，因为每位贡献者在提交贡献时即接受
  [`CLA.md`](../../CLA.md) 中的再许可授权。触发本身无需额外的
  再许可提交。
- 为清晰起见，本项目可随时在本文件中显式注明触发日；即使未显式注明，
  上述任一条件满足时切换的法律效力不会延后。

使用者必须遵守相关贡献在提交时生效的许可证的全部条款和条件。

## 版本发布记录

- `0.0.1`（2026-07-06）：当前 LGPL/GFDL/CC0 阶段的首个正式 0.x 版本。该版本不触发未来阶段，因为切换规则以 `1.0.0` 为首次公开发行示例并排除 `0.x`。

## 媒体文件脱敏要求

对于本项目中的媒体文件（包括但不限于图片、音频、视频等），若其未明确标注适用 CC0 1.0 公共领域贡献许可证，则在使用时必须进行脱敏处理。

脱敏处理包括但不限于：

1. 移除或模糊化所有个人身份信息
2. 处理面部、车牌号等可识别特征
3. 删除或替换敏感位置信息
4. 匿名化任何可能识别个人或实体的数据

## 合规使用说明

- 仅标注为 CC0 1.0 的媒体文件可无需脱敏直接使用
- 使用非 CC0 1.0 媒体文件时，必须在遵守相应许可证的同时完成脱敏
- 经脱敏处理的衍生媒体文件仍需遵守原始许可证条款
- 使用者对脱敏处理的合规性承担全部责任

## 免责声明

项目维护者不对使用者未适当脱敏导致的任何隐私侵权、法律纠纷或损失承担责任。建议在使用前咨询法律专业人士。

## 许可证文本

完整许可证文本可在以下仓库根目录文件中查阅，并附以上游权威链接：

### 当前阶段文本

- LGPL-3.0-or-later：[`LICENSE-code`](../../LICENSE-code)，
  `https://www.gnu.org/licenses/lgpl-3.0.html`
- FDL-1.3-or-later：[`LICENSE-docs`](../../LICENSE-docs)，
  `https://www.gnu.org/licenses/fdl-1.3.html`
- CC0 1.0 Universal：[`LICENSE-cc0`](../../LICENSE-cc0)，
  `https://creativecommons.org/publicdomain/zero/1.0/`

### 未来阶段文本

- MIT 或后续版本：[`LICENSE-mit`](../../LICENSE-mit)，
  `https://opensource.org/licenses/MIT`
- Apache License 2.0 或后续版本：[`LICENSE-apache`](../../LICENSE-apache)，
  `https://www.apache.org/licenses/LICENSE-2.0`
- CC BY-SA 4.0 或后续版本：[`LICENSE-cc-by-sa`](../../LICENSE-cc-by-sa)，
  `https://creativecommons.org/licenses/by-sa/4.0/legalcode`

### 贡献者协议

- [`CLA.md`](../../CLA.md)（中文镜像：[`.github/note/CLA-zh.md`](CLA-zh.md)）

### REUSE 合规

仓库根目录包含 [`REUSE.toml`](../../REUSE.toml) 文件，按 FSFE REUSE 3.0 为每类文件（源代码、文档、视觉元素、配置和脚本）声明许可证标注。标注将每个 glob 映射到其当前阶段许可证的 SPDX 标识符并附版权行。提交新增或移动文件的贡献前，可在本地运行 `uv tool run reuse lint`（或 `pipx run reuse lint`）验证合规性。

本脱敏声明旨在确保用户在使用本项目中的媒体文件时，尊重隐私权和相关法律法规。如有任何疑问，请联系项目维护者获取更多信息。
