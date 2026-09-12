"""
Storage package init.
"""
from src.storage.repository import RepositoryInterface, SQLiteRepository

__all__ = ["RepositoryInterface", "SQLiteRepository"]
