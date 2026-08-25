# memorandums/ai_engine/extractors.py

import os
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import anthropic
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_model = None


def _get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _get_claude_client():
    from django.conf import settings
    api_key = getattr(settings, "CLAUDE_API_KEY", None) or os.getenv("CLAUDE_API_KEY")
    if not api_key:
        raise ValueError("CLAUDE_API_KEY is not configured.")
    return anthropic.Anthropic(api_key=api_key)


def _build_property_context_header(property_data: dict) -> str:
    if not property_data:
        return ""
    return (
        "=== PROPERTY PROFILE ===\n"
        f"Property Name: {property_data.get('property_name', 'N/A')}\n"
        f"Address: {property_data.get('property_address', 'N/A')}\n"
        f"Property Type: {property_data.get('property_type', 'Commercial / Hospitality')}\n"
        f"Units / Keys: {property_data.get('number_of_units', 'N/A')}\n"
        f"Rentable Area: {property_data.get('rentable_area', 'N/A')} SF\n"
        f"Year Built: {property_data.get('year_built', 'N/A')}\n"
        f"Year Renovated: {property_data.get('year_renovated', 'N/A')}\n"
        f"Occupancy Rate: {property_data.get('occupancy', 'N/A')}%\n"
        f"Parking Spaces: {property_data.get('parking_spaces', 'N/A')}\n"
        f"Coordinates: Lat {property_data.get('latitude', 'N/A')}, Lng {property_data.get('longitude', 'N/A')}\n"
        "========================\n"
    )


GLOBAL_MEMORANDUM_GUIDELINES = (
    "You are a Senior Commercial Real Estate Analyst creating a formal, publication-grade Offering Memorandum (OM).\n"
    "STRICT EXECUTION RULES:\n"
    "1. Write the section content directly in professional, institutional investment memorandum markdown format (with clean headings, polished prose, and structured bullet points).\n"
    "2. NEVER output conversational filler, refusals, questions, disclaimers about missing files, apologies, or meta-commentary (e.g. NEVER say 'I appreciate your request', 'Context mismatch', 'What is missing', 'Please provide more info', or present options like 'Option A/B').\n"
    "3. Combine the Property Profile (exact name, location, address, asset type, scale) with any provided document excerpts and your deep real estate industry knowledge to synthesize a comprehensive, realistic, and highly compelling investment memo section.\n"
    "4. Always tailor your analysis to the specific property type and location (e.g. for a hotel/hospitality asset, analyze guest keys, meeting/banquet spaces, ADR/RevPAR, corporate/leisure demand, international airport and city transit connectivity).\n"
)


# ---------------------------------------------------------------------------
# Section Registries
# ---------------------------------------------------------------------------

