import strawberry

from app.core.database import apis_collection
from app.graphql.inputs.api import ApiInput
from app.graphql.types.standardized_api import StandardApi, StandardResource


class ApiService:

    @staticmethod
    async def create_api(data: ApiInput) -> StandardApi:
        api_dict = strawberry.asdict(data)

        existing = await apis_collection.find_one({"external_id": data.external_id})
        if existing:
            raise ValueError(f"L'API avec l'external_id {data.external_id} existe déjà.")

        await apis_collection.insert_one(api_dict)
        api_dict.pop("_id", None)
        return StandardApi(**api_dict)

    @staticmethod
    async def update_api(external_id: str, data: ApiInput) -> StandardApi:
        api_dict = strawberry.asdict(data)

        result = await apis_collection.update_one(
            {"external_id": external_id},
            {"$set": api_dict}
        )

        if result.matched_count == 0:
            raise ValueError("API introuvable.")

        return StandardApi(**api_dict)

    @staticmethod
    async def delete_api(external_id: str) -> bool:
        result = await apis_collection.delete_one({"external_id": external_id})
        return result.deleted_count > 0