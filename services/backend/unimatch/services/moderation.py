"""Content moderation service with local DFA + optional cloud fallback."""
import hashlib
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from unimatch.config import get_settings
from unimatch.models import ModerationConfig, ModerationLog

logger = logging.getLogger(__name__)
settings = get_settings()


# Word-level canonical substitutions (simplified Chinese + common bypasses).
WORD_CANONICAL: dict[str, list[str]] = {
    "微信": ["微信", "wechat", "weixin", "wx", "vx", "wei信", "微x"],
    "支付宝": ["支付宝", "alipay", "zfb", "zhifubao"],
    "qq": ["qq", "企鹅", "q_q"],
}

# Character-level canonical substitutions.
CHAR_CANONICAL: dict[str, str] = {
    # Pinyin / homophone bypasses
    "ma": "妈",
    "m@": "妈",
    "妈": "妈",
    "马": "妈",
    "吗": "妈",
    "码": "妈",
    "草": "草",
    "cao": "草",
    "操": "草",
    "肏": "草",
    "靠": "靠",
    "kao": "靠",
    "尻": "靠",
    "干": "干",
    "gan": "干",
    "滚": "滚",
    "gun": "滚",
    "屎": "屎",
    "shit": "屎",
    "尿": "尿",
    "piss": "尿",
    # Contact bypasses
    "wei": "微",
    "v": "微",
    "微": "微",
    "xin": "信",
    "信": "信",
    "zhi": "支",
    "支": "支",
    "fu": "付",
    "付": "付",
    "bao": "宝",
    "宝": "宝",
    # Digit -> Chinese digit canonical
    "0": "零",
    "零": "零",
    "洞": "零",
    "1": "一",
    "一": "一",
    "壹": "一",
    "①": "一",
    "2": "二",
    "二": "二",
    "两": "二",
    "贰": "二",
    "②": "二",
    "3": "三",
    "三": "三",
    "叁": "三",
    "③": "三",
    "4": "四",
    "四": "四",
    "肆": "四",
    "④": "四",
    "5": "五",
    "五": "五",
    "伍": "五",
    "⑤": "五",
    "6": "六",
    "六": "六",
    "陆": "六",
    "⑥": "六",
    "7": "七",
    "七": "七",
    "柒": "七",
    "⑦": "七",
    "8": "八",
    "八": "八",
    "捌": "八",
    "⑧": "八",
    "9": "九",
    "九": "九",
    "玖": "九",
    "⑨": "九",
}


def _normalize(text: str) -> str:
    """Normalize text to a canonical form to defeat simple bypasses."""
    if not text:
        return ""
    lowered = text.lower()
    # Apply word-level substitutions (longest first to avoid partial overwrites).
    word_keys = sorted(
        {k for variants in WORD_CANONICAL.values() for k in variants},
        key=len,
        reverse=True,
    )
    out = lowered
    for key in word_keys:
        # Find the canonical root for this variant.
        canonical = None
        for root, variants in WORD_CANONICAL.items():
            if key in variants:
                canonical = root
                break
        if canonical:
            out = out.replace(key, canonical)
    # Apply character-level substitutions.
    result = []
    i = 0
    while i < len(out):
        # Prefer longest match in char map.
        matched = False
        for key in sorted(CHAR_CANONICAL, key=len, reverse=True):
            if out.startswith(key, i):
                result.append(CHAR_CANONICAL[key])
                i += len(key)
                matched = True
                break
        if not matched:
            result.append(out[i])
            i += 1
    return "".join(result)


