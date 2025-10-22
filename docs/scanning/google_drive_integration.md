# Google Drive Integration

BBOT can automatically upload scan results to Google Drive for team collaboration and centralized storage.

## Features

- **Automatic CSV Upload**: Upload scan results CSV to Google Drive
- **Methodology Files**: Upload generated reconnaissance checklists
- **Team Sharing**: Automatically share files with team members
- **Organized Folders**: Results organized by scan name and date
- **Discord Integration**: Post Google Drive links to Discord channels

## Setup

### Option 1: Service Account (Recommended for Teams)

Service accounts are ideal for automated workflows and team environments.

#### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the **Google Drive API**:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Google Drive API"
   - Click "Enable"

#### 2. Create Service Account

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Fill in details:
   - **Name**: `bbot-scanner`
   - **Description**: `BBOT scan result uploader`
4. Click "Create and Continue"
5. Grant role: **Editor** (or create custom role with Drive permissions)
6. Click "Done"

#### 3. Create Service Account Key

1. Click on the service account you just created
2. Go to the "Keys" tab
3. Click "Add Key" → "Create new key"
4. Select **JSON** format
5. Click "Create" - the key file will download
6. Save this file securely (e.g., `~/.bbot/google-service-account.json`)

⚠️ **Security Note**: Never commit this file to git! Add to `.gitignore`.

#### 4. Share Drive Folder with Service Account

1. Create a folder in Google Drive for BBOT scans (e.g., "BBOT Scans")
2. Right-click the folder → "Share"
3. Add the service account email (found in the JSON file as `client_email`)
   - Example: `bbot-scanner@project-id.iam.gserviceaccount.com`
4. Give "Editor" permissions
5. Click "Share"

### Option 2: OAuth2 (For Personal Use)

OAuth2 is simpler for individual users but requires initial browser authentication.

#### 1. Create OAuth2 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Google Drive API (see above)
3. Go to "APIs & Services" → "Credentials"
4. Click "Create Credentials" → "OAuth client ID"
5. If prompted, configure OAuth consent screen:
   - User Type: **External**
   - App name: `BBOT Scanner`
   - Add your email as test user
6. Application type: **Desktop app**
7. Name: `BBOT`
8. Click "Create"
9. Download the JSON file (client_secret.json)

#### 2. Authenticate with Google

```bash
# Install google-auth-oauthlib if not already installed
pip install google-auth-oauthlib

# Run authentication helper (you'll need to create this script or use Google's quickstart)
python3 -c "
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os

SCOPES = ['https://www.googleapis.com/auth/drive.file']

flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret.json', SCOPES)
creds = flow.run_local_server(port=0)

# Save the credentials for future use
with open('token.pickle', 'wb') as token:
    pickle.dump(creds, token)

print('Authentication successful! Token saved to token.pickle')
"
```

This will open a browser window to authenticate. After authentication, a `token.pickle` file will be created.

## Configuration

### Basic Configuration

Add to `~/.config/bbot/bbot.yml`:

```yaml
modules:
  google_drive:
    credentials_file: ~/.bbot/google-service-account.json
    upload_csv: true
    upload_methodology: true
```

### Advanced Configuration

```yaml
modules:
  google_drive:
    # Path to credentials JSON file
    credentials_file: ~/.bbot/google-service-account.json

    # Specific folder ID to upload to (optional)
    # If not specified, creates "BBOT Scans" folder in Drive root
    folder_id: "1ABC_xyz123..."

    # Share with team members automatically
    share_with:
      - alice@example.com
      - bob@example.com
      - security-team@example.com

    # Generate public shareable links (default: false)
    make_public: false

    # Upload CSV results (default: true)
    upload_csv: true

    # Upload methodology markdown files (default: true)
    upload_methodology: true
```

### Getting Folder ID

To upload to a specific folder:

1. Navigate to the folder in Google Drive
2. Look at the URL: `https://drive.google.com/drive/folders/1ABC_xyz123...`
3. The folder ID is the part after `/folders/`: `1ABC_xyz123...`

