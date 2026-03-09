from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, EmailStr


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Profile schemas
# ---------------------------------------------------------------------------

class AddressBase(BaseModel):
    type: str = "work"
    line_order: int = 0
    text: str

class AddressCreate(AddressBase):
    pass

class AddressOut(AddressBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ProfileBase(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    orcid: Optional[str] = None
    linkedin: Optional[str] = None

class ProfileCreate(ProfileBase):
    addresses: list[AddressCreate] = []

class ProfileUpdate(ProfileBase):
    addresses: Optional[list[AddressCreate]] = None

class ProfileOut(ProfileBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    addresses: list[AddressOut] = []


# ---------------------------------------------------------------------------
# Works (unified scholarly outputs)
# ---------------------------------------------------------------------------

class WorkAuthorBase(BaseModel):
    author_name: str
    author_order: int = 0
    student: bool = False
    corresponding: bool = False
    cofirst: bool = False
    cosenior: bool = False

class WorkAuthorCreate(WorkAuthorBase):
    pass

class WorkAuthorOut(WorkAuthorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class WorkBase(BaseModel):
    work_type: str
    title: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    doi: Optional[str] = None
    data: Optional[dict[str, Any]] = None

class WorkCreate(WorkBase):
    authors: list[WorkAuthorCreate] = []

class WorkUpdate(WorkBase):
    authors: Optional[list[WorkAuthorCreate]] = None

class WorkOut(WorkBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    authors: list[WorkAuthorOut] = []


# ---------------------------------------------------------------------------
# CVItem (generic CV section items)
# ---------------------------------------------------------------------------

class CVItemBase(BaseModel):
    section: str
    data: dict[str, Any] = {}
    sort_order: int = 0

class CVItemCreate(CVItemBase):
    pass

class CVItemUpdate(BaseModel):
    data: Optional[dict[str, Any]] = None
    sort_order: Optional[int] = None

class CVItemOut(CVItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sort_date: Optional[int] = None


# ---------------------------------------------------------------------------
# Publications
# ---------------------------------------------------------------------------

class DOILookupRequest(BaseModel):
    doi: str

class DOILookupResponse(BaseModel):
    title: Optional[str] = None
    year: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    authors: list[str] = []
    doi: Optional[str] = None


class PublicationCandidate(BaseModel):
    title: str
    year: Optional[str] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    authors: list[str] = []
    source: str
    pmid: Optional[str] = None
    pub_type: str = "papers"
    match_warning: Optional[str] = None
    preprint_doi: Optional[str] = None
    published_doi: Optional[str] = None

class SyncCheckResponse(BaseModel):
    candidates: list[PublicationCandidate]
    searched: list[str]
    errors: dict[str, str] = {}

class SyncAddRequest(BaseModel):
    publications: list[PublicationCandidate]


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

class TemplateSectionBase(BaseModel):
    section_key: str
    enabled: bool = True
    section_order: int = 0
    config: Optional[dict] = None

class TemplateSectionCreate(TemplateSectionBase):
    pass

class TemplateSectionOut(TemplateSectionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CVTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    style: Optional[dict] = None
    sort_direction: str = "desc"

class CVTemplateCreate(CVTemplateBase):
    sections: list[TemplateSectionCreate] = []

class CVTemplateUpdate(CVTemplateBase):
    sections: Optional[list[TemplateSectionCreate]] = None

class CVTemplateOut(CVTemplateBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
    sections: list[TemplateSectionOut] = []


# ---------------------------------------------------------------------------
# CV Instances
# ---------------------------------------------------------------------------

class CVInstanceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    item_id: int


class CVInstanceSectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    section_key: str
    enabled: Optional[bool] = None
    section_order: Optional[int] = None
    heading_override: Optional[str] = None
    config_overrides: Optional[dict] = None
    curated: bool = False
    items: list[CVInstanceItemOut] = []


class CVInstanceCreate(BaseModel):
    name: str
    template_id: int
    description: Optional[str] = None
    style_overrides: Optional[dict] = None
    sort_direction_override: Optional[str] = None


class CVInstanceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    style_overrides: Optional[dict] = None
    sort_direction_override: Optional[str] = None


class CVInstanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    template_id: int
    name: str
    description: Optional[str] = None
    style_overrides: Optional[dict] = None
    sort_direction_override: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sections: list[CVInstanceSectionOut] = []
    template_name: Optional[str] = None


class CVInstanceSectionUpdate(BaseModel):
    section_key: str
    enabled: Optional[bool] = None
    section_order: Optional[int] = None
    heading_override: Optional[str] = None
    config_overrides: Optional[dict] = None
    curated: bool = False


class CVInstanceSectionsUpdate(BaseModel):
    sections: list[CVInstanceSectionUpdate]


class CVInstanceItemBulkUpdate(BaseModel):
    item_ids: list[int]


class AvailableItem(BaseModel):
    id: int
    label: str
    selected: bool = False


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------

class DashboardStats(BaseModel):
    total_publications: int
    papers: int
    preprints: int
    chapters: int
    letters: int
    scimeetings: int
    editorials: int = 0
    trainees: int
    grants: int
    profile_complete: bool
    active_grants: int = 0
    trainee_breakdown: list[dict] = []
    active_grant_breakdown: list[dict] = []
