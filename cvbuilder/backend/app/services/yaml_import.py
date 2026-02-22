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


def import_cv_yaml(cv_path: str, session) -> None:
    """Populate profile + CV section tables from CV.yml."""
    from app.models import (
        Address, Award, Class, Committee, Consulting, Education, Experience,
        Grant, Membership, MiscSection, Panel, Patent, PatentAuthor,
        Press, Profile, Seminar, Symposium, Trainee
    )

    # CV.yml may have a trailing '---', producing multiple documents; take first non-None
    docs = list(yaml.safe_load_all(Path(cv_path).read_text(encoding="utf-8")))
    data = next((d for d in docs if d is not None), {})

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------
    existing = session.query(Profile).first()
    if existing:
        profile = existing
    else:
        profile = Profile()
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
    session.query(Education).delete()
    for i, item in enumerate(data.get("education", [])):
        session.add(Education(
            degree=_clean(item.get("degree", "")),
            year=item.get("year"),
            subject=_clean(item.get("subject", "")),
            school=_clean(item.get("school", "")),
            sort_order=i,
        ))

    # ------------------------------------------------------------------
    # Experience
    # ------------------------------------------------------------------
    session.query(Experience).delete()
    for i, item in enumerate(data.get("experience", [])):
        yrs = str(item.get("years", ""))
        start, end = _parse_years(yrs)
        session.add(Experience(
            title=_clean(item.get("title", "")),
            years_start=start,
            years_end=end,
            employer=_clean(item.get("employer", "")),
            sort_order=i,
        ))

    # ------------------------------------------------------------------
    # Consulting
    # ------------------------------------------------------------------
    session.query(Consulting).delete()
    for i, item in enumerate(data.get("consulting", [])):
        session.add(Consulting(
            title=_clean(item.get("title", "")),
            years=str(item.get("years", "")),
            employer=_clean(item.get("employer", "")),
            sort_order=i,
        ))

    # ------------------------------------------------------------------
    # Memberships
    # ------------------------------------------------------------------
    session.query(Membership).delete()
    for i, item in enumerate(data.get("membership", [])):
        session.add(Membership(
            org=_clean(item.get("org", "")),
            years=str(item.get("years", "")),
            sort_order=i,
        ))

    # ------------------------------------------------------------------
    # Panels (advisory + grant review)
    # ------------------------------------------------------------------
    session.query(Panel).delete()
    for i, item in enumerate(data.get("panel", [])):
        session.add(Panel(
            panel=_clean(item.get("panel", "")),
            org=_clean(item.get("org", "")),
            role=_clean(item.get("role", "")),
            date=str(item.get("date", "")),
            panel_id=item.get("id", ""),
            type="advisory",
            sort_order=i,
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
        ))

    # ------------------------------------------------------------------
    # Patents
    # ------------------------------------------------------------------
    session.query(PatentAuthor).delete()
    session.query(Patent).delete()
    for i, item in enumerate(data.get("patent", [])):
        patent = Patent(
            name=_clean(item.get("name", "")),
            number=str(item.get("number", "")),
            status=item.get("status", ""),
            sort_order=i,
        )
        session.add(patent)
        session.flush()
        for j, author in enumerate(item.get("authors", [])):
            session.add(PatentAuthor(patent_id=patent.id, author_name=_clean(author), author_order=j))

    # ------------------------------------------------------------------
    # Symposia
    # ------------------------------------------------------------------
    session.query(Symposium).delete()
    for i, item in enumerate(data.get("symposium", [])):
        session.add(Symposium(
            title=_clean(item.get("title", "")),
            meeting=_clean(item.get("meeting", "")),
            date=str(item.get("date", "")),
            role=_clean(item.get("role", "")),
            sort_order=i,
        ))

    # ------------------------------------------------------------------
    # Classes (teaching)
    # ------------------------------------------------------------------
    session.query(Class).delete()
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
        ))

    # ------------------------------------------------------------------
    # Grants — activegrants + completedgrants
    # ------------------------------------------------------------------
    session.query(Grant).delete()
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
        ))
        sort_i += 1

    # ------------------------------------------------------------------
    # Awards / Honors
    # ------------------------------------------------------------------
    session.query(Award).delete()
    for i, item in enumerate(data.get("honor", [])):
        session.add(Award(
            name=_clean(item.get("name", "")),
            year=str(item.get("year", "")),
            org=_clean(item.get("grantee", "")),
            date=str(item.get("date", "")),
            sort_order=i,
        ))

    # ------------------------------------------------------------------
    # Press / Media
    # ------------------------------------------------------------------
    session.query(Press).delete()
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
            ))
            sort_i += 1

    # ------------------------------------------------------------------
    # Trainees (advisees + postdocs)
    # ------------------------------------------------------------------
    session.query(Trainee).delete()
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
        ))

    # ------------------------------------------------------------------
    # Seminars (invited talks)
    # ------------------------------------------------------------------
    session.query(Seminar).delete()
    for i, item in enumerate(data.get("seminars", [])):
        session.add(Seminar(
            title=_clean(item.get("title", "")),
            org=_clean(item.get("org", "")),
            date=str(item.get("date", "")),
            location=_clean(item.get("loc", "")),
            event=_clean(item.get("event", "")),
            sort_order=i,
        ))

    # ------------------------------------------------------------------
    # Committees
    # ------------------------------------------------------------------
    session.query(Committee).delete()
    for i, item in enumerate(data.get("committees", [])):
        session.add(Committee(
            committee=_clean(item.get("committee", "")),
            org=_clean(item.get("org", "")),
            role=_clean(item.get("role", "")),
            dates=str(item.get("dates", "")),
            sort_order=i,
        ))

    # ------------------------------------------------------------------
    # Misc sections (editor, peerrev, software, policypres, etc.)
    # ------------------------------------------------------------------
    session.query(MiscSection).delete()
    misc_keys = [
        "editor", "assocedit", "otheredit", "peerrev",
        "software", "policypres", "policycons", "policyother",
        "chairedsessions", "otherservice",
        "schoolwideOrals", "departmentalOrals", "finaldefense",
    ]
    for key in misc_keys:
        items = data.get(key, [])
        if isinstance(items, list):
            for i, item in enumerate(items):
                payload = item if isinstance(item, dict) else {"value": item}
                session.add(MiscSection(section=key, data=payload, sort_order=i))

    session.commit()
    print(f"[yaml_import] CV.yml imported successfully.")