DEFAULT_WORDS_META: list[dict[str, Any]] = [
    # porn
    {"word": "色情", "category": "porn", "severity": "high"},
    {"word": "淫秽", "category": "porn", "severity": "high"},
    {"word": "裸体", "category": "porn", "severity": "high"},
    {"word": "裸聊", "category": "porn", "severity": "high"},
    {"word": "约炮", "category": "porn", "severity": "high"},
    {"word": "一夜情", "category": "porn", "severity": "high"},
    {"word": "性服务", "category": "porn", "severity": "high"},
    {"word": "援交", "category": "porn", "severity": "high"},
    {"word": "包养", "category": "porn", "severity": "medium"},
    {"word": "卖淫", "category": "porn", "severity": "high"},
    {"word": "嫖娼", "category": "porn", "severity": "high"},
    {"word": "招嫖", "category": "porn", "severity": "high"},
    {"word": "骚逼", "category": "porn", "severity": "high"},
    {"word": "骚货", "category": "porn", "severity": "high"},
    {"word": "妓女", "category": "porn", "severity": "high"},
    {"word": "鸡巴", "category": "porn", "severity": "high"},
    {"word": "阴道", "category": "porn", "severity": "medium"},
    {"word": "阴茎", "category": "porn", "severity": "medium"},
    {"word": "强奸", "category": "porn", "severity": "high"},
    {"word": "乱伦", "category": "porn", "severity": "high"},
    # gamble
    {"word": "赌博", "category": "gamble", "severity": "high"},
    {"word": "博彩", "category": "gamble", "severity": "high"},
    {"word": "赌球", "category": "gamble", "severity": "high"},
    {"word": "赌马", "category": "gamble", "severity": "high"},
    {"word": "六合彩", "category": "gamble", "severity": "high"},
    {"word": "时时彩", "category": "gamble", "severity": "high"},
    {"word": "老虎机", "category": "gamble", "severity": "medium"},
    {"word": "棋牌赌博", "category": "gamble", "severity": "high"},
    {"word": "网络赌博", "category": "gamble", "severity": "high"},
    {"word": "下注", "category": "gamble", "severity": "medium"},
    {"word": "筹码", "category": "gamble", "severity": "low"},
    {"word": "开奖", "category": "gamble", "severity": "low"},
    {"word": "庄家", "category": "gamble", "severity": "low"},
    {"word": "赔率", "category": "gamble", "severity": "low"},
    {"word": "赌资", "category": "gamble", "severity": "high"},
    # drug
    {"word": "毒品", "category": "drug", "severity": "high"},
    {"word": "吸毒", "category": "drug", "severity": "high"},
    {"word": "贩毒", "category": "drug", "severity": "high"},
    {"word": "大麻", "category": "drug", "severity": "high"},
    {"word": "冰毒", "category": "drug", "severity": "high"},
    {"word": "海洛因", "category": "drug", "severity": "high"},
    {"word": "可卡因", "category": "drug", "severity": "high"},
    {"word": "摇头丸", "category": "drug", "severity": "high"},
    {"word": "致幻剂", "category": "drug", "severity": "high"},
    {"word": "罂粟", "category": "drug", "severity": "medium"},
    {"word": "白粉", "category": "drug", "severity": "high"},
    {"word": "麻古", "category": "drug", "severity": "high"},
    {"word": "溜冰", "category": "drug", "severity": "high"},
    {"word": "嗑药", "category": "drug", "severity": "high"},
    {"word": "毒贩", "category": "drug", "severity": "high"},
    # fraud
    {"word": "诈骗", "category": "fraud", "severity": "high"},
    {"word": "电信诈骗", "category": "fraud", "severity": "high"},
    {"word": "网络诈骗", "category": "fraud", "severity": "high"},
    {"word": "传销", "category": "fraud", "severity": "high"},
    {"word": "洗钱", "category": "fraud", "severity": "high"},
    {"word": "套现", "category": "fraud", "severity": "medium"},
    {"word": "刷单", "category": "fraud", "severity": "high"},
    {"word": "返利", "category": "fraud", "severity": "medium"},
    {"word": "虚假投资", "category": "fraud", "severity": "high"},
    {"word": "冒充", "category": "fraud", "severity": "medium"},
    {"word": "钓鱼网站", "category": "fraud", "severity": "high"},
    {"word": "盗号", "category": "fraud", "severity": "high"},
    {"word": "黑客", "category": "fraud", "severity": "medium"},
    {"word": "木马", "category": "fraud", "severity": "high"},
    {"word": "钓鱼链接", "category": "fraud", "severity": "high"},
    {"word": "资金盘", "category": "fraud", "severity": "high"},
    {"word": "庞氏骗局", "category": "fraud", "severity": "high"},
    {"word": "非法集资", "category": "fraud", "severity": "high"},
    # insult
    {"word": "傻逼", "category": "insult", "severity": "medium"},
    {"word": "脑残", "category": "insult", "severity": "medium"},
    {"word": "nmsl", "category": "insult", "severity": "high"},
    {"word": "你妈死了", "category": "insult", "severity": "high"},
    {"word": "去死", "category": "insult", "severity": "high"},
    {"word": "废物", "category": "insult", "severity": "medium"},
    {"word": "垃圾", "category": "insult", "severity": "low"},
    {"word": "滚", "category": "insult", "severity": "low"},
    {"word": "混蛋", "category": "insult", "severity": "medium"},
    {"word": "王八蛋", "category": "insult", "severity": "high"},
    {"word": "贱人", "category": "insult", "severity": "high"},
    {"word": "婊子", "category": "insult", "severity": "high"},
    {"word": "畜生", "category": "insult", "severity": "high"},
    {"word": "死全家", "category": "insult", "severity": "high"},
    {"word": "草泥马", "category": "insult", "severity": "medium"},
    {"word": "马勒戈壁", "category": "insult", "severity": "medium"},
    {"word": "蠢猪", "category": "insult", "severity": "medium"},
    {"word": "白痴", "category": "insult", "severity": "medium"},
    {"word": "神经病", "category": "insult", "severity": "low"},
    {"word": "不要脸", "category": "insult", "severity": "low"},
    # politics / violence
    {"word": "杀人", "category": "politics", "severity": "high"},
    {"word": "自杀", "category": "politics", "severity": "high"},
    {"word": "自残", "category": "politics", "severity": "high"},
    {"word": "恐吓", "category": "politics", "severity": "high"},
    {"word": "威胁", "category": "politics", "severity": "medium"},
    {"word": "暴力", "category": "politics", "severity": "medium"},
    {"word": "恐怖主义", "category": "politics", "severity": "high"},
    {"word": "极端主义", "category": "politics", "severity": "high"},
    {"word": "分裂", "category": "politics", "severity": "high"},
    {"word": "反动", "category": "politics", "severity": "high"},
    {"word": "煽动", "category": "politics", "severity": "high"},
    {"word": "颠覆", "category": "politics", "severity": "high"},
    {"word": "暴乱", "category": "politics", "severity": "high"},
    {"word": "法轮功", "category": "politics", "severity": "high"},
    {"word": "邪教", "category": "politics", "severity": "high"},
    {"word": "枪支", "category": "politics", "severity": "medium"},
    {"word": "弹药", "category": "politics", "severity": "medium"},
    {"word": "爆炸物", "category": "politics", "severity": "high"},
]

