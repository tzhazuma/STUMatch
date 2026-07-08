"""Pydantic schemas for request/response models."""
import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Common wrapper
class ApiResponse(BaseModel):
    data: Any | None = None
    error: str | None = None
    message: str | None = None


class TokenData(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class VerificationCodeRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    purpose: Literal["register", "login", "reset_password"] = "register"


class VerificationCodeResponse(BaseModel):
    ok: bool
    provider: str
    target: str | None


class RegisterRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    code: str
    password: str = Field(..., min_length=6)
    nickname: str = Field(..., min_length=1, max_length=64)
    school: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str | None
    phone: str | None
    nickname: str
    school: str | None
    role: str
    status: str
    is_verified_email: bool
    is_verified_school: bool
    created_at: datetime | None
    updated_at: datetime | None


class UserMeUpdate(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    nickname: str
    avatar_url: str | None
    gender: str | None
    birth_date: date | None
    age: int | None
    education_level: str | None
    school: str | None = None
    major: str | None
    mbti: str | None
    interests: list[str]
    location: str | None
    bio: str | None
    research_direction: str | None
    dating_purpose: str | None
    family_status: str | None
    ideal_person: str | None
    is_verified_email: bool = False
    is_verified_school: bool = False
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    nickname: str | None = Field(None, min_length=1, max_length=64)
    avatar_url: str | None = None
    gender: Literal["male", "female", "other"] | None = None
    birth_date: date | None = None
    age: int | None = None
    education_level: Literal["undergraduate", "master", "phd", "other"] | None = None
    major: str | None = None
    mbti: str | None = None
    interests: list[str] | None = None
    location: str | None = None
    bio: str | None = None
    research_direction: str | None = None
    dating_purpose: str | None = None
    family_status: str | None = None
    ideal_person: str | None = None


class AvatarOut(BaseModel):
    avatar_url: str


class ConsentRequest(BaseModel):
    consent_type: str
    granted: bool


class DiscoveryUser(BaseModel):
    user_id: uuid.UUID
    nickname: str
    avatar_url: str | None
    age: int | None
    education_level: str | None
    major: str | None
    interests: list[str]
    location: str | None
    match_score: float
    match_reason: str


class DiscoveryListResponse(BaseModel):
    items: list[DiscoveryUser]
    total: int
    page: int
    limit: int


class DiscoveryProfileOut(BaseModel):
    user_id: uuid.UUID
    nickname: str
    avatar_url: str | None
    age: int | None
    education_level: str | None
    school: str | None
    major: str | None
    mbti: str | None
    interests: list[str]
    location: str | None
    bio: str | None
    research_direction: str | None
    dating_purpose: str | None
    family_status: str | None
    ideal_person: str | None


class PushToggle(BaseModel):
    enabled: bool


class QuestionnaireOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    section: str
    description: str | None
    questions: list[dict]
    is_active: bool
    created_at: datetime


class QuestionnaireResponseIn(BaseModel):
    answers: dict[str, Any]


class QuestionnaireResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    questionnaire_id: uuid.UUID
    user_id: uuid.UUID
    answers: dict
    created_at: datetime
    updated_at: datetime


class MatchRecommendationOut(BaseModel):
    user_id: uuid.UUID
    nickname: str
    avatar_url: str | None
    age: int | None
    education_level: str | None
    major: str | None
    interests: list[str]
    location: str | None
    match_score: float
    match_reason: str


class MatchFeedbackIn(BaseModel):
    section: Literal["academic", "daily", "dating"]
    action: Literal["like", "dislike", "skip"]


class FriendRequestIn(BaseModel):
    to_user_id: uuid.UUID
    message: str | None = None


class FriendRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requester_id: uuid.UUID
    addressee_id: uuid.UUID
    message: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class FriendOut(BaseModel):
    user_id: uuid.UUID
    nickname: str
    avatar_url: str | None
    school: str | None
    major: str | None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    message_type: str
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class ConversationParticipant(BaseModel):
    id: uuid.UUID
    nickname: str
    avatar_url: str | None


class LastMessage(BaseModel):
    content: str
    created_at: datetime


class ConversationOut(BaseModel):
    id: uuid.UUID
    participant: ConversationParticipant
    last_message: LastMessage | None
    unread_count: int


class MessageIn(BaseModel):
    content: str
    message_type: Literal["text", "image"] = "text"


class MessageBoardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    section: str
    owner_id: uuid.UUID
    author_id: uuid.UUID
    author_nickname: str
    content: str
    created_at: datetime


class MessageBoardIn(BaseModel):
    owner_id: uuid.UUID
    content: str


class ReportIn(BaseModel):
    target_type: Literal["user", "message", "content"]
    target_id: str
    reason: str
    description: str | None = None


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reporter_id: uuid.UUID
    target_type: str
    target_id: str
    reason: str
    description: str | None
    status: str
    resolution: str | None
    created_at: datetime
    updated_at: datetime


class ModerationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    source: str
    triggered: bool
    words: list[str]
    created_at: datetime


class AIGenerateQuestionsIn(BaseModel):
    section: Literal["academic", "daily", "dating"] = "daily"
    count: int = Field(default=3, ge=1, le=10)


class AIQuestion(BaseModel):
    id: str
    text: str
    type: str
    options: list[str] | None = None


class AIGenerateQuestionsOut(BaseModel):
    questions: list[AIQuestion]


class AIMatchExplanationIn(BaseModel):
    target_user_id: uuid.UUID
    section: Literal["academic", "daily", "dating"] = "daily"


class AIMatchExplanationOut(BaseModel):
    explanation: str
    highlights: list[str]


class AdminUserStatusIn(BaseModel):
    status: Literal["active", "inactive", "suspended"]


class AdminReportResolveIn(BaseModel):
    status: Literal["resolved", "dismissed"]
    resolution: str
