from app.bom_adapter.normalizer import normalize_mapped_values


DEFAULTS = {
    "quantity": 1,
    "uom": "EA",
    "material": "N/A",
    "process": "N/A",
    "category": "standard",
    "supplier": "Unknown Supplier",
    "lead_time_days": 14,
    "module_hint": None,
    "is_spare": False,
    "is_consumable": False,
    "revision": "N/A",
    "drawing_no": "N/A",
    "notes": "",
}


def test_uom_normalization() -> None:
    result = normalize_mapped_values(
        mapped_values={"uom": " 件 "},
        defaults=DEFAULTS,
    )

    assert result["values"]["uom"] == "PCS"
    assert result["trace"]["uom"] == "alias_map"


def test_lead_time_parsing() -> None:
    weeks_result = normalize_mapped_values(mapped_values={"lead_time_days": "4 weeks"}, defaults=DEFAULTS)
    days_result = normalize_mapped_values(mapped_values={"lead_time_days": "28d"}, defaults=DEFAULTS)
    months_result = normalize_mapped_values(mapped_values={"lead_time_days": "1 month"}, defaults=DEFAULTS)

    assert weeks_result["values"]["lead_time_days"] == 28
    assert days_result["values"]["lead_time_days"] == 28
    assert months_result["values"]["lead_time_days"] == 30


def test_supplier_normalization() -> None:
    result = normalize_mapped_values(
        mapped_values={"supplier": " 安川 "},
        defaults=DEFAULTS,
    )

    assert result["values"]["supplier"] == "Yaskawa"
    assert result["trace"]["supplier"] == "alias_map"


def test_dirty_data_cleaning() -> None:
    result = normalize_mapped_values(
        mapped_values={
            "part_name": "　 Servo Motor  ",
            "revision": " rev a ",
            "category": " MOTION ",
            "notes": " N/A ",
            "is_spare": " Y ",
        },
        defaults=DEFAULTS,
    )

    assert result["values"]["part_name"] == "Servo Motor"
    assert result["values"]["revision"] == "A"
    assert result["values"]["category"] == "motion"
    assert result["values"]["notes"] == ""
    assert result["values"]["is_spare"] is True
