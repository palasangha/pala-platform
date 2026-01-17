"""
Structure Parser - Parses letter structure (salutation, body, closing, signature, attachments)
"""

import json
import logging
import re
import requests
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class StructureParser:
    """Parses letter structure using Ollama"""

    SALUTATION_PATTERNS = [
        r'^\s*(Dear|To|Hello|Greetings|Salutations|Sir|Madam|Mr\.|Mrs\.|Ms\.|Dr\.).*?[,:]',
        r'^\s*([A-Z][a-z]*(?:\s+[A-Z][a-z]*)*)\s*[,:]',
    ]

    CLOSING_PATTERNS = [
        r'(Sincerely|Yours\s+truly|Best\s+regards|Regards|Respectfully|Faithfully|Affectionately|Love|Your\s+friend)[,\s]*$',
        r'(With\s+(?:all\s+)?(?:good\s+)?wishes|Warmly|Cheers|Best)[,\s]*$',
    ]

    ATTACHMENT_PATTERNS = [
        r'(?:Enclosed|Attached|Enclosure|Enclosures|Annex|Annexure|Attachments?)[:\s]+(.+?)(?:\n|$)',
        r'(?:See|Find)\s+(?:attached|enclosed|below)[:\s]+(.+?)(?:\n|$)',
        r'(?:P\.S\.|PS)[:\s]+(.+?)(?:\n|$)',
    ]

    def __init__(self, ollama_host: str = 'http://ollama:11434', model: str = 'mixtral'):
        self.ollama_host = ollama_host
        self.model = model
        logger.info(f"StructureParser initialized with model {model}")

    async def extract_salutation(self, text: str) -> Dict[str, Any]:
        """Extract salutation from letter"""
        if not text:
            return {"salutation": "", "type": "unknown", "confidence": 0.0}

        # Regex-based extraction first
        for pattern in self.SALUTATION_PATTERNS:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                salutation = match.group(0).strip()
                return {
                    "salutation": salutation,
                    "type": self._classify_salutation_type(salutation),
                    "confidence": 0.8
                }

        # Fallback: use first line if it looks like a salutation
        lines = text.split('\n')
        if lines and len(lines[0]) > 0 and len(lines[0]) < 100:
            first_line = lines[0].strip()
            if any(word in first_line.lower() for word in ['dear', 'hello', 'greetings', 'sir', 'madam']):
                return {
                    "salutation": first_line,
                    "type": "formal",
                    "confidence": 0.6
                }

        return {"salutation": "", "type": "unknown", "confidence": 0.0}

    async def parse_body(self, text: str) -> Dict[str, Any]:
        """Parse letter body into paragraphs"""
        if not text:
            return {"body": [], "paragraph_count": 0, "average_paragraph_length": 0}

        # Remove salutation and closing
        body_text = self._extract_body_section(text)

        # Split into paragraphs by empty lines
        paragraphs = [p.strip() for p in body_text.split('\n\n') if p.strip()]

        if not paragraphs:
            # Fallback: split by newlines
            paragraphs = [p.strip() for p in body_text.split('\n') if p.strip() and len(p.strip()) > 20]

        avg_length = sum(len(p) for p in paragraphs) // len(paragraphs) if paragraphs else 0

        return {
            "body": paragraphs,
            "paragraph_count": len(paragraphs),
            "average_paragraph_length": avg_length
        }

    async def extract_closing(self, text: str) -> Dict[str, Any]:
        """Extract closing phrase from letter"""
        if not text:
            return {"closing": "", "type": "unknown", "confidence": 0.0}

        # Search from end of text
        text_lines = text.split('\n')

        for line in reversed(text_lines):
            line = line.strip()
            if not line or len(line) < 3:
                continue

            for pattern in self.CLOSING_PATTERNS:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    closing = match.group(1).strip()
                    return {
                        "closing": closing,
                        "type": self._classify_closing_type(closing),
                        "confidence": 0.85
                    }

            # Check if this line looks like a closing (short, on its own)
            if 3 < len(line) < 50 and not line.endswith('.'):
                potential_closing = ['Sincerely', 'Regards', 'Best wishes', 'Your friend']
                for closing_word in potential_closing:
                    if closing_word.lower() in line.lower():
                        return {
                            "closing": line,
                            "type": "formal",
                            "confidence": 0.6
                        }

        return {"closing": "", "type": "unknown", "confidence": 0.0}

    async def extract_signature(self, text: str) -> Dict[str, Any]:
        """Extract signature and signatory information"""
        if not text:
            return {"signature": "", "signatory_name": "", "title": "", "confidence": 0.0}

        # Find signature section (typically after closing and before end)
        lines = text.split('\n')
        signature_start = -1

        for i, line in enumerate(reversed(lines)):
            line = line.strip()
            # Look for common signature patterns
            if len(line) > 0 and len(line) < 100:
                # Check if it's a name (starts with capital, no punctuation)
                if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$', line):
                    signature_start = len(lines) - i - 1
                    break

        if signature_start >= 0:
            signature_lines = [l.strip() for l in lines[signature_start:] if l.strip()]
            signatory_name = signature_lines[0] if signature_lines else ""
            title = signature_lines[1] if len(signature_lines) > 1 else ""

            return {
                "signature": " ".join(signature_lines),
                "signatory_name": signatory_name,
                "title": title,
                "confidence": 0.7
            }

        return {"signature": "", "signatory_name": "", "title": "", "confidence": 0.0}

    async def identify_attachments(self, text: str) -> Dict[str, Any]:
        """Identify attachments and enclosures"""
        if not text:
            return {"attachments": [], "has_attachments": False}

        attachments = []

        for pattern in self.ATTACHMENT_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                description = match.group(1).strip() if len(match.groups()) > 0 else match.group(0)
                if description and len(description) > 2:
                    attachments.append({
                        "description": description,
                        "type": self._classify_attachment_type(description),
                        "mentioned_line": match.group(0)
                    })

        # Remove duplicates
        unique_attachments = []
        seen = set()
        for att in attachments:
            if att['description'] not in seen:
                unique_attachments.append(att)
                seen.add(att['description'])

        return {
            "attachments": unique_attachments,
            "has_attachments": len(unique_attachments) > 0
        }

    def _extract_body_section(self, text: str) -> str:
        """Extract main body section excluding salutation and closing"""
        lines = text.split('\n')

        # Find start of body (skip initial salutation)
        body_start = 0
        for i, line in enumerate(lines):
            if len(line.strip()) > 50:  # Body starts with longer lines
                body_start = i
                break

        # Find end of body (before signature/closing)
        body_end = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if len(line) > 20:
                body_end = i + 1
                break

        return '\n'.join(lines[body_start:body_end])

    def _classify_salutation_type(self, salutation: str) -> str:
        """Classify salutation as formal/informal/personal"""
        salutation_lower = salutation.lower()
        if any(word in salutation_lower for word in ['dear sir', 'dear madam', 'to whom', 'official']):
            return 'formal'
        elif any(word in salutation_lower for word in ['hello', 'hi', 'hey', 'dear friend']):
            return 'informal'
        else:
            return 'personal'

    def _classify_closing_type(self, closing: str) -> str:
        """Classify closing as formal/informal/personal"""
        closing_lower = closing.lower()
        if any(word in closing_lower for word in ['sincerely', 'respectfully', 'yours truly', 'official']):
            return 'formal'
        elif any(word in closing_lower for word in ['cheers', 'love', 'hugs', 'best']):
            return 'informal'
        else:
            return 'personal'

    def _classify_attachment_type(self, description: str) -> str:
        """Classify attachment type from description"""
        desc_lower = description.lower()
        if any(word in desc_lower for word in ['document', 'contract', 'agreement', 'form', 'pdf']):
            return 'document'
        elif any(word in desc_lower for word in ['image', 'photo', 'picture', 'jpg', 'png']):
            return 'image'
        elif any(word in desc_lower for word in ['list', 'schedule', 'table', 'data']):
            return 'reference'
        else:
            return 'other'
