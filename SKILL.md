---
name: test-case-gen
description: 解析 Word 需求文档（.docx），严格按规则生成测试用例并写入飞书电子表格的新工作表。当用户提供 .docx 需求文档并要求生成测试用例、编写用例、导入飞书表格时使用。
---

# 测试用例生成（test-case-gen）

把一份 Word 需求文档变成写入飞书电子表格的测试用例。你负责理解需求（含图片）和按规则编写用例；脚本负责解析 docx 和写飞书。

## 用例编写规则（逐字执行，不得增删）

你是一名经验丰富的软件测试工程师，请严格根据我提供的需求描述编写测试用例。
要求：
1. 【严格基于需求】不得添加任何需求文档中未明确提及的测试场景，不要发挥想象
2. 【覆盖维度】正向流程 / 异常流程 / 边界值 / 权限控制 / 联动逻辑，需求中有内置验收标准的必须全部转化为测试用例
3. 【输出格式】excel表格，列：用例编号 | 模块 | 优先级(P0/P1/P2) | 用例标题 | 前置条件 | 测试步骤 | 预期结果
4. 【优先级定义】P0=核心主流程/系统崩溃类；P1=重要功能/异常处理；P2=边界细节/体验优化
5. 不要输出任何解释说明，直接输出表格

**硬性禁令**：为凑覆盖维度而编造需求中不存在的场景 = 任务失败。需求没写的就不要有用例。

## 工作流

1. **确认输入**：确认用户给的 `.docx` 路径存在（`.doc` 老格式不支持，提示另存为 `.docx`）。`--target` 未指定时默认写 wiki token `M2VawdEO4iwZx2khc6xccAK1nOf`。
2. **解析文档**（命令行不传中文，路径参数除外；stdout 是 ASCII 摘要）：

   ```
   python C:/Users/Administrator/.claude/skills/test-case-gen/scripts/parse_docx.py <docx路径> <out_dir>
   ```

   out_dir 用系统临时目录，如 `C:/Users/Administrator/AppData/Local/Temp/tcg_<文档名>`。退出码 2 = 空文档，停下来问用户。
3. **看图**：用 Read 工具逐张查看 content.json 里 `images` 列出的全部图片——流程图/原型图里的信息属于需求。同时通读 `paragraphs`、`tables`、`textboxes`（文本框常藏验收标准）。
4. **生成用例**：按上方规则编写用例，用 Write 写成 JSON 到**工作目录**（留档审计）：

   ```json
   {"title": "<文档首个Heading文本，无则用文件名；不得含 \\/:*?\"<>|[] 字符>",
    "cases": [["", "模块", "P0", "用例标题", "前置条件", "测试步骤", "预期结果"], ...]}
   ```

   文件名 `testcases_<文档名>.json`。用例编号列留空串——脚本会统一重排为 TC-001..TC-nn 并校验优先级/必填列。
5. **写入飞书**：

   ```
   python C:/Users/Administrator/.claude/skills/test-case-gen/scripts/write_cases.py --cases <json路径> --target <用户链接或默认token>
   ```

   成功输出 `OK sheet_id=... title=... total=N p0=a p1=b p2=c`。脚本自动：建新工作表（重名加 -2 后缀）、写表头+用例、逐格复核。
6. **汇报**（中文）：工作表名、总条数、P0/P1/P2 分布、飞书链接 `https://my.feishu.cn/sheets/<spreadsheet_token>`。

## 错误处理

- write_cases 退出码 **2**：校验失败，stdout 有逐行问题清单（ASCII）→ 修正用例 JSON 后重跑，不要绕过校验。
- 退出码 **3 / FeishuAPIError**：code=99991672 类权限错误 → 指引用户到[开放平台](https://open.feishu.cn/app)给应用开通对应权限并发布版本，再把应用加为文档协作者（「···」→「添加文档应用」→ 可编辑）。
- 网络失败：重试一次；仍失败如实汇报。

## 明确禁止

- 禁止对飞书中**已存在**的工作表做任何写/删操作（技能只新建工作表）。
- 禁止在用例数据中混入任何解释说明文字。
- 禁止把用例数据直接经命令行参数传给脚本（中文会乱码）——一律走 JSON 文件。
