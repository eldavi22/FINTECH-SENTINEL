"""Check the API and the decisions made by the transaction risk engine."""

import unittest
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import Base, app, calculate_risk, get_db


class FintechSentinelTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

        def temporary_db():
            with session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = temporary_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def payload(self, txn_id="TXN-TEST-001", **changes):
        data = {
            "txn_id": txn_id,
            "amount": "100",
            "transaction_type": "PAYMENT",
            "customer_risk": "LOW",
            "country_risk": "LOW",
            "previous_alerts": 0,
            "description": "Regular payment",
        }
        data.update(changes)
        return data

    def test_health_and_api_metadata(self):
        self.assertEqual(self.client.get("/api/health").json()["database"], "connected")
        self.assertEqual(self.client.get("/api").json()["status"], "operational")

    def test_low_risk_transaction_is_saved_and_retrievable(self):
        result = self.client.post("/api/risk/analyze", json=self.payload())
        self.assertEqual(result.status_code, 200)
        assessment = result.json()
        self.assertEqual(assessment["risk_level"], "LOW")
        self.assertEqual(assessment["status"], "Approved")
        self.assertIn("TXN-TEST-001", assessment["report"])
        retrieved = self.client.get("/api/transactions/TXN-TEST-001")
        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(retrieved.json()["risk_score"], assessment["risk_score"])
        details = self.client.get("/api/risk/assessments/" + assessment["assessment_id"])
        self.assertEqual(details.status_code, 200)
        self.assertEqual(details.json()["txn_id"], "TXN-TEST-001")

    def test_critical_risk_is_blocked_with_explainable_factors(self):
        result = self.client.post("/api/risk/analyze", json=self.payload(
            amount="100000", customer_risk="CRITICAL",
            country_risk="CRITICAL", previous_alerts=5,
            description="Suspicious fraud and money laundering",
        ))
        self.assertEqual(result.status_code, 200)
        body = result.json()
        self.assertEqual(body["risk_score"], 100)
        self.assertEqual(body["risk_level"], "CRITICAL")
        self.assertEqual(body["status"], "Blocked")
        self.assertGreaterEqual(len(body["risk_factors"]), 3)

    def test_duplicate_transaction_is_rejected_without_new_assessment(self):
        self.assertEqual(self.client.post("/api/risk/analyze", json=self.payload()).status_code, 200)
        duplicate = self.client.post("/api/risk/analyze", json=self.payload())
        self.assertEqual(duplicate.status_code, 409)
        self.assertIn("already exists", duplicate.json()["detail"])
        self.assertEqual(len(self.client.get("/api/transactions").json()), 1)

    def test_invalid_inputs_are_rejected(self):
        for changes in ({"amount": "-1"}, {"previous_alerts": -1}, {"txn_id": ""}):
            with self.subTest(changes=changes):
                response = self.client.post("/api/risk/analyze", json=self.payload(**changes))
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.get("/api/transactions").json(), [])

    def test_missing_records_return_404(self):
        self.assertEqual(self.client.get("/api/transactions/missing").status_code, 404)
        self.assertEqual(self.client.get("/api/risk/assessments/missing").status_code, 404)

    def test_transaction_search_only_returns_matches(self):
        for txn_id in ("TXN-ALPHA", "TXN-BETA"):
            self.assertEqual(self.client.post("/api/risk/analyze", json=self.payload(txn_id)).status_code, 200)
        rows = self.client.get("/api/transactions", params={"q": "ALPHA"}).json()
        self.assertEqual([row["txn_id"] for row in rows], ["TXN-ALPHA"])

    def test_report_escapes_untrusted_transaction_id(self):
        result = self.client.post("/api/risk/analyze", json=self.payload("<script>alert(1)</script>"))
        self.assertEqual(result.status_code, 200)
        report = result.json()["report"]
        self.assertNotIn("<script>", report)
        self.assertIn("&lt;script&gt;", report)

    def test_risk_threshold_boundaries(self):
        samples = (
            (Decimal("0"), "PAYMENT", "LOW", "LOW", 0, "LOW", "Approved"),
            (Decimal("100000"), "TRANSFER", "CRITICAL", "CRITICAL", 5, "CRITICAL", "Blocked"),
        )
        for amount, transaction_type, customer, country, alerts, level, status in samples:
            with self.subTest(amount=amount):
                score, result_level, result_status, *_ = calculate_risk(
                    amount, transaction_type, customer, country, alerts, None
                )
                self.assertGreaterEqual(score, 0)
                self.assertLessEqual(score, 100)
                self.assertEqual(result_level, level)
                self.assertEqual(result_status, status)

    def test_more_alerts_do_not_lower_risk(self):
        scores = [
            calculate_risk(Decimal("15000"), "TRANSFER", "MEDIUM", "LOW", count, None)[0]
            for count in range(7)
        ]
        self.assertEqual(scores, sorted(scores))


if __name__ == "__main__":
    unittest.main()
