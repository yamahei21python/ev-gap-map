"""HTML parser - Search and detail page parsing"""

import re
from typing import Dict, Any, List, Tuple, Optional

from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .config import EV_BASE_URL


def parse_search_page(html: str) -> Tuple[List[Dict[str, Any]], int]:
    """
    Parse search page

    Returns:
        (stations, total_pages)
    """
    soup = BeautifulSoup(html, "lxml")
    stations = []

    blocks = soup.find_all(
        "div",
        class_=lambda c: c and "bg-white" in c and "border" in c and "mt-3" in c,
    )

    for block in blocks:
        station = _parse_station_block(block)
        if station:
            stations.append(station)

    total_pages = _parse_pagination(soup)
    return stations, total_pages


def _parse_station_block(block: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Parse single station block"""
    link = block.find("a", class_="font-bold")
    if not link:
        return None

    href = link.get("href", "")
    station_id = href.rstrip("/").split("/")[-1] if href else None
    if not station_id:
        return None

    name = link.get_text(strip=True)
    url = urljoin(EV_BASE_URL, href)

    addr_p = block.find("p", class_="text-sm")
    address = addr_p.get_text(strip=True) if addr_p else ""
    prefecture = _extract_prefecture(address)

    return {
        "id": station_id,
        "name": name,
        "address": address,
        "prefecture": prefecture,
        "url": url,
    }


def _parse_pagination(soup: BeautifulSoup) -> int:
    """Parse pagination for total pages"""
    nav = soup.find("nav")
    if not nav:
        return 1

    max_page = 1
    for a_tag in nav.find_all("a"):
        href = a_tag.get("href", "")
        match = re.search(r"page=(\d+)", href)
        if match:
            page_num = int(match.group(1))
            max_page = max(max_page, page_num)

    return max_page


def parse_detail_page(html: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Parse detail page

    Returns:
        (station_info, chargers)
    """
    soup = BeautifulSoup(html, "lxml")

    station_info: Dict[str, Any] = {}
    chargers: List[Dict[str, Any]] = []

    tables = soup.find_all("table")

    for table in tables:
        heading = table.find_previous(["h2", "h3", "h4"])
        heading_text = heading.get_text(strip=True) if heading else ""

        if "拠点情報" in heading_text:
            station_info = _parse_base_info_table(table)
        elif "充電機情報" in heading_text:
            charger = _parse_charger_table(table)
            if charger:
                chargers.append(charger)

    return station_info, chargers


def _parse_base_info_table(table: BeautifulSoup) -> Dict[str, Any]:
    """Parse base info table"""
    info = {}
    for row in table.find_all("tr"):
        th = row.find("th")
        td = row.find("td")
        if not th or not td:
            continue
        key = th.get_text(strip=True)
        value = td.get_text(strip=True)

        if key == "住所":
            info["address"] = value
            info["prefecture"] = _extract_prefecture(value)
        elif key == "営業時間":
            info["business_hours"] = value
        elif key == "定休日":
            info["closed_days"] = value
        elif key == "拠点名":
            info["name"] = value
        elif key == "運営会社":
            info["operator"] = value

    return info


def _parse_charger_table(table: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Parse charger info table"""
    charger = {}
    for row in table.find_all("tr"):
        th = row.find("th")
        td = row.find("td")
        if not th or not td:
            continue
        key = th.get_text(strip=True)
        value = td.get_text(strip=True)

        if key == "充電タイプ":
            charger["charger_type"] = _normalize_charger_type(value)
        elif key == "充電器数":
            charger["count"] = _parse_int(value)
        elif key == "出力":
            charger["power_kw"] = _parse_power(value)
        elif key == "最大電流値":
            charger["max_ampere"] = _parse_ampere(value)
        elif key == "充電課金":
            charger["is_paid"] = "有料" in value
        elif key == "駐車料金":
            charger["parking_fee"] = value

    return charger if "charger_type" in charger else None


def _normalize_charger_type(value: str) -> str:
    """Normalize charger type string"""
    value_lower = value.lower()
    if "chademo" in value_lower:
        return "CHAdeMO"
    elif "nacs" in value_lower:
        return "NACS"
    elif "200v" in value_lower or "200v" in value:
        return "200V"
    elif "100v" in value_lower or "100v" in value:
        return "100V"
    elif "テスラ" in value:
        return "NACS"
    return value


def _parse_int(value: str) -> int:
    """Parse integer"""
    match = re.search(r"(\d+)", value)
    return int(match.group(1)) if match else 1


def _parse_power(value: str) -> Optional[float]:
    """Parse power (kW)"""
    match = re.search(r"([\d.]+)\s*kW", value, re.IGNORECASE)
    return float(match.group(1)) if match else None


def _parse_ampere(value: str) -> Optional[float]:
    """Parse ampere"""
    match = re.search(r"([\d.]+)\s*A", value)
    return float(match.group(1)) if match else None


def _extract_prefecture(address: str) -> Optional[str]:
    """Extract prefecture from address"""
    if not address:
        return None
    match = re.match(r"(北海道|.{2,3}?[都府県])", address)
    return match.group(1) if match else None
