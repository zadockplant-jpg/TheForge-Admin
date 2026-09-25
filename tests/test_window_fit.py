from window_fit import Placement, Rect, _to_units, fit_to_work_area

# A 3840x2160 monitor at 300 % scaling with a 48 px (144 physical px) taskbar
# along the bottom, as a per-monitor DPI aware process sees it.
WORK = Rect(0, 0, 3840, 2016)
FRAME = Rect(24, 93, 24, 24)
SCALE = 3.0
MARGIN = 12


def _outer(placement: Placement) -> Rect:
    return Rect(
        placement.x,
        placement.y,
        placement.x + placement.width + FRAME.left + FRAME.right,
        placement.y + placement.height + FRAME.top + FRAME.bottom,
    )


def test_main_window_and_its_minimum_fit_above_the_taskbar():
    placement = fit_to_work_area(
        round(1180 * SCALE), round(760 * SCALE), WORK, FRAME,
        min_width=round(980 * SCALE), min_height=round(640 * SCALE), margin=MARGIN,
    )
    assert WORK.contains(_outer(placement))
    assert _to_units(placement.width, SCALE) == 1180
    height = _to_units(placement.height, SCALE)
    assert height < 760
    assert round(height * SCALE) + FRAME.top + FRAME.bottom <= WORK.height
    assert _to_units(placement.min_height, SCALE) <= height


def test_tall_dialog_centred_over_its_window_stays_on_screen():
    owner_centre_y = 1000
    width, height = round(560 * SCALE), round(680 * SCALE)
    position = (1920 - width // 2, owner_centre_y - height // 2)
    placement = fit_to_work_area(width, height, WORK, FRAME, position=position, margin=MARGIN)
    assert WORK.contains(_outer(placement))
    assert placement.y == MARGIN


def test_small_dialog_keeps_its_size_and_spot():
    placement = fit_to_work_area(round(440 * SCALE), round(180 * SCALE), WORK, FRAME, position=(1200, 700), margin=MARGIN)
    assert (placement.width, placement.height, placement.x, placement.y) == (1320, 540, 1200, 700)


def test_unit_conversion_never_rounds_past_the_fitted_pixels():
    for pixels in range(1, 3000, 7):
        for scale in (1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0):
            assert round(_to_units(pixels, scale) * scale) <= pixels