## Usage Examples

### Basic Usage

```bash
# Scan with Google Drive upload
bbot -t example.com -p subdomain-enum -om google_drive

# With methodology generation
bbot -t example.com -p subdomain-enum \
  -om google_drive,recon_methodology \
  -c modules.recon_methodology.template_repo_url=https://github.com/user/bbot-recon-templates.git
```

### Team Collaboration

```bash
# Share results with team automatically
bbot -t example.com -p subdomain-enum -om google_drive \
  -c modules.google_drive.share_with=alice@company.com,bob@company.com
```

### With Discord Notifications

```bash
# Upload to Drive and notify team on Discord
bbot -t example.com -p subdomain-enum \
  -om google_drive,recon_methodology,discord \
  -c modules.discord.webhook_url=https://discord.com/api/webhooks/... \
  -c modules.discord.include_drive_links=true
```

### Multiple Targets

```bash
# Scan multiple targets, all results in one Drive folder
bbot -t example.com test.com demo.com \
  -p subdomain-enum \
  -om google_drive,recon_methodology
```

### Python API

```python
from bbot.scanner import Scanner

# Configure Google Drive upload
config = {
    "modules": {
        "google_drive": {
            "credentials_file": "/path/to/credentials.json",
            "share_with": ["team@example.com"],
        }
    }
}

# Run scan
scan = Scanner(
    "example.com",
    presets=["subdomain-enum"],
    output_modules=["google_drive"],
    config=config
)

for event in scan.start():
    print(event)

# Get Drive links from scan context
csv_link = scan.context.get("google_drive_csv_link")
folder_link = scan.context.get("google_drive_folder_link")

print(f"Results: {csv_link}")
print(f"Folder: {folder_link}")
```

## Drive Folder Structure

BBOT organizes files in Google Drive:

```
Google Drive
└── BBOT Scans/
    ├── example_com_abc12345/
    │   ├── output.csv
    │   └── methodology/
    │       ├── example.com_WordPress.md
    │       ├── example.com_Apache.md
    │       └── api.example.com_GraphQL.md
    └── demo_com_def67890/
        ├── output.csv
        └── methodology/
            └── demo.com_Nginx.md
```

Each scan creates a folder named: `{target}_{scan_id_first_8_chars}`

## Integration with Other Modules

### Recon Methodology

Methodology files are automatically uploaded to Google Drive:

```yaml
modules:
  google_drive:
    credentials_file: ~/.bbot/creds.json
    upload_methodology: true

  recon_methodology:
    template_repo_url: https://github.com/user/bbot-recon-templates.git
    upload_to_drive: true  # Optional: redundant if google_drive.upload_methodology=true
```

### Discord

Google Drive links are automatically included in Discord notifications:

```yaml
modules:
  google_drive:
    credentials_file: ~/.bbot/creds.json

  discord:
    webhook_url: https://discord.com/api/webhooks/...
    include_scan_summary: true
    include_drive_links: true
```

Discord will post a scan summary with:
- 📁 CSV download link
- 📝 Methodology checklist links
- 📊 Scan statistics

## Troubleshooting

### Authentication Errors

**Error**: `Failed to initialize Google Drive client: Credentials invalid`

**Solution**:
1. Verify JSON file exists and is readable
2. Check JSON format is valid (service account or OAuth)
3. Ensure API is enabled in Google Cloud Console

**Error**: `403 Forbidden`

**Solution**:
1. Check service account has access to target folder
2. Verify folder is shared with service account email
3. Check API quotas in Google Cloud Console

### Upload Failures

**Error**: `Failed to upload CSV: timeout`

**Solution**:
1. Check network connectivity
2. Large files may need increased timeout
3. Check Google Drive storage quota

**Error**: `Folder not found`

**Solution**:
1. Verify `folder_id` is correct
2. Ensure service account has access to folder
3. Try without `folder_id` to use root directory

### Permission Issues

**Error**: `Failed to share with user@example.com`

