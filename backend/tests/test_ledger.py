"""Comprehensive tests for import/export flow, proration, search, and ledger operations."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.models.export_line import ExportLine
from app.models.import_line import ImportLine
from tests.conftest import login


# --- Helpers ---

def _create_import_line(db, **kwargs):
    """Create an import line directly in the DB for testing."""
    defaults = dict(
        consignor_exporter="TEST CORP",
        description="Test product",
        import_file_number="IMP/001",
        import_entry_number="25NBOIM001",
        hs_code="29336900",
        country="KE",
        supplementary_units=Decimal("100"),
        unit="KG",
        quantity_imported=Decimal("1000"),
        customs_value_kes=Decimal("50000"),
        bif_value_kes=Decimal("10000"),
        balance_quantity=Decimal("1000"),
        balance_customs_value=Decimal("50000"),
        balance_bif_value=Decimal("10000"),
        balance_supplementary_units=Decimal("100"),
        is_legacy=False,
    )
    defaults.update(kwargs)
    line = ImportLine(**defaults)
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


# --- Import Confirm Tests ---

class TestImportConfirm:
    def test_single_import_creates_line(self, client, db_session, admin_user):
        login(client, "admin", "adminpass123")
        resp = client.post("/api/import/confirm", json=[{
            "consignor_exporter": "ACME LTD",
            "description": "Widgets",
            "import_file_number": "IMP/100",
            "import_entry_number": "25NBOIM999",
            "hs_code": "84713000",
            "country": "CN",
            "unit": "UNT",
            "quantity_imported": 500,
            "customs_value_kes": 250000,
            "bif_value_kes": 50000,
        }])
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert Decimal(data[0]["quantity_imported"]) == 500
        assert Decimal(data[0]["balance_quantity"]) == 500  # no exports yet
        assert Decimal(data[0]["balance_customs_value"]) == 250000

    def test_multi_item_import(self, client, db_session, admin_user):
        login(client, "admin", "adminpass123")
        resp = client.post("/api/import/confirm", json=[
            {"quantity_imported": 100, "customs_value_kes": 10000, "description": "Item A"},
            {"quantity_imported": 200, "customs_value_kes": 20000, "description": "Item B"},
            {"quantity_imported": 300, "customs_value_kes": 30000, "description": "Item C"},
        ])
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_import_requires_auth(self, client, db_session):
        resp = client.post("/api/import/confirm", json=[{"quantity_imported": 100, "customs_value_kes": 5000}])
        assert resp.status_code == 401


# --- Export Confirm & Proration Tests ---

class TestExportConfirm:
    def test_full_export_zeroes_balance(self, client, db_session, admin_user):
        """Full export: T = J → balance should be zero."""
        imp = _create_import_line(db_session)
        login(client, "admin", "adminpass123")

        resp = client.post("/api/export/confirm", json=[{
            "import_line_id": imp.id,
            "customer_name": "BUYER A",
            "quantity_exported": 1000,
        }])
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert Decimal(data[0]["quantity_exported"]) == 1000
        # Prorated: U = K * T/J = 50000 * 1000/1000 = 50000
        assert Decimal(data[0]["customs_value_exported"]) == 50000

        # Check balance is zero
        db_session.expire_all()
        db_imp = db_session.get(ImportLine, imp.id)
        assert db_imp.balance_quantity == 0
        assert db_imp.balance_customs_value == 0

    def test_partial_export_proration(self, client, db_session, admin_user):
        """Partial export: prorated values should be proportional."""
        imp = _create_import_line(db_session)
        login(client, "admin", "adminpass123")

        resp = client.post("/api/export/confirm", json=[{
            "import_line_id": imp.id,
            "customer_name": "BUYER B",
            "quantity_exported": 250,
        }])
        assert resp.status_code == 200
        data = resp.json()
        # U = 50000 * 250/1000 = 12500
        assert Decimal(data[0]["customs_value_exported"]) == 12500
        # V = 10000 * 250/1000 = 2500
        assert Decimal(data[0]["bif_value_exported"]) == 2500

        db_session.expire_all()
        db_imp = db_session.get(ImportLine, imp.id)
        assert db_imp.balance_quantity == 750
        assert db_imp.balance_customs_value == 37500

    def test_multiple_partial_exports(self, client, db_session, admin_user):
        """Three partial exports against one import line."""
        imp = _create_import_line(db_session)
        login(client, "admin", "adminpass123")

        for qty in [300, 400, 200]:
            resp = client.post("/api/export/confirm", json=[{
                "import_line_id": imp.id,
                "quantity_exported": qty,
            }])
            assert resp.status_code == 200

        db_session.expire_all()
        db_imp = db_session.get(ImportLine, imp.id)
        assert db_imp.balance_quantity == 100  # 1000 - 300 - 400 - 200

    def test_overdraft_blocked(self, client, db_session, admin_user):
        """Over-export is blocked without admin override."""
        imp = _create_import_line(db_session, quantity_imported=Decimal("100"), balance_quantity=Decimal("100"))
        login(client, "admin", "adminpass123")

        resp = client.post("/api/export/confirm", json=[{
            "import_line_id": imp.id,
            "quantity_exported": 150,
        }])
        assert resp.status_code == 400
        assert "exceeds" in resp.json()["detail"].lower()

    def test_overdraft_admin_override(self, client, db_session, admin_user):
        """Admin override allows overdraft with reason."""
        imp = _create_import_line(db_session, quantity_imported=Decimal("100"), balance_quantity=Decimal("100"),
                                   customs_value_kes=Decimal("10000"), balance_customs_value=Decimal("10000"))
        login(client, "admin", "adminpass123")

        resp = client.post(
            "/api/export/confirm?admin_override=true&override_reason=Approved+by+manager",
            json=[{"import_line_id": imp.id, "quantity_exported": 150}],
        )
        assert resp.status_code == 200

        db_session.expire_all()
        db_imp = db_session.get(ImportLine, imp.id)
        assert db_imp.balance_quantity == -50

    def test_zero_quantity_blocked(self, client, db_session, admin_user):
        """J=0 should block proration."""
        imp = _create_import_line(db_session, quantity_imported=Decimal("0"), balance_quantity=Decimal("0"))
        login(client, "admin", "adminpass123")

        resp = client.post("/api/export/confirm", json=[{
            "import_line_id": imp.id,
            "quantity_exported": 10,
        }])
        assert resp.status_code == 400
        assert "zero" in resp.json()["detail"].lower()

    def test_export_against_two_import_lines(self, client, db_session, admin_user):
        """One export PDF drawing from two different import lines."""
        imp1 = _create_import_line(db_session, description="Product A")
        imp2 = _create_import_line(db_session, description="Product B")
        login(client, "admin", "adminpass123")

        resp = client.post("/api/export/confirm", json=[
            {"import_line_id": imp1.id, "quantity_exported": 200},
            {"import_line_id": imp2.id, "quantity_exported": 300},
        ])
        assert resp.status_code == 200
        assert len(resp.json()) == 2

        db_session.expire_all()
        assert db_session.get(ImportLine, imp1.id).balance_quantity == 800
        assert db_session.get(ImportLine, imp2.id).balance_quantity == 700


# --- Export Delete & Balance Restore ---

class TestExportDelete:
    def test_delete_restores_balance(self, client, db_session, admin_user):
        imp = _create_import_line(db_session)
        login(client, "admin", "adminpass123")

        # Create export
        resp = client.post("/api/export/confirm", json=[{
            "import_line_id": imp.id,
            "quantity_exported": 400,
        }])
        export_id = resp.json()[0]["id"]

        db_session.expire_all()
        assert db_session.get(ImportLine, imp.id).balance_quantity == 600

        # Delete export
        resp = client.delete(f"/api/export/{export_id}")
        assert resp.status_code == 204

        db_session.expire_all()
        assert db_session.get(ImportLine, imp.id).balance_quantity == 1000  # restored

    def test_delete_requires_admin(self, client, db_session, regular_user, admin_user):
        imp = _create_import_line(db_session)
        login(client, "admin", "adminpass123")
        resp = client.post("/api/export/confirm", json=[{"import_line_id": imp.id, "quantity_exported": 100}])
        export_id = resp.json()[0]["id"]

        # Login as regular user
        login(client, "alice", "alicepass123")
        resp = client.delete(f"/api/export/{export_id}")
        assert resp.status_code == 403


# --- Proration Preview ---

class TestProrationPreview:
    def test_preview_calculates_correctly(self, client, db_session, admin_user):
        imp = _create_import_line(db_session)
        login(client, "admin", "adminpass123")

        resp = client.post(f"/api/export/preview-proration?import_line_id={imp.id}&quantity_exported=500")
        assert resp.status_code == 200
        data = resp.json()
        assert Decimal(data["prorated_customs_value"]) == 25000  # 50000 * 500/1000
        assert Decimal(data["prorated_bif_value"]) == 5000
        assert Decimal(data["remaining_quantity"]) == 500
        assert data["overdraft"] is False

    def test_preview_detects_overdraft(self, client, db_session, admin_user):
        imp = _create_import_line(db_session, quantity_imported=Decimal("100"), balance_quantity=Decimal("100"))
        login(client, "admin", "adminpass123")

        resp = client.post(f"/api/export/preview-proration?import_line_id={imp.id}&quantity_exported=150")
        assert resp.status_code == 200
        data = resp.json()
        assert data["overdraft"] is True
        assert Decimal(data["remaining_quantity"]) == -50


# --- Search ---

class TestSearch:
    def test_search_by_entry_number(self, client, db_session, admin_user):
        _create_import_line(db_session, import_entry_number="25NBOIM999")
        _create_import_line(db_session, import_entry_number="25NBOIM888")
        login(client, "admin", "adminpass123")

        resp = client.get("/api/ledger/search?entry_number=999")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_search_open_balance_only(self, client, db_session, admin_user):
        _create_import_line(db_session, balance_quantity=Decimal("100"))
        _create_import_line(db_session, balance_quantity=Decimal("0"))
        login(client, "admin", "adminpass123")

        resp = client.get("/api/ledger/search?open_balance_only=true")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_search_by_hs_code(self, client, db_session, admin_user):
        _create_import_line(db_session, hs_code="12345678")
        _create_import_line(db_session, hs_code="87654321")
        login(client, "admin", "adminpass123")

        resp = client.get("/api/ledger/search?hs_code=12345678")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


# --- Import Line Detail ---

class TestImportLineDetail:
    def test_detail_includes_exports(self, client, db_session, admin_user):
        imp = _create_import_line(db_session)
        login(client, "admin", "adminpass123")

        # Create exports
        client.post("/api/export/confirm", json=[
            {"import_line_id": imp.id, "quantity_exported": 100},
            {"import_line_id": imp.id, "quantity_exported": 200},
        ])

        resp = client.get(f"/api/ledger/import-lines/{imp.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["export_lines"]) == 2


# --- Dashboard ---

class TestDashboard:
    def test_dashboard_returns_stats(self, client, db_session, admin_user):
        _create_import_line(db_session, balance_quantity=Decimal("100"))
        _create_import_line(db_session, balance_quantity=Decimal("0"))
        login(client, "admin", "adminpass123")

        resp = client.get("/api/ledger/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_import_lines"] == 2
        assert data["open_balance_lines"] == 1


# --- Audit Log ---

class TestAuditLog:
    def test_audit_log_tracks_import(self, client, db_session, admin_user):
        login(client, "admin", "adminpass123")
        client.post("/api/import/confirm", json=[{"quantity_imported": 100, "customs_value_kes": 5000}])

        resp = client.get("/api/ledger/audit?entity_type=import_line")
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) >= 1
        assert logs[0]["change_type"] == "create"

    def test_audit_log_tracks_export_delete(self, client, db_session, admin_user):
        imp = _create_import_line(db_session)
        login(client, "admin", "adminpass123")

        resp = client.post("/api/export/confirm", json=[{"import_line_id": imp.id, "quantity_exported": 100}])
        export_id = resp.json()[0]["id"]

        client.delete(f"/api/export/{export_id}")

        resp = client.get("/api/ledger/audit?entity_type=export_line&change_type=delete")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# --- Match Candidates ---

class TestMatchCandidates:
    def test_match_by_hs_code(self, client, db_session, admin_user):
        _create_import_line(db_session, hs_code="12345678", balance_quantity=Decimal("100"))
        _create_import_line(db_session, hs_code="87654321", balance_quantity=Decimal("200"))
        _create_import_line(db_session, hs_code="12345678", balance_quantity=Decimal("0"))
        login(client, "admin", "adminpass123")

        resp = client.get("/api/export/match-candidates?hs_code=12345678")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1  # only one with positive balance


# --- Download ---

class TestDownload:
    def test_download_generates_xlsx(self, client, db_session, admin_user):
        _create_import_line(db_session)
        login(client, "admin", "adminpass123")

        resp = client.get("/api/ledger/download")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]
        assert len(resp.content) > 100  # has actual content


class TestExportEntriesCsv:
    def test_requires_admin(self, client, db_session, regular_user):
        login(client, "alice", "alicepass123")
        resp = client.get("/api/ledger/entries/export")
        assert resp.status_code == 403

    def test_exports_import_and_export_rows(self, client, db_session, admin_user):
        imp = _create_import_line(db_session)
        login(client, "admin", "adminpass123")
        client.post("/api/export/confirm", json=[{
            "import_line_id": imp.id,
            "customer_name": "BUYER A",
            "quantity_exported": 400,
        }])

        resp = client.get("/api/ledger/entries/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        body = resp.text
        assert "IMPORT ENTRIES" in body
        assert "EXPORT ENTRIES" in body
        assert "BUYER A" in body
