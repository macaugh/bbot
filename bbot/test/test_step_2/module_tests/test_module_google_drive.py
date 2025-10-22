import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from .base import ModuleTestBase


class TestGoogleDrive(ModuleTestBase):
    """Test Google Drive output module"""

    targets = ["example.com"]
    modules_overrides = ["httpx"]
    config_overrides = {
        "modules": {
            "google_drive": {
                "credentials_file": "/tmp/test_credentials.json",
                "upload_csv": True,
                "upload_methodology": True,
            }
        }
    }

    async def setup_before_prep(self, module_test):
        """Setup mock Google Drive credentials and services"""
        # Create mock credentials file
        import json
        import tempfile

        self.temp_creds = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        creds_data = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        json.dump(creds_data, self.temp_creds)
        self.temp_creds.close()

        # Store credentials path for later use
        self.credentials_path = self.temp_creds.name

    async def setup_after_prep(self, module_test):
        """Mock Google Drive API calls"""
        # Create mock Google Drive service
        mock_drive_service = MagicMock()

        # Mock about().get() for authentication test
        mock_about = MagicMock()
        mock_about.get.return_value.execute.return_value = {"user": {"emailAddress": "test@example.com"}}
        mock_drive_service.about.return_value = mock_about

        # Mock files().list() for folder search
        mock_files_list = MagicMock()
        mock_files_list.execute.return_value = {"files": []}
        mock_drive_service.files.return_value.list.return_value = mock_files_list

        # Mock files().create() for file/folder creation
        mock_files_create = MagicMock()
        mock_files_create.execute.return_value = {
            "id": "test-file-id-123",
            "webViewLink": "https://drive.google.com/file/d/test-file-id-123/view",
            "webContentLink": "https://drive.google.com/uc?id=test-file-id-123",
        }
        mock_drive_service.files.return_value.create.return_value = mock_files_create

        # Mock permissions().create() for sharing
        mock_permissions = MagicMock()
        mock_permissions.create.return_value.execute.return_value = {"id": "permission-id"}
        mock_drive_service.permissions.return_value = mock_permissions

        # Patch Google API imports
        mock_credentials = MagicMock()
        mock_credentials.from_service_account_file.return_value = mock_credentials

        mock_build = MagicMock(return_value=mock_drive_service)

        module_test.monkeypatch.setattr(
            "bbot.modules.output.google_drive.service_account.Credentials", mock_credentials
        )
        module_test.monkeypatch.setattr("bbot.modules.output.google_drive.build", mock_build)

        # Create mock CSV file in scan output
        csv_file = module_test.scan.home / "output.csv"
        csv_file.write_text("Event type,Event data,IP Address\nDNS_NAME,example.com,1.2.3.4\n")

        # Create mock methodology directory with files
        methodology_dir = module_test.scan.home / "methodology"
        methodology_dir.mkdir(exist_ok=True)
        (methodology_dir / "example.com_WordPress.md").write_text("# WordPress Test")
        (methodology_dir / "example.com_Apache.md").write_text("# Apache Test")

    def check(self, module_test, events):
        """Verify Google Drive module functionality"""
        # Check that CSV link was stored in context
        assert (
            "google_drive_csv_link" in module_test.scan.context
        ), "CSV link not stored in scan context"

        csv_link = module_test.scan.context.get("google_drive_csv_link")
        assert csv_link is not None, "CSV link is None"
        assert "drive.google.com" in csv_link, "CSV link doesn't point to Google Drive"

        # Check that methodology links were stored
        assert (
            "google_drive_methodology_links" in module_test.scan.context
        ), "Methodology links not stored in scan context"

        methodology_links = module_test.scan.context.get("google_drive_methodology_links", [])
        assert len(methodology_links) > 0, "No methodology files uploaded"

        # Check folder link
        assert (
            "google_drive_folder_link" in module_test.scan.context
        ), "Folder link not stored in scan context"

        folder_link = module_test.scan.context.get("google_drive_folder_link")
        assert folder_link is not None, "Folder link is None"
        assert "drive.google.com/drive/folders" in folder_link, "Folder link incorrect format"


class TestGoogleDrive_NoCredentials(ModuleTestBase):
    """Test Google Drive module gracefully handles missing credentials"""

    targets = ["example.com"]
    modules_overrides = ["httpx"]
    config_overrides = {"modules": {"google_drive": {"credentials_file": ""}}}

    async def setup_after_prep(self, module_test):
        """No additional setup needed"""
        pass

    def check(self, module_test, events):
        """Verify module handles missing credentials gracefully"""
        # Module should not be running if credentials are missing
        google_drive_module = module_test.scan.modules.get("google_drive")

        # Check that the module properly reported setup failure
        assert google_drive_module is not None, "Google Drive module not loaded"

        # Context should not have Drive links if module didn't run
        assert (
            "google_drive_csv_link" not in module_test.scan.context
        ), "CSV link should not exist without credentials"


