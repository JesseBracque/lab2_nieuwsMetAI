from __future__ import annotations
import os
import time
import logging
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

COHERE_API_KEY = os.environ.get("COHERE_API_KEY")
logger = logging.getLogger(__name__)


class CohereClient:
    def __init__(self, api_key: Optional[str] = None, max_retries: int = 2):
        self.api_key = api_key or COHERE_API_KEY
        self.max_retries = max_retries
        self._client = None
        self._has_chat = False
        if self.api_key:
            try:
                import cohere

                self._client = cohere.Client(self.api_key)
                # detect chat support
                self._has_chat = hasattr(self._client, "chat") and hasattr(self._client.chat, "create")
            except Exception as e:
                logger.warning("Cohere client init failed: %s", e)
                self._client = None

    def _extract_text_from_response(self, resp):
        # Try several common shapes returned by SDKs
        try:
            # generations style
            gens = getattr(resp, "generations", None)
            if gens:
                return gens[0].text
        except Exception:
            pass
        try:
            # chat style: message or output
            msg = getattr(resp, "message", None)
            if msg:
                # message may be dict-like
                if isinstance(msg, dict):
                    return msg.get("content") or msg.get("text") or str(msg)
                return getattr(msg, "content", str(msg))
        except Exception:
            pass
        try:
            out = getattr(resp, "output", None)
            if out:
                if isinstance(out, (list, tuple)) and len(out) > 0:
                    first = out[0]
                    if isinstance(first, dict):
                        return first.get("content") or first.get("text") or str(first)
                    return getattr(first, "content", getattr(first, "text", str(first)))
        except Exception:
            pass
        try:
            # fallback to string
            return str(resp)
        except Exception:
            return ""

    def translate_and_rewrite(self, text: str, target_lang: str = "nl") -> dict | str:
        """Translate and rewrite using Cohere Chat if available.

        If the old Generate API is unavailable, or any error occurs, fall back to a deterministic mock.
        """
        if not text:
            return ""

        # no real client -> deterministic mock
        if not self._client:
            return f"[{target_lang.upper()} TRANSLATION - MOCK]\n" + text[:1000]

        # prefer Chat API if available
        if self._has_chat:
            try:
                prompt = (
                    f"Vertaal en herschrijf het volgende artikel naar het {target_lang} en verbeter leesbaarheid en grammatica."
                    f"\n\n{text}"
                )
                resp = self._client.chat.create(
                    model="command-xlarge-nightly",
                    messages=[
                        {"role": "system", "content": "Je bent een behulpzame vertaler en redacteur."},
                        {"role": "user", "content": prompt},
                    ],
                )
                text_out = self._extract_text_from_response(resp)
                meta = {"model": "command-xlarge-nightly"}
                # try to extract usage if present
                try:
                    usage = getattr(resp, "usage", None) or getattr(resp, "meta", None)
                    if usage:
                        meta["usage"] = usage
                except Exception:
                    pass
                return {"text": text_out, "meta": meta, "prompt": prompt}
            except Exception as e:  # pragma: no cover - runtime
                logger.warning("Cohere chat.create failed, falling back to mock: %s", e)

        # try legacy generate (may be removed) with retries; if it fails, fallback to mock
        attempt = 0
        while attempt <= self.max_retries:
            try:
                if hasattr(self._client, "generate"):
                    resp = self._client.generate(
                        model="command-xlarge-nightly",
                        prompt=f"Vertaal en herschrijf het volgende artikel naar het {target_lang} en verbeter leesbaarheid en grammatica.\n\n{str(text)}",
                        max_tokens=800,
                        temperature=0.3,
                    )
                    text_out = self._extract_text_from_response(resp)
                    meta = {"model": "generate-fallback"}
                    try:
                        usage = getattr(resp, "usage", None)
                        if usage:
                            meta["usage"] = usage
                    except Exception:
                        pass
                    return {"text": text_out, "meta": meta, "prompt": f"generate fallback: {str(text)[:200]}"}
                break
            except Exception as e:  # pragma: no cover - runtime
                # If API removed or 404-like errors, don't retry endlessly — fallback to mock
                msg = str(e)
                logger.warning("Cohere generate failed (attempt %d): %s", attempt, msg)
                if "Generate API was removed" in msg or getattr(e, "status_code", None) == 404:
                    logger.warning("Generate API removed; falling back to mock response")
                    return f"[{target_lang.upper()} TRANSLATION - MOCK]\n" + text[:1000]
                attempt += 1
                if attempt > self.max_retries:
                    logger.warning("Max retries reached for Cohere generate; falling back to mock")
                    return f"[{target_lang.upper()} TRANSLATION - MOCK]\n" + text[:1000]
                time.sleep(1 + attempt)

        # final fallback
        return f"[{target_lang.upper()} TRANSLATION - MOCK]\n" + text[:1000]

    def expand_article(self, text: str, target_lang: str = "nl", min_words: int = 350) -> dict | str:
        """Expand an article with extra background and context using Cohere Chat when available.

        If no real client is configured, returns a deterministic mock that appends a short
        'Achtergrond' section. Returns either a dict with text+meta or a str.
        """
        if not text:
            return ""

        # no real client -> deterministic mock enrichment
        if not self._client:
            extra = (
                f"\n\n[Achtergrond - MOCK]\n"
                f"Dit artikel is aangevuld met algemene context en mogelijke achtergronden. "
                f"Controleer bronnen voor de meest actuele stand van zaken."
            )
            return text + extra

        # prefer Chat API if available
        if self._has_chat:
            try:
                prompt = (
                    f"Breid onderstaande tekst betekenisvol uit naar het {target_lang}. "
                    f"Voeg feitelijke achtergrond, recente context en relevante uitleg toe. "
                    f"Vermijd speculatie en hallucinaties; vermeld geen feiten die niet algemeen bekend of verifieerbaar zijn. "
                    f"Doel: minimaal {min_words} woorden.\n\nTEKST:\n{text}"
                )
                resp = self._client.chat.create(
                    model="command-xlarge-nightly",
                    messages=[
                        {"role": "system", "content": "Je bent een nauwkeurige redacteur die feitelijke context toevoegt."},
                        {"role": "user", "content": prompt},
                    ],
                )
                text_out = self._extract_text_from_response(resp)
                meta = {"model": "command-xlarge-nightly", "task": "expand_article"}
                try:
                    usage = getattr(resp, "usage", None) or getattr(resp, "meta", None)
                    if usage:
                        meta["usage"] = usage
                except Exception:
                    pass
                return {"text": text_out, "meta": meta, "prompt": prompt}
            except Exception as e:
                logger.warning("Cohere expand_article failed, falling back to mock: %s", e)

        # fallback
        extra = (
            f"\n\n[Achtergrond - MOCK]\n"
            f"Dit artikel is aangevuld met algemene context en mogelijke achtergronden. "
            f"Controleer bronnen voor de meest actuele stand van zaken."
        )
        return text + extra


client = CohereClient()
