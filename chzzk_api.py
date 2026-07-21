# -*- coding: utf-8 -*-
"""치지직 비공식 API 래퍼 (로그인 불필요, 공개 정보만 사용)"""
import json
import urllib.parse
import urllib.request

API_BASE = "https://api.chzzk.naver.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search_channels(keyword: str, size: int = 20) -> list[dict]:
    """채널 이름으로 검색. openLive 포함된 채널 목록 반환."""
    q = urllib.parse.quote(keyword)
    data = _get(
        f"{API_BASE}/service/v1/search/channels"
        f"?keyword={q}&offset=0&size={size}&withFirstChannelContent=true"
    )
    results = []
    for item in data.get("content", {}).get("data", []):
        ch = item.get("channel") or {}
        if not ch.get("channelId"):
            continue
        results.append({
            "channelId": ch["channelId"],
            "channelName": ch.get("channelName", ""),
            "channelImageUrl": ch.get("channelImageUrl") or "",
            "verifiedMark": bool(ch.get("verifiedMark")),
            "followerCount": ch.get("followerCount") or 0,
            "openLive": bool(ch.get("openLive")),
        })
    return results


def get_channel(channel_id: str) -> dict:
    """채널 정보 조회. openLive 필드로 방송 여부 판단."""
    data = _get(f"{API_BASE}/service/v1/channels/{channel_id}")
    return data.get("content") or {}


def get_live_status(channel_id: str) -> dict:
    """방송 중일 때 제목/카테고리 등 상세 정보 (실패해도 무방한 부가 정보)."""
    try:
        data = _get(f"{API_BASE}/polling/v2/channels/{channel_id}/live-status")
        return data.get("content") or {}
    except Exception:
        return {}


def live_url(channel_id: str) -> str:
    return f"https://chzzk.naver.com/live/{channel_id}"
