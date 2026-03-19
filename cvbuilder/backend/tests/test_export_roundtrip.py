"""Round-trip test: import Einstein fixture → export YAML → reimport → compare.

Verifies that every section that survives import also survives export→reimport,
ensuring the YAML export covers all sections that import supports.
"""
import tempfile
import os
from pathlib import Path

import yaml
import pytest

from app.services.yaml_import import import_cv_yaml, import_refs_yaml
from app import models

FIXTURES = Path(__file__).parent / "fixtures"


class TestExportRoundtrip:
    """Import Einstein data for user A, export, reimport as user B, compare."""

    def _import_einstein(self, db, user_id):
        """Import both CV and refs for a given user."""
        import_cv_yaml(str(FIXTURES / "einstein_cv.yml"), db, user_id=user_id)
        import_refs_yaml(str(FIXTURES / "einstein_refs.yml"), db, user_id=user_id)

    def _cv_items(self, db, user_id, section):
        return db.query(models.CVItem).filter_by(
            user_id=user_id, section=section
        ).order_by(models.CVItem.sort_order).all()

    def _works(self, db, user_id, work_type):
        return db.query(models.Work).filter_by(
            user_id=user_id, work_type=work_type
        ).order_by(models.Work.id).all()

    def test_roundtrip(self, client, db_session, test_user, user_b):
        """Full round-trip: import → export → reimport → compare."""
        # Step 1: Import Einstein for user A (test_user)
        self._import_einstein(db_session, test_user.id)

        # Step 2: Export via API
        resp = client.get("/api/export/yaml")
        assert resp.status_code == 200
        exported = yaml.safe_load(resp.content)
        assert "cv" in exported
        assert "refs" in exported

        # Step 3: Reimport as user B using temp files
        with tempfile.TemporaryDirectory() as tmpdir:
            cv_path = os.path.join(tmpdir, "cv.yml")
            refs_path = os.path.join(tmpdir, "refs.yml")
            with open(cv_path, "w") as f:
                yaml.dump(exported["cv"], f, allow_unicode=True)
            with open(refs_path, "w") as f:
                yaml.dump(exported["refs"], f, allow_unicode=True)
            import_cv_yaml(cv_path, db_session, user_id=user_b.id)
            import_refs_yaml(refs_path, db_session, user_id=user_b.id)

        # Step 4: Compare all sections between user A and user B

        # --- CVItem sections ---
        cv_sections = [
            "education", "experience", "consulting", "memberships",
            "panels_advisory", "panels_grantreview", "symposia",
            "classes", "grants", "awards", "press",
            "trainees_advisees", "trainees_postdocs",
            "committees",
            "editor", "assocedit", "otheredit", "peerrev",
            "policypres", "policycons", "otherservice",
            "chairedsessions", "otherpractice",
            "departmentalOrals", "finaldefense", "schoolwideOrals",
        ]

        for section in cv_sections:
            items_a = self._cv_items(db_session, test_user.id, section)
            items_b = self._cv_items(db_session, user_b.id, section)
            assert len(items_a) == len(items_b), (
                f"Section {section}: count mismatch A={len(items_a)} B={len(items_b)}"
            )
            # Compare data blobs (ignore id, sort_order)
            for a, b in zip(items_a, items_b):
                # Normalize: strip trainee_type and type from data for comparison
                # since these may be added during import but not round-tripped
                da = {k: v for k, v in (a.data or {}).items() if k not in ("trainee_type", "type")}
                db_ = {k: v for k, v in (b.data or {}).items() if k not in ("trainee_type", "type")}
                assert da == db_, (
                    f"Section {section}: data mismatch\nA: {da}\nB: {db_}"
                )

        # --- Work types ---
        work_types = ["patents", "seminars", "software", "papers",
                      "preprints", "chapters", "letters", "scimeetings", "editorials"]
        for wt in work_types:
            works_a = sorted(self._works(db_session, test_user.id, wt), key=lambda w: w.title or "")
            works_b = sorted(self._works(db_session, user_b.id, wt), key=lambda w: w.title or "")
            assert len(works_a) == len(works_b), (
                f"Work type {wt}: count mismatch A={len(works_a)} B={len(works_b)}"
            )
            for a, b in zip(works_a, works_b):
                assert a.title == b.title, f"Work {wt}: title mismatch {a.title!r} vs {b.title!r}"
                # Compare author names
                authors_a = sorted([au.author_name for au in a.authors])
                authors_b = sorted([au.author_name for au in b.authors])
                assert authors_a == authors_b, (
                    f"Work {wt} '{a.title}': author mismatch {authors_a} vs {authors_b}"
                )

        # --- Dissertation (singular work) ---
        diss_a = db_session.query(models.Work).filter_by(
            user_id=test_user.id, work_type="dissertation").first()
        diss_b = db_session.query(models.Work).filter_by(
            user_id=user_b.id, work_type="dissertation").first()
        if diss_a:
            assert diss_b is not None, "Dissertation missing after round-trip"
            assert diss_a.title == diss_b.title

        # --- Profile ---
        prof_a = db_session.query(models.Profile).filter_by(user_id=test_user.id).first()
        prof_b = db_session.query(models.Profile).filter_by(user_id=user_b.id).first()
        assert prof_a.name == prof_b.name
        assert prof_a.email == prof_b.email

    def test_export_has_all_sections(self, client, db_session, test_user):
        """Verify the exported YAML contains keys for all populated sections."""
        self._import_einstein(db_session, test_user.id)
        resp = client.get("/api/export/yaml")
        exported = yaml.safe_load(resp.content)
        cv = exported["cv"]

        # Sections that should be present given Einstein fixture
        expected_keys = [
            "education", "experience", "consulting", "membership",
            "panel", "grantrev", "patent", "symposium", "classes",
            "activegrants", "completedgrants", "honor",
            "media", "advisees", "postdocs", "seminars", "committees",
            "editor", "assocedit", "otheredit", "peerrev",
            "otherservice", "policypres", "policycons",
            "chairedsessions", "policyother",
            "departmentalOrals", "finaldefense", "schoolwideOrals",
            "software", "dissertation",
        ]
        for key in expected_keys:
            assert key in cv, f"Missing export key: {key}"

    def test_press_outlets_roundtrip(self, client, db_session, test_user, user_b):
        """Press outlets specifically should round-trip as arrays."""
        self._import_einstein(db_session, test_user.id)
        resp = client.get("/api/export/yaml")
        exported = yaml.safe_load(resp.content)

        # Verify outlets in export are arrays
        media = exported["cv"]["media"]
        eclipse = [m for m in media if "eclipse" in m.get("topic", "").lower()][0]
        assert isinstance(eclipse["outlets"], list)
        assert "The Times (London)" in eclipse["outlets"]

        # Reimport and verify
        with tempfile.TemporaryDirectory() as tmpdir:
            cv_path = os.path.join(tmpdir, "cv.yml")
            with open(cv_path, "w") as f:
                yaml.dump(exported["cv"], f, allow_unicode=True)
            import_cv_yaml(cv_path, db_session, user_id=user_b.id)

        items = self._cv_items(db_session, user_b.id, "press")
        eclipse_item = [i for i in items if "eclipse" in (i.data.get("topic") or "").lower()][0]
        assert eclipse_item.data["outlets"] == ["The Times (London)", "The New York Times"]

    def test_grants_split_by_status(self, client, db_session, test_user):
        """Grants should export as activegrants/completedgrants, not single grants key."""
        self._import_einstein(db_session, test_user.id)
        resp = client.get("/api/export/yaml")
        exported = yaml.safe_load(resp.content)
        cv = exported["cv"]

        assert "grants" not in cv, "Should not have undifferentiated 'grants' key"
        assert "activegrants" in cv
        assert "completedgrants" in cv
        assert len(cv["activegrants"]) >= 1
        assert len(cv["completedgrants"]) >= 1
