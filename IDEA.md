# IDEA.md — voice2text

## 問題
手上累積大量本地語音內容需要整理：iPhone 錄的口述想法/會議記錄、手動上傳的其他音檔，還有想追蹤的 podcast 節目新集數。逐一聽完非常花時間。

## 為什麼
省下聽音檔的時間；同時把財經、AI/科技領域的內容轉成可長期查閱、可延伸利用的資料庫——財經內容變成理財參考，AI/科技內容變成每日資訊。未來還會有新的內容方向，分類系統設計成可擴充、不綁死現有兩類。最終要整合進個人助理 AXIS。

## 成功長什麼樣（MVP）
抓「哈利說」EP1 podcast episode
（https://podcasts.apple.com/tw/podcast/ep1-%E8%A9%A6%E6%92%AD%E9%9B%86-%E5%85%A8%E4%B8%96%E7%95%8C%E4%B8%80%E8%B5%B7%E5%81%9A%E4%BA%86%E4%B8%80%E5%80%8B%E7%BE%8E%E5%A4%A2/id1702409419?i=1000624338047）
→ 存成本地音檔 → 用本地端方式轉成逐字稿 → AI 整理成 10 分鐘內可讀完的 markdown 報告。

判斷標準：讀完報告覺得忠實反映內容、看得完、AI 沒有亂編，就算過關，不需要額外量化指標。

## 決定
做。方法與流程設計為公開、可攜——任何機器都能獨立部署，不綁定使用者自己的 yyds 機器；GitHub 預設 public，需要 README + .env.example，機密外部化（比照現有專案慣例）。

## 架構決策摘要

### 轉錄（語音 → 文字）
- 本地端執行，不叫付費/雲端 API
- faster-whisper（MIT license）+ large-v3 checkpoint、int8 量化跑 CPU，自架本地 whisper server，主流程用 HTTP 呼叫
- 失敗時自動退回換一種設定/引擎重試一次，兩次都不行才標記「處理失敗/待確認」寫回 Notion，不整筆跳過不留紀錄
- 音檔格式：mp3/wav/m4a 皆可，實際上不特別限制清單（底層 ffmpeg 解碼涵蓋常見格式）
- 詳細研究依據（faster-whisper vs whisper.cpp vs WhisperX vs insanely-fast-whisper 比較、中英夾雜辨識已知限制、n8n 整合模式）見同資料夾 `voice2text-research.md`

### 整理（文字 → 結構化內容）
- 這一步才用 AI，輸出 markdown 格式（給 AI 讀，不是特別排版給人看）
- 內容＝針對該來源的分析報告，目標讀者是一般程度，10 分鐘內看完；逐字稿原文一併保留
- 限制 AI 只能根據逐字稿內容整理，不能自己外加逐字稿沒提到的資訊或做延伸判斷（避免亂編）
- 分類：Notion multi-select tag，可隨時擴充新類別，一份內容可掛多個 tag；財經 → 理財參考，AI/科技 → 每日資訊，未來新方向走同一套 pipeline

### 儲存
- 原始音檔、逐字稿、整理後 markdown 都寫進 Notion（教育版方案）；原始音檔本機端保留原地不動、不搬移
- 已處理清單以 Notion 本身當來源（每筆記錄含檔名＋檔案大小），本地端視需要另存一份，非必要

### 觸發
- n8n 排程每天跑一次（不是即時監看新檔案），比照既有 Podcast workflow 的模式

### 兩條輸入來源
1. **個人音檔**（iPhone 錄音、會議記錄、手動上傳的任意格式音檔）——自己上傳到 Notion；後續可設計 iPhone 捷徑，捷徑只把錄音 POST 到 n8n 的 webhook，跟 Notion 溝通的邏輯全部留在 n8n（API token 不落在手機端）
2. **Podcast 追蹤**——自己在 Notion 貼 RSS feed 網址（不串手機既有訂閱），n8n 每天偵測新集數，自動抓音檔存進 Notion 再進轉錄流程；只有 Apple Podcasts 頁面網址時，可透過 iTunes Lookup API 轉成 RSS 網址

### 判重
檔名 + 檔案大小

### Notion 檔案上傳能力（已查證）
Notion API 有正式 File Upload API（20MB 內一次 multipart 上傳，超過走多段上傳）；免費 workspace 單檔 5MB、付費 5GB。教育版方案對應到哪一檔還沒查證（見下方待確認）。

### 未來延伸
- 整合進 AXIS 個人助理
- 分類系統要能隨時加新方向，不用重新設計架構

## 待確認 / 超出 MVP 範圍
- 已處理清單本地端是否真的需要另存一份，還是 Notion 就夠
- 教育版 Notion 的實際檔案上傳大小限制
- Podcast RSS ／ Apple Podcasts 連結反查的 n8n 節點設計細節
- 測試環境隔離（獨立音檔樣本、獨立 Notion test DB）留到實作階段，照四步驟開發循環規則處理
