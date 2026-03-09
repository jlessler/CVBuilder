from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


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
# Education
# ---------------------------------------------------------------------------

class EducationBase(BaseModel):
    degree: Optional[str] = None
    year: Optional[int] = None
    subject: Optional[str] = None
    school: Optional[str] = None
    sort_order: int = 0

class EducationCreate(EducationBase):
    pass

class EducationOut(EducationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------

class ExperienceBase(BaseModel):
    title: Optional[str] = None
    years_start: Optional[str] = None
    years_end: Optional[str] = None
    employer: Optional[str] = None
    sort_order: int = 0

class ExperienceCreate(ExperienceBase):
    pass

class ExperienceOut(ExperienceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# Consulting
# ---------------------------------------------------------------------------

class ConsultingBase(BaseModel):
    title: Optional[str] = None
    years: Optional[str] = None
    employer: Optional[str] = None
    sort_order: int = 0

class ConsultingCreate(ConsultingBase):
    pass

class ConsultingOut(ConsultingBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# Membership
# ---------------------------------------------------------------------------

class MembershipBase(BaseModel):
    org: Optional[str] = None
    years: Optional[str] = None
    sort_order: int = 0

class MembershipCreate(MembershipBase):
    pass

class MembershipOut(MembershipBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

class PanelBase(BaseModel):
    panel: Optional[str] = None
    org: Optional[str] = None
    role: Optional[str] = None
    date: Optional[str] = None
    panel_id: Optional[str] = None
    type: str = "advisory"
    sort_order: int = 0

class PanelCreate(PanelBase):
    pass

class PanelOut(PanelBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# Symposium
# ---------------------------------------------------------------------------

class SymposiumBase(BaseModel):
    title: Optional[str] = None
    meeting: Optional[str] = None
    date: Optional[str] = None
    role: Optional[str] = None
    sort_order: int = 0

class SymposiumCreate(SymposiumBase):
    pass

class SymposiumOut(SymposiumBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# Class (teaching)
# ---------------------------------------------------------------------------

class ClassBase(BaseModel):
    class_name: Optional[str] = None
    year: Optional[int] = None
    role: Optional[str] = None
    school: Optional[str] = None
    students: Optional[str] = None
    lectures: Optional[str] = None
    in_three_year: Optional[bool] = False
    sort_order: int = 0

    @field_validator('students', 'lectures', mode='before')
    @classmethod
    def coerce_to_str(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

class ClassCreate(ClassBase):
    pass

class ClassOut(ClassBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# Grant
# ---------------------------------------------------------------------------

class GrantBase(BaseModel):
    title: Optional[str] = None
    agency: Optional[str] = None
    pi: Optional[str] = None
    amount: Optional[str] = None
    years_start: Optional[str] = None
    years_end: Optional[str] = None
    role: Optional[str] = None
    id_number: Optional[str] = None
    description: Optional[str] = None
    grant_type: Optional[str] = None
    pcteffort: Optional[int] = None
    status: Optional[str] = None
    sort_order: int = 0

class GrantCreate(GrantBase):
    pass

class GrantOut(GrantBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# Award
# ---------------------------------------------------------------------------

class AwardBase(BaseModel):
    name: Optional[str] = None
    year: Optional[str] = None
    org: Optional[str] = None
    date: Optional[str] = None
    sort_order: int = 0

class AwardCreate(AwardBase):
    pass

class AwardOut(AwardBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# Press
# ---------------------------------------------------------------------------

class PressBase(BaseModel):
    outlet: Optional[str] = None
    title: Optional[str] = None
    date: Optional[str] = None
    url: Optional[str] = None
    topic: Optional[str] = None
    sort_order: int = 0

class PressCreate(PressBase):
    pass

class PressOut(PressBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# Trainee
# ---------------------------------------------------------------------------

class TraineeBase(BaseModel):
    name: Optional[str] = None
    degree: Optional[str] = None
    years_start: Optional[str] = None
    years_end: Optional[str] = None
    type: Optional[str] = None
    school: Optional[str] = None
    thesis: Optional[str] = None
    current_position: Optional[str] = None
    trainee_type: str = "advisee"
    sort_order: int = 0

class TraineeCreate(TraineeBase):
    pass

class TraineeOut(TraineeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# Committee
# ---------------------------------------------------------------------------

class CommitteeBase(BaseModel):
    committee: Optional[str] = None
    org: Optional[str] = None
    role: Optional[str] = None
    dates: Optional[str] = None
    sort_order: int = 0

class CommitteeCreate(CommitteeBase):
    pass

class CommitteeOut(CommitteeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------------------------------------------------------------------------
# MiscSection
# ---------------------------------------------------------------------------

class MiscSectionBase(BaseModel):
    section: str
    data: dict[str, Any]
    sort_order: int = 0

class MiscSectionCreate(MiscSectionBase):
    pass

class MiscSectionOut(MiscSectionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


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
