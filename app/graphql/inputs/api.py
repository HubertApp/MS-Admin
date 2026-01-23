import strawberry

@strawberry.input
class ApiCreateInput:
    title: str
    description: str
    endpoint_url: str
    api_key: str
    type: str