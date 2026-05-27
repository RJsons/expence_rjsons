from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import CategoryDB, UserDB
from app.schemas import CategoryCreate, CategoryResponse, DEFAULT_CATEGORIES

router = APIRouter(prefix="/api/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryResponse])
def get_categories(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Return user categories, seeding 8 defaults on first access."""
    categories = db.query(CategoryDB).filter(CategoryDB.user_id == current_user.id).all()
    if not categories:
        default_cats = [
            CategoryDB(
                name=cat["name"],
                color=cat["color"],
                icon=cat["icon"],
                is_default=True,
                user_id=current_user.id,
            )
            for cat in DEFAULT_CATEGORIES
        ]
        db.add_all(default_cats)
        db.commit()
        for cat in default_cats:
            db.refresh(cat)
        categories = default_cats
    return categories


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Create a custom category for the authenticated user."""
    new_category = CategoryDB(
        name=category.name,
        color=category.color or "#607D8B",
        icon=category.icon or "category",
        is_default=False,
        user_id=current_user.id,
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Update a category owned by the authenticated user."""
    db_category = db.query(CategoryDB).filter(
        CategoryDB.id == category_id,
        CategoryDB.user_id == current_user.id,
    ).first()
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or access denied",
        )
    db_category.name = category.name
    db_category.color = category.color or db_category.color
    db_category.icon = category.icon or db_category.icon
    db.commit()
    db.refresh(db_category)
    return db_category


@router.delete("/{category_id}", status_code=status.HTTP_200_OK)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Delete a category. Associated expenses are NOT deleted."""
    db_category = db.query(CategoryDB).filter(
        CategoryDB.id == category_id,
        CategoryDB.user_id == current_user.id,
    ).first()
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found or access denied",
        )
    db.delete(db_category)
    db.commit()
    return {"detail": "Category deleted successfully"}
