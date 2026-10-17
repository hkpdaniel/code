"""변환된 텍스트에서 중요한 점을 뽑아내는 모듈.

- ANTHROPIC_API_KEY가 있으면 Claude가 요약/핵심 포인트/할 일을 정리한다.
- 키가 없으면 인터넷 없이 동작하는 간단한 추출식(빈도 기반) 방법을 쓴다.
"""
import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field

MODEL = "claude-opus-5-5"

# 중요도를 높여주는 신호 단어
EMPHASIS_WORDS = [
    "중요", "핵심", "반드시", "꼭", "결론", "요약", "정리하면", "시험", "과제", "마감",
    "기한", "까지", "결정", "주의", "문제", "목표", "다음 주", "다음주", "해야",
    "important", "key", "must", "deadline", "remember", "conclusion",
]

# 한국어 조사·불용어 (키워드 계산에서 제외)
STOPWORDS = set(
    "그리고 그래서 그러면 그런데 하지만 그러나 또는 이제 지금 그냥 진짜 정말 약간 이거 저거 그거 "
    "이것 저것 그것 여기 저기 거기 우리 저희 제가 내가 너무 많이 조금 되게 이런 저런 그런 어떤 "
    "있는 있고 있어 있습니다 없는 하는 하고 해서 했고 했습니다 합니다 됩니다 되는 같은 같아요 "
    "아니 네 예 음 어 아 뭐 좀 때문에 대해 대한 통해 위해 the a an and or to of in is are it that this".split()
)
JOSA = re.compile(r"(은|는|이|가|을|를|에|에서|으로|로|와|과|도|만|의|에게|한테|까지|부터|이다|입니다|이에요|예요)$")


@dataclass
class Highlights:
    summary: str
    key_points: list[str]
    action_items: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    source: str = "local"  # "claude" 또는 "local"


# ---------------------------------------------------------------- 로컬 방식
def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。])\s+|(?<=다\.)|(?<=요\.)|\n+", text)
    return [p.strip() for p in parts if p and len(p.strip()) >= 8]


def _tokens(sentence: str) -> list[str]:
    words = re.findall(r"[가-힣A-Za-z0-9]{2,}", sentence.lower())
    out = []
    for w in words:
        w = JOSA.sub("", w)
        if len(w) >= 2 and w not in STOPWORDS:
            out.append(w)
    return out


def local_highlights(text: str, top_n: int = 5) -> Highlights:
    sentences = split_sentences(text)
    if not sentences:
        return Highlights(summary=text.strip()[:200], key_points=[], source="local")

    freq = Counter(t for s in sentences for t in _tokens(s))
    keywords = [w for w, c in freq.most_common(10) if c >= 2] or [w for w, _ in freq.most_common(5)]

    def score(s: str) -> float:
        toks = _tokens(s)
        if not toks:
            return 0.0
        base = sum(freq[t] for t in toks) / (len(toks) ** 0.5)
        bonus = sum(2.0 for w in EMPHASIS_WORDS if w in s.lower())
        return base + bonus

    ranked = sorted(range(len(sentences)), key=lambda i: score(sentences[i]), reverse=True)
    chosen = sorted(ranked[:top_n])  # 원래 순서대로 보여주기
    key_points = [sentences[i] for i in chosen]

    action_items = [
        s for s in sentences
        if re.search(r"(해야|하세요|할 것|제출|마감|까지|준비|숙제|과제|todo|deadline)", s.lower())
    ][:5]

    return Highlights(
        summary=sentences[ranked[0]],
        key_points=key_points,
        action_items=action_items,
        keywords=keywords,
        source="local",
    )


# ---------------------------------------------------------------- Claude 방식
SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}},
        "action_items": {"type": "array", "items": {"type": "string"}},
        "keywords": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "key_points", "action_items", "keywords"],
    "additionalProperties": False,
}

PROMPT = """다음은 녹음 파일을 음성 인식으로 받아 적은 텍스트입니다. 인식 오류가 섞여 있을 수 있습니다.
내용을 읽고 녹음을 듣지 못한 사람이 꼭 알아야 할 것을 정리해 주세요.

- summary: 전체 내용을 2~3문장으로 요약
- key_points: 가장 중요한 점 3~7개 (중요한 순서대로, 각각 한 문장)
- action_items: 해야 할 일·마감·약속 등 (없으면 빈 배열)
- keywords: 핵심 키워드 5개 이내

녹음 텍스트와 같은 언어로 답하세요.

<transcript>
{text}
</transcript>"""


def claude_highlights(text: str) -> Highlights:
    import anthropic

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",  # 안전 필터로 거절되면 서버가 다른 모델로 다시 시도
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": PROMPT.format(text=text)}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude가 요청을 처리하지 않았습니다.")
    raw = next(b.text for b in response.content if b.type == "text")
    data = json.loads(raw)
    return Highlights(source="claude", **data)


def extract_highlights(text: str, use_claude: bool | None = None) -> Highlights:
    """use_claude가 None이면 API 키가 있을 때만 Claude를 쓴다. 실패하면 로컬 방식으로 대체."""
    if use_claude is None:
        use_claude = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if use_claude:
        try:
            return claude_highlights(text)
        except Exception as e:  # 네트워크/키 오류 시에도 결과는 보여주기
            result = local_highlights(text)
            result.summary = f"(Claude 호출 실패: {e} — 로컬 방식으로 추출했습니다)\n\n" + result.summary
            return result
    return local_highlights(text)
