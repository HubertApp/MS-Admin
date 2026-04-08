from typing import List

import strawberry

from app.graphql.inputs.api import ApiInput
from app.graphql.types.standardized_api import StandardApi
from app.graphql.resolvers.api import resolve_search_api
from app.services.api_service import ApiService


@strawberry.type
class Query:
    search_apis: List[StandardApi] = strawberry.field(resolver=resolve_search_api)


@strawberry.type
class Mutation:

    @strawberry.mutation
    async def create_api(self, data: ApiInput) -> StandardApi:
        return await ApiService.create_api(data)

    @strawberry.mutation
    async def update_api(self, external_id: str, data: ApiInput) -> StandardApi:
        return await ApiService.update_api(external_id, data)

    @strawberry.mutation
    async def delete_api(self, external_id: str) -> bool:
        return await ApiService.delete_api(external_id)

schema = strawberry.federation.Schema(
    query=Query,
    mutation=Mutation
)
