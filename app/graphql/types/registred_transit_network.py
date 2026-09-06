import strawberry
from enum import Enum
from typing import List, Optional
from datetime import datetime

from app.core.database import registred_transit_network

@strawberry.enum
class TransitNetworkStatus(Enum):
    PENDING_AGGREGATION = "PENDING_AGGREGATION"
    DATA_AVAILABLE = "DATA_AVAILABLE"
    AGGREGATION_ERROR = "AGGREGATION_ERROR"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"

STATUS_LABELS = {
    TransitNetworkStatus.PENDING_AGGREGATION: "En attente d'agrégation",
    TransitNetworkStatus.DATA_AVAILABLE: "Données ajoutées",
    TransitNetworkStatus.AGGREGATION_ERROR: "Agrégation en erreur",
    TransitNetworkStatus.OUT_OF_SERVICE: "Hors service",
}

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
    resources : Optional[List[Resource]] = None
    status: TransitNetworkStatus = TransitNetworkStatus.PENDING_AGGREGATION

    @strawberry.field
    def status_label(self) -> str:
        return STATUS_LABELS[self.status]

    @classmethod
    async def resolve_reference(cls, **kwargs) -> Optional["TransitNetwork"]:
        external_id = kwargs.get("externalId", kwargs.get("external_id"))
        doc = await registred_transit_network.find_one({"external_id": external_id})
        if not doc:
            return None
        return build_transit_network(doc)

@strawberry.type
class PaginatedTransitNetworks:
    total_count: int
    total_pages: int
    limit: int
    offset: int
    items: Optional[List[TransitNetwork]] = None

def build_transit_network(doc: dict) -> TransitNetwork:
    doc.pop("_id", None)
    doc["resources"] = [Resource(**res) for res in doc.get("resources") or []]
    doc["status"] = TransitNetworkStatus(doc.get("status") or TransitNetworkStatus.PENDING_AGGREGATION.value)
    return TransitNetwork(**doc)
