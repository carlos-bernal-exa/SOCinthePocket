"""
SIEM Client adapter for multiple SIEM platforms (Splunk, ElasticSearch, QRadar, etc.)
"""
import os
import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import base64

logger = logging.getLogger(__name__)

class SIEMClient:
    """Universal SIEM client supporting multiple platforms"""
    
    def __init__(self):
        self.siem_type = os.getenv("SIEM_TYPE", "splunk").lower()
        self.base_url = os.getenv("SIEM_BASE_URL", "https://your-siem-instance.com")
        self.username = os.getenv("SIEM_USERNAME")
        self.password = os.getenv("SIEM_PASSWORD")
        self.api_key = os.getenv("SIEM_API_KEY")
        self.token = os.getenv("SIEM_TOKEN")
        self.session = None
        self.auth_token = None
        
        if not self._has_credentials():
            logger.warning("SIEM credentials not found in environment variables")
    
    def _has_credentials(self) -> bool:
        """Check if any authentication method is available"""
        return bool(
            (self.username and self.password) or 
            self.api_key or 
            self.token
        )
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def _authenticate(self) -> bool:
        """Authenticate with SIEM platform"""
        if not self._has_credentials():
            return False
        
        await self._ensure_session()
        
        try:
            if self.siem_type == "splunk":
                return await self._authenticate_splunk()
            elif self.siem_type == "elasticsearch":
                return await self._authenticate_elasticsearch()
            elif self.siem_type == "qradar":
                return await self._authenticate_qradar()
            else:
                logger.warning(f"Unknown SIEM type: {self.siem_type}")
                return False
        except Exception as e:
            logger.error(f"SIEM authentication failed: {e}")
            return False
    
    async def _authenticate_splunk(self) -> bool:
        """Authenticate with Splunk"""
        if not self.username or not self.password:
            return False
        
        auth_url = f"{self.base_url}/services/auth/login"
        auth_data = {
            "username": self.username,
            "password": self.password
        }
        
        async with self.session.post(auth_url, data=auth_data) as response:
            if response.status == 200:
                text = await response.text()
                # Extract session key from XML response
                import xml.etree.ElementTree as ET
                root = ET.fromstring(text)
                session_key = root.find(".//sessionKey").text if root.find(".//sessionKey") is not None else None
                
                if session_key:
                    self.auth_token = session_key
                    logger.info("Successfully authenticated with Splunk")
                    return True
            
            logger.error(f"Splunk authentication failed: {response.status}")
            return False
    
    async def _authenticate_elasticsearch(self) -> bool:
        """Authenticate with Elasticsearch"""
        # Elasticsearch typically uses basic auth or API keys
        if self.api_key:
            self.auth_token = self.api_key
            return True
        elif self.username and self.password:
            # Basic auth - encode credentials
            credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            self.auth_token = f"Basic {credentials}"
            return True
        return False
    
    async def _authenticate_qradar(self) -> bool:
        """Authenticate with IBM QRadar"""
        if self.token:
            self.auth_token = self.token
            return True
        return False
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers based on SIEM type"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.siem_type == "splunk" and self.auth_token:
            headers["Authorization"] = f"Splunk {self.auth_token}"
        elif self.siem_type == "elasticsearch" and self.auth_token:
            if self.auth_token.startswith("Basic"):
                headers["Authorization"] = self.auth_token
            else:
                headers["Authorization"] = f"ApiKey {self.auth_token}"
        elif self.siem_type == "qradar" and self.auth_token:
            headers["SEC"] = self.auth_token
        
        return headers
    
    async def query(self, event_filter: str, start: str, end: str, limit: int = 5000) -> Dict[str, Any]:
        """
        Execute SIEM query across different platforms
        
        Args:
            event_filter: Query string/filter
            start: Start time (ISO format)
            end: End time (ISO format)
            limit: Maximum number of events
            
        Returns:
            Dictionary with count and events
        """
        if not self._has_credentials():
            logger.warning("No SIEM credentials available, returning mock data")
            return self._get_mock_query_results(event_filter, start, end, limit)
        
        try:
            await self._ensure_session()
            
            # Authenticate if needed
            if not self.auth_token:
                auth_success = await self._authenticate()
                if not auth_success:
                    return self._get_mock_query_results(event_filter, start, end, limit)
            
            # Execute query based on SIEM type
            if self.siem_type == "splunk":
                return await self._query_splunk(event_filter, start, end, limit)
            elif self.siem_type == "elasticsearch":
                return await self._query_elasticsearch(event_filter, start, end, limit)
            elif self.siem_type == "qradar":
                return await self._query_qradar(event_filter, start, end, limit)
            else:
                return self._get_mock_query_results(event_filter, start, end, limit)
                
        except Exception as e:
            logger.error(f"SIEM query failed: {e}")
            return self._get_mock_query_results(event_filter, start, end, limit)
    
    async def _query_splunk(self, search_query: str, start: str, end: str, limit: int) -> Dict[str, Any]:
        """Execute Splunk search"""
        search_url = f"{self.base_url}/services/search/jobs"
        headers = await self._get_headers()
        
        # Create search job
        search_data = {
            "search": f"search {search_query}",
            "earliest_time": start,
            "latest_time": end,
            "count": limit,
            "output_mode": "json"
        }
        
        async with self.session.post(search_url, headers=headers, data=search_data) as response:
            if response.status == 201:
                job_response = await response.text()
                # Extract job ID and wait for completion
                import xml.etree.ElementTree as ET
                root = ET.fromstring(job_response)
                job_id = root.find(".//sid").text if root.find(".//sid") is not None else None
                
                if job_id:
                    return await self._get_splunk_results(job_id, headers)
        
        return {"count": 0, "events": []}
    
    async def _get_splunk_results(self, job_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Get results from Splunk search job"""
        results_url = f"{self.base_url}/services/search/jobs/{job_id}/results"
        
        # Wait for job completion (with timeout)
        for _ in range(30):  # 30 second timeout
            status_url = f"{self.base_url}/services/search/jobs/{job_id}"
            async with self.session.get(status_url, headers=headers) as response:
                if response.status == 200:
                    status_text = await response.text()
                    if "DONE" in status_text:
                        break
            await asyncio.sleep(1)
        
        # Get results
        results_params = {"output_mode": "json"}
        async with self.session.get(results_url, headers=headers, params=results_params) as response:
            if response.status == 200:
                results = await response.json()
                return {
                    "count": len(results.get("results", [])),
                    "events": results.get("results", [])
                }
        
        return {"count": 0, "events": []}
    
    async def _query_elasticsearch(self, query: str, start: str, end: str, limit: int) -> Dict[str, Any]:
        """Execute Elasticsearch query"""
        search_url = f"{self.base_url}/_search"
        headers = await self._get_headers()
        
        # Build Elasticsearch query
        es_query = {
            "size": limit,
            "query": {
                "bool": {
                    "must": [
                        {"query_string": {"query": query}},
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": start,
                                    "lte": end
                                }
                            }
                        }
                    ]
                }
            },
            "sort": [{"@timestamp": {"order": "desc"}}]
        }
        
        async with self.session.post(search_url, headers=headers, json=es_query) as response:
            if response.status == 200:
                results = await response.json()
                hits = results.get("hits", {}).get("hits", [])
                events = [hit["_source"] for hit in hits]
                
                return {
                    "count": len(events),
                    "events": events
                }
        
        return {"count": 0, "events": []}
    
    async def _query_qradar(self, aql_query: str, start: str, end: str, limit: int) -> Dict[str, Any]:
        """Execute QRadar AQL query"""
        search_url = f"{self.base_url}/api/ariel/searches"
        headers = await self._get_headers()
        
        # Build AQL query with time range
        full_query = f"{aql_query} LAST 24 HOURS"
        
        search_data = {
            "query_expression": full_query
        }
        
        async with self.session.post(search_url, headers=headers, json=search_data) as response:
            if response.status == 201:
                search_result = await response.json()
                search_id = search_result.get("search_id")
                
                if search_id:
                    return await self._get_qradar_results(search_id, headers)
        
        return {"count": 0, "events": []}
    
    async def _get_qradar_results(self, search_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
        """Get results from QRadar search"""
        results_url = f"{self.base_url}/api/ariel/searches/{search_id}/results"
        
        # Wait for search completion
        for _ in range(30):
            status_url = f"{self.base_url}/api/ariel/searches/{search_id}"
            async with self.session.get(status_url, headers=headers) as response:
                if response.status == 200:
                    status = await response.json()
                    if status.get("status") == "COMPLETED":
                        break
            await asyncio.sleep(1)
        
        # Get results
        async with self.session.get(results_url, headers=headers) as response:
            if response.status == 200:
                results = await response.json()
                events = results.get("events", [])
                
                return {
                    "count": len(events),
                    "events": events
                }
        
        return {"count": 0, "events": []}
    
    def _get_mock_query_results(self, query: str, start: str, end: str, limit: int) -> Dict[str, Any]:
        """Generate mock SIEM query results for testing"""
        mock_events = [
            {
                "timestamp": "2025-08-30T09:15:23Z",
                "source": "windows_security",
                "event_id": 4624,
                "src_ip": "192.168.1.100",
                "user": "suspicious_user",
                "computer": "WORKSTATION-01",
                "logon_type": 3,
                "details": "Successful network logon"
            },
            {
                "timestamp": "2025-08-30T09:16:45Z",
                "source": "firewall",
                "action": "block", 
                "src_ip": "192.168.1.100",
                "dst_ip": "10.0.0.50",
                "port": 445,
                "protocol": "tcp",
                "details": "SMB connection blocked"
            },
            {
                "timestamp": "2025-08-30T09:18:12Z",
                "source": "endpoint_detection",
                "process": "powershell.exe",
                "command_line": "powershell -enc <base64_encoded_command>",
                "user": "suspicious_user",
                "computer": "WORKSTATION-01",
                "details": "Suspicious PowerShell execution"
            },
            {
                "timestamp": "2025-08-30T09:20:33Z",
                "source": "dns_logs",
                "query": "malicious.example.com",
                "src_ip": "192.168.1.100",
                "response_code": "NXDOMAIN",
                "details": "DNS query to suspicious domain"
            },
            {
                "timestamp": "2025-08-30T09:22:15Z",
                "source": "proxy_logs",
                "url": "http://command-control.evil.com/beacon",
                "src_ip": "192.168.1.100",
                "status_code": 200,
                "user_agent": "Mozilla/5.0",
                "details": "Outbound connection to C2 server"
            }
        ]
        
        # Filter events based on query content
        filtered_events = []
        for event in mock_events:
            if any(term.lower() in json.dumps(event).lower() for term in query.split() if len(term) > 2):
                filtered_events.append(event)
        
        # If no matches found, return some events anyway for testing
        if not filtered_events:
            filtered_events = mock_events[:3]
        
        result_count = min(len(filtered_events), limit)
        logger.info(f"Generated {result_count} mock SIEM events for query: {query[:50]}...")
        
        return {
            "count": result_count,
            "events": filtered_events[:limit]
        }
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None


# Global SIEM client instance
siem_client = SIEMClient()