TEXT_SECTIONS = {
    "executive_summary": (
        "executive summary investment highlights thesis overview financial highlights",
        (
            "Draft a comprehensive Executive Summary. Present an institutional-grade investment overview "
            "covering the asset's strategic positioning, key operating and physical highlights, competitive advantages, "
            "stable cash flow potential, and long-term value-creation thesis."
        ),
    ),
    "property_overview": (
        "property description architectural specifications floor plan amenities units area structure",
        (
            "Write a detailed Property Overview section. Describe the physical asset, architectural quality, "
            "room/unit configuration, building specifications, facilities (e.g., conference facilities, dining, wellness, parking), "
            "and overall operational condition."
        ),
    ),
    "property_highlights": (
        "property highlights competitive advantages key features selling points asset strengths",
        (
            "Generate a bulleted Property Highlights section (6 to 8 strong, impactful bullet points). "
            "Focus on premier location, brand value, institutional-grade build quality, modern amenities, "
            "diverse revenue streams, and high guest/tenant appeal."
        ),
    ),
    "area_overview": (
        "area location city neighborhood region economy employment infrastructure transit",
        (
            "Write an in-depth Area Overview. Detail the surrounding city and submarket (based on the property address/city), "
            "regional economic drivers, employment base, international connectivity (e.g., proximity to airport and expressways), "
            "and long-term commercial growth trends."
        ),
    ),
    "area_highlights": (
        "area highlights neighborhood transit airport accessibility corporate hubs landmarks amenities",
        (
            "Provide a detailed Area Highlights section in bullet-point format. Emphasize transit connectivity "
            "(international airport, transit arterial roads, expressways), proximity to commercial and corporate hubs, "
            "diplomatic zones, convention centers, and major urban landmarks in the area."
        ),
    ),
    "market_summary": (
        "market summary vacancy occupancy rent rates hospitality submarket demand supply trends",
        (
            "Write a rigorous Market Summary analyzing the local submarket dynamics. Cover sector-specific supply and "
            "demand fundamentals (e.g., hospitality/commercial performance, business travel & tourism inflow, corporate event demand, "
            "occupancy trends, and new pipeline constraints)."
        ),
    ),
    "area_amenities": (
        "area amenities restaurants shopping entertainment parks business centers retail",
        (
            "Write a comprehensive Area Amenities section. Detail the retail, dining, corporate business parks, "
            "recreational, convention, and cultural amenities surrounding the property location that enhance its guest, tenant, and visitor appeal."
        ),
    ),
    "sponsorship": (
        "sponsorship ownership management hospitality brand track record stewardship operations",
        (
            "Write a professional Sponsorship & Management section. Highlight the institutional ownership and professional "
            "management standards, adherence to international hospitality/real estate best practices, brand affiliation "
            "(e.g., Radisson Hotel Group standards), operational excellence, and asset stewardship."
        ),
    ),
    "disclaimer": (
        "disclaimer confidentiality offering memorandum legal notice due diligence non reliance",
        (
            "Draft a formal, institutional Commercial Real Estate Offering Memorandum Disclaimer. Cover confidentiality obligations, "
            "reliance on independent investor due diligence, limitation of liability, and forward-looking statements."
        ),
    ),
}

TABLE_SECTIONS = {
    "financing_summary": (
        "financing loan terms LTV interest rate debt service loan amount lender amortization",
        (
            "Extract or structure a complete Financing Summary table with standard loan and capital structure metrics "
            "(e.g., Indicative Loan Amount, Loan-to-Value (LTV), Interest Rate, Amortization, Term, Debt Service Coverage Ratio, "
            "Current NOI, Projected NOI). If explicit loan terms are not specified in the context, provide standard underwriting "
            "benchmark rows with clean realistic values/estimates based on the property scale."
        ),
    ),
    "financial_analysis": (
        "financial analysis operating statement revenue expenses departmental income NOI cash flow",
        (
            "Extract or structure an Annual Operating Statement / Financial Summary table. Include rows for Revenues "
            "(Room Revenue / Base Rent, F&B / Banquet Revenue, Other Services), Departmental & Operating Expenses, "
            "Total Operating Expenses, and Net Operating Income (NOI). Include appropriate columns "
            "(e.g., Line Item, Historical Year, Current Year, Year 1 Pro Forma)."
        ),
    ),
    "sales_comparables": (
        "sales comparables recent transactions comparable properties price per unit cap rate",
        (
            "Extract or generate a structured Sales Comparables table for institutional / benchmark assets in this market tier. "
            "Columns must be: ['Property Name', 'Asset Type', 'Location', 'Sale Period', 'Keys / Units', 'Sale Price / Est.', 'Price Per Unit']. "
            "Provide 3-4 representative comparable rows."
        ),
    ),
    "lease_comparables": (
        "lease comparables rental rates room rates tariff corporate rates lease terms",
        (
            "Extract or generate a structured Rate / Lease Comparables table for peer assets or tenant categories in this submarket. "
            "Columns must be: ['Property / Unit Tier', 'Category', 'Average Rate / Rent', 'Term / Frequency', 'Market Comparison']. "
            "Provide 3-4 relevant comparable rows."
        ),
    ),
}

