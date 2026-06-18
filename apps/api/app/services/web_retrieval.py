from urllib.parse import urlparse
import socket

import httpx
from bs4 import BeautifulSoup

from app.core.config import Settings
from app.services.redis_client import RedisService


PRIVATE_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    if parsed.hostname.lower() in PRIVATE_HOSTS:
        return False
    try:
        ip = socket.gethostbyname(parsed.hostname)
        return not (ip.startswith("10.") or ip.startswith("192.168.") or ip.startswith("172.16."))
    except OSError:
        return False


class WebRetrievalService:
    def __init__(self, settings: Settings, redis_service: RedisService | None = None):
        self.settings = settings
        self.redis = redis_service

    async def search(self, query: str, count: int = 5) -> list[dict]:
        if not self.settings.tavily_api_key:
            return []
        result_count = min(count, self.settings.max_web_search_results)
        cache_key = f"web:search:{query}:{count}"
        if self.redis:
            cached = await self.redis.get_json(cache_key)
            if cached is not None:
                return cached
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "query": query,
                    "search_depth": self.settings.tavily_search_depth,
                    "max_results": result_count,
                    "include_answer": False,
                    "include_raw_content": False,
                    "include_usage": True,
                },
                headers={"Authorization": f"Bearer {self.settings.tavily_api_key}"},
            )
            response.raise_for_status()
            data = response.json()
        results = [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "description": item.get("content") or "",
                "content": item.get("content") or "",
                "score": item.get("score") or 0,
                "source": "tavily",
            }
            for item in data.get("results", [])[:result_count]
        ]
        if self.redis:
            await self.redis.set_json(cache_key, results, 900)
        return results

    async def fetch_extract(self, url: str) -> str:
        if not is_safe_url(url):
            return ""
        cache_key = f"web:page:{url}"
        if self.redis:
            cached = await self.redis.get_json(cache_key)
            if cached is not None:
                return cached
                
        content = ""
        # Try Tavily Extract API first
        if self.settings.tavily_api_key:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        "https://api.tavily.com/extract",
                        json={"urls": [url]},
                        headers={"Authorization": f"Bearer {self.settings.tavily_api_key}"}
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results = data.get("results", [])
                        if results and results[0].get("raw_content"):
                            content = results[0]["raw_content"][:6000]
            except Exception as e:
                pass

        # Fallback to standard httpx if Tavily failed or wasn't configured
        if not content:
            try:
                async with httpx.AsyncClient(timeout=10, follow_redirects=True, max_redirects=3) as client:
                    response = await client.get(url, headers={"User-Agent": "AIWorkspaceChatBot/0.1"})
                    content_type = response.headers.get("content-type", "")
                    if "text/html" in content_type:
                        html = response.text[:800_000]
                        soup = BeautifulSoup(html, "html.parser")
                        for tag in soup(["script", "style", "nav", "footer", "header"]):
                            tag.decompose()
                        content = " ".join(soup.get_text(" ").split())[:6000]
            except Exception:
                pass

        if content and self.redis:
            await self.redis.set_json(cache_key, content, 3600)
        return content

    async def retrieve(self, query: str) -> list[dict]:
        results = await self.search(query)
        sources = []
        for item in results[:3]:
            url = item.get("url", "")
            content = item.get("content", "") or await self.fetch_extract(url)
            if not content:
                content = item.get("description", "")
            if content:
                sources.append({
                    "title": item.get("title"),
                    "url": url,
                    "content": content[:5000],
                    "score": item.get("score") or 0,
                })
        return sources

    async def advanced_search(self, query: str) -> list[dict]:
        """Deep search with raw content extraction via Tavily."""
        if not self.settings.tavily_api_key:
            return await self.retrieve(query)
        cache_key = f"web:advanced:{query}"
        if self.redis:
            cached = await self.redis.get_json(cache_key)
            if cached is not None:
                return cached
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": self.settings.max_web_search_results,
                    "include_answer": True,
                    "include_raw_content": True,
                    "include_usage": True,
                },
                headers={"Authorization": f"Bearer {self.settings.tavily_api_key}"},
            )
            response.raise_for_status()
            data = response.json()
        results = []
        for item in data.get("results", [])[:self.settings.max_web_search_results]:
            content = item.get("raw_content") or item.get("content") or ""
            if len(content) > 12000:
                content = content[:12000]
            results.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "description": item.get("content") or "",
                "content": content,
                "score": item.get("score") or 0,
                "source": "tavily_advanced",
            })
        if self.redis:
            await self.redis.set_json(cache_key, results, 900)
        return results
