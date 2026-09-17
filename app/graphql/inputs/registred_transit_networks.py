import strawberry
from typing import List, Optional

from app.graphql.types.registred_transit_network import TransitNetworkStatus

@strawberry.input
class ResourceInput:
    title: str
    format: str
    endpoint_url: str

@strawberry.input
class TransitNetworkInput:
    fournisseur_id: str
    external_id: str
    name: str
    country_code: str
    city_or_region: str
    endpoint_url: Optional[str] = None
    description: Optional[str] = None
    resources: Optional[List[ResourceInput]] = None
    status: Optional[TransitNetworkStatus] = None
