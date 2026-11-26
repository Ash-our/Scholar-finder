from scholarship_map.similarity import jaccard, token_set, safe_to_merge


def test_jaccard_has_an_independent_known_value():
    assert jaccard({"a", "b"}, {"b", "c"}) == 1 / 3
    assert jaccard(set(), set()) == 0


def test_arabic_text_has_nonempty_features():
    assert token_set("منحة دراسية للطلاب") == {"منحة دراسية", "دراسية للطلاب"}


def test_different_cycles_or_generic_homepage_cannot_merge():
    a = {"title": "Study award", "official_url": "https://example.org/award", "cycle": "2027"}
    assert safe_to_merge(a, dict(a))
    assert not safe_to_merge(a, a | {"cycle": "2028"})
    assert not safe_to_merge(a | {"official_url": "https://example.org/"}, a | {"official_url": "https://example.org/"})
    assert not safe_to_merge(a, a | {"official_url": "https://example.org/other-award"})
