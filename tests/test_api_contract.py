import unittest
import tempfile
from io import BytesIO
from pathlib import Path


try:
    from fastapi.testclient import TestClient

    from src import storage
    from src.api import app
    from src.auth import create_user_account

    FASTAPI_AVAILABLE = True
except ModuleNotFoundError:
    FASTAPI_AVAILABLE = False


@unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI is not installed")
class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_directory = tempfile.TemporaryDirectory()
        cls.original_database_path = storage.DATABASE_PATH
        storage.DATABASE_PATH = Path(cls.database_directory.name) / "test-recommendations.db"
        create_user_account("test-admin", "AdminPassword123!", "admin")
        create_user_account("test-buyer", "BuyerPassword123!", "procurement")

    @classmethod
    def tearDownClass(cls):
        storage.DATABASE_PATH = cls.original_database_path
        cls.database_directory.cleanup()

    def setUp(self):
        self.client = TestClient(app)
        response = self.client.post(
            "/auth/login",
            json={"username": "test-admin", "password": "AdminPassword123!"},
        )
        self.assertEqual(response.status_code, 200)

    def test_authentication_and_role_permissions(self):
        anonymous = TestClient(app)
        protected_response = anonymous.post(
            "/recommend", json={"query": "TMT bars", "limit": 1}
        )
        self.assertEqual(protected_response.status_code, 401)

        buyer = TestClient(app)
        login_response = buyer.post(
            "/auth/login",
            json={"username": "test-buyer", "password": "BuyerPassword123!"},
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.json()["role"], "procurement")
        self.assertEqual(buyer.get("/auth/me").json()["username"], "test-buyer")
        self.assertEqual(buyer.get("/admin").status_code, 403)
        self.assertEqual(buyer.get("/review-summary").status_code, 403)

        logout_response = buyer.post("/auth/logout")
        self.assertEqual(logout_response.status_code, 204)
        self.assertEqual(buyer.get("/auth/me").status_code, 401)

    def test_health_returns_dataset_count(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["standards_count"], 250)
        self.assertIn("X-Request-ID", response.headers)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])

    def test_liveness_and_readiness_checks(self):
        live_response = self.client.get("/health/live")
        ready_response = self.client.get("/health/ready")

        self.assertEqual(live_response.status_code, 200)
        self.assertEqual(live_response.json()["status"], "alive")
        self.assertEqual(ready_response.status_code, 200)
        self.assertEqual(ready_response.json()["status"], "ready")
        self.assertEqual(ready_response.json()["database"], "ok")
        self.assertEqual(ready_response.json()["standards_count"], 250)

        metrics_response = self.client.get("/metrics")
        self.assertEqual(metrics_response.status_code, 200)
        self.assertIn("standards_app_requests_total", metrics_response.text)

    def test_root_serves_frontend(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Indian Standards Recommendation Engine", response.text)
        self.assertIn("Standards Library", response.text)
        self.assertIn("Recent Runs", response.text)

    def test_admin_serves_review_console(self):
        response = self.client.get("/admin")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Standards Operations", response.text)

    def test_recommend_returns_ranked_results(self):
        response = self.client.post(
            "/recommend",
            json={"query": "TMT bars for RCC work", "limit": 3},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["query"], "TMT bars for RCC work")
        self.assertGreater(payload["count"], 0)
        self.assertIsInstance(payload["search_id"], int)
        self.assertEqual(payload["results"][0]["standard_code"], "IS 1786:2008")
        self.assertIn(payload["results"][0]["confidence_label"], {"high", "moderate", "low"})
        self.assertGreater(payload["results"][0]["confidence_score"], 0)

    def test_feedback_history_and_analytics_flow(self):
        recommend_response = self.client.post(
            "/recommend",
            json={"query": "TMT bars for RCC work", "limit": 1},
        )
        recommend_payload = recommend_response.json()
        result = recommend_payload["results"][0]

        feedback_response = self.client.post(
            "/feedback",
            json={
                "search_id": recommend_payload["search_id"],
                "standard_id": result["id"],
                "standard_code": result["standard_code"],
                "rating": "useful",
            },
        )

        self.assertEqual(feedback_response.status_code, 200)
        self.assertEqual(feedback_response.json()["status"], "saved")

        history_response = self.client.get("/search-history", params={"limit": 5})
        self.assertEqual(history_response.status_code, 200)
        self.assertGreaterEqual(len(history_response.json()), 1)

        analytics_response = self.client.get("/analytics")
        self.assertEqual(analytics_response.status_code, 200)
        self.assertGreaterEqual(analytics_response.json()["feedback"]["useful"], 1)
        self.assertIn("top_feedback_standards", analytics_response.json())

    def test_human_review_flow_updates_decision_and_exports_label(self):
        recommend_response = self.client.post(
            "/recommend",
            json={"query": "TMT bars for RCC work", "limit": 1},
        )
        recommendation = recommend_response.json()
        result = recommendation["results"][0]
        review = {
            "search_id": recommendation["search_id"],
            "standard_id": result["id"],
            "standard_code": result["standard_code"],
            "decision": "accepted",
            "note": "Matches the reinforcement specification.",
        }

        accepted_response = self.client.post("/reviews", json=review)
        review["decision"] = "rejected"
        review["note"] = "Updated after technical review."
        rejected_response = self.client.post("/reviews", json=review)

        self.assertEqual(accepted_response.status_code, 200)
        self.assertEqual(rejected_response.status_code, 200)
        self.assertEqual(
            accepted_response.json()["review_id"],
            rejected_response.json()["review_id"],
        )

        reviews_response = self.client.get("/reviews", params={"limit": 50})
        saved_review = next(
            item
            for item in reviews_response.json()
            if item["search_id"] == recommendation["search_id"]
            and item["standard_id"] == result["id"]
        )
        self.assertEqual(saved_review["decision"], "rejected")
        self.assertEqual(saved_review["note"], "Updated after technical review.")

        summary_response = self.client.get("/review-summary")
        self.assertEqual(summary_response.status_code, 200)
        self.assertGreaterEqual(summary_response.json()["rejected"], 1)

        export_response = self.client.get("/reports/review-dataset.csv")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("Relevance Label", export_response.text)
        self.assertIn("TMT bars for RCC work", export_response.text)

    def test_review_rejects_standard_not_in_saved_search(self):
        recommend_response = self.client.post(
            "/recommend",
            json={"query": "TMT bars for RCC work", "limit": 1},
        )
        response = self.client.post(
            "/reviews",
            json={
                "search_id": recommend_response.json()["search_id"],
                "standard_id": "STD-NOT-RETURNED",
                "standard_code": "IS 0000:2000",
                "decision": "accepted",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("not returned", response.json()["detail"])

    def test_admin_verification_update_is_audited_and_updates_catalog(self):
        before = self.client.get("/standards/STD-0001").json()
        payload = {
            "title": before["title"],
            "source_url": "https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/standard_review/",
            "verify_status": "officially_verified",
            "note": "Checked against the official BIS standards portal.",
        }

        update_response = self.client.put(
            "/admin/standards/STD-0001/verification",
            json=payload,
        )

        self.assertEqual(update_response.status_code, 200)
        updated = update_response.json()
        self.assertEqual(updated["verify_status"], "officially_verified")
        self.assertEqual(updated["source_url"], payload["source_url"])
        self.assertEqual(updated["verification_note"], payload["note"])

        queue_response = self.client.get(
            "/verification-queue",
            params={"status": "officially_verified", "q": "IS 456"},
        )
        self.assertEqual(queue_response.status_code, 200)
        self.assertTrue(any(item["id"] == "STD-0001" for item in queue_response.json()))

        history_response = self.client.get("/verification-history")
        self.assertEqual(history_response.status_code, 200)
        history = next(
            item for item in history_response.json() if item["standard_id"] == "STD-0001"
        )
        self.assertEqual(history["changed_by"], "test-admin")
        self.assertEqual(history["previous_data"]["verify_status"], before["verify_status"])

        buyer = TestClient(app)
        buyer.post(
            "/auth/login",
            json={"username": "test-buyer", "password": "BuyerPassword123!"},
        )
        forbidden_response = buyer.put(
            "/admin/standards/STD-0001/verification",
            json=payload,
        )
        self.assertEqual(forbidden_response.status_code, 403)

    def test_dataset_quality_returns_catalog_metrics(self):
        response = self.client.get("/dataset-quality")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["standards_count"], 250)
        self.assertGreater(payload["needs_verification_count"], 0)
        self.assertGreater(len(payload["top_categories"]), 0)

    def test_search_report_exports_saved_results_as_csv(self):
        recommend_response = self.client.post(
            "/recommend",
            json={"query": "TMT bars for RCC work", "limit": 2},
        )
        search_id = recommend_response.json()["search_id"]

        response = self.client.get(f"/reports/search/{search_id}.csv")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])
        self.assertIn(f"recommendation-report-{search_id}.csv", response.headers["content-disposition"])
        self.assertIn("IS 1786:2008", response.text)
        self.assertIn("Verification Status", response.text)

        pdf_response = self.client.get(f"/reports/search/{search_id}.pdf")
        self.assertEqual(pdf_response.status_code, 200)
        self.assertIn("application/pdf", pdf_response.headers["content-type"])
        self.assertTrue(pdf_response.content.startswith(b"%PDF"))
        self.assertGreater(len(pdf_response.content), 2000)

    def test_saved_search_can_be_reopened(self):
        recommend_response = self.client.post(
            "/recommend",
            json={"query": "LED street lights for road project", "limit": 3},
        )
        original = recommend_response.json()

        response = self.client.get(f"/search-history/{original['search_id']}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], original["search_id"])
        self.assertEqual(payload["query"], "LED street lights for road project")
        self.assertEqual(payload["results"], original["results"])

    def test_retrieval_quality_and_demo_document_are_available(self):
        quality_response = self.client.get("/retrieval-quality")
        demo_response = self.client.get("/demo-document")

        self.assertEqual(quality_response.status_code, 200)
        self.assertEqual(quality_response.json()["query_count"], 375)
        self.assertGreaterEqual(quality_response.json()["top_1_accuracy"], 0.9)
        self.assertEqual(demo_response.status_code, 200)
        self.assertIn("application/pdf", demo_response.headers["content-type"])

    def test_search_report_returns_404_for_unknown_search(self):
        response = self.client.get("/reports/search/999999999.csv")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Saved search not found")

    def test_dataset_quality_report_exports_csv(self):
        response = self.client.get("/reports/dataset-quality.csv")

        self.assertEqual(response.status_code, 200)
        self.assertIn("dataset-quality-report.csv", response.headers["content-disposition"])
        self.assertIn("Needs Official Verification", response.text)
        self.assertIn("Category,Count", response.text)

    def test_extract_document_returns_text_from_txt_upload(self):
        response = self.client.post(
            "/extract-document",
            files={"file": ("tender.txt", b"LED street lights for road project", "text/plain")},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["extension"], ".txt")
        self.assertIn("LED street lights", payload["text"])

    def test_recommend_document_returns_ranked_results_from_upload(self):
        response = self.client.post(
            "/recommend-document",
            data={"limit": "3", "mode": "hybrid"},
            files={"file": ("tender.txt", b"LED street lights for road project", "text/plain")},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["filename"], "tender.txt")
        self.assertGreater(payload["count"], 0)
        self.assertIsInstance(payload["search_id"], int)
        self.assertEqual(payload["clauses_analyzed"], 1)
        self.assertEqual(payload["results"][0]["standard_code"], "IS 16107 Part 2 Section 2:2017")
        self.assertIn("LED street lights", payload["results"][0]["evidence_clauses"][0])

    def test_document_recommendation_aggregates_multiple_clauses(self):
        content = (
            b"1. Supply TMT reinforcement rods for RCC slab construction.\n"
            b"2. Provide LED street lighting fixtures for municipal poles."
        )
        response = self.client.post(
            "/recommend-document",
            data={"limit": "5", "mode": "hybrid"},
            files={"file": ("multi-item-tender.txt", content, "text/plain")},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["clauses_analyzed"], 2)
        codes = [result["standard_code"] for result in payload["results"]]
        self.assertIn("IS 1786:2008", codes)
        self.assertIn("IS 16107 Part 2 Section 2:2017", codes)
        self.assertTrue(all(result["evidence_clauses"] for result in payload["results"]))

    def test_extract_document_rejects_unsupported_file_type(self):
        response = self.client.post(
            "/extract-document",
            files={"file": ("tender.xlsx", b"not supported", "application/octet-stream")},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file type", response.json()["detail"])

    def test_extract_document_explains_scanned_pdf_limitation(self):
        import fitz

        document = fitz.open()
        document.new_page()
        content = document.tobytes()
        document.close()

        response = self.client.post(
            "/extract-document",
            files={"file": ("scan.pdf", BytesIO(content), "application/pdf")},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("scanned PDF", response.json()["detail"])
        self.assertIn("OCR", response.json()["detail"])

    def test_list_standards_can_filter_by_text(self):
        response = self.client.get("/standards", params={"q": "LED street", "limit": 5})

        self.assertEqual(response.status_code, 200)
        standards = response.json()
        self.assertGreater(len(standards), 0)
        self.assertTrue(any("LED" in standard["title"] for standard in standards))

    def test_get_standard_by_id(self):
        response = self.client.get("/standards/STD-0002")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["standard_code"], "IS 1786:2008")


if __name__ == "__main__":
    unittest.main()
