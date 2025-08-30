class SIEMClient:
    async def query(self, event_filter: str, start: str, end: str, limit: int = 5000) -> dict:
        return {"count": 0, "events": []}
