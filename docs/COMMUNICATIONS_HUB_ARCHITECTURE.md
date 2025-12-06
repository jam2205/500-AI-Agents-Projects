# Communications & Research Hub Architecture Design

## Overview

A distributed communications hub enabling agents to access web search, news feeds, research papers, and market intelligence with built-in resilience, caching, and integration with AnythingLLM agent architecture.

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENTS (30 across 10 groups)                 │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Message Bus (Async Pub/Sub)                             │   │
│  │ - Broadcast alerts/news/research to all agents          │   │
│  │ - Subscribe to topics: market_alerts, earnings, news    │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ↓                ↓                ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Web Search   │ │  News Feeds  │ │  Research    │
│ Service      │ │  Service     │ │  Service     │
│ (Port 8003)  │ │  (Port 8004) │ │  (Port 8005) │
├──────────────┤ ├──────────────┤ ├──────────────┤
│ SerpAPI      │ │ NewsAPI      │ │ arXiv API    │
│ Bing Search  │ │ Alpha Vantage│ │ Papers API   │
│ Google News  │ │ Custom RSS   │ │ OpenAlex     │
└──────────────┘ └──────────────┘ └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ↓                ↓                ↓
    ┌─────────────────────────────────────┐
    │   Communications Hub               │
    │   (Port 8006)                       │
    ├─────────────────────────────────────┤
    │ - Dedupe & filter alerts            │
    │ - Cache in S3                       │
    │ - Rate limit external APIs          │
    │ - Failover/resilience handling      │
    │ - AnythingLLM message routing       │
    └─────────────────────────────────────┘
        │
        ├──→ S3 Cache (RunPod Volume)
        ├──→ AnythingLLM Agent Network
        └──→ Service Registry
```

## 1. Service Registry Extensions

### New Service Types

```python
# Updated service_registry.py

class ServiceType(str, Enum):
    """Extended service types."""
    ANALYTICS = "analytics"
    ML = "ml"
    DATA = "data"
    FORECAST = "forecast"
    BACKTEST = "backtest"
    # NEW:
    RESEARCH = "research"         # News, papers, research
    COMMUNICATIONS = "communications"  # Hub for routing
    EXTERNAL_DATA = "external_data"    # Web APIs
    CACHE = "cache"               # Caching layer
```

### Service Registration Example

```python
from src.framework.service_registry import ServiceInfo, ServiceEndpoint, register_service

def register_research_hub_services():
    """Register all research and communications services."""

    # 1. Web Search Service
    web_search_service = ServiceInfo(
        service_id="web-search-001",
        service_name="Web Search Service",
        service_type="research",
        endpoints=[
            ServiceEndpoint(
                path="/search",
                method="POST",
                description="Search web for information",
                capabilities=["web_search", "news_search"]
            ),
            ServiceEndpoint(
                path="/search/financial",
                method="POST",
                description="Financial news and data search",
                capabilities=["financial_search"]
            ),
        ],
        capabilities=[
            "web_search",
            "news_search",
            "financial_search",
            "company_research"
        ],
        dependencies=[]
    )
    register_service(web_search_service)

    # 2. News Feed Service
    news_service = ServiceInfo(
        service_id="news-feeds-001",
        service_name="News Feed Service",
        service_type="research",
        endpoints=[
            ServiceEndpoint(
                path="/feed/latest",
                method="GET",
                description="Get latest news by category",
                capabilities=["news_feed"]
            ),
            ServiceEndpoint(
                path="/feed/subscribe",
                method="POST",
                description="Subscribe to news topic",
                capabilities=["news_subscription"]
            ),
        ],
        capabilities=[
            "news_feed",
            "market_news",
            "earnings_alerts",
            "economic_calendar",
            "news_subscription"
        ],
        dependencies=[]
    )
    register_service(news_service)

    # 3. Research Service
    research_service = ServiceInfo(
        service_id="research-001",
        service_name="Research Service",
        service_type="research",
        endpoints=[
            ServiceEndpoint(
                path="/papers/search",
                method="POST",
                description="Search academic papers",
                capabilities=["paper_search"]
            ),
            ServiceEndpoint(
                path="/analysis/summary",
                method="POST",
                description="Get research summary",
                capabilities=["research_summary"]
            ),
        ],
        capabilities=[
            "paper_search",
            "research_summary",
            "academic_research",
            "market_research"
        ],
        dependencies=[]
    )
    register_service(research_service)

    # 4. Communications Hub
    hub_service = ServiceInfo(
        service_id="comms-hub-001",
        service_name="Communications Hub",
        service_type="communications",
        endpoints=[
            ServiceEndpoint(
                path="/alert/broadcast",
                method="POST",
                description="Broadcast alert to agents",
                capabilities=["broadcast_alert"]
            ),
            ServiceEndpoint(
                path="/query",
                method="POST",
                description="Query multiple research sources",
                capabilities=["multi_source_query"]
            ),
        ],
        capabilities=[
            "broadcast_alert",
            "multi_source_query",
            "alert_aggregation",
            "intelligent_routing",
            "anything_llm_integration"
        ],
        dependencies=["research", "external_data"]
    )
    register_service(hub_service)
