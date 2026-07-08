import logging
from collections.abc import Mapping

logger = logging.getLogger(__name__)

DEFAULT_SENSITIVE_WORDS = [
    "色情", "赌博", "毒品", "吸毒", "贩毒", "卖淫", "嫖娼", "招嫖",
    "诈骗", "传销", "洗钱", "色情", "裸聊", "约炮", "包养", "强奸",
    "杀人", "自杀", "自残", "恐吓", "威胁", "诈骗", "赌博", "吸毒",
    "傻逼", "脑残", "nmsl", "你妈死了", "去死", "废物", "垃圾", "滚",
]

class DFAFilter:
    """Deterministic finite automaton based Chinese sensitive-word filter."""

    def __init__(self, words: list[str] | None = None):
        self.root: dict = {}
        for word in words or DEFAULT_SENSITIVE_WORDS:
            self.add_word(word)

    def add_word(self, word: str) -> None:
        node = self.root
        for ch in word:
            node = node.setdefault(ch, {})
        node["end"] = True

    def _check(self, text: str) -> tuple[bool, list[str]]:
        matched = []
        for i in range(len(text)):
            node = self.root
            j = i
            hit = ""
            while j < len(text) and text[j] in node:
                hit += text[j]
                node = node[text[j]]
                j += 1
                if node.get("end"):
                    matched.append(hit)
            if not matched and text[i] in self.root:
                pass
        return bool(matched), matched

    def contains(self, text: str) -> bool:
        return self._check(text)[0]

    def find_all(self, text: str) -> list[str]:
        return self._check(text)[1]


class ModerationService:
    def __init__(self, extra_words: list[str] | None = None):
        words = list(DEFAULT_SENSITIVE_WORDS)
        if extra_words:
            words.extend(extra_words)
        self.filter = DFAFilter(words)

    def check_text(self, text: str, source: str = "chat") -> dict:
        triggered, words = self._check(text)
        return {
            "triggered": triggered,
            "words": words,
            "source": source,
            "text": text,
        }

    def _check(self, text: str) -> tuple[bool, list[str]]:
        if not text:
            return False, []
        return self.filter.contains(text), self.filter.find_all(text)


def get_moderation_service() -> ModerationService:
    return ModerationService()
