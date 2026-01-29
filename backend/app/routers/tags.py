"""
Tags Router
CRUD endpoints for user tags
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Tag
from app.schemas import TagResponse, SuccessResponse
from app.middleware.auth import get_current_user_id

router = APIRouter()


class TagCreate:
    """Schema for creating a tag"""
    def __init__(self, name: str, color: str = "#6366f1"):
        self.name = name
        self.color = color


class TagUpdate:
    """Schema for updating a tag"""
    def __init__(self, name: str = None, color: str = None):
        self.name = name
        self.color = color


from pydantic import BaseModel, Field


class TagCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = Field(default="#6366f1", pattern="^#[0-9A-Fa-f]{6}$")


class TagUpdateSchema(BaseModel):
    name: str = Field(None, min_length=1, max_length=50)
    color: str = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


@router.get("", response_model=List[TagResponse])
async def list_tags(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """List all tags for the current user"""
    
    query = (
        select(Tag)
        .where(Tag.user_id == user_id)
        .order_by(Tag.name)
    )
    
    result = await db.execute(query)
    tags = result.scalars().all()
    
    return [TagResponse.model_validate(tag) for tag in tags]


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    data: TagCreateSchema,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Create a new tag"""
    
    # Check for duplicate
    existing_query = select(Tag).where(
        Tag.user_id == user_id,
        Tag.name == data.name,
    )
    result = await db.execute(existing_query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tag with this name already exists",
        )
    
    # Create tag
    tag = Tag(
        user_id=user_id,
        name=data.name,
        color=data.color,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    
    return TagResponse.model_validate(tag)


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: UUID,
    data: TagUpdateSchema,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Update a tag"""
    
    query = select(Tag).where(
        Tag.id == tag_id,
        Tag.user_id == user_id,
    )
    
    result = await db.execute(query)
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    
    # Check for duplicate name
    if data.name and data.name != tag.name:
        dup_query = select(Tag).where(
            Tag.user_id == user_id,
            Tag.name == data.name,
        )
        dup_result = await db.execute(dup_query)
        if dup_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tag with this name already exists",
            )
    
    # Update fields
    if data.name:
        tag.name = data.name
    if data.color:
        tag.color = data.color
    
    await db.commit()
    await db.refresh(tag)
    
    return TagResponse.model_validate(tag)


@router.delete("/{tag_id}", response_model=SuccessResponse)
async def delete_tag(
    tag_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Delete a tag"""
    
    query = select(Tag).where(
        Tag.id == tag_id,
        Tag.user_id == user_id,
    )
    
    result = await db.execute(query)
    tag = result.scalar_one_or_none()
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    
    await db.delete(tag)
    await db.commit()
    
    return SuccessResponse(message="Tag deleted")
