import strawberry
from typing import List, Optional
from datetime import datetime

@strawberry.type
class StandardResource:
    title: str
    format: str
    download_url: str
    updated_at: datetime
    filesize_bytes: Optional[int] = None

@strawberry.type
class StandardDatasets:
    fournisseur_id: str
    external_id: str
    name: str
    country_code: str
    city_or_region: str
    resources: List[StandardResource]