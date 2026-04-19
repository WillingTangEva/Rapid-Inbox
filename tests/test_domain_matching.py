from app.smtp.matcher import DomainMatcher, DomainRule


def test_domain_matcher_prefers_longest_suffix_and_rule_specific_normalization() -> None:
    matcher = DomainMatcher(
        [
            DomainRule(
                domain_id=1,
                root_domain_ascii="adb.com",
                accept_exact=True,
                accept_subdomains=True,
                plus_addressing_mode="keep",
                local_part_case_sensitive=False,
            ),
            DomainRule(
                domain_id=2,
                root_domain_ascii="x.adb.com",
                accept_exact=True,
                accept_subdomains=False,
                plus_addressing_mode="strip",
                local_part_case_sensitive=False,
            ),
        ]
    )

    assert matcher.match_address("Foo+tag@b.x.adb.com") is None

    exact_match = matcher.match_address("Foo+tag@x.adb.com")
    parent_match = matcher.match_address("Foo+tag@z.adb.com")

    assert exact_match is not None
    assert exact_match.domain_id == 2
    assert exact_match.address_canonical == "foo@x.adb.com"

    assert parent_match is not None
    assert parent_match.domain_id == 1
    assert parent_match.address_canonical == "foo+tag@z.adb.com"


def test_domain_matcher_normalizes_unicode_domain_to_idna() -> None:
    matcher = DomainMatcher(
        [
            DomainRule(
                domain_id=3,
                root_domain_ascii="xn--fsqu00a.xn--0zwm56d",
                accept_exact=True,
                accept_subdomains=True,
                plus_addressing_mode="keep",
                local_part_case_sensitive=False,
            )
        ]
    )

    match = matcher.match_address("Inbox@例子.测试")

    assert match is not None
    assert match.domain_ascii == "xn--fsqu00a.xn--0zwm56d"
    assert match.address_canonical == "inbox@xn--fsqu00a.xn--0zwm56d"
