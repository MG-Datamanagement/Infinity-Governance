"""
Dashboard and utility endpoints
"""
import time
import aiohttp
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.config import DATAHUB_GRAPHQL_URL
from app.utils import execute_graphql_query

router = APIRouter(tags=["dashboard"])


# Health check
@router.get("/health")
async def health_check():
    """Check API health status"""
    return {"status": "healthy", "timestamp": int(time.time() * 1000)}


# Get Corp Users for dropdown
@router.get("/corp-users")
async def get_corp_users():
    """Get list of corp users for owner dropdown"""
    query = """
    query {
      search(input: {
        type: CORP_USER
        query: "*"
        start: 0
        count: 50
      }) {
        total
        searchResults {
          entity {
            ... on CorpUser {
              urn
              type
              username
              properties {
                displayName
              }
            }
          }
        }
      }
    }
    """
    data = await execute_graphql_query(query)
    users = []
    search_results = data.get("search", {}).get("searchResults", [])
    for result in search_results:
        entity = result.get("entity", {})
        users.append({
            "urn": entity.get("urn"),
            "username": entity.get("username"),
            "displayName": entity.get("properties", {}).get("displayName", ""),
            "type": entity.get("type")
        })
    return {"status": "success", "users": users}


# Get Ownership Types for dropdown
@router.get("/ownership-types")
async def get_ownership_types():
    """Get list of ownership types for dropdown"""
    query = """
    query {
      search(input: {
        type: CUSTOM_OWNERSHIP_TYPE
        query: "*"
        start: 0
        count: 20
      }) {
        searchResults {
          entity {
            ... on OwnershipTypeEntity {
              urn
              info {
                name
                description
              }
            }
          }
        }
      }
    }
    """
    data = await execute_graphql_query(query)
    ownership_types = []
    search_results = data.get("search", {}).get("searchResults", [])
    for result in search_results:
        entity = result.get("entity", {})
        info = entity.get("info", {})
        ownership_types.append({
            "urn": entity.get("urn"),
            "name": info.get("name"),
            "description": info.get("description", "")
        })
    return {"status": "success", "ownershipTypes": ownership_types}


