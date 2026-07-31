# 本地端用 faster-whisper 轉錄，不叫雲端/付費 STT API

轉錄步驟堅持全本地執行（faster-whisper + large-v3 checkpoint、int8 量化跑 CPU，自架 OpenAI-API-相容的
whisper server，主流程走 HTTP 呼叫），拒絕任何雲端付費轉錄服務（Google STT、AssemblyAI、OpenAI Whisper API 等）。

**為什麼看起來反直覺**：雲端 STT API 通常更快設定、免維護、更新頻繁。這裡刻意不用，是因為專案要公開、可攜
（任何機器都能獨立部署），本地端轉錄才能維持「不用申請金鑰、不用付費、不綁定特定雲端帳號」這個特性；同時
中英夾雜辨識的準確度取決於 Whisper checkpoint 本身，不是雲端包裝層的差異（見 `voice2text-research.md` 第 2 節），
所以本地跑同一個 checkpoint 沒有犧牲品質。

**考慮過的替代方案**：whisper.cpp（更純 CPU 優化、無 Python 依賴，若 faster-whisper 路線卡住可換）；
WhisperX（多加詞級對齊/多人分軌，目前用不到，先不採用，之後真的有多人語音再加）；insanely-fast-whisper
（需要 CUDA/mps，CPU 環境直接排除）。
