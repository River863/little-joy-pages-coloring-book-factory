from factory.kdp import estimated_interior_pages, paperback_cover_dimensions


def test_twenty_pages_with_blank_backs():
    assert estimated_interior_pages(20, True) == 42


def test_even_page_count():
    assert estimated_interior_pages(21, False) == 24


def test_85x11_cover_dimensions():
    dims = paperback_cover_dimensions("8.5 × 11 in", 42)
    assert round(dims["spine"], 6) == round(42 * 0.002252, 6)
    assert round(dims["height"], 3) == 11.25
    assert round(dims["width"], 6) == round(0.125 + 8.5 + (42 * 0.002252) + 8.5 + 0.125, 6)
