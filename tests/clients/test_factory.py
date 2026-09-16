import pytest

from app.clients.factory import FournisseurFactory
from app.clients.france_transport_fournisseur import FranceTransportFournisseur


def test_renvoie_le_fournisseur_france_transport():
    fournisseur = FournisseurFactory.get_fournisseur("FR_TRANSPORT_GOUV")

    assert isinstance(fournisseur, FranceTransportFournisseur)
    assert fournisseur.fournisseur_id == "FR_TRANSPORT_GOUV"


def test_leve_une_erreur_pour_un_fournisseur_inconnu():
    with pytest.raises(ValueError, match="INCONNU non supporté"):
        FournisseurFactory.get_fournisseur("INCONNU")
