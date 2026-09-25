from judge.coverage import compute_coverage


def test_full_coverage():
    result = compute_coverage(["a", "b", "c"], ["a", "b", "c"])
    assert result.ratio == 1.0
    assert result.unmapped_reference == []


def test_partial_coverage():
    result = compute_coverage(["a"], ["a", "b", "c", "d"])
    assert result.mapped == ["a"]
    assert result.unmapped_reference == ["b", "c", "d"]
    assert result.ratio == 0.25


def test_extra_categories_do_not_inflate_ratio():
    result = compute_coverage(["a", "z", "y"], ["a", "b"])
    assert result.ratio == 0.5
    assert result.extra_categories == ["y", "z"]


def test_empty_reference_is_zero_not_error():
    result = compute_coverage(["a", "b"], [])
    assert result.ratio == 0.0
