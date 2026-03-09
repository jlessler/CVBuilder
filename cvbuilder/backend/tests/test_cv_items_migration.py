"""Tests for Phase 6: migration of typed section models and MiscSections
into the unified cv_items table."""
from app import models
from app.main import _migrate_cv_items_data


def test_migration_skips_when_items_exist(db_session, test_user):
    """If cv_items table already has rows, migration is a no-op."""
    db_session.add(models.CVItem(
        user_id=test_user.id, section="education", data={"degree": "PhD"},
    ))
    db_session.add(models.Education(
        user_id=test_user.id, degree="MS", year=2015,
    ))
    db_session.flush()

    _migrate_cv_items_data(db_session)
    assert db_session.query(models.CVItem).count() == 1


def test_migration_skips_when_no_source(db_session, test_user):
    """No source data → no items created."""
    _migrate_cv_items_data(db_session)
    assert db_session.query(models.CVItem).count() == 0


def test_migrate_education(db_session, test_user):
    db_session.add(models.Education(
        user_id=test_user.id, degree="PhD", year=2020,
        subject="Epidemiology", school="UNC",
    ))
    db_session.flush()

    _migrate_cv_items_data(db_session)

    items = db_session.query(models.CVItem).filter_by(section="education").all()
    assert len(items) == 1
    d = items[0].data
    assert d["degree"] == "PhD"
    assert d["year"] == 2020
    assert d["subject"] == "Epidemiology"
    assert d["school"] == "UNC"
    assert items[0].sort_date == 2020


def test_migrate_grants(db_session, test_user):
    db_session.add(models.Grant(
        user_id=test_user.id, title="Big Grant", agency="NIH",
        years_start="2022", years_end="2027", role="PI", status="active",
    ))
    db_session.flush()

    _migrate_cv_items_data(db_session)

    items = db_session.query(models.CVItem).filter_by(section="grants").all()
    assert len(items) == 1
    d = items[0].data
    assert d["title"] == "Big Grant"
    assert d["agency"] == "NIH"
    assert d["role"] == "PI"
    assert d["status"] == "active"
    assert items[0].sort_date == 2022


def test_migrate_panels_split_by_type(db_session, test_user):
    db_session.add(models.Panel(
        user_id=test_user.id, panel="DSMB", type="advisory", date="2023",
    ))
    db_session.add(models.Panel(
        user_id=test_user.id, panel="NIH Study", type="grant_review", date="2024",
    ))
    db_session.flush()

    _migrate_cv_items_data(db_session)

    adv = db_session.query(models.CVItem).filter_by(section="panels_advisory").all()
    gr = db_session.query(models.CVItem).filter_by(section="panels_grantreview").all()
    assert len(adv) == 1
    assert adv[0].data["panel"] == "DSMB"
    assert len(gr) == 1
    assert gr[0].data["panel"] == "NIH Study"


def test_migrate_trainees_split_by_type(db_session, test_user):
    db_session.add(models.Trainee(
        user_id=test_user.id, name="Student", trainee_type="advisee",
    ))
    db_session.add(models.Trainee(
        user_id=test_user.id, name="Postdoc", trainee_type="postdoc",
    ))
    db_session.flush()

    _migrate_cv_items_data(db_session)

    adv = db_session.query(models.CVItem).filter_by(section="trainees_advisees").all()
    pd = db_session.query(models.CVItem).filter_by(section="trainees_postdocs").all()
    assert len(adv) == 1
    assert adv[0].data["name"] == "Student"
    assert len(pd) == 1
    assert pd[0].data["name"] == "Postdoc"


def test_migrate_misc_sections_skips_software_dissertation(db_session, test_user):
    """MiscSections with section=software/dissertation are Works, not CVItems."""
    db_session.add(models.MiscSection(
        user_id=test_user.id, section="editorial",
        data={"journal": "Nature", "role": "Editor"},
    ))
    db_session.add(models.MiscSection(
        user_id=test_user.id, section="software",
        data={"title": "Tool"},
    ))
    db_session.add(models.MiscSection(
        user_id=test_user.id, section="dissertation",
        data={"title": "Thesis"},
    ))
    db_session.flush()

    _migrate_cv_items_data(db_session)

    items = db_session.query(models.CVItem).all()
    assert len(items) == 1
    assert items[0].section == "editorial"


def test_migrate_cv_instance_item_remapping(db_session, test_user):
    """CVInstanceItem IDs get remapped to new CVItem IDs."""
    edu = models.Education(user_id=test_user.id, degree="PhD", year=2020)
    db_session.add(edu)
    db_session.flush()
    old_id = edu.id

    tmpl = models.CVTemplate(user_id=test_user.id, name="Test", style={})
    db_session.add(tmpl)
    db_session.flush()
    inst = models.CVInstance(user_id=test_user.id, template_id=tmpl.id, name="Inst")
    db_session.add(inst)
    db_session.flush()
    sec = models.CVInstanceSection(
        cv_instance_id=inst.id, section_key="education",
        enabled=True, section_order=0,
    )
    db_session.add(sec)
    db_session.flush()
    item = models.CVInstanceItem(cv_instance_section_id=sec.id, item_id=old_id)
    db_session.add(item)
    db_session.flush()

    _migrate_cv_items_data(db_session)

    cvitem = db_session.query(models.CVItem).filter_by(section="education").first()
    assert cvitem is not None
    db_session.refresh(item)
    assert item.item_id == cvitem.id


def test_migrate_counts_match(db_session, test_user):
    """Total items = sum of all typed models + non-software/dissertation misc."""
    db_session.add(models.Education(user_id=test_user.id, degree="PhD", year=2020))
    db_session.add(models.Experience(user_id=test_user.id, title="Prof"))
    db_session.add(models.Consulting(user_id=test_user.id, title="Consult"))
    db_session.add(models.Membership(user_id=test_user.id, org="APHA"))
    db_session.add(models.Panel(user_id=test_user.id, panel="P", type="advisory"))
    db_session.add(models.Symposium(user_id=test_user.id, title="S"))
    db_session.add(models.Class(user_id=test_user.id, class_name="Epi 101"))
    db_session.add(models.Grant(user_id=test_user.id, title="Grant"))
    db_session.add(models.Award(user_id=test_user.id, name="Award"))
    db_session.add(models.Press(user_id=test_user.id, title="Press"))
    db_session.add(models.Trainee(user_id=test_user.id, name="Student", trainee_type="advisee"))
    db_session.add(models.Committee(user_id=test_user.id, committee="Cmte"))
    db_session.add(models.MiscSection(user_id=test_user.id, section="peerrev", data={"journal": "J"}))
    db_session.flush()

    _migrate_cv_items_data(db_session)

    assert db_session.query(models.CVItem).count() == 13