SECTION_ORDER = [
    "property_information",
    "executive_summary",
    "property_overview",
    "property_highlights",
    "area_overview",
    "area_highlights",
    "market_summary",
    "financing_summary",
    "financial_analysis",
    "sales_comparables",
    "lease_comparables",
    "area_amenities",
    "sponsorship",
    "disclaimer",
]

SECTION_LABELS = {
    "property_information": "Property Information",
    "executive_summary": "Executive Summary",
    "property_overview": "Property Overview",
    "property_highlights": "Property Highlights",
    "area_overview": "Area Overview",
    "area_highlights": "Area Highlights",
    "market_summary": "Market Summary",
    "financing_summary": "Financing Summary",
    "financial_analysis": "Financial Analysis",
    "sales_comparables": "Sales Comparables",
    "lease_comparables": "Lease Comparables",
    "area_amenities": "Area Amenities",
    "sponsorship": "Sponsorship",
    "disclaimer": "Disclaimer",
}


# ---------------------------------------------------------------------------
# Fallback Tables
# ---------------------------------------------------------------------------

def _get_default_empty_table(section_key: str) -> dict:
    defaults = {
        "financing_summary": {
            "columns": ["Line Item", "Value"],
            "rows": [
                ["Loan Amount", "Subject to Underwriting"],
                ["LTV", "65.0% - 75.0%"],
                ["Interest Rate", "Competitive Market Rate"],
                ["Amortization", "25 - 30 Years"],
                ["Term", "5 - 10 Years"],
                ["Debt Service Coverage Ratio (DSCR)", "1.30x - 1.45x"],
                ["Current NOI", "Available upon request"],
                ["Projected NOI", "Available upon request"],
            ],
        },
        "financial_analysis": {
            "columns": ["Operating Line Item", "Historical (Year 1)", "Current Year", "Year 1 Pro Forma"],
            "rows": [
                ["Gross Operating Revenue", "$ -", "$ -", "$ -"],
                ["Departmental & Direct Expenses", "$ -", "$ -", "$ -"],
                ["Gross Operating Profit (GOP)", "$ -", "$ -", "$ -"],
                ["Undistributed Operating Expenses", "$ -", "$ -", "$ -"],
                ["Management & Franchise Fees", "$ -", "$ -", "$ -"],
                ["Fixed Charges (Taxes & Insurance)", "$ -", "$ -", "$ -"],
                ["Net Operating Income (NOI)", "$ -", "$ -", "$ -"],
            ],
        },
        "sales_comparables": {
            "columns": ["Property Name", "Asset Type", "Location", "Sale Period", "Keys / Units", "Sale Price", "Price / Unit"],
            "rows": [
                ["Comparable Asset 1", "Hospitality / Commercial", "Primary Submarket", "Recent", "200 - 350", "Market Standard", "$ / Key"],
                ["Comparable Asset 2", "Hospitality / Commercial", "Airport Corridor", "Recent", "150 - 250", "Market Standard", "$ / Key"],
                ["Comparable Asset 3", "Hospitality / Commercial", "Business District", "Recent", "250 - 400", "Market Standard", "$ / Key"],
            ],
        },
        "lease_comparables": {
            "columns": ["Property / Unit Tier", "Category", "Avg Rate / Rent", "Term / Frequency", "Market Comparison"],
            "rows": [
                ["Standard / Deluxe Keys", "Guest Rooms", "Market Benchmark", "Daily", "Competitive Tier 1"],
                ["Executive Suites", "Premium Suites", "Market Benchmark", "Daily / Extended", "Competitive Tier 1"],
                ["Meeting & Banquet Space", "Events & Conference", "Market Benchmark", "Per Event / Day", "Prime Tier"],
            ],
        },
    }
    return defaults.get(section_key, {"columns": ["Line Item", "Value"], "rows": []})


# ---------------------------------------------------------------------------
# Core extraction functions
# ---------------------------------------------------------------------------

