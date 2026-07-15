#!/usr/bin/env python3
"""QLoRA fine-tuning script for UniMatch (Qwen2.5-Instruct).

Defaults are intentionally small (Qwen2.5-0.5B-Instruct, 1 epoch) so the script
runs quickly for smoke tests. To fine-tune the full 7B model, set
``BASE_MODEL=Qwen/Qwen2.5-7B-Instruct`` and tune the other hyperparameters.

Environment variables
---------------------
BASE_MODEL              Base model id or local path (default: Qwen/Qwen2.5-0.5B-Instruct)
OUTPUT_DIR              Adapter output directory (default: ./outputs/qlora)
DATA_PATH               SFT JSONL file (default: ./outputs/sft.jsonl)
EPOCHS                  Number of epochs (default: 1)
LR                      Learning rate (default: 2e-4)
BATCH_SIZE              Per-device train batch size (default: 1)
GRAD_ACCUM              Gradient accumulation steps (default: 4)
LORA_R                  LoRA rank (default: 16)
LORA_ALPHA              LoRA alpha (default: 32)
LORA_DROPOUT            LoRA dropout (default: 0.05)
MAX_SEQ_LENGTH          Max sequence length (default: 1024)
WARMUP_RATIO            Warmup ratio (default: 0.03)
SAVE_STEPS              Save checkpoint every N steps (default: 50)
LOGGING_STEPS           Log every N steps (default: 10)
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("train_qlora")

BASE_MODEL = os.getenv("BASE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs/qlora"))
DATA_PATH = Path(os.getenv("DATA_PATH", "./outputs/sft.jsonl"))
EPOCHS = int(os.getenv("EPOCHS", "1"))
LR = float(os.getenv("LR", "2e-4"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1"))
GRAD_ACCUM = int(os.getenv("GRAD_ACCUM", "4"))
LORA_R = int(os.getenv("LORA_R", "16"))
LORA_ALPHA = int(os.getenv("LORA_ALPHA", "32"))
LORA_DROPOUT = float(os.getenv("LORA_DROPOUT", "0.05"))
MAX_SEQ_LENGTH = int(os.getenv("MAX_SEQ_LENGTH", "1024"))
WARMUP_RATIO = float(os.getenv("WARMUP_RATIO", "0.03"))
SAVE_STEPS = int(os.getenv("SAVE_STEPS", "50"))
LOGGING_STEPS = int(os.getenv("LOGGING_STEPS", "10"))

REQUIRED_PACKAGES = ["torch", "transformers", "datasets", "peft", "trl", "bitsandbytes"]


def _check_dependencies() -> None:
    missing: list[str] = []
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    if missing:
        logger.error(
            "Missing Python packages: %s.\n"
            "Install with: pip install torch transformers datasets accelerate peft bitsandbytes trl",
            ", ".join(missing),
        )
        sys.exit(1)


def _ensure_data() -> Path:
    """Return a usable DATA_PATH, creating a tiny dummy dataset if needed."""
    if DATA_PATH.exists():
        return DATA_PATH
    logger.warning("%s not found; creating a tiny dummy dataset for smoke testing.", DATA_PATH)
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    dummy = [
        {
            "messages": [
                {
                    "role": "system",
                    "content": "你是 UniMatch 的匹配助手，帮助用户生成自然、有趣的匹配解释。",
                },
                {
                    "role": "user",
                    "content": "用户 A：INTJ，计算机科学与技术，爱好摄影与篮球；用户 B：INTP，计算机科学与技术，爱好摄影与机器学习。请生成 2 句匹配解释。",
                },
                {
                    "role": "assistant",
                    "content": "你们同是计算机专业，学术路径相近；又在摄影与前沿技术话题上有共同语言，很容易找到深入交流的话题。",
                },
            ]
        }
    ]
    with DATA_PATH.open("w", encoding="utf-8") as f:
        for example in dummy:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
    return DATA_PATH


def _formatting_func(examples: dict[str, Any], tokenizer: Any) -> dict[str, Any]:
    texts = []
    for messages in examples["messages"]:
        texts.append(
            tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
        )
    return {"text": texts}


def _train_with_unsloth(tokenizer: Any, dataset: Any) -> Any:
    from unsloth import FastLanguageModel, is_bfloat16_supported
    from transformers import TrainingArguments
    from trl import SFTTrainer

    logger.info("Using unsloth fast path.")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=None,
        load_in_4bit=True,
        trust_remote_code=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    formatted = dataset.map(
        lambda examples: _formatting_func(examples, tokenizer),
        batched=True,
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=formatted,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        args=TrainingArguments(
            output_dir=str(OUTPUT_DIR),
            num_train_epochs=EPOCHS,
            per_device_train_batch_size=BATCH_SIZE,
            gradient_accumulation_steps=GRAD_ACCUM,
            learning_rate=LR,
            warmup_ratio=WARMUP_RATIO,
            logging_steps=LOGGING_STEPS,
            save_steps=SAVE_STEPS,
            save_total_limit=2,
            bf16=is_bfloat16_supported(),
            fp16=not is_bfloat16_supported(),
            optim="paged_adamw_8bit",
            group_by_length=True,
            report_to="none",
        ),
    )
    return trainer, model, tokenizer


def _train_with_trl(tokenizer: Any, dataset: Any) -> Any:
    import torch
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig, TrainingArguments
    from trl import SFTTrainer

    logger.info("Using trl+peft fallback path.")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    )
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    peft_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    model = get_peft_model(model, peft_config)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        formatting_func=lambda example: tokenizer.apply_chat_template(
            example["messages"], tokenize=False, add_generation_prompt=False
        ),
        max_seq_length=MAX_SEQ_LENGTH,
        args=TrainingArguments(
            output_dir=str(OUTPUT_DIR),
            num_train_epochs=EPOCHS,
            per_device_train_batch_size=BATCH_SIZE,
            gradient_accumulation_steps=GRAD_ACCUM,
            learning_rate=LR,
            warmup_ratio=WARMUP_RATIO,
            logging_steps=LOGGING_STEPS,
            save_steps=SAVE_STEPS,
            save_total_limit=2,
            bf16=torch.cuda.is_bf16_supported(),
            fp16=not torch.cuda.is_bf16_supported(),
            optim="paged_adamw_8bit",
            group_by_length=True,
            report_to="none",
        ),
    )
    return trainer, model, tokenizer


def main() -> int:
    _check_dependencies()
    data_path = _ensure_data()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    from datasets import load_dataset

    dataset = load_dataset("json", data_files=str(data_path), split="train")
    logger.info("Loaded %d training examples from %s", len(dataset), data_path)

    # Decide unsloth vs trl before loading tokenizer so we can reuse the tokenizer.
    use_unsloth = False
    try:
        from unsloth import FastLanguageModel

        use_unsloth = True
        del FastLanguageModel
    except Exception:
        use_unsloth = False

    if use_unsloth:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
        trainer, model, tokenizer = _train_with_unsloth(tokenizer, dataset)
    else:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
        trainer, model, tokenizer = _train_with_trl(tokenizer, dataset)

    logger.info("Starting QLoRA training...")
    trainer.train()

    adapter_dir = OUTPUT_DIR / "final_adapter"
    trainer.save_model(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)
    logger.info("Adapter saved to %s", adapter_dir)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        logger.info("Interrupted")
        raise SystemExit(130)
