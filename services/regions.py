"""
Региональное разбиение России для Overpass API.
Копируется в: Fuelwatch_bot/data/services/regions.py
"""

REGIONS = {
    "nw_karelia":       [59.0, 28.0, 70.0, 37.0],
    "nw_leningrad":     [58.0, 28.0, 61.0, 32.0],
    "nw_novgorod":      [56.0, 30.0, 59.0, 35.0],
    "nw_pskov":         [55.0, 27.0, 59.0, 32.0],
    "center_moscow":    [54.5, 35.5, 57.0, 40.0],
    "center_tver":      [55.0, 31.0, 58.0, 38.0],
    "center_vladimir":  [55.0, 38.0, 57.0, 43.0],
    "center_ryazan":    [53.0, 38.0, 55.5, 43.0],
    "center_tula":      [52.5, 35.5, 55.0, 39.0],
    "center_kaluga":    [53.0, 33.0, 56.0, 37.0],
    "center_bryansk":   [51.5, 31.0, 54.0, 35.0],
    "center_smolensk":  [53.0, 30.0, 56.0, 34.0],
    "south_krasnodar":  [43.0, 36.0, 47.0, 42.0],
    "south_rostov":     [45.5, 37.0, 50.0, 44.0],
    "south_volgograd":  [47.0, 41.0, 51.0, 47.0],
    "south_astrakhan":  [45.0, 45.0, 49.0, 50.0],
    "south_stavropol":  [43.0, 40.0, 46.0, 45.0],
    "south_chechnya":   [42.5, 44.0, 44.0, 47.0],
    "volga_nizhny":     [54.0, 42.0, 58.0, 48.0],
    "volga_kazan":      [54.0, 47.0, 57.0, 54.0],
    "volga_samara":     [51.0, 47.0, 55.0, 53.0],
    "volga_saratov":    [49.0, 43.0, 53.0, 50.0],
    "volga_ulyanovsk":  [52.0, 46.0, 55.0, 50.0],
    "volga_penza":      [52.0, 42.0, 54.0, 47.0],
    "volga_mari":       [55.5, 45.5, 57.5, 50.5],
    "volga_udmurt":     [55.5, 51.0, 58.0, 55.0],
    "volga_tatarstan":  [54.0, 48.0, 56.5, 54.0],
    "ural_perm":        [56.0, 54.0, 62.0, 60.0],
    "ural_ekb":         [56.0, 58.0, 60.0, 66.0],
    "ural_chelyabinsk": [53.0, 58.0, 56.0, 63.0],
    "ural_tyumen":      [55.0, 64.0, 60.0, 72.0],
    "ural_kurgan":      [54.0, 62.0, 57.0, 68.0],
    "siberia_omsk":     [53.0, 70.0, 58.0, 76.0],
    "siberia_nsk":      [53.0, 76.0, 58.0, 84.0],
    "siberia_krasnoyarsk": [52.0, 84.0, 58.0, 96.0],
    "siberia_kemerovo": [52.0, 84.0, 56.0, 89.0],
    "siberia_tomsk":    [55.0, 80.0, 60.0, 88.0],
    "siberia_irkutsk":  [51.0, 96.0, 58.0, 112.0],
    "siberia_chita":    [49.0, 112.0, 57.0, 120.0],
    "siberia_ulanude":  [49.0, 104.0, 53.0, 112.0],
    "dv_khabarovsk":    [47.0, 132.0, 52.0, 140.0],
    "dv_vladivostok":   [42.0, 130.0, 48.0, 140.0],
    "dv_yakutsk":       [58.0, 120.0, 66.0, 135.0],
    "dv_magadan":       [59.0, 145.0, 66.0, 162.0],
    "dv_kamchatka":     [50.0, 155.0, 60.0, 165.0],
    "dv_sakhalin":      [46.0, 142.0, 55.0, 145.0],
    "crimea":           [44.0, 32.5, 46.5, 36.5],
    "caucasus_dagestan": [41.0, 46.0, 44.0, 49.0],
    "caucasus_ingushetia": [42.5, 44.0, 43.5, 45.5],
    "caucasus_kabardino": [42.5, 42.5, 44.0, 44.5],
    "caucasus_osetia":  [42.0, 43.0, 43.5, 45.0],
    "caucasus_karachay": [43.0, 40.5, 44.5, 43.0],
}


def get_all_regions():
    return list(REGIONS.items())


def get_region_bbox(name: str):
    return REGIONS.get(name)
