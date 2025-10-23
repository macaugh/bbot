import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from .base import ModuleTestBase


class TestDiscord_ScanSummary(ModuleTestBase):
    """Test Discord scan completion summary with Google Drive links"""

    targets = ["example.com"]
    modules_overrides = ["httpx"]
    config_overrides = {
        "modules": {
            "discord": {
                "webhook_url": "https://discord.com/api/webhooks/test/webhook",
                "include_scan_summary": True,
                "include_drive_links": True,
            }
        }
    }

    async def setup_before_prep(self, module_test):
        """Setup mock HTTP responses"""
        # Track webhook POST requests
        self.webhook_posts = []

        def capture_webhook(request):
            """Capture webhook POST data"""
            import json

            self.webhook_posts.append(json.loads(request.get_data(as_text=True)))
            return ("", 204)  # Discord returns 204 No Content on success

        # Setup httpserver to capture webhook posts
        module_test.httpserver.expect_request(
            "/api/webhooks/test/webhook", method="POST"
        ).respond_with_handler(capture_webhook)

    async def setup_after_prep(self, module_test):
        """Inject Google Drive links into scan context"""
        # Simulate Google Drive module having uploaded files
        module_test.scan.context["google_drive_csv_link"] = (
            "https://drive.google.com/file/d/test-csv-id/view"
        )
        module_test.scan.context["google_drive_methodology_links"] = [
            {"name": "example.com_WordPress", "link": "https://drive.google.com/file/d/wp-id/view"},
            {"name": "example.com_Apache", "link": "https://drive.google.com/file/d/apache-id/view"},
        ]
        module_test.scan.context["google_drive_folder_link"] = (
            "https://drive.google.com/drive/folders/test-folder-id"
        )

    def check(self, module_test, events):
        """Verify Discord scan summary was posted with Drive links"""
        # Check that webhook was called
        assert len(self.webhook_posts) > 0, "No webhook POST requests captured"

        # Find the scan summary embed
        scan_summary = None
        for post in self.webhook_posts:
            if "embeds" in post:
                for embed in post["embeds"]:
                    if "Scan Complete" in embed.get("title", ""):
                        scan_summary = embed
                        break

        assert scan_summary is not None, "Scan summary embed not found in webhook posts"

        # Verify embed structure
        assert "title" in scan_summary, "Embed missing title"
        assert "example.com" in scan_summary["title"], "Scan name not in title"

        # Check for fields
        assert "fields" in scan_summary, "Embed missing fields"
        fields = scan_summary["fields"]

        # Verify CSV Report field with link
        csv_field = next((f for f in fields if "CSV Report" in f.get("name", "")), None)
        assert csv_field is not None, "CSV Report field not found"
        assert "drive.google.com" in csv_field["value"], "CSV link not in embed"

        # Verify Methodology Checklists field
        methodology_field = next((f for f in fields if "Methodology" in f.get("name", "")), None)
        assert methodology_field is not None, "Methodology field not found"
        assert "example.com_WordPress" in methodology_field["value"], "WordPress checklist not in embed"
        assert "example.com_Apache" in methodology_field["value"], "Apache checklist not in embed"


class TestDiscord_ScanSummary_NoDriveLinks(ModuleTestBase):
    """Test Discord scan summary without Google Drive (Drive module not enabled)"""

    targets = ["example.com"]
    modules_overrides = ["httpx"]
    config_overrides = {
        "modules": {
            "discord": {
                "webhook_url": "https://discord.com/api/webhooks/test/webhook",
                "include_scan_summary": True,
                "include_drive_links": True,  # Enabled but no Drive data
            }
        }
    }

    async def setup_before_prep(self, module_test):
        """Setup mock HTTP responses"""
        self.webhook_posts = []

        def capture_webhook(request):
            import json

            self.webhook_posts.append(json.loads(request.get_data(as_text=True)))
            return ("", 204)

        module_test.httpserver.expect_request(
            "/api/webhooks/test/webhook", method="POST"
        ).respond_with_handler(capture_webhook)

    async def setup_after_prep(self, module_test):
        """Do NOT inject Drive links (simulating Drive module disabled)"""
        # scan.context should not have any Drive links
        pass

    def check(self, module_test, events):
        """Verify scan summary works without Drive links"""
        assert len(self.webhook_posts) > 0, "No webhook POST requests captured"

        # Find scan summary
        scan_summary = None
        for post in self.webhook_posts:
            if "embeds" in post:
                for embed in post["embeds"]:
                    if "Scan Complete" in embed.get("title", ""):
                        scan_summary = embed
                        break

        assert scan_summary is not None, "Scan summary embed not found"

        # Verify basic structure exists
        assert "title" in scan_summary
        assert "fields" in scan_summary

        # CSV and Methodology fields should NOT exist
        fields = scan_summary["fields"]
        csv_field = next((f for f in fields if "CSV Report" in f.get("name", "")), None)
        methodology_field = next((f for f in fields if "Methodology" in f.get("name", "")), None)

        assert csv_field is None, "CSV field should not exist without Drive module"
        assert methodology_field is None, "Methodology field should not exist without Drive module"