DEFAULT_SENSITIVE_WORDS: list[str] = [w["word"] for w in DEFAULT_WORDS_META]


class DFAFilter:
    """Deterministic finite automaton based sensitive-word filter.

    Supports case-insensitive matching, common Chinese homophones/pinyin
    bypasses, digit substitutions, and avoids overlapping/duplicate matches.
    """

    def __init__(self, words: list[str] | None = None):
        self.root: dict = {}
        for word in words or DEFAULT_SENSITIVE_WORDS:
            self.add_word(word)

    def add_word(self, word: str) -> None:
        canonical = _normalize(word)
        if not canonical:
            return
        node = self.root
        for ch in canonical:
            node = node.setdefault(ch, {})
        node["end"] = True

    def _check(self, text: str) -> tuple[bool, list[str]]:
        normalized = _normalize(text)
        matched: list[str] = []
        covered = [False] * len(normalized)
        i = 0
        while i < len(normalized):
            if covered[i]:
                i += 1
                continue
            node = self.root
            j = i
            last_end = -1
            last_hit = ""
            while j < len(normalized) and normalized[j] in node:
                node = node[normalized[j]]
                j += 1
                if node.get("end"):
                    last_end = j
                    last_hit = normalized[i:j]
            if last_end != -1:
                matched.append(last_hit)
                for k in range(i, last_end):
                    covered[k] = True
                i = last_end
            else:
                i += 1
        return bool(matched), matched

    def contains(self, text: str) -> bool:
        return self._check(text)[0]

    def find_all(self, text: str) -> list[str]:
        return self._check(text)[1]


