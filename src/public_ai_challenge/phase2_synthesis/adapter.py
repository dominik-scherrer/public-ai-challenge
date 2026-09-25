"""Phase 2 Final Adapter: Gemeinde Synthesis + PublicAI Reviewer Validation."""

import json
import logging
from pathlib import Path
from typing import Any, Dict

import httpx
from pydantic_ai import Agent

from public_ai_challenge.core import SynthesisProtocol
from public_ai_challenge.core import ScoutResult, ServiceInventoryRecord
from public_ai_challenge.phase2_synthesis.agents import process_service_content, data_extraction_agent
from public_ai_challenge.phase2_synthesis.models import ScoutedService, ServiceProcessingDeps

logger = logging.getLogger(__name__)

reviewer_agent = Agent(
    model="openai:gpt-4o",
    system_prompt=(
        "You are a strict data provenance reviewer. "
        "Review the extracted JSON facts against the raw source Markdown fragments. "
        "If the JSON contains facts (e.g. fees, requirements, emails) that DO NOT exist in the source text, "
        "you MUST remove them from the JSON. Output only the corrected JSON. "
        "Do not invent or assume any information."
    ),
    retries=2
)

class FinalSynthesisAdapter(SynthesisProtocol):
    """Combines Gemeinde LLM synthesis with rigorous hallucination review."""

    def __init__(self, model_name: str = "openai:gpt-4o"):
        self.model_name = model_name

    async def synthesize(self, scout_result: ScoutResult, output_dir: str | Path) -> list[ServiceInventoryRecord]:
        logger.info("FinalSynthesisAdapter: Starting synthesis and review.")
        results = []
        
        async with httpx.AsyncClient() as client:
            deps = ServiceProcessingDeps(http_client=client, model_name=self.model_name)
    
            for scouted in scout_result.services:
                service = ScoutedService(
                    id=scouted.metadata.get("service_id", "unknown"),
                    name=scouted.name,
                    description=scouted.description,
                    available=scouted.available,
                    urls=scouted.urls
                )

                synthesized, raw_contents = await process_service_content(service, deps, output_dir=output_dir)
                
                if service.available:
                    extraction_prompt = (
                        f"Service: {service.name}\n"
                        f"Markdown:\n{synthesized.markdown}\n"
                    )
                    extraction_result = await data_extraction_agent.run(extraction_prompt, deps=deps, model=self.model_name)
                    extracted_data = extraction_result.output.json_data
                    
                    review_prompt = (
                        f"Source Text:\n{synthesized.markdown}\n\n"
                        f"Extracted JSON:\n{json.dumps(extracted_data, indent=2)}\n\n"
                        "Return the JSON with any unsupported facts removed."
                    )
                    review_result = await reviewer_agent.run(review_prompt, model=self.model_name)
                    
                    try:
                        clean_json = review_result.output.replace("```json", "").replace("```", "").strip()
                        reviewed_data = json.loads(clean_json)
                    except json.JSONDecodeError:
                        logger.warning("Reviewer failed to output valid JSON, falling back to unreviewed data.")
                        reviewed_data = extracted_data
                else:
                    reviewed_data = {}

                results.append(
                    ServiceInventoryRecord(
                        service_name=service.name,
                        markdown_content=synthesized.markdown,
                        inventory_data=reviewed_data,
                        source_urls=synthesized.source_urls,
                        inventory_path=None,
                        markdown_path=None
                    )
                )

        return results