def extract_text_section_from_context(
    section_key: str, context: str, custom_instruction: str = "", property_data: dict = None
) -> str:
    """Invokes Claude on prepared context (thread-safe)."""
    if section_key not in TEXT_SECTIONS:
        raise ValueError(f"'{section_key}' is not a valid text section.")

    _, base_prompt = TEXT_SECTIONS[section_key]
    prop_header = _build_property_context_header(property_data)

    system_prompt = (
        f"{GLOBAL_MEMORANDUM_GUIDELINES}\n\n"
        f"SECTION GOAL: {base_prompt}\n\n"
        f"{prop_header}\n"
    )
    if custom_instruction and custom_instruction.strip():
        system_prompt += (
            f"\nUSER REGENERATION INSTRUCTION — follow this closely while maintaining a professional memorandum tone: "
            f"{custom_instruction.strip()}\n"
        )
    if context:
        system_prompt += f"\nEXTRACTED DOCUMENT CONTEXT:\n{context}\n"
    else:
        system_prompt += "\nNOTE: Rely on the Property Profile details and your professional real estate domain knowledge to generate this section."

    client = _get_claude_client()
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Write the {SECTION_LABELS.get(section_key, section_key)} section for this Offering Memorandum."}],
            extra_body={"temperature": 0.3},
        )
        return response.content[0].text.strip()
    except Exception as exc:
        logger.error("Error generating text section %s: %s", section_key, exc)
        return ""


def extract_table_section_from_context(
    section_key: str, context: str, property_data: dict = None
) -> dict:
    """Invokes Claude on prepared context to extract/synthesize table (thread-safe)."""
    if section_key not in TABLE_SECTIONS:
        raise ValueError(f"'{section_key}' is not a valid table section.")

    _, extraction_prompt = TABLE_SECTIONS[section_key]
    prop_header = _build_property_context_header(property_data)

    system_prompt = (
        f"{GLOBAL_MEMORANDUM_GUIDELINES}\n\n"
        f"TASK: Generate the structured table for '{SECTION_LABELS.get(section_key, section_key)}'.\n"
        f"{extraction_prompt}\n\n"
        "OUTPUT FORMAT REQUIREMENT:\n"
        "You MUST return ONLY a valid, parseable JSON object. Do not include markdown code fences, backticks, or any conversational text before or after the JSON.\n"
        "Shape:\n"
        "{\n"
        '  "columns": ["Col 1", "Col 2", ...],\n'
        '  "rows": [\n'
        '    ["Val 1", "Val 2", ...],\n'
        '    ...\n'
        "  ]\n"
        "}\n\n"
        f"{prop_header}\n"
        f"DOCUMENT CONTEXT:\n{context if context else 'No document files provided; use property profile and market standards.'}"
    )

    client = _get_claude_client()
    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Generate the {section_key} table in strict JSON format."}],
            extra_body={"temperature": 0.0},
        )
        raw = response.content[0].text.strip()
    except Exception as exc:
        logger.error("Error calling Claude for table section %s: %s", section_key, exc)
        return _get_default_empty_table(section_key)

    # Safe JSON extraction between first '{' and last '}'
    try:
        start_idx = raw.find('{')
        end_idx = raw.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
            json_str = raw[start_idx:end_idx+1]
            data = json.loads(json_str)
            cols = data.get("columns", [])
            rows = data.get("rows", [])
            clean_rows = []
            for r in rows:
                if isinstance(r, list):
                    clean_rows.append([str(c) if c is not None else "" for c in r])
                elif isinstance(r, dict):
                    clean_rows.append([str(r.get(c, "")) for c in cols])
            if cols and clean_rows:
                return {
                    "columns": [str(c) for c in cols],
                    "rows": clean_rows,
                }
    except Exception as e:
        logger.warning("Failed to parse JSON for table %s: %s", section_key, e)

    return _get_default_empty_table(section_key)


