# CLAUDE.md - 杨龙翔本地工作环境配置

## 系统角色定位

| 角色 | 定位 | 运行环境 |
|------|------|---------|
| **Claude Code（本地） | Windows 本地文件处理、MinerU 执行、批量脚本、环评文件 I/O | Windows (D:\) |
| **OpenClaw（服务器） | 知识沉淀、记忆编排、跨会话推理、论文写作 | Linux 服务器 |

**核心原则**：本地能做的不推服务器；需要积累、推理、写作的交给 OpenClaw。

---

## 本地关键路径

```
MINERU_DATA      D:\MinerU                       # MinerU 已解析标准文档（1726 个目录）
REVIEW_COMMENTS   D:\华南理工项目\环评知识库文件\环评（识别+审核）资料\环评（识别+审核）资料\环评审批资料\环评审批资料\修改意见  # 92 个 Word 批注文件
EXTRACTED_XML    D:\华南理工项目\环评知识库文件\...\修改意见\extracted_xml  # XML 解析结果（58 个文件）
ZOTERO_DB        本地 Zotero SQLite（运行 detect_zotero_paths.py 获取）
ZOTERO_WEBDAV   坚果云 WebDAV（zotero 附件库，ZIP 格式，按 item_key 命名）
ZOTERO_API       Zotero API Key: FLYoBrm3UUETkCX3rtKS1JDb
```

---

## 完整科研周期分工

```
【本地 NVIDIA】
Mining 任务
  ↓
【本地 MinerU 解析】
  D:\MinerU 目录
  ↓ 1726 个已解析文档
【本地 Claude Code】
  批量批注提取脚本
  ↓ 输出 Excel + XML
【服务器 OpenClaw】
  知识沉淀 + 经验提取 + 论文写作
```

---

## Claude Code 的具体职责

### 1. MinerU 相关
- minerU-open-api 解析（flash-extract / extract）
- 判断用哪个模式
- 异常重试和批量调度

### 2. 批注提取相关
- review_extractor.py 批量处理 Word 文件
- 输出 Excel + XML 到 extracted_xml 目录
- 异常文件单独记录

### 3. Zotero 相关
- detect_zotero_paths.py 获取本地路径
- build_metadata_vectors.py 生成向量索引
- 手动同步索引到服务器

### 4. 其他本地文件处理
- 文件批量 I/O
- Word / Excel 处理
- 临时数据整理

---

## OpenClaw 的具体职责

### 1. 知识沉淀
- Obsidian 笔记写入（GitHub 同步）
- MEMORY.md / meeting_minutes 更新

### 2. 知识推理
- 跨会话记忆保持
- 研究问题识别
- 论文结构规划

### 3. 经验提取
- 批注-原文对齐脚本（已在服务器）
- 结构化经验知识抽取

### 4. 论文写作
- 各阶段论文辅助写作
- 表达优化和结构建议

---

## 信息同步协议

### 本地 → 服务器

| 触发条件 | 同步方式 | 说明 |
|---------|---------|------|
| 批量处理完成 | 飞书附件（Excel/zip）+ 简短说明 | 本地跑完批注提取后，发文件 + 结果摘要 |
| 发现关键数据 | 飞书消息 + 存 MEMO.md | 描述关键发现，附文件路径 |
| 脚本执行失败 | 飞书消息 | 说明错误，附错误日志 |
| MinerU 解析完成 | 更新 checklist.md | 在共享文档记录状态 |

### 服务器 → 本地

| 触发条件 | 同步方式 | 说明 |
|---------|---------|------|
| 发出任务指令 | 飞书消息 | 说明输入路径、输出路径、处理逻辑 |
| 需要本地跑脚本 | 飞书消息 | 具体脚本名 + 参数 |
| 知识库更新完成 | Obsidian GitHub 同步 | 本地 git pull |
| 研究结论需要验证 | 飞书消息 | 说明需要本地确认的问题 |

---

## 任务交接模板

### 本地跑完脚本后发给 OpenClaw 的消息格式：

```
【处理完成】
脚本：xxx.py
输入：xxx
输出：xxx 条记录 / xxx 个文件
关键发现：xxx
输出位置：xxx
下一步建议：xxx
```

### OpenClaw 给本地任务的消息格式：

```
【任务指令】
脚本：xxx.py
输入文件：xxx 路径
输出位置：xxx 路径
处理逻辑：xxx
注意事项：xxx
触发条件：xxx 时告知 OpenClaw
```

---

## 禁止行为

- 不在本地跑破坏性操作（删除源文件、覆盖未备份数据）
- 不直接发 .sqlite 数据库文件（用 Excel/JSON 代替）
- 不在未确认前做不可逆操作
