"""
Клиент Overpass API с fallback и retry.
Копируется в: Fuelwatch_bot/data/services/overpass_client.py
"""

import time
import logging
import urllib.request
import urllib.error
import json
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

OVERPASS_ENDPOINTS = [
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

RATE_LIMIT_DELAY = 2.0
REQUEST_TIMEOUT = 300
MAX_RETRIES = 3
BACKOFF_BASE = 5.0


def _build_query(bbox: Tuple[float, float, float, float]) -> str:
    south, west, north, east = bbox
    query = f"""[out:json][timeout:300][maxsize:1073741824];
(
  node["amenity"="fuel"]({south},{west},{north},{east});
  way["amenity"="fuel"]({south},{west},{north},{east});
  relation["amenity"="fuel"]({south},{west},{north},{east});
);
out center;
"""
    return query


def _fetch_with_endpoint(url: str, query: str, timeout: int = REQUEST_TIMEOUT) -> Optional[Dict]:
    data = query.encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "FuelWatchBot/1.0",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8"))
    except Exception as e:
        logger.warning(f"Ошибка от {url}: {e}")
        return None


def fetch_fuel_stations(bbox: Tuple[float, float, float, float]) -> List[Dict]:
    query = _build_query(bbox)
    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(MAX_RETRIES):
            logger.info(f"Запрос к {endpoint} (попытка {attempt + 1}/{MAX_RETRIES})...")
            result = _fetch_with_endpoint(endpoint, query)
            if result is not None:
                stations = []
                for el in result.get("elements", []):
                    if el["type"] == "node":
                        lat, lon = el.get("lat"), el.get("lon")
                    else:
                        center = el.get("center", {})
                        lat, lon = center.get("lat"), center.get("lon")
                    if lat is None or lon is None:
                        continue
                    tags = el.get("tags", {})
                    stations.append({
                        "id": str(el.get("id", "")),
                        "osm_type": el["type"],
                        "name": tags.get("name") or tags.get("brand") or "АЗС",
                        "brand": tags.get("brand", ""),
                        "lat": lat,
                        "lon": lon,
                        "tags": tags,
                    })
                logger.info(f"✅ Получено {len(stations)} станций от {endpoint}")
                time.sleep(RATE_LIMIT_DELAY)
                return stations
            delay = BACKOFF_BASE * (2 ** attempt)
            logger.info(f"⏳ Повтор через {delay:.0f} сек...")
            time.sleep(delay)
        logger.warning(f"⚠️ Все попытки для {endpoint} исчерпаны")
    logger.error("❌ Все endpoint\'ы недоступны")
    return []
