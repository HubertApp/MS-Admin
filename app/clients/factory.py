from app.clients.france_transport_fournisseur import FranceTransportFournisseur
from app.clients.i_fournisseur import IFournisseur


class FournisseurFactory:
    _fournisseurs = {
        "FR_TRANSPORT_GOUV": FranceTransportFournisseur()
        # Renseigner d'autres fournisseurs quand implémenté
    }

    @classmethod
    def get_fournisseur(cls, fournisseur_id: str) -> IFournisseur:
        fournisseur = cls._fournisseurs.get(fournisseur_id)
        if not fournisseur:
            raise ValueError(f"Fournisseur {fournisseur_id} non supporté.")
        return fournisseur