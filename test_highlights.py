from highlights import extract_highlights, local_highlights, split_sentences
from transcriber import format_time

LECTURE = (
    "오늘은 열역학 제1법칙에 대해 배우겠습니다. 에너지는 생성되거나 소멸되지 않습니다. "
    "열역학 제1법칙은 에너지 보존 법칙입니다. 날씨가 좋네요. "
    "중요한 것은 내부 에너지 변화가 열과 일의 차이라는 점입니다. "
    "과제는 다음 주 금요일까지 제출해야 합니다. 시험에 열역학 제1법칙이 꼭 나옵니다."
)


def test_split_sentences():
    assert len(split_sentences(LECTURE)) == 7


def test_local_highlights_picks_important_sentences():
    h = local_highlights(LECTURE, top_n=3)
    assert h.source == "local"
    assert len(h.key_points) == 3
    assert any("시험" in p for p in h.key_points)
    assert not any("날씨" in p for p in h.key_points)
    assert any("과제" in a for a in h.action_items)
    assert "열역학" in h.keywords


def test_empty_text():
    h = local_highlights("")
    assert h.key_points == []


def test_extract_without_key_uses_local(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert extract_highlights(LECTURE).source == "local"


def test_format_time():
    assert format_time(65) == "01:05"
    assert format_time(3725) == "1:02:05"


def test_local_summary_is_top_ranked_sentence():
    assert "날씨" not in local_highlights(LECTURE).summary
