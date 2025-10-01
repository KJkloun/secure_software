"""FastAPI приложение для каталога идей с оценкой ценности.

Сервис держит состояния в оперативной памяти: этого достаточно для учебных
примеров и автотестов. Когда модель станет сложнее, хранилище можно заменить на
реальную базу, при этом схемы запросов/ответов менять не придётся.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, constr, validator

app = FastAPI(title="Idea Catalog", version="0.2.0")


class ApiError(Exception):
    """Контролируемая ошибка домена.

    Через неё мы отправляем пользователю понятные ответы, не полагаясь на
    внутренние тексты исключений.
    """

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        self.code = code
        self.message = message
        self.status = status


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    """Форматируем доменные ошибки в единый JSON-ответ."""
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Нормализуем исключения FastAPI, чтобы клиент всегда видел нашу обёртку."""
    detail = exc.detail if isinstance(exc.detail, str) else "http_error"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": detail}},
    )


@app.get("/health")
def health():
    """Простой пинг, чтобы CI и деплой понимали, что сервис жив."""
    return {"status": "ok"}


class IdeaStatus(str, Enum):
    """Статус идеи в жизненном цикле каталога."""

    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    archived = "archived"


@dataclass
class Evaluation:
    value: int
    effort: int
    confidence: int
    comment: Optional[str] = None


@dataclass
class IdeaRecord:
    id: int
    title: str
    description: str
    tags: List[str]
    status: IdeaStatus = IdeaStatus.draft
    evaluations: List[Evaluation] = field(default_factory=list)


class ScoreSummary(BaseModel):
    value: Optional[float] = None
    confidence: Optional[float] = None
    effort: Optional[float] = None
    impact: Optional[float] = None
    votes: int = 0

    @classmethod
    def from_evaluations(cls, evaluations: List[Evaluation]) -> "ScoreSummary":
        """Считает усреднённые метрики по всем оценкам идеи."""
        if not evaluations:
            return cls()

        votes = len(evaluations)
        total_value = 0.0
        total_confidence = 0.0
        total_effort = 0.0

        for item in evaluations:
            total_value += item.value
            total_confidence += item.confidence
            total_effort += item.effort

        avg_value = round(total_value / votes, 2)
        avg_confidence = round(total_confidence / votes, 2)
        avg_effort = round(total_effort / votes, 2)
        impact = round((avg_value * avg_confidence) / max(avg_effort, 1), 2)

        return cls(
            value=avg_value,
            confidence=avg_confidence,
            effort=avg_effort,
            impact=impact,
            votes=votes,
        )


class IdeaResponse(BaseModel):
    id: int
    title: str
    description: str
    tags: List[str]
    status: IdeaStatus
    score: ScoreSummary

    @classmethod
    def from_record(cls, record: IdeaRecord) -> "IdeaResponse":
        """Создаёт ответ API на основе состояния в памяти."""
        score = ScoreSummary.from_evaluations(record.evaluations)
        return cls(
            id=record.id,
            title=record.title,
            description=record.description,
            tags=record.tags,
            status=record.status,
            score=score,
        )


