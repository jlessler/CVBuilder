from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------------------
# User table
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(500))
    full_name: Mapped[Optional[str]] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


# ---------------------------------------------------------------------------
# Profile tables
# ---------------------------------------------------------------------------

class Profile(Base):
    __tablename__ = "profile"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[Optional[str]] = mapped_column(String(200))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(100))
    website: Mapped[Optional[str]] = mapped_column(String(500))
    orcid: Mapped[Optional[str]] = mapped_column(String(100))
    linkedin: Mapped[Optional[str]] = mapped_column(String(200))
    addresses: Mapped[list["Address"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", order_by="Address.line_order"
    )


class Address(Base):
    __tablename__ = "addresses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profile.id"))
    type: Mapped[str] = mapped_column(String(20), default="work")  # home | work
    line_order: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(String(500))
    profile: Mapped["Profile"] = relationship(back_populates="addresses")


class Education(Base):
    __tablename__ = "education"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    degree: Mapped[Optional[str]] = mapped_column(String(100))
    year: Mapped[Optional[int]] = mapped_column(Integer)
    subject: Mapped[Optional[str]] = mapped_column(String(200))
    school: Mapped[Optional[str]] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Experience(Base):
    __tablename__ = "experience"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    title: Mapped[Optional[str]] = mapped_column(String(300))
    years_start: Mapped[Optional[str]] = mapped_column(String(50))
    years_end: Mapped[Optional[str]] = mapped_column(String(50))
    employer: Mapped[Optional[str]] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Consulting(Base):
    __tablename__ = "consulting"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    title: Mapped[Optional[str]] = mapped_column(String(300))
    years: Mapped[Optional[str]] = mapped_column(String(100))
    employer: Mapped[Optional[str]] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Membership(Base):
    __tablename__ = "memberships"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    org: Mapped[Optional[str]] = mapped_column(String(500))
    years: Mapped[Optional[str]] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Panel(Base):
    __tablename__ = "panels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    panel: Mapped[Optional[str]] = mapped_column(Text)
    org: Mapped[Optional[str]] = mapped_column(Text)
    role: Mapped[Optional[str]] = mapped_column(String(200))
    date: Mapped[Optional[str]] = mapped_column(String(100))
    panel_id: Mapped[Optional[str]] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(50), default="advisory")  # advisory | grant_review
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Patent(Base):
    __tablename__ = "patents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[Optional[str]] = mapped_column(Text)
    number: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[Optional[str]] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    authors: Mapped[list["PatentAuthor"]] = relationship(
        back_populates="patent", cascade="all, delete-orphan", order_by="PatentAuthor.author_order"
    )


class PatentAuthor(Base):
    __tablename__ = "patents_authors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patent_id: Mapped[int] = mapped_column(ForeignKey("patents.id"))
    author_name: Mapped[str] = mapped_column(String(300))
    author_order: Mapped[int] = mapped_column(Integer, default=0)
    patent: Mapped["Patent"] = relationship(back_populates="authors")


