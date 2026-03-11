"""Tests for Phase 2: migration of publications, patents, seminars,
software, and dissertation into the unified works table."""
from app import models
from app.main import _migrate_works_data


def test_migration_skips_when_works_exist(db_session, test_user):
    """If works table already has rows, migration is a no-op."""
    db_session.add(models.Work(
        user_id=test_user.id, work_type="papers", title="Existing",
    ))
    db_session.flush()
    # Add a publication that should NOT be migrated
    pub = models.Publication(
        user_id=test_user.id, type="papers", title="Should Not Migrate",
        year="2024",
    )
    db_session.add(pub)
    db_session.flush()

    _migrate_works_data(db_session)
    # Only the one pre-existing work
    assert db_session.query(models.Work).count() == 1


def test_migration_skips_when_no_source_data(db_session, test_user):
    """No source data → no works created, no error."""
    _migrate_works_data(db_session)
    assert db_session.query(models.Work).count() == 0


def test_migrate_publication(db_session, test_user):
    """Publication + authors migrate to Work + WorkAuthor with correct data."""
    pub = models.Publication(
        user_id=test_user.id, type="papers", title="Great Paper",
        year="2024", journal="Nature", volume="1", issue="2", pages="10-20",
        doi="10.1234/great", corr=True, cofirsts=2, coseniors=1,
        select_flag=True, preprint_doi="10.1234/pre", published_doi="10.1234/pub",
    )
    db_session.add(pub)
    db_session.flush()
    db_session.add(models.PubAuthor(pub_id=pub.id, author_name="First A", author_order=0, student=True))
    db_session.add(models.PubAuthor(pub_id=pub.id, author_name="Second B", author_order=1))
    db_session.add(models.PubAuthor(pub_id=pub.id, author_name="Last C", author_order=2))
    db_session.flush()

    _migrate_works_data(db_session)

    works = db_session.query(models.Work).all()
    assert len(works) == 1
    w = works[0]
    assert w.work_type == "papers"
    assert w.title == "Great Paper"
    assert w.year == 2024
    assert w.doi == "10.1234/great"
    assert w.data["journal"] == "Nature"
    assert w.data["volume"] == "1"
    assert w.data["select_flag"] is True
    assert w.data["preprint_doi"] == "10.1234/pre"
    assert w.data["published_doi"] == "10.1234/pub"

    authors = sorted(
        db_session.query(models.WorkAuthor).filter_by(work_id=w.id).all(),
        key=lambda a: a.author_order,
    )
    assert len(authors) == 3
    assert authors[0].student is True
    assert authors[0].corresponding is True  # corr → first author
    assert authors[0].cofirst is True         # cofirsts=2 → first 2
    assert authors[1].cofirst is True
    assert authors[2].cofirst is False
    assert authors[2].cosenior is True        # coseniors=1 → last 1


def test_migrate_publication_non_numeric_year(db_session, test_user):
    """Publication with 'in press' year → year=None, data.year_raw preserved."""
    pub = models.Publication(
        user_id=test_user.id, type="papers", title="Pending",
        year="in press",
    )
    db_session.add(pub)
    db_session.flush()

    _migrate_works_data(db_session)
    w = db_session.query(models.Work).first()
    assert w.year is None
    assert w.data["year_raw"] == "in press"


def test_migrate_publication_year_with_suffix(db_session, test_user):
    """Publication with '2024a' year → year=2024, data.year_raw='2024a'."""
    pub = models.Publication(
        user_id=test_user.id, type="papers", title="Suffixed",
        year="2024a",
    )
    db_session.add(pub)
    db_session.flush()

    _migrate_works_data(db_session)
    w = db_session.query(models.Work).first()
    assert w.year == 2024
    assert w.data["year_raw"] == "2024a"


def test_migrate_patent(db_session, test_user):
    """Patent + authors migrate to Work + WorkAuthor."""
    patent = models.Patent(
        user_id=test_user.id, name="Cool Invention",
        number="US12345", status="granted",
    )
    db_session.add(patent)
    db_session.flush()
    db_session.add(models.PatentAuthor(
        patent_id=patent.id, author_name="Inventor A", author_order=0,
    ))
    db_session.flush()

    _migrate_works_data(db_session)

    w = db_session.query(models.Work).first()
    assert w.work_type == "patents"
    assert w.title == "Cool Invention"
    assert w.data["identifier"] == "US12345"
    assert w.data["status"] == "granted"
    authors = db_session.query(models.WorkAuthor).filter_by(work_id=w.id).all()
    assert len(authors) == 1
    assert authors[0].author_name == "Inventor A"