**Solution**:
1. Check email address is correct
2. Verify organization allows external sharing
3. Service account needs permission to share files

## Security Best Practices

### Credentials Management

✅ **DO**:
- Store credentials in `~/.bbot/` or secure location
- Use environment variables: `GOOGLE_CREDENTIALS_PATH`
- Set restrictive file permissions: `chmod 600 credentials.json`
- Use separate service accounts for dev/prod
- Rotate service account keys regularly

❌ **DON'T**:
- Commit credentials to git repositories
- Share credentials in plain text
- Use personal OAuth tokens for production
- Grant excessive permissions to service accounts

### Access Control

✅ **DO**:
- Use private folders (not public links)
- Share with specific email addresses only
- Use organizational Google Workspace for team access
- Regularly audit shared file permissions
- Set expiration dates on shared links (when possible)

❌ **DON'T**:
- Enable `make_public: true` for sensitive data
- Share folders with "Anyone with link"
- Use personal Google accounts for team scans
- Leave old scan results accessible indefinitely

### Data Handling

⚠️ **Warning**: Scan results may contain sensitive information:
- Exposed credentials in findings
- Vulnerability details
- Internal system information
- Email addresses and usernames

**Recommendations**:
1. Review results before sharing widely
2. Use Google Workspace with DLP (Data Loss Prevention)
3. Enable Google Drive encryption at rest
4. Consider data retention policies
5. Sanitize sensitive data before upload (if necessary)

## API Limits and Quotas

Google Drive API has usage limits:

| Limit Type | Default Quota |
|------------|---------------|
| Queries per 100 seconds per user | 1,000 |
| Queries per day | 1,000,000,000 |
| Upload per user per 100 seconds | 750 MB |

For most BBOT scans, these limits are sufficient. Large enterprises may need to request quota increases.

### Rate Limiting

BBOT automatically handles rate limiting:
- Exponential backoff on 429 errors
- Respects `Retry-After` headers
- 3 retries per operation

## Performance Considerations

### Upload Times

Typical upload times:

| File Size | Time (estimate) |
|-----------|-----------------|
| Small CSV (<1 MB) | 1-2 seconds |
| Medium CSV (1-10 MB) | 2-5 seconds |
| Large CSV (10-50 MB) | 5-15 seconds |
| Methodology files (<100 KB each) | <1 second each |

### Network Usage

- CSV upload: Scan-dependent (typically 1-50 MB)
- Methodology files: ~10-100 KB per file
- Metadata requests: Negligible (<1 KB each)

Total: Typically 1-100 MB per scan, depending on results.

## FAQ

**Q: Can I use a personal Google account?**
A: Yes, using OAuth2 method. However, service accounts are recommended for teams.

**Q: Will this slow down my scans?**
A: No, uploads happen at scan completion and run asynchronously.

**Q: Can I disable uploads temporarily?**
A: Yes, don't include `google_drive` in output modules, or set `credentials_file: ""`.

**Q: How long do files stay in Drive?**
A: Forever, until you delete them. Set up retention policies if needed.

**Q: Can I upload to a shared drive (Google Workspace)?**
A: Yes, use the shared drive folder ID in `folder_id` config.

**Q: What happens if upload fails?**
A: BBOT logs a warning and continues. Local files are still saved in `~/.bbot/scans/`.

**Q: Can I use multiple Google accounts?**
A: Yes, use different credentials files and specify via CLI: `-c modules.google_drive.credentials_file=path`

## Related Documentation

- [Recon Methodology Module](./recon_methodology.md)
- [Discord Integration](./discord.md)
- [Output Modules Overview](./output.md)
- [Configuration Guide](./configuration.md)

## Support

- **Issues**: [GitHub Issues](https://github.com/blacklanternsecurity/bbot/issues)
- **Discord**: [BBOT Community](https://discord.com/invite/PZqkgxu5SA)
- **Documentation**: [BBOT Docs](https://www.blacklanternsecurity.com/bbot/)
