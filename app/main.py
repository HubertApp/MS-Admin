from fastapi import FastAPI, Depends
from strawberry.fastapi import GraphQLRouter
from app.graphql.schema import schema


graphql_app = GraphQLRouter(
    schema
)
 
app = FastAPI()
app.include_router(graphql_app, prefix="/graphql")