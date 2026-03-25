"""
GraphQL utilities for Infinity Governance API
"""
import aiohttp
from fastapi import HTTPException
from app.config import DATAHUB_GRAPHQL_URL


async def execute_graphql_query(query: str, variables: dict = None):
    """
    Execute a GraphQL query against the DataHub GraphQL endpoint
    
    Args:
        query: GraphQL query string
        variables: Optional query variables dictionary
        
    Returns:
        Dictionary with the GraphQL response data
        
    Raises:
        HTTPException: If the GraphQL query returns errors
    """
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        async with session.post(
            DATAHUB_GRAPHQL_URL,
            json={"query": query, "variables": variables or {}}
        ) as response:
            result = await response.json()
            if "errors" in result:
                raise HTTPException(status_code=400, detail=result["errors"])
            return result.get("data", {})
