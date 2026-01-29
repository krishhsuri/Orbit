"""
LLM Fallback Client (Groq)
Handles ambiguous emails that locally failed classification.
"""

import json
import logging
from typing import Dict, Any, Optional

from app.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)


class GroqClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        if self.api_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
            except ImportError:
                logger.warning("Groq library not installed")

    async def extract_job_details(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract structured job details from text using Groq LLM.
        """
        if not self.client:
            return None

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this email text:\n\n{text[:1500]}",
                    }
                ],
                model="llama3-8b-8192",
                temperature=0.1,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            
            result_json = chat_completion.choices[0].message.content
            return json.loads(result_json)
            
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return None