class TestDiscord_ScanSummary_Disabled(ModuleTestBase):
    """Test that scan summary can be disabled"""

    targets = ["example.com"]
    modules_overrides = ["httpx"]
    config_overrides = {
        "modules": {
            "discord": {
                "webhook_url": "https://discord.com/api/webhooks/test/webhook",
                "include_scan_summary": False,  # Disabled
                "include_drive_links": True,
            }
        }
    }

    async def setup_before_prep(self, module_test):
        """Setup mock HTTP responses"""
        self.webhook_posts = []

        def capture_webhook(request):
            import json

            self.webhook_posts.append(json.loads(request.get_data(as_text=True)))
            return ("", 204)

        module_test.httpserver.expect_request(
            "/api/webhooks/test/webhook", method="POST"
        ).respond_with_handler(capture_webhook)

    async def setup_after_prep(self, module_test):
        """Inject Drive links (should not be used if summary disabled)"""
        module_test.scan.context["google_drive_csv_link"] = "https://drive.google.com/file/d/test/view"

    def check(self, module_test, events):
        """Verify scan summary was NOT posted when disabled"""
        # Check if any scan summary embeds were posted
        scan_summaries = []
        for post in self.webhook_posts:
            if "embeds" in post:
                for embed in post["embeds"]:
                    if "Scan Complete" in embed.get("title", ""):
                        scan_summaries.append(embed)

        assert len(scan_summaries) == 0, "Scan summary should not be posted when disabled"


class TestDiscord_ScanSummary_Statistics(ModuleTestBase):
    """Test that scan statistics are included in summary"""

    targets = ["example.com"]
    modules_overrides = ["httpx"]
    config_overrides = {
        "modules": {
            "discord": {
                "webhook_url": "https://discord.com/api/webhooks/test/webhook",
                "include_scan_summary": True,
                "include_drive_links": False,
            }
        }
    }

    async def setup_before_prep(self, module_test):
        """Setup mock HTTP responses"""
        self.webhook_posts = []

        def capture_webhook(request):
            import json

            self.webhook_posts.append(json.loads(request.get_data(as_text=True)))
            return ("", 204)

        module_test.httpserver.expect_request(
            "/api/webhooks/test/webhook", method="POST"
        ).respond_with_handler(capture_webhook)

    async def setup_after_prep(self, module_test):
        """Mock scan statistics"""
        # Inject some mock statistics
        if hasattr(module_test.scan, "stats") and hasattr(module_test.scan.stats, "module_events"):
            module_test.scan.stats.module_events = {
                "DNS_NAME": 150,
                "URL": 75,
                "VULNERABILITY": 5,
                "FINDING": 20,
                "TECHNOLOGY": 12,
            }

    def check(self, module_test, events):
        """Verify statistics are included in summary"""
        assert len(self.webhook_posts) > 0, "No webhook POST requests"

        scan_summary = None
        for post in self.webhook_posts:
            if "embeds" in post:
                for embed in post["embeds"]:
                    if "Scan Complete" in embed.get("title", ""):
                        scan_summary = embed
                        break

        assert scan_summary is not None, "Scan summary not found"

        # Check for Statistics field
        fields = scan_summary.get("fields", [])
        stats_field = next((f for f in fields if "Statistics" in f.get("name", "")), None)

        assert stats_field is not None, "Statistics field not found in embed"

        # Verify statistics content
        stats_value = stats_field["value"]
        assert "Events" in stats_value, "Events count not in statistics"
        assert "Vulnerabilities" in stats_value, "Vulnerabilities count not in statistics"
        assert "Findings" in stats_value, "Findings count not in statistics"


class TestDiscord_ScanSummary_ManyMethodologyFiles(ModuleTestBase):
    """Test handling of many methodology files (should limit to 10)"""

    targets = ["example.com"]
    modules_overrides = ["httpx"]
    config_overrides = {
        "modules": {
            "discord": {
                "webhook_url": "https://discord.com/api/webhooks/test/webhook",
                "include_scan_summary": True,
                "include_drive_links": True,
            }
        }
    }

    async def setup_before_prep(self, module_test):
        """Setup mock HTTP responses"""
        self.webhook_posts = []

        def capture_webhook(request):
            import json

            self.webhook_posts.append(json.loads(request.get_data(as_text=True)))
            return ("", 204)

        module_test.httpserver.expect_request(
            "/api/webhooks/test/webhook", method="POST"
        ).respond_with_handler(capture_webhook)

    async def setup_after_prep(self, module_test):
        """Inject 15 methodology files"""
        # Create 15 methodology links
        methodology_links = [
            {"name": f"example.com_Tech{i}", "link": f"https://drive.google.com/file/d/tech{i}/view"}
            for i in range(1, 16)
        ]

        module_test.scan.context["google_drive_methodology_links"] = methodology_links

    def check(self, module_test, events):
        """Verify only first 10 files shown with ellipsis"""
        assert len(self.webhook_posts) > 0, "No webhook POST requests"

        scan_summary = None
        for post in self.webhook_posts:
            if "embeds" in post:
                for embed in post["embeds"]:
                    if "Scan Complete" in embed.get("title", ""):
                        scan_summary = embed
                        break

        assert scan_summary is not None, "Scan summary not found"

        # Find methodology field
        fields = scan_summary.get("fields", [])
        methodology_field = next((f for f in fields if "Methodology" in f.get("name", "")), None)

        assert methodology_field is not None, "Methodology field not found"

        methodology_value = methodology_field["value"]

        # Should show first 10 files
        assert "Tech1" in methodology_value, "First file not shown"
        assert "Tech10" in methodology_value, "10th file not shown"

        # Should NOT show 11th-15th files
        assert "Tech11" not in methodology_value, "11th file should not be shown"
        assert "Tech15" not in methodology_value, "15th file should not be shown"

        # Should have "and X more files" message
        assert "more files" in methodology_value.lower(), "Missing 'more files' indicator"
