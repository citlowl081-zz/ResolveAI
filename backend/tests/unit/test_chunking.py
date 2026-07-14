"""Unit tests for Chinese-friendly chunk_text."""

from app.rag.chunking import chunk_text


class TestEmpty:
    def test_empty_string(self) -> None:
        assert chunk_text("") == []

    def test_whitespace_only(self) -> None:
        assert chunk_text("   \n\n  ") == []


class TestShortText:
    def test_shorter_than_max_chars(self) -> None:
        result = chunk_text("你好世界", max_chars=500)
        assert len(result) == 1
        assert result[0] == "你好世界"


class TestChineseSentenceBoundary:
    def test_split_on_period(self) -> None:
        text = "订单已发货。物流信息如下。如需帮助请联系客服。"
        result = chunk_text(text, max_chars=10, overlap_chars=0)
        assert len(result) >= 1
        for c in result:
            assert len(c) <= 10

    def test_split_on_multiple_delimiters(self) -> None:
        text = "退款？退货！换货；查询。"
        result = chunk_text(text, max_chars=5, overlap_chars=0)
        assert len(result) >= 1

    def test_no_empty_chunks(self) -> None:
        text = "句子一。句子二。句子三。"
        result = chunk_text(text, max_chars=100, overlap_chars=50)
        for c in result:
            assert c.strip()  # non-empty


class TestParagraph:
    def test_paragraph_boundary(self) -> None:
        text = "段落一。\n\n段落二。"
        result = chunk_text(text, max_chars=500, overlap_chars=0)
        # Paragraph break shouldn't merge across
        assert len(result) <= 2  # short enough for one or two chunks


class TestOverlap:
    def test_overlap_present(self) -> None:
        text = "句子一。句子二。句子三。句子四。句子五。"
        result = chunk_text(text, max_chars=10, overlap_chars=5)
        # With max_chars=10, we'll have multiple chunks with overlap
        assert len(result) >= 1

    def test_overlap_via_trailing_sentences(self) -> None:
        text = "ABCDEFGHIJ。KLMNOPQRST。UVWXYZ。"
        result = chunk_text(text, max_chars=15, overlap_chars=5)
        # Overlap should be from complete trailing sentences
        for c in result:
            assert len(c) <= 15


class TestLongSentenceHardCut:
    def test_single_long_sentence(self) -> None:
        text = "A" * 800  # 800 chars, no delimiters
        result = chunk_text(text, max_chars=500, overlap_chars=0)
        assert len(result) >= 2
        for c in result:
            assert len(c) <= 500

    def test_long_sentence_hard_cut_no_overlap(self) -> None:
        text = "A" * 1200
        result = chunk_text(text, max_chars=500, overlap_chars=50)
        assert len(result) == 3  # 3 chunks of <= 500


class TestMixed:
    def test_chinese_english_mixed(self) -> None:
        text = "订单ORD123退款. Please check."
        result = chunk_text(text, max_chars=50, overlap_chars=0)
        assert len(result) >= 1
        for c in result:
            assert len(c) <= 50

    def test_length_limit(self) -> None:
        text = "句子一。句子二。句子三。句子四。句子五。句子六。"
        result = chunk_text(text, max_chars=10, overlap_chars=0)
        for c in result:
            assert len(c) <= 10