class Symposium(Base):
    __tablename__ = "symposia"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    title: Mapped[Optional[str]] = mapped_column(Text)
    meeting: Mapped[Optional[str]] = mapped_column(Text)
    date: Mapped[Optional[str]] = mapped_column(String(100))
    role: Mapped[Optional[str]] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Class(Base):
    __tablename__ = "classes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    class_name: Mapped[Optional[str]] = mapped_column(Text)
    year: Mapped[Optional[int]] = mapped_column(Integer)
    role: Mapped[Optional[str]] = mapped_column(String(200))
    school: Mapped[Optional[str]] = mapped_column(String(500))
    students: Mapped[Optional[str]] = mapped_column(String(50))
    lectures: Mapped[Optional[str]] = mapped_column(String(50))
    in_three_year: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Grant(Base):
    __tablename__ = "grants"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    title: Mapped[Optional[str]] = mapped_column(Text)
    agency: Mapped[Optional[str]] = mapped_column(String(500))
    pi: Mapped[Optional[str]] = mapped_column(String(300))
    amount: Mapped[Optional[str]] = mapped_column(String(200))
    years_start: Mapped[Optional[str]] = mapped_column(String(50))
    years_end: Mapped[Optional[str]] = mapped_column(String(50))
    role: Mapped[Optional[str]] = mapped_column(String(200))
    id_number: Mapped[Optional[str]] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    grant_type: Mapped[Optional[str]] = mapped_column(String(100))
    pcteffort: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[Optional[str]] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Award(Base):
    __tablename__ = "awards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[Optional[str]] = mapped_column(Text)
    year: Mapped[Optional[str]] = mapped_column(String(50))
    org: Mapped[Optional[str]] = mapped_column(String(500))
    date: Mapped[Optional[str]] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Press(Base):
    __tablename__ = "press"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    outlet: Mapped[Optional[str]] = mapped_column(String(500))
    title: Mapped[Optional[str]] = mapped_column(Text)
    date: Mapped[Optional[str]] = mapped_column(String(100))
    url: Mapped[Optional[str]] = mapped_column(String(1000))
    topic: Mapped[Optional[str]] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Trainee(Base):
    __tablename__ = "trainees"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[Optional[str]] = mapped_column(String(300))
    degree: Mapped[Optional[str]] = mapped_column(String(100))
    years_start: Mapped[Optional[str]] = mapped_column(String(50))
    years_end: Mapped[Optional[str]] = mapped_column(String(50))
    type: Mapped[Optional[str]] = mapped_column(String(100))  # advisor | co-advisor | etc.
    school: Mapped[Optional[str]] = mapped_column(String(500))
    thesis: Mapped[Optional[str]] = mapped_column(Text)
    current_position: Mapped[Optional[str]] = mapped_column(String(500))
    trainee_type: Mapped[str] = mapped_column(String(50), default="advisee")  # advisee | postdoc
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Seminar(Base):
    """Invited seminars / talks."""
    __tablename__ = "seminars"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    title: Mapped[Optional[str]] = mapped_column(Text)
    org: Mapped[Optional[str]] = mapped_column(String(500))
    date: Mapped[Optional[str]] = mapped_column(String(100))
    location: Mapped[Optional[str]] = mapped_column(String(300))
    event: Mapped[Optional[str]] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Committee(Base):
    """Committee memberships (departmental, school, university)."""
    __tablename__ = "committees"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    committee: Mapped[Optional[str]] = mapped_column(Text)
    org: Mapped[Optional[str]] = mapped_column(String(500))
    role: Mapped[Optional[str]] = mapped_column(String(200))
    dates: Mapped[Optional[str]] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


# Misc single-item section rows (editor roles, peer-review list, software, policy, etc.)
class MiscSection(Base):
    """Generic key-value store for miscellaneous CV sections."""
    __tablename__ = "misc_sections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    section: Mapped[str] = mapped_column(String(100))   # e.g. "editor", "peerrev", "software"
    data: Mapped[dict] = mapped_column(JSON)             # flexible payload
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


# ---------------------------------------------------------------------------
# Works tables (unified scholarly outputs)
# ---------------------------------------------------------------------------

class Work(Base):
    """Unified model for all authored scholarly outputs."""
    __tablename__ = "works"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    work_type: Mapped[str] = mapped_column(String(50))  # papers|preprints|chapters|letters|scimeetings|editorials|patents|software|dissertation|seminars
    title: Mapped[Optional[str]] = mapped_column(Text)
    year: Mapped[Optional[int]] = mapped_column(Integer)
    month: Mapped[Optional[int]] = mapped_column(Integer)
    day: Mapped[Optional[int]] = mapped_column(Integer)
    doi: Mapped[Optional[str]] = mapped_column(String(500))
    data: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    authors: Mapped[list["WorkAuthor"]] = relationship(
        back_populates="work", cascade="all, delete-orphan", order_by="WorkAuthor.author_order"
    )

    def __getattr__(self, name):
        if name.startswith('_') or name in (
            'id', 'user_id', 'work_type', 'title', 'year', 'month', 'day',
            'doi', 'data', 'authors',
            'metadata', 'registry', '__clause_element__',
        ):
            raise AttributeError(name)
        data = object.__getattribute__(self, 'data')
        if data and name in data:
            return data[name]
        return None


class WorkAuthor(Base):
    __tablename__ = "work_authors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    work_id: Mapped[int] = mapped_column(ForeignKey("works.id"))
    author_name: Mapped[str] = mapped_column(String(300))
    author_order: Mapped[int] = mapped_column(Integer, default=0)
    student: Mapped[bool] = mapped_column(Boolean, default=False)
    corresponding: Mapped[bool] = mapped_column(Boolean, default=False)
    cofirst: Mapped[bool] = mapped_column(Boolean, default=False)
    cosenior: Mapped[bool] = mapped_column(Boolean, default=False)
    work: Mapped["Work"] = relationship(back_populates="authors")


