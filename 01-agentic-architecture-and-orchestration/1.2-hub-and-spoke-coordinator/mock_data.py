"""Mock data for the two subagents. Nothing to do here.

- SEARCH_INDEX feeds the web search subagent (through the web_search tool).
- DOCUMENTS feeds the document analysis subagent. The coordinator pulls the
  matching documents and pastes them into the subagent's prompt.

The data has gaps on purpose, so the refinement loop has something to fix:
  * tidal, wave, OTEC and fusion get only a thin one-line result for broad
    queries ("tidal energy"). Targeted queries ("tidal barrage projects",
    "fusion ignition milestone") return the detailed results.
  * No internal documents exist for tidal, wave, OTEC or fusion.
Figures are simplified for the exercise. Don't cite them as real statistics.
"""

# Each entry matches when every keyword group has at least one word in the query.
SEARCH_INDEX = [
    # --- mature / scaling: detailed results even for broad queries ---
    {"groups": [["solar", "photovoltaic", "pv"]],
     "title": "Global solar PV market review",
     "snippet": "Cumulative solar PV capacity passed ~1.6 TW in 2024; utility-scale PV is among the "
                "cheapest sources of new electricity. Crystalline silicon holds ~95% market share. "
                "Perovskite-silicon tandem cells have exceeded 33% efficiency in the lab. Main "
                "challenges: midday curtailment and supply-chain concentration."},
    {"groups": [["concentrated", "csp", "solar thermal"]],
     "title": "Concentrated solar power (CSP)",
     "snippet": "CSP uses mirrors to focus sunlight and drive a steam turbine. Global capacity is "
                "~7 GW. Molten-salt storage lets plants like Noor Ouarzazate (Morocco, 580 MW) keep "
                "generating after sunset. Costs are higher than PV, which has slowed growth."},
    {"groups": [["wind"]],
     "title": "Global wind energy outlook",
     "snippet": "Installed wind capacity is ~1 TW worldwide. Onshore wind is mature and low cost; "
                "offshore wind has higher capacity factors (40-50%) and turbines exceeding 15 MW. "
                "Floating foundations open deep-water sites (Hywind Scotland, 30 MW, 2017). "
                "Challenges: grid connection queues, permitting, and rising offshore costs."},
    {"groups": [["hydropower", "hydroelectric", "hydro power", "dam"]],
     "title": "Hydropower status report",
     "snippet": "Hydropower is the largest renewable source at ~1,400 GW; Three Gorges (China, "
                "22.5 GW) is the largest plant. Pumped-storage hydro provides over 90% of grid-scale "
                "storage. Challenges: drought-driven output drops and ecological impact of dams."},
    {"groups": [["geothermal"]],
     "title": "Geothermal power overview",
     "snippet": "Global geothermal capacity is ~16 GW, led by the US, Indonesia and the Philippines, "
                "with capacity factors above 80% (firm baseload). Enhanced geothermal systems (EGS) "
                "fracture hot dry rock using oil-and-gas drilling techniques; Fervo Energy's Utah "
                "project is a leading pilot. Main barrier: upfront drilling risk."},
    {"groups": [["biomass", "bioenergy", "biofuel", "biogas"]],
     "title": "Bioenergy in the energy mix",
     "snippet": "Bioenergy supplies ~150 GW of power capacity plus heat and transport fuels "
                "(ethanol, biodiesel, biogas). BECCS pairs combustion with carbon capture for "
                "potential negative emissions (Drax, UK, is piloting it). Sustainability depends on "
                "feedstock: residues and waste score well, dedicated energy crops often poorly."},
    # --- pilot / experimental: thin for broad queries, detail for targeted ones ---
    {"groups": [["tidal"]],
     "title": "Tidal energy - encyclopedia stub",
     "snippet": "Tidal energy is a form of ocean energy."},
    {"groups": [["tidal"], ["barrage", "stream", "lagoon", "turbine", "project", "capacity", "sihwa", "meygen", "rance"]],
     "title": "Tidal power projects and technologies",
     "snippet": "Tidal barrages (La Rance, France, 240 MW, 1966; Sihwa Lake, South Korea, 254 MW) "
                "trap water behind a dam. Tidal stream turbines such as MeyGen (Scotland) work "
                "like underwater wind turbines. Tides are highly predictable, but costs remain high."},
    {"groups": [["wave"]],
     "title": "Wave energy - encyclopedia stub",
     "snippet": "Wave energy captures energy from ocean surface waves."},
    {"groups": [["wave"], ["converter", "oscillating", "mutriku", "device", "project", "absorber"]],
     "title": "Wave energy converters",
     "snippet": "Designs include oscillating water columns (Mutriku, Spain, ~300 kW), point "
                "absorbers and attenuators. Wave energy is still pre-commercial; survivability "
                "in storms is the main engineering challenge."},
    {"groups": [["ocean thermal", "otec"]],
     "title": "OTEC - encyclopedia stub",
     "snippet": "Ocean thermal energy conversion uses the temperature difference in seawater."},
    {"groups": [["ocean thermal", "otec"], ["pilot", "plant", "hawaii", "makai", "project", "status"]],
     "title": "OTEC pilot plants",
     "snippet": "OTEC needs a ~20 C difference between surface and deep water, so it only works in "
                "the tropics. Makai's 100 kW plant in Hawaii (2015) is the largest grid-connected "
                "demo. Low efficiency (~3%) and costly deep-water pipes keep it pre-commercial."},
    {"groups": [["fusion"]],
     "title": "Fusion energy - encyclopedia stub",
     "snippet": "Fusion is the process that powers the sun."},
    {"groups": [["fusion"], ["iter", "tokamak", "ignition", "nif", "stellarator", "milestone", "commercial", "status", "progress"]],
     "title": "Fusion energy progress",
     "snippet": "In Dec 2022 the US National Ignition Facility achieved ignition (3.15 MJ out from "
                "2.05 MJ of laser energy). ITER, a large tokamak in France, is under construction. "
                "Private firms are pursuing compact tokamaks and stellarators; commercial power "
                "is not expected before the late 2030s at the earliest."},
    # --- cross-cutting ---
    {"groups": [["storage", "battery", "batteries"]],
     "title": "Grid storage for renewables",
     "snippet": "Lithium-ion battery storage deployment is growing fast; 4-hour systems dominate. "
                "Long-duration options (iron-air, flow batteries) are in early deployment."},
    {"groups": [["hydrogen"]],
     "title": "Green hydrogen",
     "snippet": "Green hydrogen is produced by electrolysis powered by renewables. It is an "
                "energy carrier rather than a primary source; <1% of hydrogen is green today. "
                "Target uses: steel, ammonia, shipping fuel."},
]


