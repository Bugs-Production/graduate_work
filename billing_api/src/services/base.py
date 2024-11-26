from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Generic, TypeVar
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Base
from services.exceptions import ObjectNotFoundError

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class AbstractRepository(ABC):
    @abstractmethod
    async def create(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def get(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def get_many(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def update(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def delete(self, *args, **kwargs):
        raise NotImplementedError


class SQLAlchemyRepository(
    AbstractRepository, Generic[ModelType, CreateSchemaType, UpdateSchemaType]
):
    def __init__(self, model: type[ModelType]):
        self._model = model

    async def create(self, session: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = jsonable_encoder(obj_in)
        entity = self._model(**obj_in_data)
        session.add(entity)
        await session.commit()
        await session.refresh(entity)
        return entity

    async def get_one_or_none(self, session: AsyncSession, entity_id: UUID) -> ModelType | None:
        stmt = select(self._model).where(self._model.id == entity_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get(self, session: AsyncSession, entity_id: UUID) -> ModelType:
        db_obj = await self.get_one_or_none(session, entity_id=entity_id)
        if not db_obj:
            raise ObjectNotFoundError(f"Запрашиваемый объект с id={entity_id} не найден")
        return db_obj

    async def get_many(
        self, session: AsyncSession, *, limit: int = 100, offset: int = 0
    ) -> Sequence[ModelType]:
        stmt = select(self._model).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def update(
        self, session: AsyncSession, *, entity_id: UUID, obj_in: UpdateSchemaType
    ) -> ModelType:
        db_obj = await self.get(session, entity_id=entity_id)
        update_dict = obj_in.model_dump(exclude_none=True, exclude_unset=True)
        for field, value in update_dict.items():
            setattr(db_obj, field, value)
        db_obj = await session.merge(db_obj)
        await session.commit()
        return db_obj

    async def delete(self, session: AsyncSession, *, entity_id: UUID) -> None:
        db_obj = await self.get(session, entity_id=entity_id)
        await session.delete(db_obj)
        await session.commit()
