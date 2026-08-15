"""
===============================================================================
KAIZEN / MISSION AVINYA - Documentation & Knowledge Base Database Services
===============================================================================
Module Purpose:
  Provides database services for club documentation, knowledge base articles, and guidelines
  with line-by-line comments.
===============================================================================
"""

# Import Python standard datetime utilities
from datetime import datetime, timezone

# Import base DB client and audit logging
from .base import _get_client, log_action


def get_all_documents(category: str = None):
    """
    Fetches published and internal documents ordered by update date descending.
    """
    query = _get_client().table("documents").select("*").order("updated_at", desc=True)
    if category:
        query = query.eq("category", category)
    res = query.execute()
    return res.data if (res and res.data is not None) else []


def get_document(doc_id: str):
    """
    Fetches a single document by its UUID identifier.
    """
    query = _get_client().table("documents").select("*").eq("id", doc_id)
    return query.single().execute().data


def create_document(title: str, content: str, category: str, tags: list[str] | None, published: bool,
                    user_id: str):
    """
    Creates a new knowledge base document or guide.
    """
    data = {k: v for k, v in {
        "title": title,
        "content": content,
        "category": category,
        "tags": tags or [],
        "published": published,
        "created_by": user_id
    }.items() if v is not None}
    
    res = _get_client().table("documents").insert(data).execute().data[0]
    log_action(user_id, "document_created", "document", res["id"], new_values=data)
    return res


def update_document(doc_id: str, title: str, content: str, category: str, tags: list[str] | None,
                    published: bool, user_id: str):
    """
    Updates document content, title, category, or publish status.
    """
    old = get_document(doc_id)
    new_data = {k: v for k, v in {
        "title": title,
        "content": content,
        "category": category,
        "tags": tags or [],
        "published": published,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }.items() if v is not None}
    
    _get_client().table("documents").update(new_data).eq("id", doc_id).execute()
    log_action(user_id, "document_updated", "document", doc_id, old_values=old, new_values=new_data)


def delete_document(doc_id: str, user_id: str):
    """
    Deletes a document entry from the knowledge base.
    """
    old = get_document(doc_id)
    _get_client().table("documents").delete().eq("id", doc_id).execute()
    log_action(user_id, "document_deleted", "document", doc_id, old_values=old)