DOCUMENTS = {
    "solar": "INTERNAL REPORT - Solar (2025): Module prices fell ~50% between 2022 and 2024. "
             "Key risks: supply-chain concentration, grid curtailment at midday peaks.",
    "wind": "INTERNAL REPORT - Wind (2025): Offshore project costs rose 20-40% since 2021 due to "
            "interest rates and supply-chain issues; several projects were cancelled or re-bid.",
    "geothermal": "INTERNAL REPORT - Geothermal (2025): Upfront drilling risk is the main barrier; "
                  "EGS pilot results in Utah and Nevada show commercially promising flow rates.",
    "biomass": "INTERNAL REPORT - Bioenergy (2025): Lifecycle emissions vary widely by feedstock; "
               "forestry residues score well, dedicated energy crops often poorly.",
    "hydro": "INTERNAL REPORT - Hydropower (2025): Droughts cut output in several regions; "
             "new growth is concentrated in pumped storage rather than new dams.",
    "storage": "INTERNAL REPORT - Storage (2025): 4-hour lithium-ion batteries dominate new "
               "installs; long-duration storage (iron-air, flow batteries) is in early deployment.",
    # No documents for tidal, wave, OTEC or fusion, on purpose.
}

# Alternative words the coordinator may use in a subtopic name
_DOC_ALIASES = {
    "solar": ["solar", "photovoltaic"],
    "wind": ["wind"],
    "geothermal": ["geothermal"],
    "biomass": ["biomass", "bioenergy", "biofuel"],
    "hydro": ["hydropower", "hydroelectric", "hydro "],
    "storage": ["storage", "batter"],
}


def search(query: str) -> list[dict]:
    """Return every entry whose keyword groups all match the query."""
    q = query.lower()
    hits = [
        {"title": e["title"], "snippet": e["snippet"]}
        for e in SEARCH_INDEX
        if all(any(word in q for word in group) for group in e["groups"])
    ]
    return hits or [{"title": "No results", "snippet": f"No results found for '{query}'."}]


def get_documents(subtopic: str) -> list[str]:
    """Return the internal documents relevant to a subtopic name (may be empty)."""
    s = subtopic.lower() + " "
    return [DOCUMENTS[key] for key, words in _DOC_ALIASES.items() if any(w in s for w in words)]