```

---

## 2. Web Search Service

### Implementation

```python
# src/services/research/web_search.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import aiohttp
import asyncio
from enum import Enum

class SearchSource(str, Enum):
    SERP_API = "serp_api"
    BING = "bing_search"
    GOOGLE_NEWS = "google_news"
    ALPHA_VANTAGE = "alpha_vantage"

@dataclass
class SearchResult:
    """Search result from web."""
    source: SearchSource
    title: str
    url: str
    snippet: str
    timestamp: datetime
    relevance_score: float
    content_type: str  # "news", "financial", "research", "general"

class WebSearchService:
    """Multi-source web search with resilience."""

    def __init__(self):
        self.serp_api_key = os.getenv("SERP_API_KEY")
        self.bing_api_key = os.getenv("BING_SEARCH_KEY")
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_KEY")
        self.session = None
        self.request_cache = {}  # In-memory cache

    async def initialize(self):
        """Create HTTP session."""
        self.session = aiohttp.ClientSession()

    async def shutdown(self):
        """Close HTTP session."""
        if self.session:
            await self.session.aclose()

    async def search_financial_news(
        self,
        query: str,
        num_results: int = 5,
        time_range: str = "7d"  # 7d, 1m, 3m
    ) -> List[SearchResult]:
        """
        Search for financial news across multiple sources.

        Args:
            query: Search terms (e.g., "EURUSD economic data")
            num_results: Number of results to return
            time_range: Time period to search

        Returns:
            List of search results ranked by relevance
        """
        cache_key = f"fin_news:{query}:{time_range}"
        if cache_key in self.request_cache:
            return self.request_cache[cache_key]

        # Try multiple sources in parallel
        tasks = [
            self._search_alpha_vantage(query, num_results),
            self._search_serp_api(query, num_results, "financial"),
            self._search_bing(query, num_results)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine and deduplicate results
        all_results = []
        seen_urls = set()

        for result_list in results:
            if isinstance(result_list, list):
                for result in result_list:
                    if result.url not in seen_urls:
                        all_results.append(result)
                        seen_urls.add(result.url)

        # Sort by relevance
        all_results.sort(key=lambda x: x.relevance_score, reverse=True)

        # Cache and return
        top_results = all_results[:num_results]
        self.request_cache[cache_key] = top_results

        return top_results

    async def search_company(
        self,
        company: str,
        search_type: str = "all"  # "news", "earnings", "analysis", "all"
    ) -> Dict[str, Any]:
        """Search for company-specific information."""
        # Implementation
        pass

    async def search_economic_calendar(
        self,
        country: str = None,
        event_type: str = None
    ) -> List[Dict[str, Any]]:
        """Get upcoming economic events."""
        # Implementation
        pass

    async def _search_alpha_vantage(
        self,
        query: str,
        num_results: int
    ) -> List[SearchResult]:
        """Alpha Vantage financial news API."""
        try:
            async with self.session.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "NEWS_SENTIMENT",
                    "topics": "financial",
                    "keywords": query,
                    "apikey": self.alpha_vantage_key
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Parse and convert to SearchResult objects
                    return self._parse_alpha_vantage_results(data)
        except Exception as e:
            logger.warning(f"Alpha Vantage search failed: {e}")

        return []

    async def _search_serp_api(
        self,
        query: str,
        num_results: int,
        search_type: str
    ) -> List[SearchResult]:
        """SerpAPI for web/news search."""
        try:
            search_engine = "google" if search_type == "general" else "google_news"

            async with self.session.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "engine": search_engine,
                    "api_key": self.serp_api_key,
                    "num": num_results,
                    "tbm": "nws" if search_type == "news" else None
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return self._parse_serp_api_results(data)
        except Exception as e:
            logger.warning(f"SerpAPI search failed: {e}")

        return []

    async def _search_bing(
        self,
        query: str,
        num_results: int
    ) -> List[SearchResult]:
        """Bing Search API."""
        try:
            async with self.session.get(
                "https://api.bing.microsoft.com/v7.0/search",
                params={"q": query, "count": num_results},
                headers={"Ocp-Apim-Subscription-Key": self.bing_api_key},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return self._parse_bing_results(data)
        except Exception as e:
            logger.warning(f"Bing search failed: {e}")

        return []

    def _parse_alpha_vantage_results(self, data: Dict) -> List[SearchResult]:
        """Convert Alpha Vantage response to SearchResult objects."""
        results = []
        # Implementation
        return results

    def _parse_serp_api_results(self, data: Dict) -> List[SearchResult]:
        """Convert SerpAPI response to SearchResult objects."""
        results = []
        # Implementation
        return results

    def _parse_bing_results(self, data: Dict) -> List[SearchResult]:
        """Convert Bing response to SearchResult objects."""
        results = []
        # Implementation
        return results
```

---

## 3. News Feed Service

### Implementation

```python
# src/services/research/news_feeds.py

from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import feedparser
import aiohttp

class NewsCategory(str, Enum):
    GENERAL = "general"
    FINANCIAL = "financial"
    CRYPTO = "crypto"
    COMMODITIES = "commodities"
    ECONOMIC = "economic"
    EARNINGS = "earnings"
    GEOPOLITICAL = "geopolitical"

@dataclass
class NewsItem:
    """Single news item from feed."""
    source: str
    title: str
    description: str
    url: str
    timestamp: datetime
    category: NewsCategory
    sentiment: str  # "positive", "negative", "neutral"
    relevance_score: float
    tags: List[str]

class NewsFeedService:
    """Multi-source news aggregation with filtering."""

    def __init__(self):
        self.news_api_key = os.getenv("NEWS_API_KEY")
        self.session = None
        self.subscriptions = {}  # topic -> list of agents
        self.feed_cache = {}  # url -> (data, timestamp)
        self.cache_ttl = 300  # 5 minutes

    async def initialize(self):
        self.session = aiohttp.ClientSession()

    async def subscribe_to_topic(
        self,
        agent_id: str,
        topic: str,
        category: NewsCategory = NewsCategory.FINANCIAL
    ):
        """Agent subscribes to news topic."""
        key = f"{topic}:{category}"
        if key not in self.subscriptions:
            self.subscriptions[key] = []

        if agent_id not in self.subscriptions[key]:
            self.subscriptions[key].append(agent_id)
            logger.info(f"Agent {agent_id} subscribed to {key}")

    async def get_latest_news(
        self,
        category: NewsCategory = NewsCategory.FINANCIAL,
        hours: int = 24
    ) -> List[NewsItem]:
        """Get latest news in category."""

        tasks = []

        # NewsAPI
        if category == NewsCategory.FINANCIAL:
            tasks.append(
                self._fetch_newsapi(
                    search_query="finance OR stock OR market",
                    hours=hours
                )
            )

        # Specific feeds
        if category == NewsCategory.EARNINGS:
            tasks.append(
                self._fetch_rss_feed("https://feeds.bloomberg.com/markets/earnings.rss")
            )

        if category == NewsCategory.ECONOMIC:
            tasks.append(
                self._fetch_rss_feed("https://feeds.reuters.com/finance/markets")
            )

        # Run in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten and dedupe
        all_items = []
        seen_titles = set()

        for result_list in results:
            if isinstance(result_list, list):
                for item in result_list:
                    if item.title not in seen_titles:
                        all_items.append(item)
                        seen_titles.add(item.title)

        # Sort by recency
        all_items.sort(key=lambda x: x.timestamp, reverse=True)

        return all_items

    async def _fetch_newsapi(
        self,
        search_query: str,
        hours: int = 24
    ) -> List[NewsItem]:
        """Fetch from NewsAPI.org."""
        try:
            from_date = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

            async with self.session.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": search_query,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "apiKey": self.news_api_key,
                    "from": from_date
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return self._parse_newsapi_response(data)
        except Exception as e:
            logger.warning(f"NewsAPI fetch failed: {e}")

        return []

    async def _fetch_rss_feed(self, url: str) -> List[NewsItem]:
        """Fetch and parse RSS feed."""
        try:
            # Check cache
            if url in self.feed_cache:
                data, timestamp = self.feed_cache[url]
                if datetime.utcnow().timestamp() - timestamp < self.cache_ttl:
                    return data

            async with self.session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    feed_content = await resp.text()
                    items = self._parse_rss_feed(feed_content, url)

                    # Cache
                    self.feed_cache[url] = (items, datetime.utcnow().timestamp())

                    return items
        except Exception as e:
            logger.warning(f"RSS feed fetch failed for {url}: {e}")

        return []

    def _parse_newsapi_response(self, data: Dict) -> List[NewsItem]:
        """Parse NewsAPI response."""
        items = []
        for article in data.get("articles", []):
            item = NewsItem(
                source=article.get("source", {}).get("name", "Unknown"),
                title=article.get("title", ""),
                description=article.get("description", ""),
                url=article.get("url", ""),
                timestamp=datetime.fromisoformat(
                    article.get("publishedAt", "").replace("Z", "+00:00")
                ),
                category=NewsCategory.FINANCIAL,
                sentiment="neutral",  # Could use NLP for sentiment
                relevance_score=0.8,
                tags=[]
            )
            items.append(item)

        return items

    def _parse_rss_feed(self, content: str, url: str) -> List[NewsItem]:
        """Parse RSS feed content."""
        items = []
        feed = feedparser.parse(content)

        for entry in feed.entries[:20]:  # Limit to 20 items
            item = NewsItem(
                source=feed.feed.get("title", "RSS Feed"),
                title=entry.get("title", ""),
                description=entry.get("summary", ""),
                url=entry.get("link", ""),
                timestamp=datetime(*entry.get("published_parsed", datetime.utcnow().timetuple())[:6]),
                category=NewsCategory.FINANCIAL,
                sentiment="neutral",
                relevance_score=0.7,
                tags=entry.get("tags", [])
            )
            items.append(item)

        return items
```

---

## 4. Communications Hub

### Central Coordinator

```python
# src/services/communications/hub.py

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio
import boto3
from src.framework.service_registry import get_services_by_type

class AlertPriority(str, Enum):
    CRITICAL = "critical"      # Market moving
    HIGH = "high"              # Important updates
    MEDIUM = "medium"          # Standard news
    LOW = "low"                # FYI

@dataclass
class Alert:
    """Alert broadcast to agents."""
    alert_id: str
    source: str                # "news", "research", "web_search", etc.
    title: str
    content: str
    priority: AlertPriority
    category: str              # "earnings", "economic", "news", etc.
    tags: List[str]
    timestamp: datetime
    url: Optional[str] = None
    relevant_symbols: List[str] = None
    agent_subscriptions: Set[str] = None  # Which agents subscribed

class CommunicationsHub:
    """
    Central hub for:
    1. Aggregating alerts from multiple research services
    2. Deduplicating and filtering
    3. Intelligent routing to agents
    4. Caching in S3
    5. AnythingLLM integration
    """

    def __init__(self, message_bus, s3_bucket: str):
        self.message_bus = message_bus
        self.s3_client = boto3.client("s3")
        self.s3_bucket = s3_bucket
        self.alert_history = {}  # alert_id -> Alert
        self.dedup_cache = set()  # Recent alert titles for dedup

    async def process_web_search_result(
        self,
        query: str,
        results: List[Dict[str, Any]],
        agent_id: str = None
    ):
        """
        Process web search results and broadcast if relevant.

        Args:
            query: Original search query
            results: Results from WebSearchService
            agent_id: Agent that requested search (optional)
        """
        for result in results:
            # Create alert from result
            alert = Alert(
                alert_id=f"search:{hash(result['url'])}",
                source="web_search",
                title=result.get("title", ""),
                content=result.get("snippet", ""),
                priority=AlertPriority.MEDIUM,
                category="research",
                tags=[query.lower()],
                timestamp=datetime.utcnow(),
                url=result.get("url"),
                relevant_symbols=self._extract_symbols(result.get("title", ""))
            )

            # Process alert (dedup, enrich, store)
            await self.process_alert(alert, requester_id=agent_id)

    async def process_news_feed(
        self,
        news_items: List[Dict[str, Any]]
    ):
        """
        Process incoming news feed items.

        Args:
            news_items: Items from NewsFeedService
        """
        for item in news_items:
            alert = Alert(
                alert_id=f"news:{hash(item['url'])}",
                source="news_feed",
                title=item.get("title", ""),
                content=item.get("description", ""),
                priority=self._determine_priority(item),
                category=item.get("category", "general"),
                tags=item.get("tags", []),
                timestamp=item.get("timestamp", datetime.utcnow()),
                url=item.get("url"),
                relevant_symbols=self._extract_symbols(item.get("title", ""))
            )

            await self.process_alert(alert)

    async def process_alert(
        self,
        alert: Alert,
        requester_id: str = None
    ):
        """
        Main alert processing pipeline:
        1. Check for duplicates
        2. Enrich with metadata
        3. Determine relevance to agents
        4. Cache in S3
        5. Broadcast to message bus
        6. Send to AnythingLLM if needed
        """
        # 1. Deduplication
        alert_hash = hash(alert.title)
        if alert_hash in self.dedup_cache:
            logger.debug(f"Duplicate alert suppressed: {alert.title[:50]}")
            return

        self.dedup_cache.add(alert_hash)

        # 2. Store in history and S3
        self.alert_history[alert.alert_id] = alert
        await self._store_alert_in_s3(alert)

        # 3. Determine relevant agents
        alert.agent_subscriptions = await self._find_relevant_agents(alert)

        # 4. Broadcast to message bus
        await self._broadcast_alert(alert)

        # 5. Send to AnythingLLM if critical
        if alert.priority in [AlertPriority.CRITICAL, AlertPriority.HIGH]:
            await self._send_to_anything_llm(alert)

    async def _store_alert_in_s3(self, alert: Alert):
        """Store alert in S3 for persistence and analytics."""
        try:
            key = f"alerts/{alert.source}/{alert.timestamp.isoformat()}/{alert.alert_id}.json"

            alert_json = {
                "alert_id": alert.alert_id,
                "source": alert.source,
                "title": alert.title,
                "content": alert.content,
                "priority": alert.priority.value,
                "category": alert.category,
                "tags": alert.tags,
                "timestamp": alert.timestamp.isoformat(),
                "url": alert.url,
                "relevant_symbols": alert.relevant_symbols,
                "subscribed_agents": list(alert.agent_subscriptions or [])
            }

            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=json.dumps(alert_json),
                ContentType="application/json"
            )
        except Exception as e:
            logger.error(f"Failed to store alert in S3: {e}")

    async def _broadcast_alert(self, alert: Alert):
        """Broadcast alert via message bus."""
        from src.framework.base_agent import Message

        message = Message(
            sender_id="comms-hub",
            message_type="alert",
            content={
                "alert_id": alert.alert_id,
                "source": alert.source,
                "title": alert.title,
                "content": alert.content,
                "priority": alert.priority.value,
                "category": alert.category,
                "tags": alert.tags,
                "timestamp": alert.timestamp.isoformat(),
                "url": alert.url,
                "relevant_symbols": alert.relevant_symbols
            },
            recipient_ids=list(alert.agent_subscriptions or [])
        )

        await self.message_bus.publish(message)

    async def _send_to_anything_llm(self, alert: Alert):
        """
        Send critical alerts to AnythingLLM for analysis.

        Integration with AnythingLLM agent architecture.
        """
        try:
            anything_llm_api = os.getenv("ANYTHING_LLM_API_URL")
            anything_llm_key = os.getenv("ANYTHING_LLM_API_KEY")

            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{anything_llm_api}/api/chat",
                    headers={"Authorization": f"Bearer {anything_llm_key}"},
                    json={
                        "message": f"ALERT: {alert.title}\n\n{alert.content}\n\nSymbols: {alert.relevant_symbols}",
                        "mode": "query",
                        "workspace": "trading_workspace"
                    }
                )
        except Exception as e:
            logger.warning(f"AnythingLLM integration failed: {e}")

    async def _find_relevant_agents(self, alert: Alert) -> Set[str]:
        """
        Determine which agents should receive this alert.

        Rules:
        - Agents with relevant symbol subscriptions
        - Agents with category subscriptions
        - RiskManager gets all HIGH/CRITICAL
        - All agents get critical market alerts
        """
        relevant = set()

        # Find agents subscribed to relevant symbols
        if alert.relevant_symbols:
            # Query agent registry (would be added to system)
            # For now: broadcast to all
            relevant.add("*")  # All agents

        # Critical alerts go to risk manager
        if alert.priority in [AlertPriority.CRITICAL, AlertPriority.HIGH]:
            relevant.add("RiskManagerAgent")

        # Research agent subscribes to research alerts
        if alert.category == "research":
            relevant.add("DataScienceAgent")

        return relevant if relevant else {"*"}  # Broadcast to all if no specific match

    def _extract_symbols(self, text: str) -> List[str]:
        """Extract trading symbols from text."""
        import re

        # Common forex, stock, crypto symbols
        pattern = r'\b([A-Z]{2,5}USD|EUR[A-Z]{3}|BTC|ETH|ES|NQ|GC|CL|ZB)\b'
        matches = re.findall(pattern, text.upper())

        return list(set(matches))

    def _determine_priority(self, item: Dict[str, Any]) -> AlertPriority:
        """Determine alert priority based on content."""

        critical_keywords = ["crash", "collapse", "emergency", "circuit breaker", "halted"]
        high_keywords = ["surge", "plunge", "shock", "unexpected", "warning"]

        title_lower = item.get("title", "").lower()

        for keyword in critical_keywords:
            if keyword in title_lower:
                return AlertPriority.CRITICAL

        for keyword in high_keywords:
            if keyword in title_lower:
                return AlertPriority.HIGH

        return AlertPriority.MEDIUM
