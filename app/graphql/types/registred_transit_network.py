import strawberry
from typing import List, Optional
from datetime import datetime

@strawberry.type
class Resource:
    title: str
    format: str
    endpoint_url: str
    updated_at: Optional[datetime] = None
    filesize_bytes: Optional[int] = None

@strawberry.type
class TransitNetworks:
    fournisseur_id: str
    external_id: str
    name: str
    country_code: str
    city_or_region: str
    endpoint_url: Optional[str] = None
    description: Optional[str] = None
    resources : Optional[List[Resource]]

@strawberry.type
class PaginatedTransitNetworks:
    total_count: int
    total_pages: int
    limit: int
    offset: int
    items: Optional[List[TransitNetworks]] = None