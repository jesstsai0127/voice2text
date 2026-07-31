# voice2text — Local Whisper Pipeline Research (idea-grilling stage)

Researched 2026-07-31. Goal: pick an offline/local ASR stack for a large backlog of Traditional-Chinese + English code-switched audio, orchestrated from n8n, running 24/7 on `yyds` (assume CPU-only or modest consumer GPU — no confirmed GPU specs).

## 1. Tool comparison

| Tool | License | Last push (GitHub API) | Stars / open issues | Code-switching suitability | CPU/GPU needs |
|---|---|---|---|---|---|
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | MIT | 2026-07-30 | 52.4k / 1228 | Runs any Whisper checkpoint incl. large-v3, so inherits Whisper's own code-switching behavior; no special enhancement | **CPU-first** design (AVX/NEON), optional GPU backends (CUDA, Metal, Vulkan, OpenVINO) — best CPU story of the four |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT | 2025-11-19 | 24.6k / 315 | Same underlying Whisper weights as whisper.cpp; CTranslate2 int8 keeps CPU viable | CPU (int8) or GPU (CUDA), good middle ground |
| [WhisperX](https://github.com/m-bain/whisperX) | BSD-2-Clause | 2026-07-13 | 23.3k / 209 | Same ASR core (now uses faster-whisper as backend) + adds word-level alignment/diarization on top — doesn't change code-switching accuracy itself | Alignment models are per-language (wav2vec2); diarization via pyannote (CC-BY-4.0, separate license) adds GPU-leaning overhead |
| [insanely-fast-whisper](https://github.com/Vaibhavs10/insanely-fast-whisper) | Apache-2.0 | 2025-10-25 | 13.0k / 116 | Same Whisper weights, no accuracy change | **Requires NVIDIA CUDA or Apple `mps`** — explicitly no practical CPU-only path, disqualifying for this project |

All four are MIT/BSD/Apache — no GPL or usage-restricted licenses, all fine for the household's default-public GitHub convention. None show an active security advisory or an archived/abandoned state as of check date. faster-whisper and insanely-fast-whisper haven't pushed in ~8–9 months (not yet "stale" by the >1yr flag, but slower cadence than whisper.cpp/WhisperX, which pushed within the last month).

Sources: [ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp), [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper), [m-bain/whisperX](https://github.com/m-bain/whisperX), [Vaibhavs10/insanely-fast-whisper](https://github.com/Vaibhavs10/insanely-fast-whisper) (stats pulled live via GitHub REST API `/repos/{owner}/{repo}`).

## 2. Mandarin-English code-switching accuracy

- **Base Whisper was not designed for code-switching.** It does 30-second-window language detection and assumes one language per window; maintainers/users confirm on the official repo that when it hits a second language mid-clip it tends to *translate* the foreign words into the detected primary language rather than transcribing them faithfully — a known, discussed limitation, not a bug that gets silently fixed. See [openai/whisper Discussion #2385 "Whisper should support mixed languages"](https://github.com/openai/whisper/discussions/2385), [#976 "Codeswitching"](https://github.com/openai/whisper/discussions/976), [#807 "audio contains Chinese and English, can it be recognized at the same time?"](https://github.com/openai/whisper/discussions/807).
- The official [Whisper model card](https://github.com/openai/whisper/blob/main/model-card.md) documents general "uneven performance across languages" and hallucination risk under weak supervision, but does not give a code-switching-specific number — this is a documented gap the community fills, not OpenAI.
- **large-v3 is the strongest general-purpose checkpoint for this**: [openai/whisper-large-v3 model card](https://huggingface.co/openai/whisper-large-v3) states it "shows improved performance over a wide variety of languages, showing 10% to 20% reduction of errors compared to Whisper large-v2," Apache-2.0 licensed.
- **large-v3-turbo** is a pruned decoder variant (32→4 decoding layers) with much higher throughput (RTFx ≈ 200 vs large-v3) but "minor quality degradation" per its own [model card](https://huggingface.co/openai/whisper-large-v3-turbo) — no quantified Chinese-specific number published; treat the tradeoff as a speed/accuracy dial, not a free lunch.
- **Traditional-Chinese-specific fine-tunes exist and target exactly this gap**: e.g. [shooding/faster-whisper-large-v3-zh-TW](https://huggingface.co/shooding/faster-whisper-large-v3-zh-TW) — LoRA fine-tune of large-v3 on Taiwan government's Taiwan-Tongues-ASR-CE dataset, Apache-2.0, already converted to CTranslate2/faster-whisper format; and the [JacobLinCool Traditional Chinese ASR collection](https://huggingface.co/collections/JacobLinCool/traditional-chinese-asr-model). These are evidence the community explicitly treats stock Whisper's zh-TW accuracy as needing improvement — neither publishes a rigorous code-switching benchmark yet (shooding's card says exact zh-TW benchmark numbers are "planned for a future update"), so treat as directionally promising, not proven.
- One directly relevant academic comparison, [arXiv:2412.00721 "A Comparative Study of LLM-based ASR and Whisper in Low Resource and Code Switching Scenario"](https://arxiv.org/abs/2412.00721), reports Whisper *outperforming* LLM-based ASR specifically in Mandarin-English code-switching (even though an LLM-based approach won on plain low-resource ASR) — **note: this paper was withdrawn by its author (2024-12-04) and is incomplete**, so treat as a weak, directional signal only, not settled evidence.
- Practical implication: stock `large-v3` via faster-whisper/whisper.cpp is a reasonable starting point given no better-proven alternative was found; if code-switching WER turns out too high in practice, swapping in a zh-TW fine-tune (same CTranslate2 format, drop-in for faster-whisper) is a low-cost next step, not a rebuild.

## 3. n8n integration precedent

There is **no first-party "local Whisper" n8n node that fits this use case**. What people actually do, per official templates and community threads:

- **Execute Command node → local Whisper binary/CLI.** n8n's own template [Generate & Translate Video Subtitles with OpenAI Whisper and LibreTranslate](https://n8n.io/workflows/9301-generate-and-translate-video-subtitles-with-openai-whisper-and-libretranslate/) and community guides both require self-hosted n8n (cloud n8n can't shell out) plus FFmpeg + Whisper installed on the same host, invoked via Execute Command.
- **HTTP Request node → self-hosted OpenAI-compatible transcription server.** This is the cleaner pattern for a 24/7 box: run a faster-whisper-backed server that speaks the OpenAI `/v1/audio/transcriptions` API, then just point an HTTP Request node at `localhost`. Concrete primary-source options: [fedirz/faster-whisper-server](https://github.com/fedirz/faster-whisper-server) (OpenAI-API-compatible, Docker-deployable, faster-whisper backend, supports streaming) and [hwdsl2/docker-whisper](https://github.com/hwdsl2/docker-whisper) (faster-whisper-powered, diarization, JSON/SRT/VTT output, offline mode, GPU optional). Both let n8n stay a thin HTTP client with zero Python/Whisper installed inside the n8n container itself.
- **Existing community n8n node is a dead end for this project**: [dioveath/n8n-nodes-transcribe-audio](https://github.com/dioveath/n8n-nodes-transcribe-audio) (MIT) uses Transformers.js with `Xenova/whisper-*.en` models — **English-only variants**, unusable for Mandarin/code-switching, and shows only 10 commits total with no visible recent activity.
- Real user pain confirmed on [community.n8n.io: "Can't set up Whisper or Python locally"](https://community.n8n.io/t/cant-set-up-whisper-or-python-locally/74378) — the asker hit Docker/Alpine permission errors trying to `pip install openai-whisper` inside the n8n container; the community fix was a custom Dockerfile layering Python+pip+whisper onto the n8n image and calling it via n8n's Python3 node. This reinforces that a **separate whisper server + HTTP Request node** is architecturally cleaner than embedding Whisper inside n8n's own container.

## 4. Hardware/performance tradeoffs (CPU-only assumption)

whisper.cpp's own community-submitted CPU benchmarks ([Issue #89](https://github.com/ggml-org/whisper.cpp/issues/89), encode time per ~1 sample, 8 threads):

| Model | MacBook M1 Pro (NEON) | Ryzen 9 5950X (AVX2) | Ryzen 9 3900X (AVX2, older) |
|---|---|---|---|
| tiny | 102ms | 197ms | 422ms |
| base | 220ms | 421ms | 880ms |
| small | 685ms | 1393ms | 2874ms |
| medium | 1928ms | 4404ms | 9610ms |
| large | 3350ms | 8118ms | 16917ms |

Takeaway: on a modern desktop-class CPU (5950X-tier), `small` and even `medium` stay well within real-time-ish territory for batch/offline processing (this is a backlog job, not live transcription, so RTF > 1 is tolerable as long as it's not absurd). `large`/`large-v3` on CPU is the slow end but still finishes a clip in low-single-digit multiples of its length — acceptable for an overnight batch job on a 24/7 box, not for live use.

faster-whisper's own README benchmarks ([SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper)) show `small` model, CPU, int8: **1m42s** vs OpenAI reference implementation's **6m58s** for the same audio, at lower RAM (1477MB vs 2335MB) — i.e., CTranslate2 int8 quantization is the single biggest CPU lever available, roughly 4x over the naive OpenAI Python implementation, independent of GPU.

insanely-fast-whisper is excluded from the CPU-viable set entirely — its own README benchmarks are all GPU/`mps`, with no meaningful CPU path.

Given "assume CPU-only or at best a modest consumer GPU": **faster-whisper with int8 quantization, `large-v3` (or `medium` if large proves too slow at scale), run as an offline batch job** is the realistic sweet spot — it's the only one of the four with both a credible CPU story *and* a documented ~4x speed multiplier over naive Whisper, without requiring a GPU class that isn't confirmed to exist on `yyds`.

## 5. Recommended output format for the transcript step

Both faster-whisper and whisper.cpp natively support word-level timestamps and multiple export formats (SRT/VTT/JSON) — see faster-whisper's `word_timestamps=True` / `vad_filter=True` options in its [README](https://github.com/SYSTRAN/faster-whisper) and whisper.cpp's built-in SRT/VTT/JSON exporters. WhisperX adds forced-alignment word timestamps (±50ms vs Whisper's native ~500ms) and pyannote-based speaker diarization on top, output as SRT or a JSON with per-word start/end and speaker labels ([m-bain/whisperX](https://github.com/m-bain/whisperX)).

Recommendation for this project:
- **Capture plain text + segment-level timestamps as JSON** (not just flat .txt) — faster-whisper/whisper.cpp give this for free, and it costs nothing extra to keep.
- **Skip diarization (WhisperX's main value-add) unless most of the backlog is multi-speaker.** The brief describes "user talking/listening to content" — likely single-speaker-dominant. Diarization pulls in pyannote (extra GPU-leaning dependency, separate CC-BY-4.0 license, own model download) for a feature that may not be needed. Add it later only if a real multi-speaker use case shows up.
- **Word-level timestamps are worth keeping** even without diarization — they make the downstream LLM-to-Notion step able to cite "at 12:34" or chunk long transcripts sensibly, and both whisper.cpp and faster-whisper emit them without WhisperX.
- Store the JSON (raw ASR output, timestamps intact) as the "raw transcript" artifact, and let the separate out-of-scope LLM step consume that JSON to produce the Notion-organized version — keeping both per the stated requirement.

## 6. Final recommendation

**Primary pick: faster-whisper (SYSTRAN/faster-whisper, MIT) running the `large-v3` checkpoint with int8 CPU quantization, served via a self-hosted OpenAI-compatible wrapper (e.g. [fedirz/faster-whisper-server](https://github.com/fedirz/faster-whisper-server) or [hwdsl2/docker-whisper](https://github.com/hwdsl2/docker-whisper)) that n8n calls over HTTP Request node.**

Why this wins against the project's constraints:
- Offline/free: fully local, MIT-licensed, no API key, no paid tier — satisfies the hard "no online transcription service" requirement.
- Code-switching: uses the exact same large-v3 weights as every other option here (code-switching quality is a Whisper-checkpoint property, not a wrapper property) while being the most CPU-practical way to run that checkpoint, with a documented ~4x speed win over naive Whisper on CPU.
- n8n integration: HTTP Request → local server is the cleanest, most-precedented pattern found (avoids the Docker/Python-inside-n8n pain reported on community.n8n.io), and both wrapper projects already emit JSON/SRT/VTT with timestamps for free.
- Hardware fit: explicitly designed to be CPU-viable (unlike insanely-fast-whisper, which is GPU/mps-only and is disqualified outright), while still taking advantage of a GPU later if `yyds` turns out to have one.

**Alternative 1 — whisper.cpp (MIT), same large-v3 weights.** Marginally more CPU-optimized in the whisper.cpp README/bench numbers, no Python runtime dependency at all (pure C/C++, good fit for a lean 24/7 box), and the most actively updated repo of the four (pushed same day as this research). Reasonable swap-in if the faster-whisper server route hits friction, or if avoiding a Python dependency chain matters more than the OpenAI-API-compatible convenience.

**Alternative 2 — WhisperX (BSD-2-Clause), if diarization/precise word alignment become a real requirement later** (e.g. if a chunk of the backlog turns out to be multi-speaker conversations, not just solo talking/listening). It layers cleanly on top of the same ASR core, so this isn't a fork-in-the-road decision made now — it's an additive upgrade path.

**Not recommended: insanely-fast-whisper** — no viable CPU path (CUDA/mps only per its own README), doesn't fit the "no confirmed GPU" hardware assumption, and offers no code-switching accuracy advantage over the other three since it runs the same underlying weights.

If code-switching accuracy on the actual backlog proves insufficient with stock large-v3, the next investigative step (out of scope for this research pass) is trialing a zh-TW fine-tune such as [shooding/faster-whisper-large-v3-zh-TW](https://huggingface.co/shooding/faster-whisper-large-v3-zh-TW) — it's already in faster-whisper/CTranslate2 format, so it's a config change, not an architecture change.
