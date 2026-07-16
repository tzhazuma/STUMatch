#!/usr/bin/env python3
"""Retrain a lightweight Two-Tower / matrix-factorization recommendation model.

Reads ``match_feedbacks`` from PostgreSQL and exports user/item embeddings to a
JSON file that the backend ``TwoTowerScorer`` can load.

The torch trainer follows ideas from:

* Rendle et al., "BPR: Bayesian Personalized Ranking from Implicit Feedback",
  UAI 2009 -- pairwise ranking objective.
* He et al., "Neural Collaborative Filtering", WWW 2017 -- neural interaction
  function (MLP) on top of user/item embeddings.

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
USE_BPR                 Add BPR pairwise term to torch loss (default: 1)
VAL_RATIO               Fraction of latest interactions used for validation (default: 0.2)
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
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
USE_BPR = os.getenv("USE_BPR", "1").lower() in ("1", "true", "yes")
VAL_RATIO = float(os.getenv("VAL_RATIO", "0.2"))

ACTION_SCORES = {"like": 1.0, "skip": 0.0, "dislike": -1.0}


def _normalize_action(action: str) -> float:
    return ACTION_SCORES.get(action, 0.0)


async def _fetch_async(db_url: str) -> list[dict[str, Any]]:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(db_url, future=True)
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT user_id, target_user_id, action, created_at "
                "FROM match_feedbacks ORDER BY created_at"
            )
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


def _build_mappings(rows: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, int]]:
    """Map UUIDs to dense indices using all rows (train + validation)."""
    user_map: dict[str, int] = {}
    item_map: dict[str, int] = {}
    for row in rows:
        uid = str(row["user_id"])
        iid = str(row["target_user_id"])
        if uid not in user_map:
            user_map[uid] = len(user_map)
        if iid not in item_map:
            item_map[iid] = len(item_map)
    return user_map, item_map


def _rows_to_pairs(
    rows: list[dict[str, Any]], user_map: dict[str, int], item_map: dict[str, int]
) -> list[tuple[int, int, float]]:
    """Convert feedback rows to (user_idx, item_idx, score) triples."""
    pairs: list[tuple[int, int, float]] = []
    for row in rows:
        action = str(row.get("action", "skip"))
        score = _normalize_action(action)
        pairs.append((user_map[str(row["user_id"])], item_map[str(row["target_user_id"])], score))
    return pairs


def _time_split(
    rows: list[dict[str, Any]], val_ratio: float
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Hold out the latest ``val_ratio`` interactions as a validation set.

    Time-based splitting is closer to production conditions than random splits
    because it tests whether the model generalises to future interactions.
    """
    n_val = max(1, int(len(rows) * val_ratio))
    return rows[:-n_val], rows[-n_val:]


def _ranking_metrics(
    pairs: list[tuple[int, int, float]],
    user_emb: Any,
    item_emb: Any,
    mlp: Any | None,
    k: int = 10,
) -> tuple[float, float]:
    """Compute HitRatio@K and NDCG@K on validation pairs.

    Only positive interactions (score > 0) are treated as ground-truth items.
    """
    import numpy as np

    if not pairs:
        return 0.0, 0.0

    user_to_items: dict[int, set[int]] = {}
    for u_idx, i_idx, score in pairs:
        if score <= 0:
            continue
        user_to_items.setdefault(u_idx, set()).add(i_idx)

    if not user_to_items:
        return 0.0, 0.0

    n_items = item_emb.shape[0]
    hits = 0.0
    ndcg_sum = 0.0

    all_item_indices = np.arange(n_items)
    for u_idx, positives in user_to_items.items():
        u_vec = user_emb[u_idx]
        # Score every item for this user.
        if mlp is not None:
            import torch

            with torch.no_grad():
                u_t = torch.tensor([u_idx] * n_items, dtype=torch.long)
                i_t = torch.tensor(all_item_indices, dtype=torch.long)
                scores = mlp(torch.cat([user_emb[u_t], item_emb[i_t]], dim=1)).squeeze().cpu().numpy()
        else:
            scores = item_emb @ u_vec

        top_k_idx = np.argpartition(scores, -k)[-k:]
        top_k_idx = top_k_idx[np.argsort(-scores[top_k_idx])]
        top_k_set = set(int(i) for i in top_k_idx)

        if positives & top_k_set:
            hits += 1.0

        # DCG@K
        dcg = 0.0
        for rank, item_idx in enumerate(top_k_idx, start=1):
            if int(item_idx) in positives:
                dcg += 1.0 / math.log2(rank + 1)
        # IDCG@K -- all positives ranked at the top
        ideal_len = min(len(positives), k)
        idcg = sum(1.0 / math.log2(rank + 2) for rank in range(ideal_len))
        if idcg > 0:
            ndcg_sum += dcg / idcg

    n_users = len(user_to_items)
    return hits / n_users, ndcg_sum / n_users


