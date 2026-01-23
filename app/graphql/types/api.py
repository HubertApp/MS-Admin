import strawberry

@strawberry.type
class ApiType:
    id: int
    title: str
    description: str
    endpoint_url: str
    api_key: str
    type: str