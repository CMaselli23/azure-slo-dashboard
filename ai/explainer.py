import httpx
import logging
from app.config import config
from slo.calculator import SLOStatus

logger = logging.getLogger(__name__)

async def explain_slo_status(slo_status: SLOStatus) -> str:
    """
    Uses Claude via OpenRouter to explain the current SLO status
    in plain English with recommended actions.
    
    SRE concept: AIOps — using AI to reduce cognitive load on
    on-call engineers by translating raw metrics into actionable
    insights. This is the pattern companies like PagerDuty and
    Datadog are building into their products right now.
    """
    if not config.OPENROUTER_API_KEY:
        return "AI explainer not configured — set OPENROUTER_API_KEY in .env"

    # Build a structured prompt with the SLO data
    prompt = f"""You are a senior SRE analyst. Analyze this SLO status report and provide clear guidance.

SERVICE SLO STATUS:
- SLO Type: {slo_status.slo_name.upper()}
- Target: {slo_status.target_pct}%
- Current: {slo_status.current_pct}%
- SLO Met: {slo_status.slo_met}
- Error Budget Total: {slo_status.error_budget_total_pct}%
- Error Budget Consumed: {slo_status.error_budget_consumed_pct}%
- Error Budget Remaining: {slo_status.error_budget_remaining_pct}%
- Burn Rate: {slo_status.burn_rate}x
- Status: {slo_status.status.upper()}
- Total Requests: {slo_status.total_requests}
- Total Errors/Violations: {slo_status.total_errors}

Provide exactly this structure:
**Summary:** One sentence describing the current situation.
**Risk Level:** Low / Medium / High / Critical
**What This Means:** 2-3 sentences in plain English for a non-technical stakeholder.
**Recommended Actions:** 3 bullet points of specific, actionable steps for the on-call engineer.
**Deployment Policy:** Should new deployments be allowed? Yes / Freeze / Rollback required."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/azure-slo-dashboard",
                },
                json={
                    "model": config.OPENROUTER_MODEL,
                    "max_tokens": 500,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a senior SRE. Be concise, specific, and actionable. Use the exact output format requested."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    except httpx.TimeoutException:
        logger.error("OpenRouter API timeout")
        return "AI explainer timed out — check OpenRouter API status"
    except httpx.HTTPStatusError as e:
        logger.error(f"OpenRouter API error: {e.response.status_code}")
        return f"AI explainer error: {e.response.status_code}"
    except Exception as e:
        logger.error(f"Unexpected AI explainer error: {e}")
        return f"AI explainer unavailable: {str(e)}"