"""Import CV.yml and refs.yml into the SQLite database."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


def _clean(value):
    """Remove LaTeX markup, normalise whitespace."""
    if not isinstance(value, str):
        return value
    # strip LaTeX \textbf{...}, \url{...}, $^*$ etc.
    value = re.sub(r"\\textbf\{([^}]*)\}", r"\1", value)
    value = re.sub(r"\\url\{([^}]*)\}", r"\1", value)
    value = re.sub(r"\$\^[^$]*\$", "", value)
    value = re.sub(r"\\[a-z'`\"]+\{([^}]*)\}", r"\1", value)
    value = value.replace("\\", "").strip()
    return " ".join(value.split())


def _parse_years(years_str: str) -> tuple[str, str]:
    """Split 'YYYY-YYYY' or 'YYYY-present' into (start, end)."""
    if not years_str:
        return ("", "")
    parts = str(years_str).split("-", 1)
    start = parts[0].strip()
    end = parts[1].strip() if len(parts) > 1 else ""
    return (start, end)


def _parse_dates(dates_str: str) -> tuple[str, str]:
    """Split 'Month YYYY-Month YYYY' or 'Month YYYY-present'."""
    if not dates_str:
        return ("", "")
    # Try splitting on ' - ' first, then '-'
    if " - " in str(dates_str):
        parts = str(dates_str).split(" - ", 1)
    else:
        parts = str(dates_str).split("-", 1)
    start = parts[0].strip()
    end = parts[1].strip() if len(parts) > 1 else ""
    return (start, end)


def _parse_year_int(val):
    """Extract 4-digit year from string/int → (year_int, raw_or_None)."""
    if val is None:
        return None, None
    if isinstance(val, int):
        return val, None
    s = str(val).strip()
    if not s:
        return None, None
    m = re.search(r'\d{4}', s)
    if m:
        year_int = int(m.group())
        return (year_int, None) if s == m.group() else (year_int, s)
    return None, s


def _parse_month_from_date(date_str):
    """Try to extract month number from a date string."""
    if not date_str:
        return None
    _months = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    }
    lower = str(date_str).lower()
    for name, num in _months.items():
        if name in lower:
            return num
    return None


def _delete_works_by_type(session, user_id, work_type):
    """Delete all Work + WorkAuthor rows of a given type for a user."""
    from app.models import Work, WorkAuthor
    work_ids = [w.id for w in session.query(Work).filter_by(user_id=user_id, work_type=work_type).all()]
    if work_ids:
        session.query(WorkAuthor).filter(WorkAuthor.work_id.in_(work_ids)).delete(synchronize_session=False)
    session.query(Work).filter_by(user_id=user_id, work_type=work_type).delete()


def import_cv_yaml(cv_path: str, session, user_id: int = 1) -> None:
    """Populate profile + CV section tables from CV.yml."""
    from app.models import (
        Address, Award, Class, Committee, Consulting, Education, Experience,
        Grant, Membership, MiscSection, Panel, Work, WorkAuthor,
        Press, Profile, Symposium, Trainee
    )

    # CV.yml may have a trailing '---', producing multiple documents; take first non-None
    docs = list(yaml.safe_load_all(Path(cv_path).read_text(encoding="utf-8")))
    data = next((d for d in docs if d is not None), {})

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------
    existing = session.query(Profile).filter_by(user_id=user_id).first()
    if existing:
        profile = existing
    else:
        profile = Profile(user_id=user_id)
        session.add(profile)

    profile.name = _clean(data.get("name", ""))
    profile.email = data.get("email", "")
    profile.phone = data.get("phone", "")

    # Addresses
    session.query(Address).filter(Address.profile_id == profile.id).delete()
    for addr_type in ("home", "work"):
        key = f"address-{addr_type}"
        for i, line in enumerate(data.get(key, [])):
            session.add(Address(profile=profile, type=addr_type, line_order=i, text=_clean(line)))

    session.flush()

    # ------------------------------------------------------------------
    # Education
    # ------------------------------------------------------------------
    session.query(Education).filter_by(user_id=user_id).delete()
    for i, item in enumerate(data.get("education", [])):
        session.add(Education(
            degree=_clean(item.get("degree", "")),
            year=item.get("year"),
            subject=_clean(item.get("subject", "")),
            school=_clean(item.get("school", "")),
            sort_order=i,
            user_id=user_id,
        ))

    # ------------------------------------------------------------------
    # Experience
    # ------------------------------------------------------------------
    session.query(Experience).filter_by(user_id=user_id).delete()
    for i, item in enumerate(data.get("experience", [])):
        yrs = str(item.get("years", ""))
        start, end = _parse_years(yrs)
        session.add(Experience(
            title=_clean(item.get("title", "")),
            years_start=start,
            years_end=end,
            employer=_clean(item.get("employer", "")),
            sort_order=i,
            user_id=user_id,
        ))

    # ------------------------------------------------------------------
    # Consulting
    # ------------------------------------------------------------------
    session.query(Consulting).filter_by(user_id=user_id).delete()
    for i, item in enumerate(data.get("consulting", [])):
        session.add(Consulting(
            title=_clean(item.get("title", "")),
            years=str(item.get("years", "")),
            employer=_clean(item.get("employer", "")),
            sort_order=i,
            user_id=user_id,
        ))

    # ------------------------------------------------------------------
    # Memberships
    # ------------------------------------------------------------------
    session.query(Membership).filter_by(user_id=user_id).delete()
    for i, item in enumerate(data.get("membership", [])):
        session.add(Membership(
            org=_clean(item.get("org", "")),
            years=str(item.get("years", "")),
            sort_order=i,
            user_id=user_id,
        ))

    # ------------------------------------------------------------------
    # Panels (advisory + grant review)
    # ------------------------------------------------------------------
    session.query(Panel).filter_by(user_id=user_id).delete()
    for i, item in enumerate(data.get("panel", [])):
        session.add(Panel(
            panel=_clean(item.get("panel", "")),
            org=_clean(item.get("org", "")),
            role=_clean(item.get("role", "")),
            date=str(item.get("date", "")),
            panel_id=item.get("id", ""),
            type="advisory",
            sort_order=i,
            user_id=user_id,
        ))
    offset = len(data.get("panel", []))
    for i, item in enumerate(data.get("grantrev", [])):
        session.add(Panel(
            panel=_clean(item.get("panel", "")),
            org=_clean(item.get("org", "")),
            role=_clean(item.get("role", "")),
            date=str(item.get("date", "")),
            panel_id=item.get("id", ""),
            type="grant_review",
            sort_order=offset + i,
            user_id=user_id,
        ))

    # ------------------------------------------------------------------
    # Patents (stored as Work with work_type='patents')
    # ------------------------------------------------------------------
    _delete_works_by_type(session, user_id, "patents")
    for i, item in enumerate(data.get("patent", [])):
        work_data = {}
        num = str(item.get("number", ""))
        if num:
            work_data["identifier"] = num
        status = item.get("status", "")
        if status:
            work_data["status"] = status
        work = Work(
            work_type="patents",
            title=_clean(item.get("name", "")),
            data=work_data,
            user_id=user_id,
        )
        session.add(work)
        session.flush()
        for j, author in enumerate(item.get("authors", [])):
            session.add(WorkAuthor(work_id=work.id, author_name=_clean(author), author_order=j))

    # ------------------------------------------------------------------
    # Symposia
    # ------------------------------------------------------------------
    session.query(Symposium).filter_by(user_id=user_id).delete()
    for i, item in enumerate(data.get("symposium", [])):
        session.add(Symposium(
            title=_clean(item.get("title", "")),
            meeting=_clean(item.get("meeting", "")),
            date=str(item.get("date", "")),
            role=_clean(item.get("role", "")),
            sort_order=i,
            user_id=user_id,
        ))

    # ------------------------------------------------------------------
    # Classes (teaching)
    # ------------------------------------------------------------------
    session.query(Class).filter_by(user_id=user_id).delete()
    for i, item in enumerate(data.get("classes", [])):
        in3 = item.get("inthreeyear", False)
        session.add(Class(
            class_name=_clean(item.get("class", "")),
            year=item.get("year"),
            role=_clean(item.get("role", "")),
            school=_clean(item.get("school", "")),
            students=str(item.get("students", "") or ""),
            lectures=str(item.get("lectures", "") or ""),
            in_three_year=bool(in3),
            sort_order=i,
            user_id=user_id,
        ))

    # ------------------------------------------------------------------
    # Grants — activegrants + completedgrants
    # ------------------------------------------------------------------
    session.query(Grant).filter_by(user_id=user_id).delete()
    sort_i = 0
    for item in data.get("activegrants", []):
        dates = str(item.get("dates", ""))
        start, end = _parse_dates(dates)
        title = _clean(item.get("title", "") or item.get("org", ""))
        session.add(Grant(
            title=title,
            agency=_clean(item.get("org", "")),
            pi=_clean(item.get("PI", "")),
            amount=str(item.get("amount", "")),
            years_start=start,
            years_end=end,
            role=_clean(item.get("role", "")),
            id_number=str(item.get("number", "")),
            description=_clean(item.get("description", "")),
            grant_type=_clean(item.get("type", "")),
            pcteffort=item.get("pcteffort"),
            status="active",
            sort_order=sort_i,
            user_id=user_id,
        ))
        sort_i += 1
    for item in data.get("completedgrants", []):
        dates = str(item.get("dates", ""))
        start, end = _parse_dates(dates)
        title = _clean(item.get("title", "") or item.get("org", ""))
        session.add(Grant(
            title=title,
            agency=_clean(item.get("org", "")),
            pi=_clean(item.get("PI", "")),
            amount=str(item.get("amount", "")),
            years_start=start,
            years_end=end,
            role=_clean(item.get("role", "")),
            id_number=str(item.get("number", "")),
            description=_clean(item.get("description", "")),
            grant_type=_clean(item.get("type", "")),
            pcteffort=item.get("pcteffort"),
            status="completed",
            sort_order=sort_i,
            user_id=user_id,
        ))
        sort_i += 1

    # ------------------------------------------------------------------
    # Awards / Honors
    # ------------------------------------------------------------------
    session.query(Award).filter_by(user_id=user_id).delete()
    for i, item in enumerate(data.get("honor", [])):
        session.add(Award(
            name=_clean(item.get("name", "")),
            year=str(item.get("year", "")),
            org=_clean(item.get("grantee", "")),
            date=str(item.get("date", "")),
            sort_order=i,
            user_id=user_id,
        ))

    # ------------------------------------------------------------------
    # Press / Media
    # ------------------------------------------------------------------
    session.query(Press).filter_by(user_id=user_id).delete()
    sort_i = 0
    for item in data.get("media", []):
        topic = _clean(item.get("topic", ""))
        date = str(item.get("date", ""))
        for outlet in item.get("outlets", []):
            session.add(Press(
                outlet=_clean(outlet),
                topic=topic,
                date=date,
                sort_order=sort_i,
                user_id=user_id,
            ))
            sort_i += 1

    # ------------------------------------------------------------------
    # Trainees (advisees + postdocs)
    # ------------------------------------------------------------------
    session.query(Trainee).filter_by(user_id=user_id).delete()
    for i, item in enumerate(data.get("advisees", [])):
        dates = str(item.get("dates", ""))
        start, end = _parse_dates(dates)
        session.add(Trainee(
            name=_clean(item.get("name", "")),
            degree=item.get("degree", ""),
            years_start=start,
            years_end=end,
            type=item.get("type", "advisor"),
            school=_clean(item.get("school", "")),
            thesis=_clean(item.get("thesis", "")),
            current_position=_clean(item.get("wherenow", "")),
            trainee_type="advisee",
            sort_order=i,
            user_id=user_id,
        ))
    offset = len(data.get("advisees", []))
    for i, item in enumerate(data.get("postdocs", [])):
        dates = str(item.get("dates", ""))
        start, end = _parse_dates(dates)
        session.add(Trainee(
            name=_clean(item.get("name", "")),
            years_start=start,
            years_end=end,
            current_position=_clean(item.get("wherenow", "")),
            trainee_type="postdoc",
            sort_order=offset + i,
            user_id=user_id,
        ))

    # ------------------------------------------------------------------
    # Seminars (stored as Work with work_type='seminars')
    # ------------------------------------------------------------------
    _delete_works_by_type(session, user_id, "seminars")
    for i, item in enumerate(data.get("seminars", [])):
        date_str = str(item.get("date", ""))
        year_int, year_raw = _parse_year_int(date_str)
        month_int = _parse_month_from_date(date_str)
        work_data = {}
        org = _clean(item.get("org", ""))
        if org:
            work_data["institution"] = org
        event = _clean(item.get("event", ""))
        if event:
            work_data["conference"] = event
        loc = _clean(item.get("loc", ""))
        if loc:
            work_data["location"] = loc
        if year_raw:
            work_data["date_raw"] = year_raw
        session.add(Work(
            work_type="seminars",
            title=_clean(item.get("title", "")),
            year=year_int,
            month=month_int,
            data=work_data,
            user_id=user_id,
        ))

    # ------------------------------------------------------------------
    # Committees
    # ------------------------------------------------------------------
    session.query(Committee).filter_by(user_id=user_id).delete()
    for i, item in enumerate(data.get("committees", [])):
        session.add(Committee(
            committee=_clean(item.get("committee", "")),
            org=_clean(item.get("org", "")),
            role=_clean(item.get("role", "")),
            dates=str(item.get("dates", "")),
            sort_order=i,
            user_id=user_id,
        ))

    # ------------------------------------------------------------------
    # Misc sections (editor, peerrev, policypres, etc.)
    # Software and dissertation are now stored as Work.
    # ------------------------------------------------------------------
    session.query(MiscSection).filter_by(user_id=user_id).delete()
    misc_keys = [
        "editor", "assocedit", "otheredit", "peerrev",
        "policypres", "policycons",
        "otherservice",
        "schoolwideOrals", "departmentalOrals", "finaldefense",
    ]
    for key in misc_keys:
        items = data.get(key, [])
        if isinstance(items, list):
            for i, item in enumerate(items):
                payload = item if isinstance(item, dict) else {"value": item}
                session.add(MiscSection(section=key, data=payload, sort_order=i, user_id=user_id))

    # chairedsessions: remap YAML keys year/conference → date/meeting
    for i, item in enumerate(data.get("chairedsessions", [])):
        session.add(MiscSection(section="chairedsessions", sort_order=i, user_id=user_id, data={
            "title": _clean(item.get("title", "")),
            "date": str(item.get("year", "")),
            "meeting": _clean(item.get("conference", "")),
        }))

    # policyother → stored as "otherpractice"
    for i, item in enumerate(data.get("policyother", [])):
        payload = item if isinstance(item, dict) else {"value": item}
        session.add(MiscSection(section="otherpractice", data=payload, sort_order=i, user_id=user_id))

    # Software (stored as Work with work_type='software')
    _delete_works_by_type(session, user_id, "software")
    for i, item in enumerate(data.get("software", [])):
        if not isinstance(item, dict):
            continue
        year_int, year_raw = _parse_year_int(item.get("year"))
        work_data = {}
        if item.get("publisher"):
            work_data["publisher"] = _clean(item["publisher"])
        if item.get("url"):
            work_data["url"] = item["url"]
        if year_raw:
            work_data["year_raw"] = year_raw
        work = Work(
            work_type="software",
            title=_clean(item.get("title", "")),
            year=year_int,
            data=work_data,
            user_id=user_id,
        )
        session.add(work)
        session.flush()
        authors_str = item.get("authors", "")
        if isinstance(authors_str, str) and authors_str:
            for j, name in enumerate(a.strip() for a in authors_str.split(",") if a.strip()):
                session.add(WorkAuthor(work_id=work.id, author_name=_clean(name), author_order=j))

    # Dissertation (stored as Work with work_type='dissertation')
    _delete_works_by_type(session, user_id, "dissertation")
    diss = data.get("dissertation")
    if isinstance(diss, dict):
        year_int, year_raw = _parse_year_int(diss.get("year"))
        work_data = {}
        institution = _clean(
            (diss.get("department", "") + ", " + diss.get("institution", "")).strip(", ")
        )
        if institution:
            work_data["institution"] = institution
        if year_raw:
            work_data["year_raw"] = year_raw
        session.add(Work(
            work_type="dissertation",
            title=_clean(diss.get("title", "")),
            year=year_int,
            data=work_data,
            user_id=user_id,
        ))

    session.commit()
    print(f"[yaml_import] CV.yml imported successfully.")


def import_refs_yaml(refs_path: str, session, user_id: int = 1) -> None:
    """Populate works table from refs.yml (publications)."""
    from app.models import Work, WorkAuthor

    docs = list(yaml.safe_load_all(Path(refs_path).read_text(encoding="utf-8")))
    data = next((d for d in docs if d is not None), {})

    # Delete only this user's publication-type works and their authors
    _PUB_TYPES = ["papers", "preprints", "chapters", "letters", "scimeetings", "editorials"]
    for pt in _PUB_TYPES:
        _delete_works_by_type(session, user_id, pt)

    # Map YAML keys to DB type names (papersNoPeer → editorials)
    pub_type_map = {
        "papers": "papers", "preprints": "preprints", "chapters": "chapters",
        "letters": "letters", "scimeetings": "scimeetings",
        "papersNoPeer": "editorials",
    }
    for yaml_key, pub_type in pub_type_map.items():
        for item in data.get(yaml_key, []):
            authors_raw = item.get("authors", [])
            corr_val = item.get("corr", False)
            if isinstance(corr_val, str):
                corr_val = corr_val.lower() in ("true", "yes", "1")
            corr_val = bool(corr_val)

            select_raw = item.get("select", False)
            if isinstance(select_raw, str):
                select_flag = select_raw not in ("", "0", "false", "no")
            else:
                select_flag = bool(select_raw)

            cofirsts = int(item.get("cofirsts", 0) or 0)
            coseniors = int(item.get("coseniors", 0) or 0)

            year_int, year_raw = _parse_year_int(item.get("year"))
            work_data = {}
            journal = _clean(item.get("journal", "") or "")
            if journal:
                work_data["journal"] = journal
            volume = str(item.get("volume", "") or "")
            if volume:
                work_data["volume"] = volume
            issue = str(item.get("issue", "") or "")
            if issue:
                work_data["issue"] = issue
            pages = str(item.get("pages", "") or "")
            if pages:
                work_data["pages"] = pages
            if select_flag:
                work_data["select_flag"] = True
            conference = _clean(item.get("conference", "") or "")
            if conference:
                work_data["conference"] = conference
            pres_type = item.get("pres_type", "")
            if pres_type:
                work_data["pres_type"] = pres_type
            publisher = _clean(item.get("publisher", "") or "")
            if publisher:
                work_data["publisher"] = publisher
            preprint_doi = str(item.get("preprint_doi", "") or "") or None
            if preprint_doi:
                work_data["preprint_doi"] = preprint_doi
            published_doi = str(item.get("published_doi", "") or "") or None
            if published_doi:
                work_data["published_doi"] = published_doi
            if year_raw:
                work_data["year_raw"] = year_raw

            doi = str(item.get("doi", "") or "")

            work = Work(
                work_type=pub_type,
                title=_clean(item.get("title", "")),
                year=year_int,
                doi=doi or None,
                data=work_data,
                user_id=user_id,
            )
            session.add(work)
            session.flush()

            for j, author in enumerate(authors_raw):
                raw = str(author)
                student = bool(re.search(r'\$\^[\*\{]', raw))
                wa = WorkAuthor(
                    work_id=work.id,
                    author_name=_clean(raw),
                    author_order=j,
                    student=student,
                )
                session.add(wa)
            session.flush()

            # Convert pub-level role markers to per-author flags
            if authors_raw:
                work_authors = sorted(
                    session.query(WorkAuthor).filter_by(work_id=work.id).all(),
                    key=lambda a: a.author_order,
                )
                if corr_val and work_authors:
                    work_authors[0].corresponding = True
                if cofirsts > 0:
                    for wa in work_authors[:cofirsts]:
                        wa.cofirst = True
                if coseniors > 0:
                    for wa in work_authors[-coseniors:]:
                        wa.cosenior = True

    session.commit()
    print(f"[yaml_import] refs.yml imported successfully.")


def main():
    parser = argparse.ArgumentParser(description="Import CV YAML data into the database.")
    parser.add_argument("--cv", default="mydata/CV.yml")
    parser.add_argument("--refs", default="mydata/refs.yml")
    parser.add_argument("--db", default="sqlite:///./data/cvbuilder.db")
    args = parser.parse_args()

    import os
    os.environ.setdefault("DATABASE_URL", args.db)

    from app.database import SessionLocal, create_tables
    create_tables()
    db = SessionLocal()
    try:
        if Path(args.cv).exists():
            import_cv_yaml(args.cv, db, user_id=1)
        else:
            print(f"[yaml_import] CV file not found: {args.cv}", file=sys.stderr)

        if Path(args.refs).exists():
            import_refs_yaml(args.refs, db, user_id=1)
        else:
            print(f"[yaml_import] refs file not found: {args.refs}", file=sys.stderr)
    finally:
        db.close()


if __name__ == "__main__":
    main()