```

---

## 5. Research Service Agent Integration

### Agent Using Communications Hub

```python
# src/agents/research_hub_agent.py

from src.framework.base_agent import BaseAgent, AgentConfig, Message
from src.framework.service_registry import get_service_by_name

class ResearchHubAgent(BaseAgent):
    """
    Coordinates with communications hub to:
    1. Request web searches on demand
    2. Subscribe to news feeds
    3. Route research findings to other agents
    4. Track research requests and results
    """

    def __init__(self, config: AgentConfig, message_bus=None):
        super().__init__(config, message_bus)
        self.comms_hub_url = "http://comms-hub:8006"
        self.http_client = None

    async def initialize(self):
        await super().initialize()
        self.http_client = aiohttp.ClientSession()

        # Subscribe to alerts
        await self.message_bus.subscribe(
            self.agent_id,
            self.handle_alert
        )

    async def handle_alert(self, alert: Dict[str, Any]):
        """
        Handle incoming alert from communications hub.

        Example: NewsHound agent gets "EURUSD breaks 1.10" alert
        """
        if alert["priority"] in ["critical", "high"]:
            # Create context for LLM analysis
            context = {
                "alert": alert,
                "symbols": alert.get("relevant_symbols", []),
                "timestamp": alert["timestamp"]
            }

            analysis = await self.think(
                f"""Analyze this market alert and suggest trading implications:

Title: {alert['title']}
Content: {alert['content']}
Symbols: {alert.get('relevant_symbols', [])}
Source: {alert['source']}

Provide:
1. Key information from alert
2. Potential market impact
3. Recommended actions for traders
4. Symbols that might be affected""",
                context=context
            )

            # Broadcast analysis
            analysis_msg = Message(
                sender_id=self.agent_id,
                message_type="research_analysis",
                content={
                    "alert_id": alert["alert_id"],
                    "analysis": analysis,
                    "symbols": alert.get("relevant_symbols", []),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            await self.message_bus.publish(analysis_msg)

    async def research_topic(
        self,
        topic: str,
        search_type: str = "web"  # web, news, research, financial
    ) -> Dict[str, Any]:
        """
        Request research on a topic from the hub.

        Args:
            topic: What to research
            search_type: Type of search

        Returns:
            Research findings
        """

        try:
            async with self.http_client.post(
                f"{self.comms_hub_url}/query",
                json={
                    "query": topic,
                    "type": search_type,
                    "requester": self.agent_id,
                    "max_results": 10
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            self.logger.error(f"Research query failed: {e}")

        return {"error": "Research request failed"}

    async def subscribe_to_news(
        self,
        topic: str,
        category: str = "financial"
    ):
        """Subscribe to news on a topic."""
        try:
            async with self.http_client.post(
                f"{self.comms_hub_url}/feed/subscribe",
                json={
                    "agent_id": self.agent_id,
                    "topic": topic,
                    "category": category
                }
            ) as resp:
                if resp.status == 200:
                    self.logger.info(f"Subscribed to {topic} news")
        except Exception as e:
            self.logger.error(f"News subscription failed: {e}")
```

---

## 6. FastAPI Endpoints (Communications Hub)

### HTTP API

```python
# src/services/communications/api.py

from fastapi import FastAPI, HTTPException
import logging

app = FastAPI(
    title="Communications Hub",
    description="Central hub for alerts, research, and agent coordination",
    version="1.0.0"
)

logger = logging.getLogger(__name__)

# Initialize services
hub = CommunicationsHub(message_bus, s3_bucket=os.getenv("S3_BUCKET"))
web_search = WebSearchService()
news_feed = NewsFeedService()

@app.on_event("startup")
async def startup():
    await web_search.initialize()
    await news_feed.initialize()

@app.on_event("shutdown")
async def shutdown():
    await web_search.shutdown()
    await news_feed.shutdown()

# =========================================================
# WEB SEARCH ENDPOINTS
# =========================================================

@app.post("/search/financial")
async def search_financial(query: str, num_results: int = 5):
    """Search for financial information."""
    try:
        results = await web_search.search_financial_news(
            query,
            num_results=num_results
        )

        # Process through hub
        await hub.process_web_search_result(query, results)

        return {"query": query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/search/company")
async def search_company(company: str, search_type: str = "all"):
    """Search for company information."""
    try:
        results = await web_search.search_company(company, search_type)
        return {"company": company, "results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/search/economic-calendar")
async def get_economic_calendar(country: str = None):
    """Get economic calendar events."""
    try:
        events = await web_search.search_economic_calendar(country)
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =========================================================
# NEWS FEED ENDPOINTS
# =========================================================

@app.get("/feed/latest")
async def get_latest_news(
    category: str = "financial",
    hours: int = 24
):
    """Get latest news in category."""
    try:
        from src.services.research.news_feeds import NewsCategory

        items = await news_feed.get_latest_news(
            category=NewsCategory(category),
            hours=hours
        )

        # Process through hub
        await hub.process_news_feed(items)

        return {"category": category, "items": items}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/feed/subscribe")
async def subscribe_to_feed(agent_id: str, topic: str, category: str = "financial"):
    """Subscribe agent to news topic."""
    try:
        from src.services.research.news_feeds import NewsCategory

        await news_feed.subscribe_to_topic(
            agent_id,
            topic,
            NewsCategory(category)
        )

        return {"status": "subscribed", "agent_id": agent_id, "topic": topic}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =========================================================
# COMMUNICATIONS HUB ENDPOINTS
# =========================================================

@app.post("/query")
async def multi_source_query(
    query: str,
    query_type: str = "financial",  # financial, news, research, all
    max_results: int = 10
):
    """Query multiple sources simultaneously."""
    try:
        results = {}

        if query_type in ["financial", "all"]:
            results["financial"] = await web_search.search_financial_news(
                query,
                num_results=max_results
            )

        if query_type in ["news", "all"]:
            results["news"] = await news_feed.get_latest_news()

        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/alerts/history")
async def get_alert_history(
    limit: int = 100,
    source: str = None,
    priority: str = None
):
    """Get alert history from S3."""
    try:
        alerts = []
        # Fetch from S3
        # Filter by source/priority
        return {"alerts": alerts[:limit]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "communications-hub"
    }
```

---

## 7. Deployment Configuration

### Docker Setup

```dockerfile
# docker/Dockerfile.comms-hub

FROM python:3.10-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY src/ ./src/

# Environment
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO
ENV PORT=8006

EXPOSE 8006

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8006/health || exit 1

CMD ["python", "-m", "uvicorn", "src.services.communications.api:app", \
     "--host", "0.0.0.0", "--port", "8006"]
```

### Docker Compose Update

```yaml
# Add to docker-compose.yml

  web-search-api:
    build:
      context: .
      dockerfile: docker/Dockerfile.web-search
    container_name: web-search-api
    ports:
      - "8003:8003"
    environment:
      - SERP_API_KEY=${SERP_API_KEY}
      - BING_SEARCH_KEY=${BING_SEARCH_KEY}
      - ALPHA_VANTAGE_KEY=${ALPHA_VANTAGE_KEY}
      - LOG_LEVEL=INFO
    networks:
      - trading-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      - analytics-api

  news-feeds-api:
    build:
      context: .
      dockerfile: docker/Dockerfile.news-feeds
    container_name: news-feeds-api
    ports:
      - "8004:8004"
    environment:
      - NEWS_API_KEY=${NEWS_API_KEY}
      - LOG_LEVEL=INFO
    networks:
      - trading-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      - analytics-api

  comms-hub:
    build:
      context: .
      dockerfile: docker/Dockerfile.comms-hub
    container_name: comms-hub
    ports:
      - "8006:8006"
    environment:
      - LOG_LEVEL=INFO
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - S3_BUCKET=${S3_BUCKET}
      - ANYTHING_LLM_API_URL=${ANYTHING_LLM_API_URL}
      - ANYTHING_LLM_API_KEY=${ANYTHING_LLM_API_KEY}
    networks:
      - trading-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8006/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      - analytics-api
      - web-search-api
      - news-feeds-api
```

---

## 8. AnythingLLM Integration

### Workspace Configuration

```python
# src/integrations/anything_llm.py

import aiohttp
import os

class AnythingLLMIntegration:
    """Bridge between trading agents and AnythingLLM workspace."""

    def __init__(self):
        self.api_url = os.getenv("ANYTHING_LLM_API_URL")
        self.api_key = os.getenv("ANYTHING_LLM_API_KEY")
        self.workspace = os.getenv("ANYTHING_LLM_WORKSPACE", "trading_workspace")

    async def send_to_workspace(
        self,
        message: str,
        context: Dict[str, Any] = None
    ) -> str:
        """
        Send message to AnythingLLM workspace for analysis.

        Uses AnythingLLM's agent architecture to:
        1. Parse market data
        2. Retrieve relevant documents
        3. Generate analysis
        4. Return insights
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "message": message,
                    "mode": "query",
                    "workspace": self.workspace
                }

                if context:
                    payload["context"] = context

                async with session.post(
                    f"{self.api_url}/api/chat",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("response", "")
        except Exception as e:
            logger.error(f"AnythingLLM request failed: {e}")

        return ""
```

---

## 9. Architecture Summary

```
┌──────────────────────────────────────────────────────────────┐
│                     COMMUNICATIONS ARCHITECTURE              │
└──────────────────────────────────────────────────────────────┘

TIER 1: DATA SOURCES
├─ Web Search (SerpAPI, Bing, Google News)
├─ News Feeds (NewsAPI, RSS, Alpha Vantage)
├─ Research Papers (arXiv, OpenAlex)
└─ Economic Calendar (Trading Economics, etc.)

TIER 2: SERVICE LAYER (Microservices)
├─ WebSearchService (Port 8003)
├─ NewsFeedService (Port 8004)
├─ ResearchService (Port 8005)
└─ All registered in ServiceRegistry

TIER 3: COMMUNICATIONS HUB (Port 8006)
├─ Alert Aggregation (Dedup & filter)
├─ S3 Caching & Storage
├─ Intelligent Routing
├─ AnythingLLM Integration
└─ Message Bus Broadcasting

TIER 4: AGENT ECOSYSTEM
├─ 30 Trading Agents
├─ ResearchHubAgent (coordinates hub)
├─ Message Bus (async pub/sub)
└─ Service Registry (discovery)

TIER 5: INTEGRATION LAYER
├─ AnythingLLM Workspace
├─ RunPod Compute (scaling)
└─ S3 Storage (persistence)

RESILIENCE:
├─ Multi-source fallbacks (try SERP → Bing → Google)
├─ Circuit breakers for failing APIs
├─ Exponential backoff for retries
├─ Request deduplication
├─ Caching (in-memory + S3)
└─ Health checks via service registry
```

---

## 10. Implementation Roadmap

```
Phase 1: Foundation (Week 1)
├─ Service Registry extensions
├─ Web Search Service
├─ News Feed Service
└─ Basic Communications Hub

Phase 2: Integration (Week 2)
├─ FastAPI endpoints
├─ S3 storage integration
├─ AnythingLLM bridge
└─ Agent subscription system

Phase 3: Resilience (Week 3)
├─ Multi-source failover
├─ Request deduplication
├─ Circuit breakers
├─ Health monitoring
└─ Rate limiting

Phase 4: Optimization (Week 4)
├─ Caching strategy
├─ Request batching
├─ Performance tuning
├─ Load testing
└─ Documentation

Phase 5: Deployment (Week 5)
├─ Docker containers
├─ Kubernetes manifests
├─ RunPod integration
└─ S3 setup with volume mounting
```

This architecture provides a robust, scalable communications hub that integrates seamlessly with your existing agent system while leveraging RunPod compute and S3 storage for resilience and scalability.

Would you like me to proceed with implementing any specific component?
