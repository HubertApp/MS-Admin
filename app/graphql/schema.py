import strawberry
from app.graphql.inputs.api import ApiCreateInput
from app.graphql.resolvers.api import resolve_get_api_by_id, resolve_get_apis, resolve_create_api, resolve_delete_api_by_id
from app.graphql.types.api import ApiType, PaginatedApiType

@strawberry.type
class Query:
    get_apis:PaginatedApiType = strawberry.field(resolver=resolve_get_apis)
    get_api_by_id: ApiType  = strawberry.field(resolver=resolve_get_api_by_id)

@strawberry.type
class Mutation:
    @strawberry.field
    async def create_api(self, info: strawberry.Info, input: ApiCreateInput) -> ApiType:
        return await resolve_create_api(info, input)

    @strawberry.field
    async def delete_api_by_id(self, info: strawberry.Info, api_id: int) -> bool:
        return await resolve_delete_api_by_id(info, api_id)

schema = strawberry.federation.Schema(
    query=Query,
    mutation=Mutation
)