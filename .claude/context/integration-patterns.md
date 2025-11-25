# Common Integration Patterns

## External Service Integration

### Qdrant Vector Database

```python
# Connection pattern for external Qdrant (configure via environment)
from qdrant_client import QdrantClient
import os

async def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333"))
    )

# Query pattern with error handling
async def search_vectors(query_vector: List[float], limit: int = 10):
    client = await get_qdrant_client()
    try:
        results = client.search(
            collection_name="knowledge_base",
            query_vector=query_vector,
            limit=limit
        )
        return results
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise VectorSearchError(f"Unable to search vectors: {e}") from e
```

### MCP Server Communication

```python
# MCP client pattern for Zen server integration
async def call_mcp_tool(tool_name: str, params: dict):
    async with MCPClient() as client:
        try:
            result = await client.call_tool(tool_name, params)
            return result
        except MCPError as e:
            logger.error(f"MCP call failed: {e}")
            # Fallback to local processing if available
            return await fallback_processing(tool_name, params)
```

## API Integration Patterns

### FastAPI Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1")

class RequestModel(BaseModel):
    field: str
    optional_field: Optional[str] = None

@router.post("/endpoint")
async def endpoint_handler(
    request: RequestModel,
    service: ServiceClass = Depends(get_service)
) -> ResponseModel:
    try:
        result = await service.process(request)
        return ResponseModel.from_result(result)
    except ServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Authentication Patterns

```python
# JWT token validation
from fastapi.security import HTTPBearer
from jose import jwt, JWTError

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return await get_user(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## Data Processing Patterns

### Async Batch Processing

```python
import asyncio
from typing import List, TypeVar

T = TypeVar('T')
R = TypeVar('R')

async def process_batch(items: List[T], processor: Callable[[T], Awaitable[R]],
                       batch_size: int = 10) -> List[R]:
    """Process items in batches to avoid overwhelming external services."""
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = await asyncio.gather(*[
            processor(item) for item in batch
        ])
        results.extend(batch_results)
    return results
```

### Error Recovery Patterns

```python
import asyncio
from functools import wraps

def with_retry(max_attempts: int = 3, delay: float = 1.0):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay * (2 ** attempt))
                        logger.warning(f"Retry {attempt + 1}/{max_attempts} for {func.__name__}: {e}")
            raise last_exception
        return wrapper
    return decorator
```

## Configuration Integration

### Environment-Based Configuration

```python
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    api_key: Optional[str] = None
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### Service Integration Factory

```python
from typing import Protocol

class ServiceProtocol(Protocol):
    async def process(self, data: Any) -> Any: ...

def get_service_implementation(service_type: str) -> ServiceProtocol:
    """Factory pattern for service selection based on configuration."""
    if service_type == "local":
        return LocalService()
    elif service_type == "remote":
        return RemoteService()
    else:
        raise ValueError(f"Unknown service type: {service_type}")
```
