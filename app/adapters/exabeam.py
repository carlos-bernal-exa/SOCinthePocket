"""
Exabeam API client for fetching case data and investigation details
"""
import os
import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class ExabeamClient:
    """Real Exabeam API client for case data retrieval"""
    
    def __init__(self):
        self.base_url = os.getenv("EXABEAM_BASE_URL", "https://your-exabeam-instance.com")
        self.username = os.getenv("EXABEAM_USERNAME")
        self.password = os.getenv("EXABEAM_PASSWORD")
        self.api_key = os.getenv("EXABEAM_API_KEY")
        self.session = None
        self.auth_token = None
        
        if not self.username or not self.password:
            logger.warning("Exabeam credentials not found in environment variables")
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def _authenticate(self) -> bool:
        """Authenticate with Exabeam and get access token"""
        await self._ensure_session()
        
        if not self.username or not self.password:
            return False
        
        try:
            auth_url = f"{self.base_url}/api/auth/login"
            auth_data = {
                "username": self.username,
                "password": self.password
            }
            
            async with self.session.post(auth_url, json=auth_data) as response:
                if response.status == 200:
                    auth_result = await response.json()
                    self.auth_token = auth_result.get("token") or auth_result.get("access_token")
                    logger.info("Successfully authenticated with Exabeam")
                    return True
                else:
                    logger.error(f"Exabeam authentication failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error authenticating with Exabeam: {e}")
            return False
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
            
        return headers
    
    async def fetch_cases(self, case_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch case data from Exabeam API
        
        Args:
            case_ids: List of case IDs to fetch
            
        Returns:
            List of case data dictionaries
        """
        if not case_ids:
            return []
        
        # If no credentials available, return mock data for testing
        if not (self.username and self.password) and not self.api_key:
            logger.warning("No Exabeam credentials available, returning mock data")
            return self._get_mock_case_data(case_ids)
        
        try:
            await self._ensure_session()
            
            # Authenticate if needed
            if not self.auth_token and not self.api_key:
                auth_success = await self._authenticate()
                if not auth_success:
                    return self._get_mock_case_data(case_ids)
            
            cases_data = []
            headers = await self._get_headers()
            
            # Fetch each case individually
            for case_id in case_ids:
                case_data = await self._fetch_single_case(case_id, headers)
                if case_data:
                    cases_data.append(case_data)
            
            logger.info(f"Successfully fetched {len(cases_data)} cases from Exabeam")
            return cases_data
            
        except Exception as e:
            logger.error(f"Error fetching cases from Exabeam: {e}")
            return self._get_mock_case_data(case_ids)
    
    async def _fetch_single_case(self, case_id: str, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Fetch a single case from Exabeam API"""
        try:
            case_url = f"{self.base_url}/api/cases/{case_id}"
            
            async with self.session.get(case_url, headers=headers) as response:
                if response.status == 200:
                    case_data = await response.json()
                    return self._format_case_data(case_data)
                elif response.status == 404:
                    logger.warning(f"Case {case_id} not found in Exabeam")
                    return None
                else:
                    logger.error(f"Failed to fetch case {case_id}: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching case {case_id}: {e}")
            return None
    
    def _format_case_data(self, raw_case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format Exabeam case data to our standard format"""
        return {
            "case_id": raw_case_data.get("id") or raw_case_data.get("caseId"),
            "raw_data": {
                "events": raw_case_data.get("events", []),
                "detection_rule": raw_case_data.get("ruleName") or raw_case_data.get("detectionRule", ""),
                "rule_type": self._extract_rule_type(raw_case_data.get("ruleName", "")),
                "confidence": raw_case_data.get("confidence", 0.8),
                "priority": raw_case_data.get("priority", "MEDIUM"),
                "status": raw_case_data.get("status", "OPEN"),
                "created_at": raw_case_data.get("createdTime") or raw_case_data.get("timestamp"),
                "description": raw_case_data.get("description", ""),
                "entities": self._extract_entities_from_case(raw_case_data)
            },
            "retrieved_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _extract_rule_type(self, rule_name: str) -> str:
        """Extract rule type from rule name"""
        if not rule_name:
            return "unknown"
        
        rule_name_lower = rule_name.lower()
        if rule_name_lower.startswith("fact"):
            return "fact"
        elif rule_name_lower.startswith("profile"):
            return "profile"
        elif rule_name_lower.startswith("behavioral"):
            return "behavioral"
        elif rule_name_lower.startswith("anomaly"):
            return "anomaly"
        else:
            return "other"
    
    def _extract_entities_from_case(self, case_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract entities from Exabeam case data"""
        entities = []
        
        # Extract from events
        for event in case_data.get("events", []):
            # Extract IPs
            for ip_field in ["srcIp", "destIp", "clientIp", "serverIp"]:
                if ip_field in event and event[ip_field]:
                    entities.append({"type": "ip", "value": event[ip_field]})
            
            # Extract users
            for user_field in ["user", "username", "userId", "actor"]:
                if user_field in event and event[user_field]:
                    entities.append({"type": "user", "value": event[user_field]})
            
            # Extract domains/hostnames
            for domain_field in ["domain", "hostname", "dest", "target"]:
                if domain_field in event and event[domain_field]:
                    entities.append({"type": "domain", "value": event[domain_field]})
        
        # Remove duplicates
        unique_entities = []
        seen = set()
        for entity in entities:
            key = f"{entity['type']}:{entity['value']}"
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        return unique_entities
    
    def _get_mock_case_data(self, case_ids: List[str]) -> List[Dict[str, Any]]:
        """Generate mock case data for testing when API is unavailable"""
        mock_cases = []
        
        for case_id in case_ids:
            # Generate rule type based on case ID pattern
            rule_type = "fact" if "fact" in case_id.lower() else "profile" if "profile" in case_id.lower() else "other"
            
            mock_case = {
                "case_id": case_id,
                "raw_data": {
                    "events": [
                        {
                            "timestamp": "2025-08-30T10:30:00Z",
                            "source": "windows_security",
                            "event_id": 4624,
                            "srcIp": "192.168.1.100",
                            "user": "suspicious_user",
                            "details": f"Security event for case {case_id}"
                        },
                        {
                            "timestamp": "2025-08-30T10:32:00Z",
                            "source": "proxy_logs", 
                            "srcIp": "192.168.1.100",
                            "domain": "malicious.example.com",
                            "details": f"Network event for case {case_id}"
                        }
                    ],
                    "detection_rule": f"{rule_type}_detection_{case_id.split('-')[-1]}",
                    "rule_type": rule_type,
                    "confidence": 0.85,
                    "priority": "HIGH",
                    "status": "OPEN",
                    "created_at": "2025-08-30T10:30:00Z",
                    "description": f"Security incident detected in case {case_id}",
                    "entities": [
                        {"type": "ip", "value": "192.168.1.100"},
                        {"type": "user", "value": "suspicious_user"},
                        {"type": "domain", "value": "malicious.example.com"}
                    ]
                },
                "retrieved_at": datetime.now(timezone.utc).isoformat()
            }
            
            mock_cases.append(mock_case)
        
        logger.info(f"Generated {len(mock_cases)} mock cases for testing")
        return mock_cases
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None


# Global client instance
exabeam_client = ExabeamClient()
