from typing import Optional

import strawberry

from app.core.broker import broker
from app.core.database import registred_transit_network
from app.core.topology import GTFS_FILE_AVAILABLE
from app.graphql.inputs.registred_transit_networks import TransitNetworkInput
from app.graphql.types.registred_transit_network import (
    TransitNetwork,
    TransitNetworkStatus,
    build_transit_network,
)


class TransitNetworkService:

    @staticmethod
    async def create_transit_network(data: TransitNetworkInput) -> TransitNetwork:
        tn_dict = strawberry.asdict(data)

        existing = await registred_transit_network.find_one({"external_id": data.external_id})
        if existing:
            raise ValueError(f"L'API avec l'external_id {data.external_id} existe déjà.")

        status = data.status or TransitNetworkStatus.PENDING_AGGREGATION
        tn_dict["status"] = status.value

        await registred_transit_network.insert_one(tn_dict)

        gtfs_url, gtfs_format = TransitNetworkService._resolve_gtfs_source(data)
        if gtfs_url:
            await broker.publish(
                {
                    "network_id": data.external_id,
                    "url": gtfs_url,
                    "format": gtfs_format,
                },
                queue=GTFS_FILE_AVAILABLE,
                persist=True,
            )

        return build_transit_network(tn_dict)

    @staticmethod
    def _resolve_gtfs_source(data: TransitNetworkInput):
        for resource in data.resources or []:
            resource_format = resource.format.strip().upper()
            if resource_format == "GTFS":
                return resource.endpoint_url, resource_format
        return data.endpoint_url, "GTFS"

    @staticmethod
    async def find_by_external_id(external_id: str) -> Optional[dict]:
        return await registred_transit_network.find_one({"external_id": external_id})

    @staticmethod
    async def set_status(external_id: str, status: TransitNetworkStatus) -> bool:
        result = await registred_transit_network.update_one(
            {"external_id": external_id},
            {"$set": {"status": status.value}},
        )
        return result.matched_count > 0

    @staticmethod
    async def retrigger_aggregation(external_id: str) -> TransitNetwork:
        doc = await registred_transit_network.find_one({"external_id": external_id})
        if not doc:
            raise ValueError(f"Réseau introuvable : {external_id}")

        network = build_transit_network(doc)
        gtfs_url, gtfs_format = TransitNetworkService._resolve_gtfs_source(network)
        if not gtfs_url:
            raise ValueError(
                f"Aucune source GTFS exploitable pour {external_id} : "
                "ni ressource au format GTFS, ni endpointUrl."
            )

        await broker.publish(
            {
                "network_id": external_id,
                "url": gtfs_url,
                "format": gtfs_format,
            },
            queue=GTFS_FILE_AVAILABLE,
            persist=True,
        )

        await TransitNetworkService.set_status(external_id, TransitNetworkStatus.PENDING_AGGREGATION)
        network.status = TransitNetworkStatus.PENDING_AGGREGATION
        return network

    @staticmethod
    async def update_transit_network(external_id: str, data: TransitNetworkInput) -> TransitNetwork:
        tn_dict = strawberry.asdict(data)

        if data.status is None:
            tn_dict.pop("status", None)
        else:
            tn_dict["status"] = data.status.value

        result = await registred_transit_network.update_one(
            {"external_id": external_id},
            {"$set": tn_dict}
        )

        if result.matched_count == 0:
            raise ValueError("API introuvable.")

        doc = await registred_transit_network.find_one({"external_id": external_id})
        return build_transit_network(doc)

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

        resultats = [build_transit_network(tn) for tn in tn_in_db]
        return {
            "total_count": total_count,
            "total_pages": (total_count + limit - 1) // limit if limit > 0 else 0,
            "limit": limit,
            "offset": offset,
            "items": resultats
        }
