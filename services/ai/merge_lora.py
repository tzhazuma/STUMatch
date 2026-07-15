#!/usr/bin/env python3
"""Merge a UniMatch LoRA adapter into its base model and optionally export GGUF.

Environment variables
---------------------
BASE_MODEL          Base model id or path (default: Qwen/Qwen2.5-0.5B-Instruct)
LORA_DIR            Directory containing the LoRA adapter (default: ./outputs/qlora/final_adapter)
OUTPUT_DIR          Directory for the merged HuggingFace model (default: ./outputs/merged)
GGUF_OUTPUT_DIR     Directory for the exported GGUF file (default: ./outputs/gguf)
GGUF_QUANTIZATION   GGUF quantization type, e.g. Q4_K_M (default: Q4_K_M)
LLAMA_CPP_PATH      Path to a local llama.cpp checkout (default: search PATH/common paths)
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("merge_lora")

BASE_MODEL = os.getenv("BASE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
LORA_DIR = Path(os.getenv("LORA_DIR", "./outputs/qlora/final_adapter"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs/merged"))
GGUF_OUTPUT_DIR = Path(os.getenv("GGUF_OUTPUT_DIR", "./outputs/gguf"))
GGUF_QUANTIZATION = os.getenv("GGUF_QUANTIZATION", "Q4_K_M")
LLAMA_CPP_PATH = os.getenv("LLAMA_CPP_PATH", "")

REQUIRED_PACKAGES = ["torch", "transformers", "peft"]


def _check_dependencies() -> None:
    missing: list[str] = []
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    if missing:
        logger.error(
            "Missing Python packages: %s.\nInstall with: pip install torch transformers peft",
            ", ".join(missing),
        )
        sys.exit(1)


def _find_convert_script() -> Path | None:
    """Locate llama.cpp convert_hf_to_gguf.py if available."""
    if LLAMA_CPP_PATH:
        candidates = [Path(LLAMA_CPP_PATH) / "convert_hf_to_gguf.py"]
    else:
        candidates = [
            Path("llama.cpp") / "convert_hf_to_gguf.py",
            Path("../llama.cpp") / "convert_hf_to_gguf.py",
            Path.home() / "llama.cpp" / "convert_hf_to_gguf.py",
            Path("/opt/llama.cpp/convert_hf_to_gguf.py"),
        ]
        # Also search next to any llama.cpp binary on PATH.
        for binary in ("llama-cli", "llama-server"):
            bin_path = shutil.which(binary)
            if bin_path:
                candidates.append(Path(bin_path).parent.parent / "convert_hf_to_gguf.py")
                candidates.append(Path(bin_path).parent / "convert_hf_to_gguf.py")

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    _check_dependencies()

    if not LORA_DIR.exists():
        logger.error("LoRA adapter directory not found: %s", LORA_DIR)
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    import torch
    from peft import AutoPeftModelForCausalLM
    from transformers import AutoTokenizer

    logger.info("Loading base model %s with adapter %s", BASE_MODEL, LORA_DIR)
    model = AutoPeftModelForCausalLM.from_pretrained(
        str(LORA_DIR),
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )

    logger.info("Merging and unloading LoRA weights...")
    merged = model.merge_and_unload()

    logger.info("Saving merged model to %s", OUTPUT_DIR)
    merged.save_pretrained(OUTPUT_DIR)

    logger.info("Saving tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(str(LORA_DIR), trust_remote_code=True)
    tokenizer.save_pretrained(OUTPUT_DIR)

    logger.info("Merged model saved to %s", OUTPUT_DIR)

    GGUF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_script = _find_convert_script()
    gguf_path = GGUF_OUTPUT_DIR / f"unimatch-{GGUF_QUANTIZATION}.gguf"
    if convert_script:
        cmd = [
            sys.executable,
            str(convert_script),
            str(OUTPUT_DIR),
            "--outfile",
            str(gguf_path),
            "--outtype",
            GGUF_QUANTIZATION,
        ]
        logger.info("Running GGUF export: %s", " ".join(cmd))
        result = subprocess.run(cmd)
        if result.returncode != 0:
            logger.warning("GGUF export failed; see output above. Manual command:\n  %s", " ".join(cmd))
        else:
            logger.info("GGUF exported to %s", gguf_path)
    else:
        logger.info(
            "llama.cpp convert_hf_to_gguf.py not found. "
            "Set LLAMA_CPP_PATH to enable automatic GGUF export.\n"
            "Manual example:\n"
            "  python llama.cpp/convert_hf_to_gguf.py %s --outfile %s --outtype %s",
            OUTPUT_DIR,
            gguf_path,
            GGUF_QUANTIZATION,
        )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        logger.info("Interrupted")
        raise SystemExit(130)
