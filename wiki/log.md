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