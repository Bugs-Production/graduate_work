from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Generic, TypeVar
from uuid import UUID

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


class SQLAlchemyRepository(AbstractRepository, Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self._model = model
        self._session = session

    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = obj_in.model_dump(exclude_none=True, exclude_unset=True)
        entity = self._model(**obj_in_data)
        self._session.add(entity)
        await self._session.commit()
        await self._session.refresh(entity)
        return entity

    async def get_one_or_none(self, entity_id: UUID) -> ModelType | None:
        stmt = select(self._model).where(self._model.id == entity_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get(self, entity_id: UUID) -> ModelType:
        db_obj = await self.get_one_or_none(entity_id=entity_id)
        if not db_obj:
            raise ObjectNotFoundError(f"Запрашиваемый объект {self._model.__name__} с id={entity_id} не найден")
        return db_obj

    async def get_many(self, filters: dict | None = None) -> Sequence[ModelType]:
        stmt = select(self._model)
        if filters is None:
            filters = {}

        for column_name, filter_value in filters.items():
            column = getattr(self._model, column_name)
            stmt = stmt.where(column == filter_value)

        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def update(self, entity_id: UUID, obj_in: UpdateSchemaType) -> ModelType:
        db_obj = await self.get(entity_id=entity_id)
        update_dict = obj_in.model_dump(exclude_none=True, exclude_unset=True)
        for field, value in update_dict.items():
            setattr(db_obj, field, value)
        db_obj = await self._session.merge(db_obj)
        await self._session.commit()
        return db_obj

    async def delete(self, entity_id: UUID) -> None:
        db_obj = await self.get(entity_id=entity_id)
        await self._session.delete(db_obj)
        await self._session.commit()
