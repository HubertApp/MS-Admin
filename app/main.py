from fastapi import FastAPI, Depends
from strawberry.fastapi import GraphQLRouter
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.graphql.schema import schema

async def get_context(db: AsyncSession = Depends(get_db_session)):
    return {"db": db}

graphql_app = GraphQLRouter(
    schema, 
    context_getter=get_context
)

app = FastAPI()
app.include_router(graphql_app, prefix="/graphql")