def import_refs_yaml(refs_path: str, session) -> None:
    """Populate publications tables from refs.yml."""
    from app.models import Publication, PubAuthor

    docs = list(yaml.safe_load_all(Path(refs_path).read_text(encoding="utf-8")))
    data = next((d for d in docs if d is not None), {})

    session.query(PubAuthor).delete()
    session.query(Publication).delete()

    pub_types = ["papers", "preprints", "papersNoPeer", "chapters", "letters", "scimeetings"]
    for pub_type in pub_types:
        for item in data.get(pub_type, []):
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

            pub = Publication(
                type=pub_type,
                title=_clean(item.get("title", "")),
                year=str(item.get("year", "") or ""),
                journal=_clean(item.get("journal", "") or ""),
                volume=str(item.get("volume", "") or ""),
                issue=str(item.get("issue", "") or ""),
                pages=str(item.get("pages", "") or ""),
                doi=str(item.get("doi", "") or ""),
                corr=corr_val,
                cofirsts=cofirsts,
                coseniors=coseniors,
                select_flag=select_flag,
                conference=_clean(item.get("conference", "") or ""),
                pres_type=item.get("pres_type", ""),
                publisher=_clean(item.get("publisher", "") or ""),
            )
            session.add(pub)
            session.flush()
            for j, author in enumerate(authors_raw):
                raw = str(author)
                # Detect student-author marker from original LaTeX format ($^*$)
                student = bool(re.search(r'\$\^[\*\{]', raw))
                session.add(PubAuthor(
                    pub_id=pub.id,
                    author_name=_clean(raw),
                    author_order=j,
                    student=student,
                ))

    session.commit()
    print(f"[yaml_import] refs.yml imported successfully.")


def main():
    parser = argparse.ArgumentParser(description="Import CV YAML data into the database.")
    parser.add_argument("--cv", default="mydata/CV.yml")
    parser.add_argument("--refs", default="mydata/refs.yml")
    parser.add_argument("--db", default="sqlite:///./cvbuilder.db")
    args = parser.parse_args()

    import os
    os.environ.setdefault("DATABASE_URL", args.db)

    from app.database import SessionLocal, create_tables
    create_tables()
    db = SessionLocal()
    try:
        if Path(args.cv).exists():
            import_cv_yaml(args.cv, db)
        else:
            print(f"[yaml_import] CV file not found: {args.cv}", file=sys.stderr)

        if Path(args.refs).exists():
            import_refs_yaml(args.refs, db)
        else:
            print(f"[yaml_import] refs file not found: {args.refs}", file=sys.stderr)
    finally:
        db.close()


if __name__ == "__main__":
    main()
