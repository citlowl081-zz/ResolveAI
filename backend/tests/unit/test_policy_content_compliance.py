from pathlib import Path

POLICY_DIR = Path(__file__).parents[3] / "data" / "policies"


def _read(name: str) -> str:
    return (POLICY_DIR / name).read_text(encoding="utf-8")


def test_return_policies_do_not_blanket_exclude_opened_electronics() -> None:
    content = "\n".join(
        [
            _read("POL-REF-003-七天无理由退货规则.md"),
            _read("POL-RET-901-七天无理由退货规则.md"),
            _read("POL-RET-902-不适用无理由退货商品.md"),
            _read("POL-EXC-901-换货与品类特殊规则.md"),
        ]
    )

    assert "耳机、音箱：拆封后不支持无理由退货" not in content
    assert "数码电子产品（拆封后影响二次销售）" not in content
    assert "合理调试" in content
    assert "不得仅因" in content or "不得仅按" in content


def test_external_policy_sources_use_verified_official_domains() -> None:
    external_policies = [
        "POL-RET-901-七天无理由退货规则.md",
        "POL-RET-902-不适用无理由退货商品.md",
        "POL-REF-901-质量问题退货规则.md",
        "POL-REF-902-退款时限与运费规则.md",
        "POL-EXC-901-换货与品类特殊规则.md",
        "POL-LOG-901-物流争议处理规则.md",
        "POL-RES-901-少件漏件与补发规则.md",
        "POL-GEN-901-售后数据收集最小化规则.md",
    ]
    allowed_domains = (
        "www.samr.gov.cn",
        "www.npc.gov.cn",
        "flk.npc.gov.cn",
        "xzfg.moj.gov.cn",
        "www.court.gov.cn",
        "www.spb.gov.cn",
    )

    for name in external_policies:
        content = _read(name)
        source_line = next(line for line in content.splitlines() if line.startswith("  url: "))
        assert any(domain in source_line for domain in allowed_domains), name
