import strawberry
from typing import List, Optional

@strawberry.input
class ResourceInput:
    title: str
    format: str
    download_url: str

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