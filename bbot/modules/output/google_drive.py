"""
Google Drive output module for BBOT
Uploads scan results (CSV and methodology files) to Google Drive
"""

import asyncio
from pathlib import Path
from contextlib import suppress

from bbot.modules.output.base import BaseOutputModule


class GoogleDrive(BaseOutputModule):
    watched_events = ["FINISHED"]
    meta = {
        "description": "Upload scan results to Google Drive",
        "created_date": "2025-10-14",
        "author": "@mcaughman",
    }
    options = {
        "credentials_file": "",
        "folder_id": "",
        "share_with": [],
        "make_public": False,
        "upload_csv": True,
        "upload_methodology": True,
    }
    options_desc = {
        "credentials_file": "Path to Google OAuth2 credentials JSON (service account or OAuth)",
        "folder_id": "Google Drive folder ID to upload files to (optional, uses root if not specified)",
        "share_with": "List of email addresses to share files with",
        "make_public": "Generate public shareable links",
        "upload_csv": "Upload CSV results file",
        "upload_methodology": "Upload methodology markdown files",
    }

    deps_pip = ["google-api-python-client~=2.100.0", "google-auth-httplib2~=0.1.1", "google-auth~=2.23.0"]

    async def setup(self):
        """Initialize Google Drive API client and validate credentials"""
        self.credentials_file = self.config.get("credentials_file", "")
        self.folder_id = self.config.get("folder_id", "")
        self.share_with = self.config.get("share_with", [])
        self.make_public = self.config.get("make_public", False)
        self.upload_csv = self.config.get("upload_csv", True)
        self.upload_methodology = self.config.get("upload_methodology", True)

        # Ensure share_with is a list
        if isinstance(self.share_with, str):
            self.share_with = [email.strip() for email in self.share_with.split(",")]

        # Validate credentials file exists
        if not self.credentials_file:
            self.warning("No credentials_file specified. Google Drive upload will be disabled.")
            return False

        credentials_path = Path(self.credentials_file).expanduser()
        if not credentials_path.exists():
            self.warning(f"Credentials file not found: {credentials_path}")
            return False

        # Initialize Google API client
        try:
            await self._init_google_client(credentials_path)
        except Exception as e:
            self.warning(f"Failed to initialize Google Drive client: {e}")
            return False

        self.info(f"Google Drive integration enabled. Upload CSV: {self.upload_csv}, Methodology: {self.upload_methodology}")
        return True

    async def _init_google_client(self, credentials_path):
        """Initialize Google Drive API client"""
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        import json

        # Load credentials file to determine type
        with open(credentials_path) as f:
            creds_data = json.load(f)

        # Check if service account or OAuth credentials
        if creds_data.get("type") == "service_account":
            self.debug("Using service account authentication")
            self.credentials = service_account.Credentials.from_service_account_file(
                str(credentials_path),
                scopes=["https://www.googleapis.com/auth/drive.file"]
            )
        else:
            self.debug("Using OAuth2 authentication")
            # For OAuth, the file should be a token.json with refresh_token
            self.credentials = Credentials.from_authorized_user_file(
                str(credentials_path),
                scopes=["https://www.googleapis.com/auth/drive.file"]
            )

            # Refresh if expired
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())

        # Build Drive API client
        self.drive_service = build("drive", "v3", credentials=self.credentials)

        # Test connection
        self.drive_service.about().get(fields="user").execute()
        self.debug("Successfully authenticated with Google Drive")

    async def handle_event(self, event):
        """On FINISHED event, upload files to Google Drive"""
        if event.type != "FINISHED":
            return

        uploaded_files = {}

        # Create or get scan folder
        scan_folder_id = await self._get_or_create_scan_folder()

        # Upload CSV file
        if self.upload_csv:
            csv_file = self.scan.home / "output.csv"
            if csv_file.exists():
                try:
                    csv_link = await self._upload_file(csv_file, scan_folder_id, "text/csv")
                    uploaded_files["csv"] = csv_link
                    self.info(f"Uploaded CSV to Google Drive: {csv_link}")
                except Exception as e:
                    self.warning(f"Failed to upload CSV: {e}")

        # Upload methodology files
        if self.upload_methodology:
            methodology_dir = self.scan.home / "methodology"
            if methodology_dir.exists() and methodology_dir.is_dir():
                methodology_links = []
                for md_file in methodology_dir.glob("*.md"):
                    try:
                        link = await self._upload_file(md_file, scan_folder_id, "text/markdown")
                        methodology_links.append({"name": md_file.stem, "link": link})
                        self.debug(f"Uploaded methodology file: {md_file.name}")
                    except Exception as e:
                        self.warning(f"Failed to upload {md_file.name}: {e}")

                if methodology_links:
                    uploaded_files["methodology"] = methodology_links
                    self.info(f"Uploaded {len(methodology_links)} methodology files to Google Drive")

        # Share uploaded files with specified users
        if self.share_with and uploaded_files:
            await self._share_scan_folder(scan_folder_id)

        # Store links in scan context for other modules (like Discord)
        if "csv" in uploaded_files:
            self.scan.context["google_drive_csv_link"] = uploaded_files["csv"]
        if "methodology" in uploaded_files:
            self.scan.context["google_drive_methodology_links"] = uploaded_files["methodology"]

        # Store folder link
        if scan_folder_id:
            folder_link = f"https://drive.google.com/drive/folders/{scan_folder_id}"
            self.scan.context["google_drive_folder_link"] = folder_link
            self.info(f"All scan files available at: {folder_link}")

    async def _get_or_create_scan_folder(self):
        """Get or create a folder for this scan in Google Drive"""
        try:
            # Create parent "BBOT Scans" folder if it doesn't exist
            parent_folder_id = self.folder_id or "root"

            if not self.folder_id:
                # Create/get "BBOT Scans" folder
                parent_folder_id = await self._get_or_create_folder("BBOT Scans", "root")

            # Create scan-specific folder
            scan_folder_name = f"{self.scan.name}_{self.scan.id[:8]}"
            scan_folder_id = await self._get_or_create_folder(scan_folder_name, parent_folder_id)

            return scan_folder_id
        except Exception as e:
            self.warning(f"Failed to create scan folder: {e}")
            return self.folder_id or None

    async def _get_or_create_folder(self, folder_name, parent_id="root"):
        """Get existing folder or create new one"""
        def _run_in_thread():
            # Search for existing folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id != "root":
                query += f" and '{parent_id}' in parents"

            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name)",
                spaces="drive"
            ).execute()

            files = results.get("files", [])
            if files:
                return files[0]["id"]

            # Create new folder
            folder_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id] if parent_id != "root" else []
            }

            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields="id"
            ).execute()

            return folder["id"]

        # Run Google API calls in thread pool to avoid blocking
        return await asyncio.to_thread(_run_in_thread)

    async def _upload_file(self, file_path, folder_id=None, mime_type="text/plain"):
        """Upload a file to Google Drive and return shareable link"""
        from googleapiclient.http import MediaFileUpload

        def _run_in_thread():
            file_metadata = {
                "name": file_path.name,
                "parents": [folder_id] if folder_id else []
            }

            media = MediaFileUpload(
                str(file_path),
                mimetype=mime_type,
                resumable=True
            )

            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink, webContentLink"
            ).execute()

            file_id = file["id"]

            # Make public if requested
            if self.make_public:
                permission = {
                    "type": "anyone",
                    "role": "reader"
                }
                self.drive_service.permissions().create(
                    fileId=file_id,
                    body=permission
                ).execute()

            # Return web view link (opens in Drive UI)
            return file.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view")

        return await asyncio.to_thread(_run_in_thread)

    async def _share_scan_folder(self, folder_id):
        """Share the scan folder with specified users"""
        if not self.share_with or not folder_id:
            return

        def _run_in_thread():
            for email in self.share_with:
                try:
                    permission = {
                        "type": "user",
                        "role": "reader",
                        "emailAddress": email.strip()
                    }
                    self.drive_service.permissions().create(
                        fileId=folder_id,
                        body=permission,
                        sendNotificationEmail=True
                    ).execute()
                    self.debug(f"Shared scan folder with {email}")
                except Exception as e:
                    self.warning(f"Failed to share with {email}: {e}")

        await asyncio.to_thread(_run_in_thread)

    async def cleanup(self):
        """Cleanup resources"""
        with suppress(Exception):
            if hasattr(self, "drive_service"):
                del self.drive_service
            if hasattr(self, "credentials"):
                del self.credentials

    async def report(self):
        """Report upload status at scan completion"""
        csv_link = self.scan.context.get("google_drive_csv_link")
        methodology_links = self.scan.context.get("google_drive_methodology_links", [])
        folder_link = self.scan.context.get("google_drive_folder_link")

        if folder_link:
            self.info(f"Google Drive folder: {folder_link}")
        if csv_link:
            self.info(f"CSV results: {csv_link}")
        if methodology_links:
            self.info(f"Methodology files: {len(methodology_links)} files uploaded")
