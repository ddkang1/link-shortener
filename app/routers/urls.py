from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ShortenRequest, ShortenResponse, StatsResponse
import app.services as services

router = APIRouter()


@router.post("/shorten", response_model=ShortenResponse)
def shorten(request: Request, payload: ShortenRequest, db: Session = Depends(get_db)):
    base_url = str(request.base_url).rstrip("/")
    url_obj = services.shorten_url(db, payload.url, base_url)
    short_url = f"{base_url}/{url_obj.short_code}"
    return ShortenResponse(short_code=url_obj.short_code, short_url=short_url)


@router.get("/stats/{short_code}", response_model=StatsResponse)
def stats(short_code: str, db: Session = Depends(get_db)):
    url_obj = services.get_stats(db, short_code)
    return StatsResponse(
        original_url=url_obj.original_url,
        short_code=url_obj.short_code,
        click_count=url_obj.click_count,
        created_at=url_obj.created_at,
    )


@router.get("/{short_code}")
def redirect(short_code: str, db: Session = Depends(get_db)):
    original_url = services.increment_and_redirect(db, short_code)
    return RedirectResponse(url=original_url, status_code=302)
