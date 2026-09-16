import strawberry
from typing import List

@strawberry.input
class ResourceInput:
    title: str
    format: str
    endpoint_url: str

@strawberry.input
class DatasetsInput:
    fournisseur_id: str
    external_id: str
    name: str
    country_code: str
    city_or_region: str
    resources: List[ResourceInput] = strawberry.field(default_factory=list)