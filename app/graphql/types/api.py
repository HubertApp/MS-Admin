import strawberry

@strawberry.type
class ApiType:
    id: int
    title: str
    description: str
    endpoint_url: str
    api_key: str
    type: str
    
@strawberry.type
class PaginatedApiType:
    items: list[ApiType]
    total_count: int
    page: int
    page_size: int
    @strawberry.field
    def total_pages(self) -> int:
        import math
        if self.page_size == 0: return 0
        return math.ceil(self.total_count / self.page_size)