def _train_torch(
    train_pairs: list[tuple[int, int, float]],
    val_pairs: list[tuple[int, int, float]],
    n_users: int,
    n_items: int,
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
    # Inspired by He et al., "Neural Collaborative Filtering", WWW 2017.
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

    users = torch.tensor([p[0] for p in train_pairs], dtype=torch.long)
    items = torch.tensor([p[1] for p in train_pairs], dtype=torch.long)
    scores = torch.tensor([p[2] for p in train_pairs], dtype=torch.float32).unsqueeze(1)

    # Pre-compute observed user-item interactions for BPR negative sampling.
    observed: dict[int, set[int]] = {}
    for u_idx, i_idx, _ in train_pairs:
        observed.setdefault(u_idx, set()).add(i_idx)
    positive_indices = [i for i, (_, _, s) in enumerate(train_pairs) if s > 0]

    rng = np.random.default_rng(RANDOM_SEED)

    for epoch in range(EPOCHS):
        u = user_emb(users)
        i = item_emb(items)
        pred = mlp(torch.cat([u, i], dim=1))
        loss = nn.MSELoss()(pred, scores)

        if USE_BPR and positive_indices:
            # BPR pairwise objective: for each positive interaction sample one
            # random negative item and maximise pred_pos - pred_neg.
            # See Rendle et al., "BPR: Bayesian Personalized Ranking from
            # Implicit Feedback", UAI 2009.
            neg_items: list[int] = []
            pos_items: list[int] = []
            pos_users: list[int] = []
            for idx in positive_indices:
                u_idx, i_idx, _ = train_pairs[idx]
                seen = observed[u_idx]
                # Fast rejection sampling; datasets are small enough.
                for _ in range(20):
                    neg = rng.integers(0, n_items)
                    if neg not in seen:
                        break
                neg_items.append(int(neg))
                pos_items.append(i_idx)
                pos_users.append(u_idx)

            pos_u = user_emb(torch.tensor(pos_users, dtype=torch.long))
            pos_i = item_emb(torch.tensor(pos_items, dtype=torch.long))
            neg_i = item_emb(torch.tensor(neg_items, dtype=torch.long))
            pos_pred = mlp(torch.cat([pos_u, pos_i], dim=1))
            neg_pred = mlp(torch.cat([pos_u, neg_i], dim=1))
            bpr_loss = -torch.log(torch.sigmoid(pos_pred - neg_pred) + 1e-8).mean()
            loss = loss + bpr_loss

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if epoch % 20 == 0 or epoch == EPOCHS - 1:
            user_weights = user_emb.weight.detach().cpu().numpy()
            item_weights = item_emb.weight.detach().cpu().numpy()
            val_mse = _validation_mse(val_pairs, user_weights, item_weights, mlp)
            hr, ndcg = _ranking_metrics(val_pairs, user_emb.weight, item_emb.weight, mlp, k=10)
            logger.info(
                "Epoch %d/%d - train MSE: %.6f, val MSE: %.6f, HitRatio@10: %.4f, NDCG@10: %.4f",
                epoch + 1,
                EPOCHS,
                float(nn.MSELoss()(pred, scores).item()),
                val_mse,
                hr,
                ndcg,
            )

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


def _validation_mse(
    val_pairs: list[tuple[int, int, float]],
    user_emb: Any,
    item_emb: Any,
    mlp: Any | None,
) -> float:
    import numpy as np
    import torch

    if not val_pairs:
        return 0.0

    users = torch.tensor([p[0] for p in val_pairs], dtype=torch.long)
    items = torch.tensor([p[1] for p in val_pairs], dtype=torch.long)
    targets = torch.tensor([p[2] for p in val_pairs], dtype=torch.float32).unsqueeze(1)

    u = torch.tensor(user_emb[users], dtype=torch.float32)
    i = torch.tensor(item_emb[items], dtype=torch.float32)
    if mlp is not None:
        with torch.no_grad():
            pred = mlp(torch.cat([u, i], dim=1))
    else:
        pred = (u * i).sum(dim=1, keepdim=True)
    return float(torch.nn.functional.mse_loss(pred, targets).item())


def _train_numpy(
    train_pairs: list[tuple[int, int, float]],
    val_pairs: list[tuple[int, int, float]],
    n_users: int,
    n_items: int,
) -> tuple[Any, Any, None]:
    import numpy as np

    rng = np.random.default_rng(RANDOM_SEED)
    user_emb = rng.normal(0.0, 0.01, (n_users, EMBEDDING_DIM)).astype(np.float32)
    item_emb = rng.normal(0.0, 0.01, (n_items, EMBEDDING_DIM)).astype(np.float32)

    observed: dict[int, set[int]] = {}
    for u_idx, i_idx, _ in train_pairs:
        observed.setdefault(u_idx, set()).add(i_idx)
    positive_indices = [i for i, (_, _, s) in enumerate(train_pairs) if s > 0]

    for epoch in range(EPOCHS):
        total_loss = 0.0
        for u_idx, i_idx, score in train_pairs:
            pred = float(np.dot(user_emb[u_idx], item_emb[i_idx]))
            err = score - pred
            total_loss += err * err
            user_grad = LR * (err * item_emb[i_idx] - REG * user_emb[u_idx])
            item_grad = LR * (err * user_emb[u_idx] - REG * item_emb[i_idx])
            user_emb[u_idx] += user_grad
            item_emb[i_idx] += item_grad

        if USE_BPR and positive_indices:
            # Simple numpy BPR update.
            for idx in positive_indices:
                u_idx, i_idx, _ = train_pairs[idx]
                seen = observed[u_idx]
                for _ in range(20):
                    neg = rng.integers(0, n_items)
                    if neg not in seen:
                        break
                pos_pred = float(np.dot(user_emb[u_idx], item_emb[i_idx]))
                neg_pred = float(np.dot(user_emb[u_idx], item_emb[neg]))
                diff = pos_pred - neg_pred
                sig = 1.0 / (1.0 + math.exp(diff))
                user_emb[u_idx] += LR * (sig * (item_emb[i_idx] - item_emb[neg]) - REG * user_emb[u_idx])
                item_emb[i_idx] += LR * (sig * user_emb[u_idx] - REG * item_emb[i_idx])
                item_emb[neg] -= LR * (sig * user_emb[u_idx] - REG * item_emb[neg])

        if epoch % 20 == 0 or epoch == EPOCHS - 1:
            val_mse = _validation_mse_numpy(val_pairs, user_emb, item_emb)
            logger.info(
                "Epoch %d/%d - train MSE: %.6f, val MSE: %.6f",
                epoch + 1,
                EPOCHS,
                total_loss / max(len(train_pairs), 1),
                val_mse,
            )
    return user_emb, item_emb, None


def _validation_mse_numpy(
    val_pairs: list[tuple[int, int, float]],
    user_emb: Any,
    item_emb: Any,
) -> float:
    import numpy as np

    if not val_pairs:
        return 0.0
    total = 0.0
    for u_idx, i_idx, score in val_pairs:
        pred = float(np.dot(user_emb[u_idx], item_emb[i_idx]))
        total += (score - pred) ** 2
    return total / len(val_pairs)


def train(
    train_pairs: list[tuple[int, int, float]],
    val_pairs: list[tuple[int, int, float]],
    n_users: int,
    n_items: int,
) -> tuple[Any, Any, dict[str, Any] | None]:
    if USE_TORCH:
        try:
            return _train_torch(train_pairs, val_pairs, n_users, n_items)
        except Exception as exc:
            logger.warning("PyTorch training failed (%s), falling back to numpy ALS", exc)
    return _train_numpy(train_pairs, val_pairs, n_users, n_items)


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

    train_rows, val_rows = _time_split(rows, VAL_RATIO)
    logger.info("Train rows: %d, validation rows: %d", len(train_rows), len(val_rows))

    user_map, item_map = _build_mappings(train_rows + val_rows)
    logger.info(
        "Mapped feedback to %d users and %d items", len(user_map), len(item_map)
    )

    train_pairs = _rows_to_pairs(train_rows, user_map, item_map)
    val_pairs = _rows_to_pairs(val_rows, user_map, item_map)

    user_emb, item_emb, mlp_weights = train(
        train_pairs, val_pairs, len(user_map), len(item_map)
    )
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
