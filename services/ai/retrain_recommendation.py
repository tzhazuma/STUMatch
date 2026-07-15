#!/usr/bin/env python3
"""Retrain a lightweight Two-Tower / matrix-factorization recommendation model.

Reads ``match_feedbacks`` from PostgreSQL and exports user/item embeddings to a
JSON file that the backend ``TwoTowerScorer`` can load.

Environment variables
---------------------
DATABASE_URL            PostgreSQL URL (default: postgresql+asyncpg://postgres:postgres@localhost:5432/unimatch)
OUTPUT_PATH             Output JSON path (default: ./outputs/recommendation_weights.json)
EMBEDDING_DIM           Embedding dimension (default: 64)
EPOCHS                  Training epochs (default: 200)
LR                      Learning rate (default: 0.01)
REG                     L2 regularization (default: 0.001)
RANDOM_SEED             Random seed (default: 42)
USE_TORCH               Prefer torch implementation if available (default: 1)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("retrain_recommendation")

DEFAULT_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/unimatch"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
OUTPUT_PATH = Path(os.getenv("OUTPUT_PATH", "./outputs/recommendation_weights.json"))
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "64"))
EPOCHS = int(os.getenv("EPOCHS", "200"))
LR = float(os.getenv("LR", "0.01"))
REG = float(os.getenv("REG", "0.001"))
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))
USE_TORCH = os.getenv("USE_TORCH", "1").lower() in ("1", "true", "yes")

ACTION_SCORES = {"like": 1.0, "skip": 0.0, "dislike": -1.0}


def _normalize_action(action: str) -> float:
    return ACTION_SCORES.get(action, 0.0)


async def _fetch_async(db_url: str) -> list[dict[str, Any]]:
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(db_url, future=True)
    async with engine.connect() as conn:
        result = await conn.execute(
            "SELECT user_id, target_user_id, action, created_at "
            "FROM match_feedbacks ORDER BY created_at"
        )
        rows = [dict(row) for row in result.mappings()]
    await engine.dispose()
    return rows


def _fetch_sync(db_url: str) -> list[dict[str, Any]]:
    """Fallback synchronous fetch using psycopg2/psycopg."""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
    except Exception as exc:
        try:
            import psycopg

            conn = psycopg.connect(db_url)
            cur = conn.cursor(row_factory=psycopg.rows.dict_row)
        except Exception as exc2:
            raise RuntimeError(
                "Could not connect synchronously (tried psycopg2 and psycopg). "
                f"Errors: {exc}; {exc2}"
            ) from exc2

    try:
        cur.execute(
            "SELECT user_id, target_user_id, action, created_at "
            "FROM match_feedbacks ORDER BY created_at"
        )
        rows = [dict(row) for row in cur.fetchall()]
        return rows
    finally:
        cur.close()
        conn.close()


async def fetch_feedbacks() -> list[dict[str, Any]]:
    if "+asyncpg" in DATABASE_URL:
        try:
            return await _fetch_async(DATABASE_URL)
        except Exception as exc:
            logger.warning("Async fetch failed (%s), trying sync fallback", exc)
            sync_url = DATABASE_URL.replace("+asyncpg", "")
            return _fetch_sync(sync_url)
    return _fetch_sync(DATABASE_URL)


def _build_mappings(rows: list[dict[str, Any]]) -> tuple[list[tuple[int, int, float]], dict[str, int], dict[str, int]]:
    """Map UUIDs to dense indices and return (user_idx, item_idx, score) triples."""
    user_map: dict[str, int] = {}
    item_map: dict[str, int] = {}
    pairs: list[tuple[int, int, float]] = []
    for row in rows:
        action = str(row.get("action", "skip"))
        score = _normalize_action(action)
        uid = str(row["user_id"])
        iid = str(row["target_user_id"])
        if uid not in user_map:
            user_map[uid] = len(user_map)
        if iid not in item_map:
            item_map[iid] = len(item_map)
        pairs.append((user_map[uid], item_map[iid], score))
    return pairs, user_map, item_map


def _train_torch(
    pairs: list[tuple[int, int, float]], n_users: int, n_items: int
) -> tuple[Any, Any, dict[str, Any] | None]:
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.optim as optim

    torch.manual_seed(RANDOM_SEED)
    user_emb = nn.Embedding(n_users, EMBEDDING_DIM)
    item_emb = nn.Embedding(n_items, EMBEDDING_DIM)
    nn.init.xavier_uniform_(user_emb.weight)
    nn.init.xavier_uniform_(item_emb.weight)

    # Simple Two-Tower interaction MLP.
    mlp = nn.Sequential(
        nn.Linear(EMBEDDING_DIM * 2, EMBEDDING_DIM),
        nn.ReLU(),
        nn.Linear(EMBEDDING_DIM, 1),
    )

    optimizer = optim.Adam(
        list(user_emb.parameters()) + list(item_emb.parameters()) + list(mlp.parameters()),
        lr=LR,
        weight_decay=REG,
    )

    users = torch.tensor([p[0] for p in pairs], dtype=torch.long)
    items = torch.tensor([p[1] for p in pairs], dtype=torch.long)
    scores = torch.tensor([p[2] for p in pairs], dtype=torch.float32).unsqueeze(1)

    for epoch in range(EPOCHS):
        u = user_emb(users)
        i = item_emb(items)
        pred = mlp(torch.cat([u, i], dim=1))
        loss = nn.MSELoss()(pred, scores)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        if epoch % 20 == 0 or epoch == EPOCHS - 1:
            logger.info("Epoch %d/%d - MSE loss: %.6f", epoch + 1, EPOCHS, loss.item())

    user_weights = user_emb.weight.detach().cpu().numpy()
    item_weights = item_emb.weight.detach().cpu().numpy()

    mlp_state = mlp.state_dict()
    mlp_weights: dict[str, Any] = {
        "W1": mlp_state["0.weight"].cpu().numpy().tolist(),
        "b1": mlp_state["0.bias"].cpu().numpy().tolist(),
        "W2": mlp_state["2.weight"].cpu().numpy().tolist(),
        "b2": mlp_state["2.bias"].cpu().numpy().tolist(),
    }
    return user_weights, item_weights, mlp_weights


def _train_numpy(
    pairs: list[tuple[int, int, float]], n_users: int, n_items: int
) -> tuple[Any, Any, None]:
    import numpy as np

    rng = np.random.default_rng(RANDOM_SEED)
    user_emb = rng.normal(0.0, 0.01, (n_users, EMBEDDING_DIM)).astype(np.float32)
    item_emb = rng.normal(0.0, 0.01, (n_items, EMBEDDING_DIM)).astype(np.float32)

    for epoch in range(EPOCHS):
        total_loss = 0.0
        for u_idx, i_idx, score in pairs:
            pred = float(np.dot(user_emb[u_idx], item_emb[i_idx]))
            err = score - pred
            total_loss += err * err
            user_grad = LR * (err * item_emb[i_idx] - REG * user_emb[u_idx])
            item_grad = LR * (err * user_emb[u_idx] - REG * item_emb[i_idx])
            user_emb[u_idx] += user_grad
            item_emb[i_idx] += item_grad
        if epoch % 20 == 0 or epoch == EPOCHS - 1:
            logger.info(
                "Epoch %d/%d - MSE loss: %.6f",
                epoch + 1,
                EPOCHS,
                total_loss / max(len(pairs), 1),
            )
    return user_emb, item_emb, None


def train(
    pairs: list[tuple[int, int, float]], n_users: int, n_items: int
) -> tuple[Any, Any, dict[str, Any] | None]:
    if USE_TORCH:
        try:
            return _train_torch(pairs, n_users, n_items)
        except Exception as exc:
            logger.warning("PyTorch training failed (%s), falling back to numpy ALS", exc)
    return _train_numpy(pairs, n_users, n_items)


def export_weights(
    user_emb: Any,
    item_emb: Any,
    mlp_weights: dict[str, Any] | None,
    user_map: dict[str, int],
    item_map: dict[str, int],
    n_interactions: int,
) -> None:
    user_map_inv = {v: k for k, v in user_map.items()}
    item_map_inv = {v: k for k, v in item_map.items()}

    payload: dict[str, Any] = {
        "version": "1.0",
        "model_type": "two_tower_mf",
        "dim": EMBEDDING_DIM,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_embeddings": {
            user_map_inv[i]: user_emb[i].tolist() for i in range(len(user_map))
        },
        "item_embeddings": {
            item_map_inv[i]: item_emb[i].tolist() for i in range(len(item_map))
        },
        "mlp_weights": mlp_weights,
        "stats": {
            "num_users": len(user_map),
            "num_items": len(item_map),
            "num_interactions": n_interactions,
        },
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info(
        "Saved recommendation weights: %d users, %d items, %d interactions -> %s",
        len(user_map),
        len(item_map),
        n_interactions,
        OUTPUT_PATH,
    )


async def main() -> int:
    logger.info("Fetching match feedback...")
    rows = await fetch_feedbacks()
    logger.info("Loaded %d feedback rows", len(rows))

    if not rows:
        logger.warning("No feedback data; writing empty weights file.")
        export_weights(
            [], [], None, {}, {}, 0
        )
        return 0

    pairs, user_map, item_map = _build_mappings(rows)
    logger.info(
        "Mapped feedback to %d users and %d items", len(user_map), len(item_map)
    )

    user_emb, item_emb, mlp_weights = train(pairs, len(user_map), len(item_map))
    export_weights(
        user_emb,
        item_emb,
        mlp_weights,
        user_map,
        item_map,
        len(rows),
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        logger.info("Interrupted")
        raise SystemExit(130)
