UNIT_VALUES = {
    "ANGSTROM": 1e-10,
    "NANOMETER": 1e-9,
    "MICROMETER": 1e-6,
    "MILLIMETER": 1e-3,
    "METER": 1.0,
    "AU": 1.0,
}


def unit_value(unit):
    if isinstance(unit, (int, float)):
        return float(unit)
    return UNIT_VALUES[parse_unit(unit)]


def unit_name(unit):
    value = unit_value(unit)
    for name, candidate in UNIT_VALUES.items():
        if candidate == value:
            return name
    return "AU"


def parse_unit(unit):
    if unit in ['A', 'Å', '\\u00C5', 'ANGSTROM', 'ÅNGSTROM', 'ÅNGSTRÖM', 'Ångstrom', 'angstrom', 'ångström', 'ångstrom']:
        return "ANGSTROM"
    if unit in ['nm', 'nanometer', 'NM', 'NANOMETER']:
        return "NANOMETER"
    if unit in ['\\u00B5m', 'micron', 'micrometer', 'microns', 'um', 'µm', 'MICROMETER']:
        return "MICROMETER"
    if unit in ['mm', 'millimeter', 'MM', 'MILLIMETER']:
        return "MILLIMETER"
    if unit in ['m', 'meter', 'M', 'METER']:
        return "METER"
    return "AU"
