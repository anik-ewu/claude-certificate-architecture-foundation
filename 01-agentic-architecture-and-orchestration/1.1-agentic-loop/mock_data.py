"""Mock search index for the web_search stub.

The facts are about a made-up company on purpose. Claude can't know them,
so it has to call web_search before it can calculate anything.
"""

MOCK_SEARCH_INDEX = {
    "nimbus robotics revenue": [
        {
            "title": "Nimbus Robotics FY2025 annual report",
            "snippet": "Nimbus Robotics reported total revenue of $48.6 million for fiscal year 2025.",
        }
    ],
    "nimbus robotics employees": [
        {
            "title": "Nimbus Robotics - About us",
            "snippet": "Nimbus Robotics employs 312 people across 3 offices.",
        }
    ],
    "nimbus robotics founded": [
        {
            "title": "Nimbus Robotics - Company history",
            "snippet": "Nimbus Robotics was founded in 2014 in Tallinn, Estonia.",
        }
    ],
}


def search(query: str) -> list[dict]:
    """Return results whose key words all appear in the query, or a no-results marker."""
    q = query.lower()
    for key, results in MOCK_SEARCH_INDEX.items():
        if all(word in q for word in key.split()):
            return results
    return [{"title": "No results", "snippet": f"No results found for '{query}'."}]
