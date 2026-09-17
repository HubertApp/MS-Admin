import pytest

from app.core.topology import GTFS_FILE_AVAILABLE, GTFS_INGESTION_RESULT


# Contrat partagé avec MS-aom-agregator : une divergence de nom ou de
# durabilité provoque un PRECONDITION_FAILED au démarrage de l'un des services.
@pytest.mark.parametrize(
    "queue, nom_attendu",
    [
        (GTFS_FILE_AVAILABLE, "gtfs.file.available"),
        (GTFS_INGESTION_RESULT, "gtfs.ingestion.result"),
    ],
)
def test_queue_partagee_nommee_et_durable(queue, nom_attendu):
    assert queue.name == nom_attendu
    assert queue.durable is True
