import strawberry

from app.core.database import registred_transit_network
from app.graphql.inputs.registred_transit_networks import TransitNetworkInput
from app.graphql.types.registred_transit_network import TransitNetworks, Resource


class TransitNetworkService:

    @staticmethod
    async def create_transit_network(data: TransitNetworkInput) -> TransitNetworks:
        tn_dict = strawberry.asdict(data)

        existing = await registred_transit_network.find_one({"external_id": data.external_id})
        if existing:
            raise ValueError(f"L'API avec l'external_id {data.external_id} existe déjà.")

        await registred_transit_network.insert_one(tn_dict)
        tn_dict.pop("_id", None)
        if tn_dict.get("resources"):
            tn_dict["resources"] = [Resource(**res) for res in tn_dict["resources"]]
        print(tn_dict, flush=True)
        return TransitNetworks(**tn_dict)

    @staticmethod
    async def update_transit_network(external_id: str, data: TransitNetworkInput) -> TransitNetworks:
        tn_dict = strawberry.asdict(data)

        result = await registred_transit_network.update_one(
            {"external_id": external_id},
            {"$set": tn_dict}
        )

        if result.matched_count == 0:
            raise ValueError("API introuvable.")

        return TransitNetworks(**tn_dict)

    @staticmethod
    async def delete_transit_network(external_id: str) -> bool:
        result = await registred_transit_network.delete_one({"external_id": external_id})
        return result.deleted_count > 0

    @staticmethod
    async def search_registred_transit_network(limit: int = 10, offset: int = 0, fournisseur_id: str = ""):
        filtre = {"fournisseur_id": fournisseur_id} if fournisseur_id else {}
        total_count = await registred_transit_network.count_documents(filtre)
        cursor = registred_transit_network.find(filtre).skip(offset).limit(limit)
        tn_in_db = await cursor.to_list(length=limit)

        resultats = []
        for tn in tn_in_db:
            tn.pop("_id", None)
            raw_resources = tn.get("resources") or []
            tn["resources"] = [Resource(**res) for res in raw_resources]
            resultats.append(TransitNetworks(**tn))
        return {
            "total_count": total_count,
            "total_pages": (total_count + limit - 1) // limit if limit > 0 else 0,
            "limit": limit,
            "offset": offset,
            "items": resultats
        }