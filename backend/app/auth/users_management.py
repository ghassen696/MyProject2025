from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.users.elastic_queries import es,get_all_users, update_user_doc, delete_user_doc
from typing import Optional
from fastapi import Depends
from app.auth.dependencies import require_roles, get_current_user

router = APIRouter()

# --- Schemas ---
class UpdateUserRequest(BaseModel):
    email: str
    role: str
    employee_id: str

router = APIRouter()

# --- List users ---
@router.get("/users")
def list_users(search: Optional[str] = None, page: int = 1, page_size: int = 10,user=Depends(require_roles(["admin"]))):
    """
    Returns users with optional search, pagination.
    """
    all_users = get_all_users()  # returns all users from Elasticsearch
    active_count = sum(1 for u in all_users if u.get("status") == "active")
    pending_count = sum(1 for u in all_users if u.get("status") == "pending")
    admin_count = sum(1 for u in all_users if u.get("role") == "admin")

    # Filter by search if provided
    if search:
        search_lower = search.lower()
        all_users = [
            u for u in all_users
            if search_lower in u["username"].lower() 
            or search_lower in u["email"].lower() 
            or search_lower in u["employee_id"].lower()
        ]

    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    paginated_users = all_users[start:end]

    return {
        "users": paginated_users,
        "total": len(all_users),
        "active": active_count,
        "pending": pending_count,
        "admins": admin_count,
        "page": page,
        "page_size": page_size
    }

# --- Update user ---
class UpdateUserRequest(BaseModel):
    username: Optional[str]
    email: Optional[str]
    role: Optional[str]
    employee_id: Optional[str]
    status: Optional[str]

@router.put("/users/{employee_id}")
def update_user(employee_id: str, data: UpdateUserRequest, user=Depends(require_roles(["admin"]))
):
    update_user_doc(employee_id, data.dict(exclude_none=True))
    return {"message": "User updated"}

# --- Delete user ---
@router.delete("/users/{employee_id}")
def delete_user(employee_id: str, user=Depends(require_roles(["admin"]))):
    delete_user_doc(employee_id)
    return {"message": "User deleted"}
