from fastapi import APIRouter

from app.api.routes import documents, jobs, operations, signatures, system

router = APIRouter()
router.include_router(system.router)
router.include_router(documents.router)
router.include_router(operations.router)
router.include_router(jobs.router)
router.include_router(signatures.router)
