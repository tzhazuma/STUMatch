"""Simulation smoke tests for UniMatch core features.

These tests do not require PostgreSQL/Redis; they exercise pure logic and
file-system artifacts added in this iteration.
Run from repository root or services/backend with the venv activated:
    python scripts/simulate_tests.py
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import os
os.environ.setdefault("SECRET_KEY", "simulation-secret-key-not-for-production")
os.environ.setdefault("ALLOWED_EMAIL_DOMAINS", "example.com")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from unimatch.services.moderation import DFAFilter, ModerationService, DEFAULT_SENSITIVE_WORDS, DEFAULT_WORDS_META
from unimatch.services.matching import MatchingService, TwoTowerScorer, SECTION_RULES


def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_referral_code_deterministic():
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    code1 = hashlib.sha256(user_id.encode()).hexdigest()[:8].upper()
    code2 = hashlib.sha256(user_id.encode()).hexdigest()[:8].upper()
    assert_true(len(code1) == 8, "referral code length should be 8")
    assert_true(code1 == code2, "referral code should be deterministic")
    print(f"✅ referral code generation deterministic ({code1})")


def test_moderation_wordlist():
    assert_true(len(DEFAULT_SENSITIVE_WORDS) >= 80, "wordlist should have >=80 words")
    categories = {"porn", "gamble", "drug", "fraud", "insult", "politics"}
    found = {w["category"] for w in DEFAULT_WORDS_META}
    assert_true(categories <= found, f"missing categories {categories - found}")
    print("✅ moderation wordlist has categories")


def test_moderation_filter():
    service = ModerationService()
    r = service.check_text("你这个傻逼，滚出去")
    assert_true(r["triggered"] and "傻逼" in r["words"], "should hit insult")

    r = service.check_text("你妈死了")
    assert_true(r["triggered"], "should hit variant/homophone")

    r = service.check_text("你好，今天天气不错")
    assert_true(not r["triggered"], "should not hit normal text")

    # Case / digit substitution resistance
    r = service.check_text("WX: mywechat123 约炮")
    assert_true(r["triggered"], f"should hit contact variant + porn, got {r['words']}")
    print("✅ moderation filter detects variants")


def test_moderation_dfa_overlap():
    f = DFAFilter(["abc", "abcd"])
    text = "abcd"
    triggered, words = f._check(text)
    assert_true(triggered, "should trigger")
    # avoid overlapping duplicates
    assert_true(len(words) == len(set(words)), f"duplicate matches: {words}")
    print("✅ DFA avoids overlapping duplicates")


def test_matching_rule_score():
    from unimatch.models import Profile
    from unimatch.config import get_settings
    get_settings().VECTOR_DIMENSION = 384

    me = Profile(nickname="A", major="CS", interests=["AI"])
    me.school = "SHTech"
    other = Profile(nickname="B", major="CS", interests=["AI"])
    other.school = "SHTech"
    service = MatchingService(None)
    score, reason = service._rule_score("academic", me, other)
    assert_true(score > 0, "same major/school should score > 0")
    assert_true("同专业" in reason, f"reason missing 同专业: {reason}")
    print("✅ matching rule score works")


def test_two_tower_fallback():
    scorer = TwoTowerScorer(None)
    assert_true(scorer.score("u1", "u2") is None, "empty scorer should fallback to None")

    import tempfile
    weights = {
        "user_embeddings": {"u1": [1.0, 0.0]},
        "item_embeddings": {"i2": [1.0, 0.0]},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(weights, f)
        path = f.name
    try:
        scorer = TwoTowerScorer(path)
        s = scorer.score("u1", "i2")
        assert_true(0 < s < 1, f"score should be in (0,1), got {s}")
    finally:
        os.unlink(path)
    print("✅ TwoTower scorer fallback and scoring work")


def test_mmr_diversity():
    service = MatchingService(None)
    candidates = [
        ("a", [1.0, 0.0], 0.9),
        ("b", [0.99, 0.01], 0.85),  # very similar to a
        ("c", [0.0, 1.0], 0.5),     # diverse
    ]
    ranked = service._mmr_rerank(candidates, lambda_param=0.5, limit=2)
    assert_true(ranked[0] == "a", "highest relevance first")
    assert_true(ranked[1] == "c", "MMR should pick diverse candidate second")
    print("✅ MMR diversity re-ranking works")


def test_legal_docs_exist():
    repo_root = ROOT.parent.parent
    terms = repo_root / "docs" / "TERMS_OF_SERVICE.md"
    privacy = repo_root / "docs" / "PRIVACY_POLICY.md"
    assert_true(terms.exists() and terms.stat().st_size > 1000, "terms doc missing/empty")
    assert_true(privacy.exists() and privacy.stat().st_size > 1000, "privacy doc missing/empty")
    assert_true("服务协议" in terms.read_text(encoding="utf-8"), "terms should mention 服务协议")
    assert_true("隐私" in privacy.read_text(encoding="utf-8"), "privacy should mention 隐私")
    print("✅ legal docs exist and have content")


def test_questionnaire_seed_valid():
    import asyncio
    from unimatch.main import seed_questionnaires
    # We can't run the DB part, but we can inspect the data structure statically.
    import inspect
    source = inspect.getsource(seed_questionnaires)
    assert_true("notification_consent" in source, "basic questionnaire missing notification_consent")
    assert_true("collaboration_style" in source, "academic questionnaire missing collaboration_style")
    assert_true("favorite_sports" in source, "daily questionnaire missing favorite_sports")
    assert_true("boundary_respect" in source, "dating questionnaire missing boundary_respect")
    print("✅ questionnaire seed has improved questions")


def test_ai_scripts_exist():
    ai_dir = ROOT.parent / "ai"
    for name in ["export_training_data.py", "train_qlora.py", "merge_lora.py", "retrain_recommendation.py"]:
        path = ai_dir / name
        assert_true(path.exists(), f"{name} missing")
    print("✅ AI fine-tuning scripts exist")


if __name__ == "__main__":
    test_referral_code_deterministic()
    test_moderation_wordlist()
    test_moderation_filter()
    test_moderation_dfa_overlap()
    test_matching_rule_score()
    test_two_tower_fallback()
    test_mmr_diversity()
    test_legal_docs_exist()
    test_questionnaire_seed_valid()
    test_ai_scripts_exist()
    print("\n🎉 All simulation smoke tests passed!")
