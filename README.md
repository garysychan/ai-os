# AI OS Control Plane

AI OS Control Plane 是一套以文件驅動的 AI 專案治理框架。它把治理、Agent 分工、工程規則、系統架構、執行流程與任務狀態分開管理，讓 AI、Codex、人類審核者及 GitHub 能在同一套可追蹤規則下協作。

## 六個控制文件

| 文件 | 負責內容 | 能建立的能力 |
|---|---|---|
| [`CONTROL_PLANE.md`](CONTROL_PLANE.md) | 治理、權限、版本、變更審批、衝突處理與一致性檢查 | 建立整個 AI OS 的治理核心，防止 Agent 未經批准改變規則、架構或安全邊界 |
| [`AGENTS.md`](AGENTS.md) | Controller、Planner、Researcher、Developer、Tester、Reviewer、Fixer 的角色與交接規則 | 建立可分工、可交接、可升級問題的多 Agent 執行模型 |
| [`PROJECT_RULES.md`](PROJECT_RULES.md) | 程式、架構、Git、測試、安全、文件與品質閘門 | 建立所有 Agent 與工程工作的強制行為準則及品質底線 |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | AI OS、Codex、GitHub、模組、資料狀態、整合與安全架構 | 建立可模組化、可替換整合、可測試及可持續演進的系統藍圖 |
| [`WORKFLOW.md`](WORKFLOW.md) | Requirement → Analysis → Planning → Execution → Testing → Review → Validation → Completion | 建立可實際執行的任務生命週期、狀態轉換、審批閘門與錯誤處理流程 |
| [`TASKS.md`](TASKS.md) | Task ID、優先級、Agent、依賴、驗收條件、狀態及 Roadmap | 建立可追蹤、可排程、可與 GitHub Issues／Projects 同步的持久任務登錄表 |

## 六個文件組合後能做甚麼

這套 Control Plane 可以用來建立：

- **受治理的 AI 開發系統**：Agent 只能在明確權限、規則與批准範圍內行動。
- **多 Agent 軟體工程團隊**：從規劃、研究、開發、測試到審核與修正，各角色有清楚責任。
- **Codex 執行層**：Codex 可依 Task 執行 Repository 檢查、實作、測試、修正及準備 Commit／PR。
- **GitHub 協作流程**：把 Task、Branch、Commit、Pull Request、Review 與 Merge 串成可追溯流程。
- **自動品質閘門**：依變更風險執行測試、Review、Validation、安全與完成條件檢查。
- **Control Plane 一致性檢查器**：偵測缺少文件、無效 Agent、錯誤狀態、死引用、權限衝突及規則矛盾。
- **人類在環治理**：重大架構、政策、安全、權限、破壞性或生產環境變更必須由人類明確批准。
- **可恢復的專案狀態**：GitHub 保存版本歷史，`TASKS.md` 保存工作狀態，讓決策與執行結果可審計及復原。

## 運作關係

```text
CONTROL_PLANE.md
├── AGENTS.md          定義誰執行
├── PROJECT_RULES.md   定義必須遵守甚麼
├── ARCHITECTURE.md    定義系統如何組成
├── WORKFLOW.md        定義工作如何流轉
└── TASKS.md           記錄目前要做甚麼與進度
```

當文件發生衝突時，先判斷衝突所屬領域，再以該領域的 authoritative document 為準；不得由 Agent 靜默猜測或跳過審批。

## 目標

AI OS 應保持：

- Governed
- Traceable
- Reviewable
- Testable
- Versioned
- Recoverable
- Human-controlled
