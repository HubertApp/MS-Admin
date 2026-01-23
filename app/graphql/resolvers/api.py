import strawberry
from strawberry.types import Info
from app.graphql.types.api import ApiType, PaginatedApiType
from app.graphql.inputs.api import ApiCreateInput
from app.services.api_service import create_api_service, get_all_apis_service, get_api_by_id_service

async def resolve_create_api(info: Info, input: ApiCreateInput) -> ApiType:
    db_session = info.context["db"]

    api_model = await create_api_service(session=db_session, data=input)

    return ApiType(
        id=api_model.id,
        title=api_model.title,
        type=api_model.type,
        description=api_model.description,
        endpoint_url=api_model.endpoint_url,
        api_key=api_model.api_key
    )

async def resolve_get_apis(info: Info, page: int = 1, page_size: int = 25) -> list[ApiType]:
    db = info.context["db"]
    offset = (page - 1) * page_size
    
    apis_db, total_count = await get_all_apis_service(db, offset=offset, limit=page_size)
    items_graphql = [
        ApiType(
            id=x.id,
            title=x.title,
            type=x.type,
            description=x.description,
            endpoint_url=x.endpoint_url,
            api_key=x.api_key
        )
        for x in apis_db
    ]

    return PaginatedApiType(
        items=items_graphql,
        total_count=total_count,
        page=page,
        page_size=page_size
    )

async def resolve_get_api_by_id(info: Info, api_id: int) -> ApiType:
    db = info.context["db"]
    api_db = await get_api_by_id_service(db, api_id)

    return ApiType(
            id=api_db.id,
            title=api_db.title,
            type=api_db.type,
            description=api_db.description,
            endpoint_url=api_db.endpoint_url,
            api_key=api_db.api_key
        )