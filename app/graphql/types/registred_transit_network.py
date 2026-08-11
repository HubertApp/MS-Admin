import strawberry
from typing import List, Optional
from datetime import datetime

from app.core.database import registred_transit_network

@strawberry.type
class Resource:
    title: str
    format: str
    endpoint_url: str
    updated_at: Optional[datetime] = None
    filesize_bytes: Optional[int] = None

@strawberry.federation.type(keys=["externalId"])
class TransitNetwork:
    fournisseur_id: str
    external_id: str
    name: str
    country_code: str
    city_or_region: str
    endpoint_url: Optional[str] = None
    description: Optional[str] = None
    resources : Optional[List[Resource]]

    @classmethod
    async def resolve_reference(cls, **kwargs) -> Optional["TransitNetwork"]:
        external_id = kwargs.get("externalId", kwargs.get("external_id"))
        doc = await registred_transit_network.find_one({"external_id": external_id})
        if not doc:
            return None
        doc.pop("_id", None)
        doc["resources"] = [Resource(**res) for res in doc.get("resources") or []]
        return cls(**doc)

@strawberry.type
class PaginatedTransitNetworks:
    total_count: int
    total_pages: int
    limit: int
    offset: int
    items: Optional[List[TransitNetwork]] = None