def extract_text_section(
    vector_store, section_key: str, custom_instruction: str = "", property_data: dict = None
) -> str:
    """Helper for single section regeneration."""
    query, _ = TEXT_SECTIONS[section_key]
    chunks = []
    if vector_store and vector_store.index.ntotal > 0:
        embedding = _get_embedding_model().encode([query])[0].tolist()
        chunks = vector_store.search(embedding, top_k=8)
    context = "\n\n".join(chunks)
    return extract_text_section_from_context(section_key, context, custom_instruction, property_data)


def extract_table_section(vector_store, section_key: str, property_data: dict = None) -> dict:
    """Helper for single table extraction."""
    query, _ = TABLE_SECTIONS[section_key]
    chunks = []
    if vector_store and vector_store.index.ntotal > 0:
        embedding = _get_embedding_model().encode([query])[0].tolist()
        chunks = vector_store.search(embedding, top_k=8)
    context = "\n\n".join(chunks)
    return extract_table_section_from_context(section_key, context, property_data)


def extract_all_sections(vector_store, property_data: dict) -> dict:
    """
    Extract all 14 sections with pre-computed vector searches and parallel Claude API requests.
    """
    results = {}

    # 1. property_information (formatted from property_data)
    results["property_information"] = {
        "type": "text",
        "content": (
            f"Property Name: {property_data.get('property_name', 'N/A')}\n"
            f"Address: {property_data.get('property_address', 'N/A')}\n"
            f"Property Type: {property_data.get('property_type', 'N/A')}\n"
            f"Number of Units / Keys: {property_data.get('number_of_units', 'N/A')}\n"
            f"Rentable Area: {property_data.get('rentable_area', 'N/A')} SF\n"
            f"Year Built: {property_data.get('year_built', 'N/A')}\n"
            f"Year Renovated: {property_data.get('year_renovated', 'N/A')}\n"
            f"Occupancy: {property_data.get('occupancy', 'N/A')}%\n"
            f"Parking Spaces: {property_data.get('parking_spaces', 'N/A')}\n"
            f"Latitude: {property_data.get('latitude', 'N/A')}\n"
            f"Longitude: {property_data.get('longitude', 'N/A')}"
        ),
    }

    # 2. Main thread: Pre-search all vector embeddings
    embedding_model = _get_embedding_model()
    
    text_keys = list(TEXT_SECTIONS.keys())
    text_queries = [TEXT_SECTIONS[k][0] for k in text_keys]
    
    table_keys = list(TABLE_SECTIONS.keys())
    table_queries = [TABLE_SECTIONS[k][0] for k in table_keys]

    if vector_store and vector_store.index.ntotal > 0:
        text_embs = embedding_model.encode(text_queries)
        all_text_chunks = vector_store.batch_search([e.tolist() for e in text_embs], top_k=8)

        table_embs = embedding_model.encode(table_queries)
        all_table_chunks = vector_store.batch_search([e.tolist() for e in table_embs], top_k=8)
    else:
        all_text_chunks = [[] for _ in text_keys]
        all_table_chunks = [[] for _ in table_keys]

    # Map prepared contexts
    text_contexts = {k: "\n\n".join(chunks) for k, chunks in zip(text_keys, all_text_chunks)}
    table_contexts = {k: "\n\n".join(chunks) for k, chunks in zip(table_keys, all_table_chunks)}

    # 3. ThreadPool for parallel network requests to Claude API
    def _run_text(key):
        content = extract_text_section_from_context(key, text_contexts[key], property_data=property_data)
        return key, {"type": "text", "content": content}

    def _run_table(key):
        table_dict = extract_table_section_from_context(key, table_contexts[key], property_data=property_data)
        return key, {"type": "table", "content": table_dict}

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for key in text_keys:
            futures.append(executor.submit(_run_text, key))
        for key in table_keys:
            futures.append(executor.submit(_run_table, key))

        for future in as_completed(futures):
            key, section_res = future.result()
            results[key] = section_res

    return results
