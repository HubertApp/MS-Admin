from typing import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.api import ApiModel
from app.graphql.inputs.api import ApiCreateInput
from app.core.broker import broker

async def create_api_service(session: AsyncSession, data: ApiCreateInput) -> ApiModel:

    # 2. Création de l'objet SQLAlchemy
    new_api = ApiModel(
        title=data.title,
        type=data.type,
        description=data.description,
        endpoint_url=data.endpoint_url,
        api_key=data.api_key,
    )

    # 3. Sauvegarde en BDD
    session.add(new_api)
    await session.commit()
    await session.refresh(new_api)

    # Le worker attrapera ce message
    # await broker.publish(
    #     {"api_id": new_api.id},
    #     queue="api_created_queue"
    # )

    return new_api

async def get_all_apis_service(session: AsyncSession) -> Sequence[ApiModel]:
    query = select(ApiModel)

    result = await session.execute(query)

    return result.scalars().all()

async def get_api_by_id_service(session: AsyncSession, api_id: int) -> ApiModel:
    query = select(ApiModel).where(ApiModel.id == api_id)

    result = await session.execute(query)

    return result.scalars().first()