class TestGoogleDrive_UploadCSVOnly(ModuleTestBase):
    """Test uploading only CSV without methodology files"""

    targets = ["example.com"]
    modules_overrides = ["httpx"]
    config_overrides = {
        "modules": {
            "google_drive": {
                "credentials_file": "/tmp/test_credentials.json",
                "upload_csv": True,
                "upload_methodology": False,
            }
        }
    }

    async def setup_before_prep(self, module_test):
        """Setup mock credentials"""
        import json
        import tempfile

        self.temp_creds = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        creds_data = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        json.dump(creds_data, self.temp_creds)
        self.temp_creds.close()
        module_test.scan.config.modules.google_drive.credentials_file = self.temp_creds.name

    async def setup_after_prep(self, module_test):
        """Mock Google Drive API"""
        mock_drive_service = MagicMock()
        mock_about = MagicMock()
        mock_about.get.return_value.execute.return_value = {"user": {"emailAddress": "test@example.com"}}
        mock_drive_service.about.return_value = mock_about

        mock_files_list = MagicMock()
        mock_files_list.execute.return_value = {"files": []}
        mock_drive_service.files.return_value.list.return_value = mock_files_list

        mock_files_create = MagicMock()
        mock_files_create.execute.return_value = {
            "id": "csv-file-id",
            "webViewLink": "https://drive.google.com/file/d/csv-file-id/view",
        }
        mock_drive_service.files.return_value.create.return_value = mock_files_create

        mock_credentials = MagicMock()
        mock_credentials.from_service_account_file.return_value = mock_credentials
        mock_build = MagicMock(return_value=mock_drive_service)

        module_test.monkeypatch.setattr(
            "bbot.modules.output.google_drive.service_account.Credentials", mock_credentials
        )
        module_test.monkeypatch.setattr("bbot.modules.output.google_drive.build", mock_build)

        # Create CSV but no methodology
        csv_file = module_test.scan.home / "output.csv"
        csv_file.write_text("Event type,Event data\nDNS_NAME,example.com\n")

    def check(self, module_test, events):
        """Verify only CSV was uploaded"""
        assert "google_drive_csv_link" in module_test.scan.context, "CSV link not stored"

        # Methodology links should not exist
        methodology_links = module_test.scan.context.get("google_drive_methodology_links", [])
        assert len(methodology_links) == 0, "Methodology files should not be uploaded when disabled"


class TestGoogleDrive_ShareWith(ModuleTestBase):
    """Test file sharing with team members"""

    targets = ["example.com"]
    modules_overrides = ["httpx"]
    config_overrides = {
        "modules": {
            "google_drive": {
                "credentials_file": "/tmp/test_credentials.json",
                "share_with": ["alice@example.com", "bob@example.com"],
                "upload_csv": True,
            }
        }
    }

    async def setup_before_prep(self, module_test):
        """Setup mock credentials"""
        import json
        import tempfile

        self.temp_creds = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        creds_data = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
        }
        json.dump(creds_data, self.temp_creds)
        self.temp_creds.close()
        module_test.scan.config.modules.google_drive.credentials_file = self.temp_creds.name

        # Track permission creation calls
        self.permission_calls = []

    async def setup_after_prep(self, module_test):
        """Mock Google Drive API with permission tracking"""
        mock_drive_service = MagicMock()
        mock_about = MagicMock()
        mock_about.get.return_value.execute.return_value = {"user": {"emailAddress": "test@example.com"}}
        mock_drive_service.about.return_value = mock_about

        mock_files_list = MagicMock()
        mock_files_list.execute.return_value = {"files": []}
        mock_drive_service.files.return_value.list.return_value = mock_files_list

        mock_files_create = MagicMock()
        mock_files_create.execute.return_value = {
            "id": "test-folder-id",
            "webViewLink": "https://drive.google.com/file/d/test-folder-id/view",
        }
        mock_drive_service.files.return_value.create.return_value = mock_files_create

        # Track permission creation
        def track_permission_create(**kwargs):
            self.permission_calls.append(kwargs)
            mock_result = MagicMock()
            mock_result.execute.return_value = {"id": "permission-id"}
            return mock_result

        mock_permissions = MagicMock()
        mock_permissions.create.side_effect = track_permission_create
        mock_drive_service.permissions.return_value = mock_permissions

        mock_credentials = MagicMock()
        mock_credentials.from_service_account_file.return_value = mock_credentials
        mock_build = MagicMock(return_value=mock_drive_service)

        module_test.monkeypatch.setattr(
            "bbot.modules.output.google_drive.service_account.Credentials", mock_credentials
        )
        module_test.monkeypatch.setattr("bbot.modules.output.google_drive.build", mock_build)

        csv_file = module_test.scan.home / "output.csv"
        csv_file.write_text("Event type,Event data\nDNS_NAME,example.com\n")

    def check(self, module_test, events):
        """Verify files were shared with specified users"""
        # Check that permissions were created
        assert len(self.permission_calls) > 0, "No permission creation calls made"

        # Verify email addresses in permission calls
        permission_bodies = [call.get("body", {}) for call in self.permission_calls]
        shared_emails = [body.get("emailAddress") for body in permission_bodies if "emailAddress" in body]

        assert "alice@example.com" in shared_emails, "alice@example.com not in shared users"
        assert "bob@example.com" in shared_emails, "bob@example.com not in shared users"
