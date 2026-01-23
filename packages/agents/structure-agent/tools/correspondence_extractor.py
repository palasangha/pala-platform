"""
Correspondence Extractor - Extracts sender, recipient, cc, date information
"""

import json
import logging
import re
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class CorrespondenceExtractor:
    """Extracts correspondence information from letters"""

    # Common date patterns
    DATE_PATTERNS = [
        r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
        r'(\d{1,2}/\d{1,2}/\d{4})',
        r'(\d{4}-\d{2}-\d{2})',
        r'(?:Date[:\s]+)?(\d{1,2}\s+\w+\s+\d{4})',
    ]

    def __init__(self, ollama_host: str = 'http://ollama:11434', model: str = 'mixtral'):
        self.ollama_host = ollama_host
        self.model = model
        logger.info("CorrespondenceExtractor initialized")

    async def extract(self, text: str) -> Dict[str, Any]:
        """Extract correspondence information from letter"""
        if not text:
            return self._default_correspondence()

        # Extract sender (usually in signature)
        sender = await self._extract_sender(text)

        # Extract recipient (usually in salutation)
        recipient = await self._extract_recipient(text)

        # Extract cc and bcc
        cc = await self._extract_cc(text)
        bcc = await self._extract_bcc(text)

        # Extract date
        date = self._extract_date(text)

        return {
            "correspondence": {
                "sender": sender,
                "recipient": recipient,
                "cc": cc,
                "bcc": bcc,
                "date": date
            }
        }

    async def _extract_sender(self, text: str) -> Dict[str, str]:
        """Extract sender information from signature"""
        lines = text.split('\n')
        sender = {"name": "", "title": "", "organization": ""}

        # Look for signature section (usually at end)
        for i in range(len(lines) - 1, max(0, len(lines) - 10), -1):
            line = lines[i].strip()

            # Check if line looks like a name
            if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$', line) and len(line) > 2:
                sender['name'] = line
                # Look at next lines for title/organization
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line[0].isupper():
                        sender['title'] = next_line
                    if i + 2 < len(lines):
                        org_line = lines[i + 2].strip()
                        if org_line and len(org_line) > 5:
                            sender['organization'] = org_line
                break

        # Try to extract from text patterns
        if not sender['name']:
            name_match = re.search(r'from:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text, re.IGNORECASE)
            if name_match:
                sender['name'] = name_match.group(1)

        return sender

    async def _extract_recipient(self, text: str) -> Dict[str, str]:
        """Extract recipient information from salutation"""
        recipient = {"name": "", "title": "", "organization": ""}

        # Look for salutation patterns
        lines = text.split('\n')
        for i, line in enumerate(lines[:5]):  # Check first 5 lines
            line_lower = line.lower()
            if any(word in line_lower for word in ['dear', 'hello', 'to', 'greetings']):
                # Extract name from salutation
                match = re.search(r'(?:Dear|Hello|To)\s+(?:(Mr|Mrs|Ms|Dr|Sir|Madam)\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', line, re.IGNORECASE)
                if match:
                    if match.group(1):
                        recipient['title'] = match.group(1)
                    recipient['name'] = match.group(2)
                break

        # Try to extract from text patterns
        if not recipient['name']:
            to_match = re.search(r'to:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text, re.IGNORECASE)
            if to_match:
                recipient['name'] = to_match.group(1)

        return recipient

    async def _extract_cc(self, text: str) -> List[Dict[str, str]]:
        """Extract CC recipients"""
        cc_list = []

        # Look for cc patterns
        cc_match = re.search(r'(?:CC|Cc|cc)[:\s]+(.+?)(?:\n|;|$)', text)
        if cc_match:
            cc_str = cc_match.group(1)
            # Split by comma or semicolon
            cc_names = re.split(r'[,;]', cc_str)
            for name in cc_names:
                name = name.strip()
                if name:
                    cc_list.append({"name": name})

        return cc_list

    async def _extract_bcc(self, text: str) -> List[Dict[str, str]]:
        """Extract BCC recipients"""
        bcc_list = []

        # Look for bcc patterns
        bcc_match = re.search(r'(?:BCC|Bcc|bcc)[:\s]+(.+?)(?:\n|;|$)', text)
        if bcc_match:
            bcc_str = bcc_match.group(1)
            # Split by comma or semicolon
            bcc_names = re.split(r'[,;]', bcc_str)
            for name in bcc_names:
                name = name.strip()
                if name:
                    bcc_list.append({"name": name})

        return bcc_list

    def _extract_date(self, text: str) -> str:
        """Extract date from letter"""
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return ""

    def _default_correspondence(self) -> Dict[str, Any]:
        """Return default correspondence structure"""
        return {
            "correspondence": {
                "sender": {"name": "", "title": "", "organization": ""},
                "recipient": {"name": "", "title": "", "organization": ""},
                "cc": [],
                "bcc": [],
                "date": ""
            }
        }