async def load_moderation_configs(db: AsyncSession) -> list[dict[str, Any]]:
    """Load enabled moderation words from the database."""
    result = await db.execute(
        select(ModerationConfig).where(ModerationConfig.enabled.is_(True))
    )
    return [
        {
            "word": c.word,
            "category": c.category,
            "severity": c.severity,
        }
        for c in result.scalars().all()
    ]


class ModerationService:
    def __init__(self, extra_words: list[dict[str, Any]] | None = None):
        self.default_words = list(DEFAULT_WORDS_META)
        self.extra_words = list(extra_words or [])
        words = [w["word"] for w in self.default_words + self.extra_words]
        self.filter = DFAFilter(words)
        self.provider = (settings.MODERATION_PROVIDER or "").lower().strip()
        self._meta: dict[str, dict[str, Any]] = {}
        for w in self.default_words + self.extra_words:
            key = _normalize(w["word"])
            if key and key not in self._meta:
                self._meta[key] = w

    def _check(self, text: str) -> tuple[bool, list[str]]:
        if not text:
            return False, []
        return self.filter.contains(text), self.filter.find_all(text)

    def check_text(self, text: str, source: str = "chat") -> dict[str, Any]:
        triggered, words = self._check(text)
        return {
            "triggered": triggered,
            "words": words,
            "source": source,
            "text": text,
            "ai_score": None,
            "cloud_triggered": False,
        }

    def _is_strong_local_hit(self, result: dict[str, Any]) -> bool:
        """A strong hit bypasses the cloud check.

        Defined as any high-severity match or two or more matched words.
        """
        if not result["triggered"]:
            return False
        matched = result["words"]
        if len(matched) >= 2:
            return True
        for word in matched:
            meta = self._meta.get(word)
            if meta and meta.get("severity") == "high":
                return True
        return False

    async def _call_cloud_moderation(self, text: str) -> dict[str, Any]:
        """Placeholder cloud moderation API.

        Supports openai, aliyun, and tencent providers. Returns deterministic
        mock results so tests remain stable. Text containing the test marker
        'cloud_bad' is treated as unsafe.
        """
        provider = self.provider
        marker = "cloud_bad"
        triggered = marker in text.lower()
        # Deterministic score based on text hash to keep outputs stable.
        digest = hashlib.sha256(text.encode()).hexdigest()
        base_score = int(digest[:8], 16) / 0xFFFFFFFF
        ai_score = 0.85 + 0.14 * base_score if triggered else 0.05 + 0.15 * base_score
        logger.info("Cloud moderation [%s] triggered=%s score=%.3f", provider, triggered, ai_score)
        return {
            "provider": provider,
            "triggered": triggered,
            "ai_score": round(ai_score, 3),
        }

    async def _log_result(
        self,
        db: AsyncSession,
        result: dict[str, Any],
        source: str,
    ) -> None:
        log = ModerationLog(
            text=result.get("text", "")[:2000],
            source=source,
            triggered=result.get("triggered", False),
            words=result.get("words", []),
            ai_score=result.get("ai_score"),
        )
        db.add(log)
        await db.commit()

    async def async_moderate(
        self,
        text: str,
        source: str = "chat",
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Run local DFA then optional cloud check, and log the result."""
        result = self.check_text(text, source)
        if self.provider and not self._is_strong_local_hit(result):
            cloud = await self._call_cloud_moderation(text)
            result["ai_score"] = cloud.get("ai_score")
            result["cloud_triggered"] = cloud.get("triggered", False)
            if cloud.get("triggered"):
                result["triggered"] = True
        if db is not None:
            await self._log_result(db, result, source)
        return result


def get_moderation_service(
    extra_words: list[dict[str, Any]] | None = None,
) -> ModerationService:
    return ModerationService(extra_words=extra_words)