class IdeaCreate(BaseModel):
    title: constr(min_length=3, max_length=120)
    description: constr(min_length=10, max_length=2000)
    tags: List[constr(min_length=1, max_length=30)] = Field(default_factory=list)

    @validator("title")
    def tidy_title(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("title must contain at least 3 characters")
        return cleaned

    @validator("description")
    def tidy_description(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("description must contain at least 10 characters")
        return cleaned

    @validator("tags", each_item=True)
    def tidy_tag(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("tag cannot be blank")
        return cleaned


class IdeaUpdate(BaseModel):
    title: Optional[constr(min_length=3, max_length=120)] = None
    description: Optional[constr(min_length=10, max_length=2000)] = None
    status: Optional[str] = None
    tags: Optional[List[constr(min_length=1, max_length=30)]] = None

    @validator("title")
    def tidy_title(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise ValueError("title must contain at least 3 characters")
        return cleaned

    @validator("description")
    def tidy_description(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise ValueError("description must contain at least 10 characters")
        return cleaned

    @validator("tags")
    def tidy_tags(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return None
        cleaned: List[str] = []
        for raw in value:
            tag = raw.strip().lower()
            if not tag:
                raise ValueError("tag cannot be blank")
            cleaned.append(tag)
        return cleaned

    @validator("status")
    def tidy_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            raise ValueError("status cannot be blank")
        return cleaned


class EvaluationCreate(BaseModel):
    value: int = Field(..., ge=1, le=10)
    effort: int = Field(..., ge=1, le=10)
    confidence: int = Field(..., ge=1, le=10)
    comment: Optional[constr(max_length=500)] = None

    @validator("comment")
    def tidy_comment(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class IdeaStorage:
    """Миниатюрное in-memory хранилище для идей.

    В продакшене здесь будет база данных, но интерфейс оставим тем же самым.
    """

    def __init__(self) -> None:
        self._ideas: Dict[int, IdeaRecord] = {}
        self._next_id = 1

    def create(self, payload: IdeaCreate) -> IdeaResponse:
        """Создаёт идею и возвращает её состояние."""
        tags = sorted({tag for tag in payload.tags})
        record = IdeaRecord(
            id=self._next_id,
            title=payload.title.strip(),
            description=payload.description.strip(),
            tags=tags,
        )
        self._ideas[record.id] = record
        self._next_id += 1
        return IdeaResponse.from_record(record)

    def list(
        self,
        *,
        tag: Optional[str] = None,
        status: Optional[IdeaStatus] = None,
        min_score: Optional[float] = None,
    ) -> List[IdeaResponse]:
        ideas = []
        for record in sorted(self._ideas.values(), key=lambda item: item.id):
            idea = IdeaResponse.from_record(record)
            if tag and tag.lower() not in idea.tags:
                continue
            if status and idea.status != status:
                continue
            if min_score is not None:
                current_score = idea.score.value
                if current_score is None or current_score < min_score:
                    continue
            ideas.append(idea)
        return ideas

    def get(self, idea_id: int) -> IdeaResponse:
        """Возвращает идею по идентификатору или отдаёт 404."""
        record = self._get_or_raise(idea_id)
        return IdeaResponse.from_record(record)

    def update(self, idea_id: int, payload: IdeaUpdate) -> IdeaResponse:
        """Обновляет только те поля, которые передал клиент."""
        record = self._get_or_raise(idea_id)

        if payload.title is not None:
            record.title = payload.title.strip()
        if payload.description is not None:
            record.description = payload.description.strip()
        if payload.status is not None:
            try:
                record.status = IdeaStatus(payload.status)
            except ValueError:
                raise ApiError(
                    code="invalid_status", message="unsupported status", status=422
                )
        if payload.tags is not None:
            record.tags = sorted({tag for tag in payload.tags})

        return IdeaResponse.from_record(record)

    def add_evaluation(self, idea_id: int, payload: EvaluationCreate) -> IdeaResponse:
        """Добавляет новую оценку и возвращает идею с пересчитанным рейтингом."""
        record = self._get_or_raise(idea_id)
        entry = Evaluation(
            value=payload.value,
            effort=payload.effort,
            confidence=payload.confidence,
            comment=payload.comment,
        )
        record.evaluations.append(entry)
        return IdeaResponse.from_record(record)

    def evaluations(self, idea_id: int) -> List[Dict[str, object]]:
        """История оценок для детального просмотра в интерфейсе/тестах."""
        record = self._get_or_raise(idea_id)
        history: List[Dict[str, object]] = []
        for item in record.evaluations:
            history.append(
                {
                    "value": item.value,
                    "effort": item.effort,
                    "confidence": item.confidence,
                    "comment": item.comment,
                }
            )
        return history

    def clear(self) -> None:
        """Сбрасывает состояние. Используется в тестах."""
        self._ideas.clear()
        self._next_id = 1

    def _get_or_raise(self, idea_id: int) -> IdeaRecord:
        """Утилита, чтобы не дублировать проверку на существование."""
        if idea_id not in self._ideas:
            raise ApiError(code="idea_not_found", message="idea not found", status=404)
        return self._ideas[idea_id]


storage = IdeaStorage()


@app.post("/ideas", response_model=IdeaResponse, status_code=201)
def create_idea(payload: IdeaCreate):
    """Создать новую идею о продукте."""
    try:
        return storage.create(payload)
    except ValueError as exc:
        raise ApiError(code="validation_error", message=str(exc), status=422)


@app.get("/ideas", response_model=List[IdeaResponse])
def list_ideas(
    tag: Optional[str] = Query(default=None, description="Filter ideas by tag"),
    min_score: Optional[float] = Query(
        default=None,
        ge=0,
        le=10,
        description="Only return ideas with average value score at or above this number",
    ),
    status: Optional[str] = Query(
        default=None, description="Filter by workflow status"
    ),
):
    """Получить список идей с простыми фильтрами."""
    status_filter: Optional[IdeaStatus] = None
    if status:
        try:
            status_filter = IdeaStatus(status)
        except ValueError:
            raise ApiError(
                code="invalid_status", message="unsupported status", status=422
            )

    return storage.list(tag=tag, status=status_filter, min_score=min_score)


@app.get("/ideas/{idea_id}", response_model=IdeaResponse)
def get_idea(idea_id: int):
    """Вернуть одну идею. Полезно для карточки в интерфейсе."""
    return storage.get(idea_id)


@app.patch("/ideas/{idea_id}", response_model=IdeaResponse)
def update_idea(idea_id: int, payload: IdeaUpdate):
    """Обновить описание, статус или теги существующей идеи."""
    updates = payload.dict(exclude_unset=True)
    if not updates:
        raise ApiError(code="validation_error", message="payload is empty", status=422)

    try:
        return storage.update(idea_id, payload)
    except ValueError as exc:
        raise ApiError(code="validation_error", message=str(exc), status=422)


@app.post("/ideas/{idea_id}/evaluations", response_model=IdeaResponse)
def evaluate_idea(idea_id: int, payload: EvaluationCreate):
    """Сохранить свежую оценку и вернуть пересчитанный рейтинг."""
    return storage.add_evaluation(idea_id, payload)


@app.get("/ideas/{idea_id}/evaluations")
def list_evaluations(idea_id: int):
    """Посмотреть все оценки, которые команда оставила по идее."""
    return storage.evaluations(idea_id)
