"""Unit tests for compute_content_hash — deterministic semantic hashing."""

from app.rag.content_hash import compute_content_hash


def _make_doc(**overrides: object) -> dict:
    defaults: dict = {
        "title": "Test Policy",
        "category": "REFUND",
        "issue_types": ["PRE_SHIP_REFUND", "QUALITY_REFUND"],
        "content": "Full policy text here.",
        "content_summary": "Summary.",
        "metadata_filter": {"max_days": 7},
        "effective_date": "2025-01-01",
        "expiration_date": None,
        "source": "company_policy",
        # Fields that should NOT affect hash:
        "id": "uuid-123",
        "policy_key": "POL-REF-001",
        "version": 1,
        "status": "DRAFT",
        "superseded_by": None,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-02T00:00:00Z",
    }
    defaults.update({k: v for k, v in overrides.items() if v is not ...})
    return defaults


class TestDeterministic:
    def test_same_content_same_hash(self) -> None:
        h1 = compute_content_hash(_make_doc())
        h2 = compute_content_hash(_make_doc())
        assert h1 == h2

    def test_different_content_different_hash(self) -> None:
        h1 = compute_content_hash(_make_doc(title="Alpha"))
        h2 = compute_content_hash(_make_doc(title="Beta"))
        assert h1 != h2


class TestStatusVersionIgnored:
    def test_status_change_ignored(self) -> None:
        h1 = compute_content_hash(_make_doc(status="DRAFT"))
        h2 = compute_content_hash(_make_doc(status="ACTIVE"))
        assert h1 == h2

    def test_version_change_ignored(self) -> None:
        h1 = compute_content_hash(_make_doc(version=1))
        h2 = compute_content_hash(_make_doc(version=5))
        assert h1 == h2

    def test_policy_key_ignored(self) -> None:
        h1 = compute_content_hash(_make_doc(policy_key="POL-REF-001"))
        h2 = compute_content_hash(_make_doc(policy_key="POL-REF-999"))
        assert h1 == h2

    def test_timestamps_ignored(self) -> None:
        h1 = compute_content_hash(_make_doc(created_at="2020-01-01", updated_at="2020-01-01"))
        h2 = compute_content_hash(_make_doc(created_at="2030-12-31", updated_at="2030-12-31"))
        assert h1 == h2


class TestIssueTypesOrder:
    def test_issue_types_order_does_not_matter(self) -> None:
        h1 = compute_content_hash(_make_doc(issue_types=["A", "B"]))
        h2 = compute_content_hash(_make_doc(issue_types=["B", "A"]))
        assert h1 == h2


class TestMetadataFilterOrder:
    def test_dict_key_order_does_not_matter(self) -> None:
        h1 = compute_content_hash(_make_doc(metadata_filter={"b": 1, "a": 2}))
        # This will naturally be in the given order, but canonicalization sorts
        h2 = compute_content_hash(_make_doc(metadata_filter={"a": 2, "b": 1}))
        assert h1 == h2


class TestSemanticFields:
    """Each of the 9 semantic fields affects the hash when changed."""

    def test_title_change(self) -> None:
        h1 = compute_content_hash(_make_doc(title="X"))
        h2 = compute_content_hash(_make_doc(title="Y"))
        assert h1 != h2

    def test_category_change(self) -> None:
        h1 = compute_content_hash(_make_doc(category="REFUND"))
        h2 = compute_content_hash(_make_doc(category="RETURN"))
        assert h1 != h2

    def test_content_change(self) -> None:
        h1 = compute_content_hash(_make_doc(content="Alpha"))
        h2 = compute_content_hash(_make_doc(content="Beta"))
        assert h1 != h2

    def test_content_summary_change(self) -> None:
        h1 = compute_content_hash(_make_doc(content_summary="A"))
        h2 = compute_content_hash(_make_doc(content_summary="B"))
        assert h1 != h2

    def test_effective_date_change(self) -> None:
        h1 = compute_content_hash(_make_doc(effective_date="2020-01-01"))
        h2 = compute_content_hash(_make_doc(effective_date="2030-01-01"))
        assert h1 != h2

    def test_expiration_date_change(self) -> None:
        h1 = compute_content_hash(_make_doc(expiration_date=None))
        h2 = compute_content_hash(_make_doc(expiration_date="2030-01-01"))
        assert h1 != h2

    def test_source_change(self) -> None:
        h1 = compute_content_hash(_make_doc(source="legal"))
        h2 = compute_content_hash(_make_doc(source="company"))
        assert h1 != h2
