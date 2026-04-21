from fastapi import FastAPI, Depends
from strawberry.fastapi import GraphQLRouter
from app.graphql.schema import schema
from fastapi.middleware.cors import CORSMiddleware



graphql_app = GraphQLRouter(
    schema
)
 
app = FastAPI()
app.include_router(graphql_app, prefix="/graphql")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)