from app.graphql.types.registred_transit_network import PaginatedTransitNetworks
from app.services.transit_network_service import TransitNetworkService


async def resolve_get_registred_transit_network(actual_page: int = 1, limit: int = 10, offset: int = 0) -> PaginatedTransitNetworks:
        computed_offset = offset if offset else (actual_page - 1) * limit
        data = await TransitNetworkService.search_registred_transit_network(limit, computed_offset)
        return PaginatedTransitNetworks(**data)