@router.get("/dashboard/entitymetrics")
async def get_entity_counts():
    """Get total counts for assets, tags, domains, incidents"""
    try:
        count_query = """
        query CountTotalAssets {
          getEntityCounts(input: { types: [DATASET, TAG, DOMAIN,INCIDENT] }) {
            counts { entityType count }
          }
        }
        """
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(DATAHUB_GRAPHQL_URL, json={"query": count_query}) as response:
                result = await response.json()
        
        if "errors" in result:
            raise HTTPException(status_code=400, detail=result["errors"])
        
        counts_data = result.get("data", {}).get("getEntityCounts", {}).get("counts", [])
        stats = {}
        for count in counts_data:
            entity_type = count.get("entityType", "").replace("Entity", "")
            stats[entity_type] = count.get("count", 0)
        
        expected_types = ["DATASET", "TAG", "DOMAIN", "INCIDENT"]
        for t in expected_types:
            stats.setdefault(t, 0)
        
        return {
            "status": "success",
            "timestamp": int(time.time() * 1000),
            "total_assets": sum(stats.values()),
            "counts": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/platforms")
async def get_platforms_with_counts():
    """
    Get dataset counts by platform using GraphQL aggregation
    """
    try:
        platform_query = """
        query datasetCountsByPlatform {
          aggregateAcrossEntities(input: {
            types: [DATASET]
            facets: ["platform"]
            query: "*"
          }) {
            facets {
              field
              aggregations {
                value
                count
              }
            }
          }
        }
        """
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(
                DATAHUB_GRAPHQL_URL,
                json={"query": platform_query}
            ) as response:
                result = await response.json()
        
        # Handle GraphQL errors
        if "errors" in result:
            raise HTTPException(status_code=400, detail=result["errors"])
        
        facets_data = result.get("data", {}).get("aggregateAcrossEntities", {}).get("facets", [])
        
        if not facets_data:
            return {
                "status": "success",
                "timestamp": int(time.time() * 1000),
                "total_platforms": 0,
                "platforms": []
            }
        
        # Extract platform data
        platforms = []
        platform_facet = None
        
        for facet in facets_data:
            if facet.get("field") == "platform":
                platform_facet = facet
                break
        
        if platform_facet:
            for agg in platform_facet.get("aggregations", []):
                platform_urn = agg.get("value", "")
                count = agg.get("count", 0)
                
                # Extract platform name from URN (urn:li:dataPlatform:postgres -> postgres)
                platform_name = platform_urn.split(":")[-1] if platform_urn else "unknown"
                
                platforms.append({
                    "platform_urn": platform_urn,
                    "platform_name": platform_name,
                    "dataset_count": count
                })
        
        # Sort by count (descending)
        platforms.sort(key=lambda x: x["dataset_count"], reverse=True)
        total_datasets = sum(p["dataset_count"] for p in platforms)
        
        return {
            "status": "success",
            "timestamp": int(time.time() * 1000),
            "total_datasets": total_datasets,
            "total_platforms": len(platforms),
            "platforms": platforms
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch platforms: {str(e)}")


@router.get("/dashboard/domain_with_counts")
async def get_domains_with_counts():
    """
    Get all domains with their asset counts, sorted by assets DESC
    """
    try:
        domains_query = """
        query ActiveDomainsCount {
          getEntityCounts(input: { types: [ DOMAIN ] }) {
            counts {
              entityType
              count
            }
          }
          listDomains(input: { start: 0, count: 1000 }) {
            total
            domains {
              urn
              properties {
                name
              }
              entities {
                total
              }
            }
          }
        }
        """
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(
                DATAHUB_GRAPHQL_URL,
                json={"query": domains_query}
            ) as response:
                result = await response.json()
        
        # Handle GraphQL errors
        if "errors" in result:
            raise HTTPException(status_code=400, detail=result["errors"])
        
        data = result.get("data", {})
        
        # Extract total domain count
        total_domains = 0
        counts = data.get("getEntityCounts", {}).get("counts", [])
        for count in counts:
            if count.get("entityType") == "DOMAIN":
                total_domains = count.get("count", 0)
                break
        
        # Extract domain list
        domains_data = data.get("listDomains", {})
        domains_raw = domains_data.get("domains", [])
        total_returned = domains_data.get("total", 0)
        
        # Transform and sort domains by entities.total DESC
        domains = []
        for domain in domains_raw:
            urn = domain.get("urn", "")
            name = domain.get("properties", {}).get("name", "Unknown")
            asset_count = domain.get("entities", {}).get("total", 0)
            
            domains.append({
                "urn": urn,
                "name": name.strip(),  # Clean whitespace
                "asset_count": asset_count
            })
        
        # Sort by asset_count DESCENDING
        domains.sort(key=lambda x: x["asset_count"], reverse=True)
        
        # Calculate totals
        total_assets_in_domains = sum(d["asset_count"] for d in domains)
        
        return {
            "status": "success",
            "timestamp": int(time.time() * 1000),
            "total_domains": total_domains,
            "total_returned": total_returned,
            "total_assets_in_domains": total_assets_in_domains,
            "domains": domains
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch domains: {str(e)}")


@router.get("/dashboard/recent-assets")
async def get_all_recommendations(
    user_urn: Optional[str] = Query("urn:li:corpuser:Mindgraph", description="user URN")
):
    """
    Get ALL raw recommendations data from listRecommendations (HOME scenario).
    Returns complete structure: modules, content, entities (no filtering).
    """
    try:
        all_recommendations_query = """
        query getRecentlyViewedDatasets($userUrn: String!, $limit: Int!) {
          listRecommendations(input: {
            userUrn: $userUrn
            requestContext: { scenario: HOME }
            limit: $limit
          }) {
            modules {
              moduleId
              content {
                entity {
                  urn
                  type
                  ... on Dataset {
                    name
                    platform {
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {"userUrn": user_urn, "limit": 100}
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(
                DATAHUB_GRAPHQL_URL,
                json={"query": all_recommendations_query, "variables": variables}
            ) as response:
                result = await response.json()
        
        if "errors" in result:
            raise HTTPException(status_code=400, detail=result["errors"])
        
        # Return COMPLETE raw structure - NO filtering
        recommendations_data = result.get("data", {}).get("listRecommendations", {})
        
        return {
            "status": "success",
            "timestamp": int(time.time() * 1000),
            "user_urn": user_urn,
            "recommendations": recommendations_data  # Full modules/content/entities
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch recommendations: {str(e)}")


@router.get("/dashboard/recent")
async def get_recently_viewed_datasets(
    user_urn: Optional[str] = Query("urn:li:corpuser:Mindgraph", description="user URN")
):
    """
    Get ALL recently viewed datasets for user using listRecommendations (HOME scenario).
    Filters client-side to return ONLY DATASET entities with name, platform, description.
    """
    try:
        recent_datasets_query = """
        query getRecentlyViewedEntities($userUrn: String!, $limit: Int!) {
          listRecommendations(input: {
            userUrn: $userUrn
            requestContext: { scenario: HOME }
            limit: $limit
          }) {
            modules {
              moduleId
              content {
                entity {
                  urn
                  type
                  ... on Dataset {
                    name
                    platform {
                      name
                    }
                    description
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {
            "userUrn": user_urn,
            "limit": 100  # Get full recommendations
        }
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(
                DATAHUB_GRAPHQL_URL,
                json={"query": recent_datasets_query, "variables": variables}
            ) as response:
                result = await response.json()
        
        if "errors" in result:
            raise HTTPException(status_code=400, detail=result["errors"])
        
        # CLIENT-SIDE FILTERING: Only DATASET entities
        datasets = []
        rec_data = result.get("data", {}).get("listRecommendations", {})
        
        for module in rec_data.get("modules", []):
            module_id = module.get("moduleId", "Unknown")
            for item in module.get("content", []):
                entity = item.get("entity", {})
                
                # STRICT FILTER: Must be DATASET with populated fragment fields
                if (entity.get("type") == "DATASET" and 
                    entity.get("name") and 
                    entity.get("platform")):
                    
                    datasets.append({
                        "urn": entity.get("urn"),
                        "name": entity.get("name"),
                        "platform": entity.get("platform", {}).get("name"),
                        "description": entity.get("description", ""),
                        "source_module": module_id
                    })
        
        return {
            "status": "success",
            "timestamp": int(time.time() * 1000),
            "user_urn": user_urn,
            "total_datasets": len(datasets),
            "recently_viewed_datasets": datasets  # ALL matching datasets
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch recent datasets: {str(e)}")