# ---------------------------------------------------------------------------
# Publications tables
# ---------------------------------------------------------------------------

class Publication(Base):
    __tablename__ = "publications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(50))  # papers | preprints | chapters | letters | scimeetings
    title: Mapped[Optional[str]] = mapped_column(Text)
    year: Mapped[Optional[str]] = mapped_column(String(20))
    journal: Mapped[Optional[str]] = mapped_column(Text)
    volume: Mapped[Optional[str]] = mapped_column(String(50))
    issue: Mapped[Optional[str]] = mapped_column(String(50))
    pages: Mapped[Optional[str]] = mapped_column(String(100))
    doi: Mapped[Optional[str]] = mapped_column(String(500))
    corr: Mapped[bool] = mapped_column(Boolean, default=False)
    cofirsts: Mapped[int] = mapped_column(Integer, default=0)
    coseniors: Mapped[int] = mapped_column(Integer, default=0)
    select_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    # For scimeetings
    conference: Mapped[Optional[str]] = mapped_column(Text)
    pres_type: Mapped[Optional[str]] = mapped_column(String(100))
    # For chapters
    publisher: Mapped[Optional[str]] = mapped_column(Text)
    # Cross-references between preprints and published versions
    preprint_doi: Mapped[Optional[str]] = mapped_column(String(500))
    published_doi: Mapped[Optional[str]] = mapped_column(String(500))
    authors: Mapped[list["PubAuthor"]] = relationship(
        back_populates="publication", cascade="all, delete-orphan", order_by="PubAuthor.author_order"
    )


class PubAuthor(Base):
    __tablename__ = "pub_authors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pub_id: Mapped[int] = mapped_column(ForeignKey("publications.id"))
    author_name: Mapped[str] = mapped_column(String(300))
    author_order: Mapped[int] = mapped_column(Integer, default=0)
    student: Mapped[bool] = mapped_column(Boolean, default=False)
    publication: Mapped["Publication"] = relationship(back_populates="authors")


# ---------------------------------------------------------------------------
# Template tables
# ---------------------------------------------------------------------------

class CVTemplate(Base):
    __tablename__ = "cv_templates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    style: Mapped[Optional[dict]] = mapped_column(JSON)
    sort_direction: Mapped[str] = mapped_column(String(20), default="desc")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    sections: Mapped[list["TemplateSection"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="TemplateSection.section_order"
    )


class TemplateSection(Base):
    __tablename__ = "template_sections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("cv_templates.id"))
    section_key: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    section_order: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[Optional[dict]] = mapped_column(JSON)  # heading text, etc.
    template: Mapped["CVTemplate"] = relationship(back_populates="sections")


# ---------------------------------------------------------------------------
# CV Instance tables — curated CV versions linked to a template
# ---------------------------------------------------------------------------

class CVInstance(Base):
    __tablename__ = "cv_instances"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    template_id: Mapped[int] = mapped_column(Integer, ForeignKey("cv_templates.id"))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    style_overrides: Mapped[Optional[dict]] = mapped_column(JSON)
    sort_direction_override: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    template: Mapped["CVTemplate"] = relationship()
    sections: Mapped[list["CVInstanceSection"]] = relationship(
        back_populates="cv_instance", cascade="all, delete-orphan",
        order_by="CVInstanceSection.section_order",
    )


class CVInstanceSection(Base):
    __tablename__ = "cv_instance_sections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cv_instance_id: Mapped[int] = mapped_column(Integer, ForeignKey("cv_instances.id", ondelete="CASCADE"))
    section_key: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)  # null = inherit
    section_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    heading_override: Mapped[Optional[str]] = mapped_column(String(300))
    config_overrides: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    curated: Mapped[bool] = mapped_column(Boolean, default=False)
    cv_instance: Mapped["CVInstance"] = relationship(back_populates="sections")
    items: Mapped[list["CVInstanceItem"]] = relationship(
        back_populates="section", cascade="all, delete-orphan",
    )


class CVInstanceItem(Base):
    __tablename__ = "cv_instance_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cv_instance_section_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cv_instance_sections.id", ondelete="CASCADE"),
    )
    item_id: Mapped[int] = mapped_column(Integer)
    section: Mapped["CVInstanceSection"] = relationship(back_populates="items")
