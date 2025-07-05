"""
Neo4j test endpoints for verifying graph database connectivity.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status

from ....core.deps import get_optional_user

# Setup logger
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get(
    "/neo4j/status",
    summary="Neo4j Status Check",
    description="Check Neo4j database connectivity and return basic information"
)
async def neo4j_status(
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
) -> Dict[str, Any]:
    """Test Neo4j connectivity and return status."""
    try:
        # Import neo4j driver
        from neo4j import GraphDatabase
        import os
        
        # Get Neo4j configuration from environment
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        # Create driver and test connection
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
        
        with driver.session() as session:
            # Test connection and get basic info
            result = session.run("""
                CALL dbms.components() YIELD name, versions, edition
                RETURN name, versions[0] as version, edition
                UNION ALL
                MATCH (n) RETURN 'Node Count' as name, count(n) as version, 'data' as edition
                UNION ALL  
                MATCH ()-[r]->() RETURN 'Relationship Count' as name, count(r) as version, 'data' as edition
            """)
            
            info = {}
            for record in result:
                if record["name"] == "Neo4j Kernel":
                    info["neo4j_version"] = record["version"]
                    info["edition"] = record["edition"]
                elif record["name"] == "Node Count":
                    info["node_count"] = record["version"]
                elif record["name"] == "Relationship Count":
                    info["relationship_count"] = record["version"]
        
        driver.close()
        
        # Get sample companies
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
        with driver.session() as session:
            companies_result = session.run("""
                MATCH (c:Company) 
                RETURN c.symbol, c.name 
                ORDER BY c.market_cap DESC 
                LIMIT 5
            """)
            companies = [{"symbol": record["c.symbol"], "name": record["c.name"]} 
                        for record in companies_result]
        
        driver.close()
        
        logger.info(f"Neo4j status check successful for user: {current_user.get('user_id', 'anonymous') if current_user else 'anonymous'}")
        
        return {
            "success": True,
            "data": {
                "status": "connected",
                "connection_uri": neo4j_uri,
                "database_info": info,
                "sample_companies": companies,
                "plugins_available": ["APOC", "Graph Data Science"],
                "timestamp": "now"
            }
        }
        
    except ImportError:
        logger.warning("Neo4j driver not available")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": 503,
                "message": "Neo4j driver not installed",
                "type": "dependency_error"
            }
        )
    except Exception as e:
        logger.error(f"Neo4j connection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": 503,
                "message": f"Neo4j connection failed: {str(e)}",
                "type": "connection_error"
            }
        )

@router.get(
    "/neo4j/companies",
    summary="Get Companies from Neo4j",
    description="Retrieve company data from Neo4j graph database"
)
async def get_companies_from_neo4j(
    limit: int = 10,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
) -> Dict[str, Any]:
    """Get companies from Neo4j with their sector relationships."""
    try:
        from neo4j import GraphDatabase
        import os
        
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j") 
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
        
        with driver.session() as session:
            result = session.run("""
                MATCH (c:Company)-[:BELONGS_TO]->(s:Sector)
                RETURN c.symbol, c.name, c.market_cap, s.name as sector
                ORDER BY c.market_cap DESC
                LIMIT $limit
            """, limit=limit)
            
            companies = []
            for record in result:
                companies.append({
                    "symbol": record["c.symbol"],
                    "name": record["c.name"], 
                    "market_cap": record["c.market_cap"],
                    "sector": record["sector"]
                })
        
        driver.close()
        
        logger.info(f"Retrieved {len(companies)} companies from Neo4j for user: {current_user.get('user_id', 'anonymous') if current_user else 'anonymous'}")
        
        return {
            "success": True,
            "data": {
                "companies": companies,
                "count": len(companies),
                "source": "neo4j_graph_database"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to retrieve companies from Neo4j: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": 500,
                "message": f"Failed to retrieve companies: {str(e)}",
                "type": "query_error"
            }
        )