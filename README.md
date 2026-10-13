# Onsite Pagination Audit

<p align="center"><img src="assets/onsite-audit-cover.png" alt="Onsite Audit 系列封面：网站检查、放大镜和审计报告" width="640"></p>

用于 onsite audit 第 **14. Pagination** 项的 Codex skill。复用 [SF Shared Config](https://github.com/timn-firstpage/On-_site_SF_shared_config)，按已确认的六项检查读取 Screaming Frog 结果，生成 Excel。

Skill 名称：`onsite-audit-pagination`。入口：[SKILL.md](SKILL.md)。**14.1 默认 Human check；View All 跳过；提供的 SF 记录就是本次检查范围。**

## 安装与使用

将本仓库根目录安装或链接为 Codex skills 目录下的 `onsite-audit-pagination`，刷新技能列表。Clone 仓库不等于安装 skill。SF 准备流程由另行安装的 `sf-shared-config` 负责；已有适用 crawl／导出就直接复用。

示例：

> 使用 $onsite-audit-pagination，检查 https://example.com，公司名 Example。沿用我的 onsite global config 和已保存的 .seospider，按约定输出 pagination audit Excel。

提供网站、公司名、global config 和 crawl／导出路径即可，无需额外的 Begin／Review 表单或 workbook 模板。独立运行可复制 [config.template.json](config.template.json) 到本地 run 目录填写；模板不会自动连接 MCP、安装依赖或启动 crawl。

## 简单流程

**支持直接提供已爬好的 `.seospider` 文件**：使用 `source.mode=saved_crawl` 和 `source.crawl_file`，或直接提供文件路径。复用匹配导出，必要时通过 SF 支持的功能打开一次，与其他 onsite audits 共用结果；不重载 global config、不自动重爬。`source.allow_new_crawl=false` 不影响读取已有文件。

`.seospiderconfig` 是配置文件，不是 crawl。没有 reader 时，只要求打开已有 crawl 并导出必要结果，不能改成 Configuration → Load → Start。详见 [共用 saved-crawl 操作与报错说明](https://github.com/timn-firstpage/On-_site_SF_shared_config/blob/main/references/saved-crawl-entry.md)。

1. 复用同一网站、同一 crawl 的现有导出，记录来源与日期。
2. 读取分页合集、Internal All 和 Near Duplicates URL 配对。
3. Python 按 14.1–14.6 判断，保存结果、证据及错误。
4. Node 生成 Excel，读回验证内容并生成可用预览。
5. Agent 检查排版，交付报告与需要人工处理的下一步。

本模块不自动启动 crawl、不点击 AJAX 或 View All，也不修改网站。数据多少就检查多少，不额外推断全站完整性并因此要求 Human check。

## SF 数据与分工

| 数据／组件 | 负责内容 |
| --- | --- |
| Pagination → First Page ∪ Paginated 2+ Pages | 定义分页范围，提供 canonical、rel=next 和 rel=prev；等价的 Pagination All 导出也可使用。 |
| Internal → All | 建立 Address 查询表，读取状态、跳转、canonical，以及重复配对双方的 Indexability／Indexability Status。 |
| Content → Near Duplicates 配对 | 提供当前 URL 与匹配 URL；只有相似度或数量、没有匹配地址的 overview 不够。 |
| Agent | 获取完整 native 导出、映射字段并检查报告。 |
| Python／Node | Python 离线判定及归档；Node 校验、生成和读回 Excel。脚本不调用 SF、网站或付费 API。 |

默认文件名：`pagination_all.csv`、`internal_all.csv`、`near_duplicate_pairs.csv`。可在 `pagination.exports` 映射实际路径，或分别提供 First Page 和 Paginated 2+ Pages。字段和别名见 [CSV 输入说明](references/exports.md)。

因为 14.1 已跳过，不需要 All Outlinks 或 Pagination URL Not In Anchor Tag。有效的只有表头、没有记录的 CSV 是空结果；缺文件、零字节文件或缺必要字段是实际输入错误，不能当空结果。

## 14.1–14.6 逐项检查逻辑

| Item | 怎么检查 | 结果判断 |
| --- | --- | --- |
| **14.1 Are there on-page links to page 2 and onward? (can be hidden with CSS for users if ajax is being used)** | 按约定跳过自动检查，不执行先前的 anchor／next linkage 算法。 | 固定 **Human check**。人工核验分页 anchor、AJAX 发现方式及末页例外；不进入问题页。 |
| **14.2 Is the client having both a “View All” page and paginated pages without a correct rel=canonical?** | 保留原 item name，实际检查分页 canonical；View All 不参与判断。 | **√**：指向自身或同一分页的干净 URL。**X**：缺失、无效、声明冲突，或指向错误的首页／其他分页／无关 URL。列当前 URL、canonical、预期目标和原因。 |
| **14.3 Are rel=”prev” and rel=”next” link attributes being used, so that Google knows to consolidate the ranking signals?** | 每条分页记录检查 rel=next／rel=prev 是否有值；不检查对应 anchor 或目标响应。 | 任一有值 → 该记录通过；两者都空 → **X**。不要求两者都有，不使用 N/A。有效分页结果为空也记 **X**，说明未找到声明。 |
| **14.4 Does the client have a page=1 in addition to the root page? (This is wrong if no canonical)** | 精确筛选 `page=1`，只移除这个参数、保留其他参数，找对应 root；在 Internal All 查询双方。 | root 不在数据中 → 不触发 X。双方存在：301／308 永久跳转到 root，或 200 canonical 正确指向 root → **√**；200 缺失／自身／其他／冲突 canonical，或永久跳转目标错误／循环 → **X**。404／410 不算重复入口；其他未覆盖响应状态 → **Human check**。 |
| **14.5 Caused Duplication? (Even if your H1 etc are the same, the actual page content differs, it’s not duplication)** | 读取实际配对；至少一端在分页范围内，关联双方索引状态，排除自身配对并合并正反重复。 | 双方都是 Indexable，且都没有 Canonicalised 状态 → **X**，列双方 URL；否则不触发 X。相同 H1／title 不单独判重复。有效空配对结果 → **√**。 |
| **14.6 On paginated content, does the canonical tag always refer to the page itself?** | 复用 14.2 的判断，保留独立 checklist 行。 | **√／X** 与 14.2 一致；相同缺陷在问题页合并一条，标注 **14.2/14.6**。 |

**Canonical 例外：** `page=1` 可以指向对应 root；tracking 变体可以指向同一页码的干净 URL。默认移除 `utm_*`、gclid、fbclid、msclkid，保留筛选、排序、语言和页码参数。不静默合并路径大小写、尾斜杠或 www 变体。

**14.3 的原名称保留，但 Google 已不再使用 prev／next 合并排名信号。** 当前结果只表示声明是否存在，不声称缺少标签会损害 Google 排名。

**14.5 是约定的 SF 相似内容筛选规则，不是正文完全相同的证明。** Canonicalised 是状态，不是 Canonical Link Element 是否有值；双方即使都有 self-canonical，仍可能触发规则。报告建议复核实际内容，不声称 Google 重复内容处罚。

每项发现任何匹配错误即 X。除固定跳过的 14.1 和未覆盖响应状态外，Human check 用于实际文件、字段或工具错误。已有明确 X 时保留 X，并说明其他错误。详细边界见 [六项审计规则](references/audit-rules.md)。

## Excel 输出

文件名：**`{site_name}_onsite_pagination_audit_{YYYY-MM-DD}.xlsx`**。日期使用明确指定值或配置时区，默认 Asia/Hong_Kong；拒绝覆盖旧报告。

**1. Checklist — 始终输出六项**

| Item No. | Item Name | Check Result | Findings | Instruction |
| --- | --- | --- | --- | --- |
| 14.1–14.6 | 原始英文检查名称 | √ / X / Human check | 简短发现与原因 | 人需要做的下一步 |

**2. 14. Pagination — 只有出现 X 才创建**

| Address | Issue | Instruction |
| --- | --- | --- |
| 当前 URL | 检查编号、问题、canonical／目标／配对 URL 及原因 | 具体处理建议 |

**Findings 只写发现，Instruction 只写下一步。** 无需处理时填“无需处理。”；没有 Coverage 列。Human check 留在 Checklist，不写入问题页。14.2／14.6 相同问题只列一次，保留两个编号。完整问题保存在 workbook，不以聊天样本或预览代替；来源、hash、数量与错误留在内部记录。详见 [输出合同](references/output-contract.md)。

## Global config 接入

共用 `site/source/mcp/budget/cache/output`；本模块只增加 `checks.pagination`、`pagination.exports` 和 `pagination.tracking_parameters`。`checks.pagination=false` 时禁用，不写报告。沿用已有配置、SF handover、缓存及累计预算，不修改其他 onsite 模块设置、不归零 usage。

同一个 SF 实例串行打开／导出，各模块读取同一批缓存文件。`checks.live_checks=false` 禁止新增网站读取，不妨碍解析已有文件或支持的 SF 导出。本模块的判断本身不需要 live requests。

只写共享 run 下的 **`pagination/`** 子目录，已有子目录不覆盖。协调流程可读取 `findings.json` 汇总；master workbook 合并由明确请求的协调流程负责。详见 [共享配置与证据交接](references/shared-config.md)。

## 运行、测试与打包

Agent 先解析路径、获取导出，再执行：

```text
python scripts/audit.py --config <config.json> --run-dir <shared-run>
node scripts/build_report.mjs --input <shared-run>/pagination/findings.json --node-modules <discovered-bundled-node_modules> --preview
```

Python 需要 **3.10+**，检查脚本只用标准库。Excel 生成器使用 Spreadsheets skill 提供的 Node 和 `@oai/artifact-tool`，由 agent 通过 `load_workspace_dependencies` 查找。生成 workbook 前遵循该 skill 的 artifact-operation marker；不向 bundled runtime 自动安装依赖。`output.language` 支持 zh／en。命令中的占位符替换为实际机器路径；相对配置路径按 config 所在目录解析。

输出位于 `<shared-run>/pagination/`：findings.json、manifest.json、原始导出归档（开启时）、CSV 中间文件、Excel 及验证／预览记录。Excel 导出或读回失败时保留 findings 和证据。

离线验证与打包：

```text
python -m unittest discover -s tests -v
node --test tests/report.test.mjs
python scripts/package_skill.py --output dist/onsite-audit-pagination.zip
```

ZIP 内是一个 `onsite-audit-pagination/` runtime 目录，包含 skill、说明、配置、references 和运行脚本，不包含本地数据、tests、依赖、计划或 Git 历史。

设置 `AUDIT_NODE_MODULES` 为实际 bundled node_modules 路径，才能运行报告 CLI 集成测试；未设置时该依赖测试会跳过。预览在独立进程运行，preview-status.json 记录 PNG 是否可用及 renderer 退出异常；预览异常不改变检查结果，也不代表已验证的 workbook 导出失败。

## 文档与验证

- [Skill 入口](SKILL.md)
- [六项审计规则](references/audit-rules.md)
- [SF 导出与字段映射](references/exports.md)
- [共享配置接入](references/shared-config.md)
- [Excel 与 findings schema](references/output-contract.md)

已通过 **14 项 Python 测试和 4 项 Node 测试**，包括 canonical、page=1／root、相似配对、空结果／坏 CSV，以及实际 Excel 生成与读回验证。Windows 原生预览 renderer 的退出异常已隔离并记录，不宣称其底层问题已修复。

目前验证使用合成数据，尚未完成真实网站的 SF → 导出 → Excel 全流程验证。GitHub 导入不会自动提供 SF 连接、文件权限或 bundled spreadsheet runtime；Multica／远程 agent 需要在实际执行环境准备这些资源。该包是 agent 工作流和本地检查／报表工具，不是独立一键 crawler。

运行证据、客户 URL、报告、凭据和本机配置均留在忽略的 run 目录，不提交 Git。