def test_migrate_seminar(db_session, test_user):
    """Seminar migrates to Work with date parsed to year/month."""
    sem = models.Seminar(
        user_id=test_user.id, title="My Talk",
        org="MIT", date="March 2024", location="Boston", event="EpiCon",
    )
    db_session.add(sem)
    db_session.flush()

    _migrate_works_data(db_session)

    w = db_session.query(models.Work).first()
    assert w.work_type == "seminars"
    assert w.title == "My Talk"
    assert w.year == 2024
    assert w.month == 3
    assert w.data["institution"] == "MIT"
    assert w.data["conference"] == "EpiCon"
    assert w.data["location"] == "Boston"
    assert w.data["date_raw"] == "March 2024"


def test_migrate_seminar_year_only(db_session, test_user):
    """Seminar with just a year has no date_raw (no extra info)."""
    sem = models.Seminar(
        user_id=test_user.id, title="Talk", org="MIT", date="2020",
    )
    db_session.add(sem)
    db_session.flush()

    _migrate_works_data(db_session)

    w = db_session.query(models.Work).first()
    assert w.year == 2020
    assert "date_raw" not in (w.data or {})


def test_migrate_software(db_session, test_user):
    """Software MiscSection → Work with parsed comma-sep authors."""
    ms = models.MiscSection(
        user_id=test_user.id, section="software",
        data={
            "title": "EpiTools",
            "authors": "Dev A, Dev B, Dev C",
            "year": "2022",
            "publisher": "GitHub",
            "url": "https://github.com/test",
        },
    )
    db_session.add(ms)
    db_session.flush()

    _migrate_works_data(db_session)

    w = db_session.query(models.Work).first()
    assert w.work_type == "software"
    assert w.title == "EpiTools"
    assert w.year == 2022
    assert w.data["publisher"] == "GitHub"
    assert w.data["url"] == "https://github.com/test"
    authors = sorted(
        db_session.query(models.WorkAuthor).filter_by(work_id=w.id).all(),
        key=lambda a: a.author_order,
    )
    assert len(authors) == 3
    assert authors[0].author_name == "Dev A"
    assert authors[2].author_name == "Dev C"


def test_migrate_dissertation(db_session, test_user):
    """Dissertation MiscSection → Work."""
    ms = models.MiscSection(
        user_id=test_user.id, section="dissertation",
        data={"title": "My Thesis", "year": "2010", "institution": "Harvard"},
    )
    db_session.add(ms)
    db_session.flush()

    _migrate_works_data(db_session)

    w = db_session.query(models.Work).first()
    assert w.work_type == "dissertation"
    assert w.title == "My Thesis"
    assert w.year == 2010
    assert w.data["institution"] == "Harvard"


def test_migrate_cv_instance_item_remapping(db_session, test_user):
    """CVInstanceItem IDs get remapped to new Work IDs."""
    # Create a publication
    pub = models.Publication(
        user_id=test_user.id, type="papers", title="Remapped Paper", year="2024",
    )
    db_session.add(pub)
    db_session.flush()
    old_pub_id = pub.id

    # Create a template + instance + section + item pointing to the publication
    tmpl = models.CVTemplate(
        user_id=test_user.id, name="Test", style={},
    )
    db_session.add(tmpl)
    db_session.flush()
    inst = models.CVInstance(
        user_id=test_user.id, template_id=tmpl.id, name="Test Instance",
    )
    db_session.add(inst)
    db_session.flush()
    sec = models.CVInstanceSection(
        cv_instance_id=inst.id, section_key="publications_papers",
        enabled=True, section_order=0,
    )
    db_session.add(sec)
    db_session.flush()
    item = models.CVInstanceItem(
        cv_instance_section_id=sec.id, item_id=old_pub_id,
    )
    db_session.add(item)
    db_session.flush()

    _migrate_works_data(db_session)

    # The work should have been created
    work = db_session.query(models.Work).first()
    assert work is not None

    # The CVInstanceItem should now point to the new work ID
    db_session.refresh(item)
    assert item.item_id == work.id


def test_migrate_counts_match(db_session, test_user):
    """Total works created = sum of all source rows."""
    db_session.add(models.Publication(user_id=test_user.id, type="papers", title="P1", year="2024"))
    db_session.add(models.Publication(user_id=test_user.id, type="preprints", title="P2", year="2023"))
    db_session.add(models.Patent(user_id=test_user.id, name="Pat1"))
    db_session.add(models.Seminar(user_id=test_user.id, title="S1", org="MIT", date="2020"))
    db_session.add(models.MiscSection(user_id=test_user.id, section="software", data={"title": "SW1"}))
    db_session.add(models.MiscSection(user_id=test_user.id, section="dissertation", data={"title": "D1"}))
    # This misc section should NOT be migrated (not software/dissertation)
    db_session.add(models.MiscSection(user_id=test_user.id, section="editorial", data={"journal": "J1"}))
    db_session.flush()

    _migrate_works_data(db_session)

    assert db_session.query(models.Work).count() == 6  # 2 pubs + 1 patent + 1 seminar + 1 sw + 1 diss
