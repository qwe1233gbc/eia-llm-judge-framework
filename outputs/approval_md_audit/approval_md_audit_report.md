# Approval PDF → MD Coverage Audit Report

## Summary

- Approval PDFs: 3195
- Matched valid approval md: 0
- Candidate needs review: 107
- Missing md: 2559
- Wrong type (md not approval): 529

## Key Finding

Approval PDFs were NOT processed by MinerU. The mineru_extracted/ directory contains only REPORT MDs.
Approval PDFs are small (avg 410KB, 72% under 200KB) and can be read directly by Codex via pypdf.

## Recommended Strategy for Codex

- **Reports**: Use MinerU MDs from mineru_extracted/
- **Approvals**: Read PDFs directly (they're small text documents, not scanned images)
- Approval MD conversion is NOT needed; PDF direct reading is fine

## CODEX_MD_ONLY_INSTRUCTION

Codex 后续 strict pipeline 必须区分处理方式：

报告（受理公告）输入优先来自：
E:\软件\mineru_extracted（MD格式，已解析好）

批复输入：
E:\软件\2023-2026年顺德批复文件（PDF格式，直接读取，无需转MD）
批复 PDF 体积小（平均410KB），72% 小于200KB，可直接用 pypdf 读取。

如果某个批复 PDF 特别大（>1MB），可能是扫描件，需要单独处理。

## Details

### Matched (MD found for approval)

None. Approval PDFs were not processed by MinerU.

### Candidate Matches (107)



(0 total, showing first 30)

### Missing MD (High Priority)

- 2019_2019_3110582_1.pdf
- 2019_2019_3110582_2.pdf
- 2019_2019_3110582_3.pdf
- 2019_2019_3110582_4.pdf
- 2019_2019_3110582_5.pdf
- 2019_2019_3110582_6.pdf
- 2019_2019_3110628_1.pdf
- 2019_2019_3110628_2.pdf
- 2019_2019_3110628_3.pdf
- 2019_2019_3110628_4.pdf
- 2019_2019_3110628_5.pdf
- 2019_2019_3110628_6.pdf
- 2019_2019_3110636_1.pdf
- 2019_2019_3110644_1.pdf
- 2019_2019_3110644_2.pdf
- 2019_2019_3110644_3.pdf
- 2019_2019_3110644_4.pdf
- 2019_2019_3110644_5.pdf
- 2019_2019_3110652_1.pdf
- 2019_2019_3110652_2.pdf
