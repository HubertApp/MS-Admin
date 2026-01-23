# app/workers/callbacks/email.py
from faststream.rabbit import RabbitRouter
from pydantic import BaseModel
from app.core.database import async_session
from app.services.email_service import send_welcome_email

# On crée un router spécifique pour ce fichier
# On peut même préfixer les queues si besoin, mais restons simples
email_router = RabbitRouter()

# Définition du schéma du message attendu
class UserCreatedMessage(BaseModel):
    user_id: int
    email: str

# On utilise le décorateur du ROUTER, pas du broker global
@email_router.subscriber("user_created_queue")
async def handle_user_created(msg: UserCreatedMessage):
    """
    Callback isolé : reçoit le message, ouvre la session, appelle le service.
    """
    async with async_session() as db:
        print(f"[Worker Email] Traitement pour user {msg.user_id}")
        await send_welcome_email(session=db, user_id=msg.user_id, email=msg.email)