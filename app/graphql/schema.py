from typing import List

import strawberry

from app.graphql.inputs.registred_transit_networks import TransitNetworkInput
from app.graphql.inputs.transit_network_datasets import DatasetsInput
from app.graphql.resolvers.registred_transit_networks import resolve_get_registred_transit_network
from app.graphql.types.registred_transit_network import TransitNetworks, PaginatedTransitNetworks
from app.graphql.types.standardized_datasets import StandardDatasets
from app.graphql.resolvers.transit_network_datasets import resolve_search_datasets
from app.services.transit_network_service import TransitNetworkService


@strawberry.type
class Query:
    search_transit_networks_datasets: List[StandardDatasets] = strawberry.field(resolver=resolve_search_datasets)
    get_registred_transit_networks: PaginatedTransitNetworks = strawberry.field(resolver=resolve_get_registred_transit_network)


@strawberry.type
class Mutation:

    @strawberry.mutation
    async def create_transit_network(self, data: TransitNetworkInput) -> TransitNetworks:
        return await TransitNetworkService.create_transit_network(data)

    @strawberry.mutation
    async def update_transit_network(self, external_id: str, data: TransitNetworkInput) -> TransitNetworks:
        return await TransitNetworkService.update_transit_network(external_id, data)

    @strawberry.mutation
    async def delete_transit_network(self, external_id: str) -> bool:
        return await TransitNetworkService.delete_transit_network(external_id)

schema = strawberry.federation.Schema(
    query=Query,
    mutation=Mutation
)
