# UniMatch AI 服务

本目录承载 UniMatch 的 AI 网关配置、模型调用策略、本地模型推理说明以及可选的模型微调与推荐模型重训练流水线。

> 当前生产推理通过 OpenAI SDK 兼容层接入 DeepSeek / Kimi / LMStudio / OpenCode / MIMO，无需在此目录部署额外服务。本地模型微调与推荐模型离线重训练仅作为可选扩展路线。

---

## 目录

- [推理架构](#推理架构)
- [支持的 Provider](#支持的-provider)
- [本地模型：使用 LMStudio 推理](#本地模型使用-lmstudio-推理)
- [模型微调工作流](#模型微调工作流)
  - [环境准备](#环境准备)
  - [1. 导出训练数据](#1-导出训练数据)
  - [2. QLoRA 微调](#2-qlora-微调)
  - [3. 合并 LoRA 并导出 GGUF](#3-合并-lora-并导出-gguf)
  - [4. 接入 LMStudio](#4-接入-lmstudio)
- [推荐模型离线重训练](#推荐模型离线重训练)
- [训练数据格式](#训练数据格式)
- [参考](#参考)

---

## 推理架构

```mermaid
graph LR
  A[FastAPI 后端] -->|OpenAI SDK| B[AI 网关抽象]
  B --> C[DeepSeek]
  B --> D[Kimi]
  B --> E[LMStudio]
  B --> F[OpenCode]
  B --> G[MIMO]
```

- 后端通过统一的 `chat.completions` 接口调用 AI。
- 在 `.env` 中通过 `AI_PROVIDER` 指定默认 provider，并在运行时读取对应 API Key 与 Base URL。
- 生成任务包括：进阶问卷生成、匹配解释、可选的内容审核辅助。

---

## 支持的 Provider

| Provider | 必需环境变量 | Base URL 示例 |
|----------|--------------|---------------|
| DeepSeek | `DEEPSEEK_API_KEY` | `https://api.deepseek.com` |
| Kimi | `KIMI_API_KEY` | `https://api.moonshot.cn/v1` |
| LMStudio | `LMSTUDIO_API_KEY`（可填 `not-needed`） | `http://localhost:1234/v1` |
| OpenCode | `OPENCODE_API_KEY` | 待确认 |
| MIMO | `MIMO_API_KEY` | 待确认 |

---

## 本地模型：使用 LMStudio 推理

1. 安装 [LMStudio](https://lmstudio.ai/) 并下载兼容 OpenAI SDK 的模型（如 `Qwen2.5-7B-Instruct-GGUF`）。
2. 启动模型服务并开启 Local Server（默认端口 `1234`）。
3. 在 `.env` 中设置：

```env
AI_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_API_KEY=not-needed
LMSTUDIO_MODEL=qwen2.5-7b-instruct
```

4. 后端调用时会自动通过 OpenAI SDK 兼容接口请求本地模型。

---

## 模型微调工作流

本目录提供从业务数据到本地可部署模型的完整脚本：

| 脚本 | 作用 |
|------|------|
| `export_training_data.py` | 从 PostgreSQL 导出匿名化的 SFT / DPO 训练数据 |
| `train_qlora.py` | 使用 QLoRA 微调 Qwen2.5-Instruct |
| `merge_lora.py` | 合并 LoRA 权重并可选导出 GGUF |
| `retrain_recommendation.py` | 离线训练 Two-Tower / 矩阵分解推荐模型 |

### 环境准备

```bash
conda create -n unimatch-qlora python=3.11
conda activate unimatch-qlora
pip install -r services/ai/requirements.txt
```

`requirements.txt` 已包含运行脚本所需的核心依赖。如果希望使用 `unsloth` 加速训练，可额外安装：

```bash
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
```

### 1. 导出训练数据

```bash
cd services/ai
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/unimatch" \
  python export_training_data.py
```

会在 `services/ai/outputs/` 下生成：

- `sft.jsonl` — 匹配解释生成任务的 SFT 数据
- `dpo.jsonl` — 基于 like/dislike/skip 的偏好对比数据
- `training_metadata.json` — 导出统计信息

环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/unimatch` | 数据库连接串 |
| `OUTPUT_DIR` | `./outputs` | 输出目录 |

### 2. QLoRA 微调

```bash
cd services/ai
BASE_MODEL=Qwen/Qwen2.5-7B-Instruct \
DATA_PATH=./outputs/sft.jsonl \
OUTPUT_DIR=./outputs/qlora \
EPOCHS=3 \
LR=2e-4 \
LORA_R=64 \
LORA_ALPHA=16 \
MAX_SEQ_LENGTH=2048 \
python train_qlora.py
```

默认使用 `Qwen/Qwen2.5-0.5B-Instruct` 与 1 epoch，方便在没有大显存的环境做冒烟测试。要训练 7B 模型，请显式设置 `BASE_MODEL`。

常用环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BASE_MODEL` | `Qwen/Qwen2.5-0.5B-Instruct` | 基础模型 ID 或本地路径 |
| `DATA_PATH` | `./outputs/sft.jsonl` | SFT JSONL 数据路径 |
| `OUTPUT_DIR` | `./outputs/qlora` | 适配器输出目录 |
| `EPOCHS` | `1` | 训练轮数 |
| `LR` | `2e-4` | 学习率 |
| `BATCH_SIZE` | `1` | 单卡 batch size |
| `GRAD_ACCUM` | `4` | 梯度累积步数 |
| `LORA_R` | `16` | LoRA rank |
| `LORA_ALPHA` | `32` | LoRA alpha |
| `LORA_DROPOUT` | `0.05` | LoRA dropout |
| `MAX_SEQ_LENGTH` | `1024` | 最大序列长度 |

脚本会自动检测 `unsloth`：若已安装则走 FastLanguageModel 快速路径，否则回退到 `trl + peft + bitsandbytes`。

### 3. 合并 LoRA 并导出 GGUF

```bash
cd services/ai
BASE_MODEL=Qwen/Qwen2.5-7B-Instruct \
LORA_DIR=./outputs/qlora/final_adapter \
OUTPUT_DIR=./outputs/merged \
GGUF_OUTPUT_DIR=./outputs/gguf \
GGUF_QUANTIZATION=Q4_K_M \
python merge_lora.py
```

若本地有 [llama.cpp](https://github.com/ggerganov/llama.cpp) 仓库，可设置 `LLAMA_CPP_PATH=/path/to/llama.cpp` 自动调用 `convert_hf_to_gguf.py` 导出 GGUF。否则脚本会输出手动转换命令。

### 4. 接入 LMStudio

- **HuggingFace 格式**：在 LMStudio 中选择 ` outputs/merged` 文件夹作为模型路径，设置 `LMSTUDIO_MODEL` 为该文件夹名称。
- **GGUF 格式**：将 `outputs/gguf/unimatch-Q4_K_M.gguf` 拖入 LMStudio 模型目录，加载后即可在 UniMatch 后端通过 `AI_PROVIDER=lmstudio` 调用。

---

## 推荐模型离线重训练

`retrain_recommendation.py` 读取 `match_feedbacks` 表，训练一个轻量 Two-Tower / 矩阵分解模型，并导出后端可加载的 `recommendation_weights.json`。

```bash
cd services/ai
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/unimatch" \
OUTPUT_PATH=./outputs/recommendation_weights.json \
EMBEDDING_DIM=64 \
EPOCHS=200 \
LR=0.01 \
python retrain_recommendation.py
```

输出文件结构：

```json
{
  "version": "1.0",
  "model_type": "two_tower_mf",
  "dim": 64,
  "timestamp": "2026-07-15T12:00:00+00:00",
  "user_embeddings": { "<user_uuid>": [0.1, -0.2, ...] },
  "item_embeddings": { "<target_user_uuid>": [0.3, 0.1, ...] },
  "mlp_weights": { "W1": [...], "b1": [...], "W2": [...], "b2": [...] },
  "stats": { "num_users": 100, "num_items": 120, "num_interactions": 500 }
}
```

后端 `services/backend/unimatch/services/matching.py` 中的 `TwoTowerScorer` 可读取该 JSON 并计算用户与候选人的匹配分。

---

## 训练数据格式

### SFT JSONL（`sft.jsonl`）

采用 Qwen 对话格式，每条记录包含 `messages` 数组：

```json
{
  "messages": [
    {
      "role": "system",
      "content": "你是 UniMatch 校园匹配平台的 AI 匹配助手。"
    },
    {
      "role": "user",
      "content": "请为 UniMatch 用户 u0 在「academic」板块生成匹配解释。\n用户画像：...\n目标用户画像：..."
    },
    {
      "role": "assistant",
      "content": "你们同是计算机专业，学术路径相近；又在摄影与前沿技术话题上有共同语言..."
    }
  ]
}
```

### DPO JSONL（`dpo.jsonl`）

每条记录包含 `prompt`、`chosen`、`rejected`：

```json
{
  "prompt": "请为 UniMatch 用户 u0 在「daily」板块生成匹配解释。...",
  "chosen": "你们都喜欢户外徒步与摄影，年龄相近，容易找到共同话题。",
  "rejected": "在「daily」板块，当前用户与对方画像匹配度较低，不建议优先推荐（反馈动作：skip）。"
}
```

训练前请确保数据经过脱敏、合规审查，并符合《个人信息保护法》及学校相关规定。

---

## 参考

- [Qwen 模型仓库](https://huggingface.co/Qwen)
- [PEFT / LoRA 官方文档](https://huggingface.co/docs/peft)
- [QLoRA: Efficient Finetuning of Quantized LLMs](https://arxiv.org/abs/2305.14314)
- [InstructGPT / RLHF](https://arxiv.org/abs/2203.02155)
- [Direct Preference Optimization (DPO)](https://arxiv.org/abs/2305.18290)
- [SFT (Supervised Fine-Tuning) with TRL](https://huggingface.co/docs/trl/sft_trainer)
- [LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation](https://arxiv.org/abs/2002.02126)
- [Two-Tower Models for Recommendation (Google)](https://ai.googleblog.com/2019/05/introducing-research-on-recommendations.html)
- [LMStudio Local Server](https://lmstudio.ai/docs/local-server)
- [llama.cpp GGUF conversion](https://github.com/ggerganov/llama.cpp)

---

> 注意：训练产生的 LoRA 权重、中间 checkpoint、合并模型与推荐权重应通过 CI/CD 或私有对象存储分发，避免直接提交到 Git 仓库。`outputs/` 目录已被 `.gitignore` 忽略。
