# Log

## [2026-06-11] ingest | 凱迪拉克初級.pdf

- 依使用者要求跳過首 5 頁與末 5 頁，處理 PDF 第 6-133 頁。
- 使用 `pdftoppm` 渲染掃描頁，使用 macOS Vision OCR 產生中文 OCR JSONL。
- 自動裁切動作圖並寫入 `wiki/assets/cadillac_beginner_actions/`。
- 建立 source note、動作索引與肌肉/肌群分類頁。

## [2026-06-11] ingest | 凱迪拉克中高階.pdf

- 依使用者要求沿用初級處理方式，跳過首 5 頁與末 5 頁，處理 PDF 第 6-175 頁。
- 使用 `pdftoppm` 渲染橫向掃描頁，使用 macOS Vision OCR 產生中文 OCR JSONL。
- 自動裁切動作圖並寫入 `wiki/assets/cadillac_intermediate_advanced_actions/`。
- 建立 source note、動作索引與中高階肌肉/肌群分類頁。

## [2026-06-11] ingest | 普拉提塑身機初級 / 中級

- 依使用者要求沿用既有處理方式，兩份 PDF 均跳過首 5 頁與末 5 頁。
- 初級處理 PDF 第 6-111 頁；中級處理 PDF 第 6-163 頁。
- 使用 `pdftoppm` 渲染橫向掃描頁，使用 macOS Vision OCR 產生中文 OCR JSONL，再轉為繁體中文整理。
- 自動裁切動作圖並寫入 `wiki/assets/reformer_beginner_actions/` 與 `wiki/assets/reformer_intermediate_actions/`。
- 建立塑身機 source note、動作索引與肌肉/肌群分類頁；初級 44 個條目，中級 66 個條目。
