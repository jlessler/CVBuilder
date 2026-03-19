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
    is_admin: bool = False
    created_at: Optional[datetime] = None


class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    full_name: Optional[str] = None

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
    semantic_scholar_id: Optional[str] = None
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

class ScholarlyOutputStats(BaseModel):
    total_works: int = 0
    counts_by_type: dict[str, int] = {}
    works_by_year: list[dict] = []  # [{year, count}]
    first_author_count: int = 0
    corresponding_author_count: int = 0
    senior_author_count: int = 0
    student_led_count: int = 0
    h_index: int = 0
    i10_index: int = 0
    total_citations: int = 0
    citations_by_year: list[dict] = []  # [{year, count}]

class TraineeDetail(BaseModel):
    name: str = ""
    degree: str = ""
    advisor_type: str = ""
    institution: str = ""
    period: str = ""
    current_position: str = ""
    is_current: bool = False

class MentorshipCategory(BaseModel):
    count: int = 0
    current: int = 0
    trainees: list[TraineeDetail] = []

class RoleCount(BaseModel):
    role: str
    count: int

class TeachingStats(BaseModel):
    courses_total: int = 0
    courses_three_year: int = 0
    unique_courses: int = 0
    by_role: list[RoleCount] = []
    by_role_five_year: list[RoleCount] = []

class MentorshipStats(BaseModel):
    total: int = 0
    current: int = 0
    postdoctoral: MentorshipCategory = MentorshipCategory()
    doctoral: MentorshipCategory = MentorshipCategory()
    masters: MentorshipCategory = MentorshipCategory()
    undergraduate: MentorshipCategory = MentorshipCategory()
    other: MentorshipCategory = MentorshipCategory()

class TeachingMentorshipStats(BaseModel):
    teaching: TeachingStats = TeachingStats()
    mentorship: MentorshipStats = MentorshipStats()
    # Legacy flat fields kept for backward compat
    courses_total: int = 0
    courses_three_year: int = 0
    unique_courses: int = 0
    trainees_total: int = 0
    trainee_breakdown: list[dict] = []  # [{type, count}]
    current_trainees: int = 0

class GrantDetail(BaseModel):
    title: str = ""
    agency: str = ""
    role: str = ""
    period: str = ""
    amount: str = ""
    id_number: str = ""

class GrantCategoryStats(BaseModel):
    count: int = 0
    total_amount: float = 0.0
    total_amount_display: str = ""
    by_role: list[dict] = []  # [{role, count}]
    grants: list[GrantDetail] = []

class FundingStats(BaseModel):
    grants_total: int = 0
    total_funding_amount: str = ""
    total_funding_raw: float = 0.0
    active: GrantCategoryStats = GrantCategoryStats()
    completed: GrantCategoryStats = GrantCategoryStats()

class ServiceStats(BaseModel):
    committees: int = 0
    advisory_panels: int = 0
    grant_review_panels: int = 0
    symposia: int = 0
    editorial: int = 0
    peer_review: int = 0
    service_breakdown: list[dict] = []  # [{label, count}]

class DashboardData(BaseModel):
    profile_complete: bool = False
    scholarly_output: ScholarlyOutputStats = ScholarlyOutputStats()
    teaching_mentorship: TeachingMentorshipStats = TeachingMentorshipStats()
    funding: FundingStats = FundingStats()
    service: ServiceStats = ServiceStats()
