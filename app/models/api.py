from sqlalchemy import Column, Integer, String
from app.models.base import Base, TimestampMixin

class ApiModel(Base, TimestampMixin):
    __tablename__ = "apis"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    endpoint_url = Column(String, nullable=False)
    api_key = Column(String, nullable=False)
    type = Column(String, nullable=False)