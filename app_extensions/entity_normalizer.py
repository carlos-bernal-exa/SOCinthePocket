"""
Entity Normalization Module with robust field mapping and validation.

This module provides clean, consistent entity extraction from diverse raw fields
to improve similarity search, graph upserts, and correlation accuracy.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set, Union
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv6Address, AddressValueError
import email.utils

logger = logging.getLogger(__name__)


@dataclass
class NormalizedEntity:
    """Represents a normalized entity with validation metadata."""
    type: str
    value: str
    original_field: str
    confidence: float
    validation_passed: bool
    metadata: Dict[str, Any] = None


class EntityNormalizer:
    """
    Robust entity extraction and normalization with field mapping fallbacks.
    """
    
    def __init__(self):
        # Field mapping configurations with fallback priorities
        self.user_field_map = [
            'user',
            'username',
            'user_name', 
            'email_address',
            'source_user_entity_id',
            'user_entities.email_address',
            'user_entities.username',
            'user_entity.name'
        ]
        
        self.host_field_map = [
            'src_host',
            'dest_host',
            'host',
            'hostname',
            'host_name',
            'device_entities.host_name',
            'device_entities.hostname',
            'endpoint.hostname',
            'computer_name'
        ]
        
        self.ip_field_map = [
            'src_ip',
            'dest_ip', 
            'ip',
            'ip_address',
            'source_ip',
            'destination_ip',
            'src_endpoint.ip',
            'dest_endpoint.ip',
            'endpoint.ip_address',
            'network.source_ip',
            'network.dest_ip'
        ]
        
        self.domain_field_map = [
            'domain',
            'dns_domain',
            'fqdn',
            'host_domain',
            'src_domain',
            'dest_domain'
        ]
        
        # Validation patterns
        self.ip_v4_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
        self.ip_v6_pattern = re.compile(r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$')
        self.fqdn_pattern = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$')
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.ued_prefix_pattern = re.compile(r'^UEM\d+\\(.+)$')  # UEM prefix pattern
    
    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Optional[Any]:
        """
        Get value from nested dictionary using dot notation.
        
        Args:
            data: Source dictionary
            field_path: Field path like 'user_entities.email_address'
            
        Returns:
            Value if found, None otherwise
        """
        try:
            keys = field_path.split('.')
            value = data
            
            for key in keys:
                if isinstance(value, list) and value:
                    # Handle arrays by taking first element
                    value = value[0]
                
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
                    
            return value
        except (KeyError, IndexError, TypeError):
            return None
    
    def _extract_field_with_fallbacks(self, data: Dict[str, Any], field_map: List[str]) -> Optional[str]:
        """
        Extract field value using fallback priority list.
        
        Args:
            data: Source data dictionary
            field_map: List of field names in priority order
            
        Returns:
            First found value, None if none found
        """
        for field in field_map:
            value = None
            
            # Try direct field access first
            if field in data:
                value = data[field]
            else:
                # Try nested field access
                value = self._get_nested_value(data, field)
            
            if value:
                # Handle different value types
                if isinstance(value, list) and value:
                    value = value[0]  # Take first element from arrays
                
                if isinstance(value, str) and value.strip():
                    return value.strip()
                elif not isinstance(value, str) and value:
                    return str(value).strip()
        
        return None
    
    def _validate_ip_address(self, ip_str: str) -> bool:
        """Validate IP address format."""
        try:
            # Try parsing as IPv4 or IPv6
            IPv4Address(ip_str)
            return True
        except AddressValueError:
            try:
                IPv6Address(ip_str)
                return True
            except AddressValueError:
                return False
    
    def _validate_hostname(self, hostname: str) -> bool:
        """Validate hostname/FQDN format."""
        if not hostname or len(hostname) > 253:
            return False
        
        # Check FQDN pattern
        return bool(self.fqdn_pattern.match(hostname.lower()))
    
    def _validate_email(self, email_str: str) -> bool:
        """Validate email address format."""
        return bool(self.email_pattern.match(email_str))
    
    def _normalize_user_value(self, value: str) -> str:
        """Normalize user value with UEM prefix handling."""
        # Handle UEM prefix (e.g., "UEM123\\username" -> "username")
        ued_match = self.ued_prefix_pattern.match(value)
        if ued_match:
            return ued_match.group(1)
        
        # Extract local part from email if it looks like email
        if '@' in value and self._validate_email(value):
            return value.split('@')[0]
        
        return value.lower().strip()
    
    def _normalize_host_value(self, value: str) -> str:
        """Normalize hostname value."""
        # Convert to lowercase and strip domain if needed
        normalized = value.lower().strip()
        
        # Remove common domain suffixes if this is just a hostname
        if '.' in normalized and not self._validate_ip_address(normalized):
            parts = normalized.split('.')
            if len(parts) > 2:  # Likely FQDN, keep as-is
                return normalized
            else:  # Might be hostname.domain, consider keeping full
                return normalized
        
        return normalized
    
    def _normalize_domain_value(self, value: str) -> str:
        """Normalize domain value."""
        return value.lower().strip().lstrip('.')
    
    def extract_users(self, data: Dict[str, Any]) -> List[NormalizedEntity]:
        """Extract and normalize user entities."""
        entities = []
        
        user_value = self._extract_field_with_fallbacks(data, self.user_field_map)
        if user_value:
            normalized_value = self._normalize_user_value(user_value)
            
            # Determine original field for traceability
            original_field = 'user'  # Default
            for field in self.user_field_map:
                if field in data or self._get_nested_value(data, field):
                    original_field = field
                    break
            
            entity = NormalizedEntity(
                type='user',
                value=normalized_value,
                original_field=original_field,
                confidence=0.9,
                validation_passed=len(normalized_value) > 0,
                metadata={'original_value': user_value}
            )
            entities.append(entity)
            logger.debug(f"Extracted user: {normalized_value} from {original_field}")
        
        return entities
    
    def extract_hosts(self, data: Dict[str, Any]) -> List[NormalizedEntity]:
        """Extract and normalize host entities."""
        entities = []
        seen_hosts = set()
        
        for field in self.host_field_map:
            host_value = None
            
            if field in data:
                host_value = data[field]
            else:
                host_value = self._get_nested_value(data, field)
            
            if host_value:
                if isinstance(host_value, list):
                    host_values = host_value
                else:
                    host_values = [host_value]
                
                for value in host_values:
                    if isinstance(value, str) and value.strip():
                        normalized_value = self._normalize_host_value(value.strip())
                        
                        # Avoid duplicates
                        if normalized_value not in seen_hosts:
                            seen_hosts.add(normalized_value)
                            
                            entity = NormalizedEntity(
                                type='host',
                                value=normalized_value,
                                original_field=field,
                                confidence=0.8,
                                validation_passed=self._validate_hostname(normalized_value),
                                metadata={'original_value': value.strip()}
                            )
                            entities.append(entity)
                            logger.debug(f"Extracted host: {normalized_value} from {field}")
        
        return entities
    
    def extract_ips(self, data: Dict[str, Any]) -> List[NormalizedEntity]:
        """Extract and normalize IP address entities."""
        entities = []
        seen_ips = set()
        
        for field in self.ip_field_map:
            ip_value = None
            
            if field in data:
                ip_value = data[field]
            else:
                ip_value = self._get_nested_value(data, field)
            
            if ip_value:
                if isinstance(ip_value, list):
                    ip_values = ip_value
                else:
                    ip_values = [ip_value]
                
                for value in ip_values:
                    if isinstance(value, str) and value.strip():
                        normalized_value = value.strip()
                        
                        # Avoid duplicates
                        if normalized_value not in seen_ips:
                            seen_ips.add(normalized_value)
                            
                            is_valid = self._validate_ip_address(normalized_value)
                            
                            entity = NormalizedEntity(
                                type='ip',
                                value=normalized_value,
                                original_field=field,
                                confidence=0.9 if is_valid else 0.5,
                                validation_passed=is_valid,
                                metadata={'original_value': value.strip()}
                            )
                            entities.append(entity)
                            logger.debug(f"Extracted IP: {normalized_value} from {field} (valid: {is_valid})")
        
        return entities
    
    def extract_domains(self, data: Dict[str, Any]) -> List[NormalizedEntity]:
        """Extract and normalize domain entities."""
        entities = []
        seen_domains = set()
        
        for field in self.domain_field_map:
            domain_value = self._extract_field_with_fallbacks(data, [field])
            
            if domain_value:
                normalized_value = self._normalize_domain_value(domain_value)
                
                # Avoid duplicates
                if normalized_value not in seen_domains:
                    seen_domains.add(normalized_value)
                    
                    is_valid = self._validate_hostname(normalized_value)
                    
                    entity = NormalizedEntity(
                        type='domain',
                        value=normalized_value,
                        original_field=field,
                        confidence=0.8 if is_valid else 0.5,
                        validation_passed=is_valid,
                        metadata={'original_value': domain_value}
                    )
                    entities.append(entity)
                    logger.debug(f"Extracted domain: {normalized_value} from {field} (valid: {is_valid})")
        
        return entities
    
    def normalize_from_summary(self, summary: Dict[str, Any]) -> Dict[str, List[NormalizedEntity]]:
        """
        Main entry point for entity normalization from case summary.
        
        Args:
            summary: Case summary data containing entity information
            
        Returns:
            Dict mapping entity type to list of normalized entities
        """
        normalized_entities = {
            'users': [],
            'hosts': [],
            'ips': [],
            'domains': []
        }
        
        try:
            # Extract each entity type
            normalized_entities['users'] = self.extract_users(summary)
            normalized_entities['hosts'] = self.extract_hosts(summary)
            normalized_entities['ips'] = self.extract_ips(summary)
            normalized_entities['domains'] = self.extract_domains(summary)
            
            # Log extraction summary
            total_entities = sum(len(entities) for entities in normalized_entities.values())
            valid_entities = sum(
                len([e for e in entities if e.validation_passed])
                for entities in normalized_entities.values()
            )
            
            logger.info(f"Normalized {total_entities} entities ({valid_entities} valid) from summary")
            
            return normalized_entities
            
        except Exception as e:
            logger.error(f"Entity normalization failed: {str(e)}")
            return normalized_entities
    
    def get_normalized_dict(self, summary: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Get normalized entities as simple dictionary for backward compatibility.
        
        Args:
            summary: Case summary data
            
        Returns:
            Dict mapping entity type to list of values
        """
        normalized = self.normalize_from_summary(summary)
        
        result = {}
        for entity_type, entities in normalized.items():
            # Only include valid entities
            valid_values = [e.value for e in entities if e.validation_passed]
            if valid_values:
                result[entity_type] = valid_values
        
        return result


# Legacy function for backward compatibility
def normalize_from_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Legacy function for backward compatibility.
    
    Args:
        summary: Case summary data
        
    Returns:
        Normalized entities dictionary
    """
    normalizer = EntityNormalizer()
    return normalizer.get_normalized_dict(summary)