# BBOT Recon Methodology Output System - Technical Specification

## Document Information
- **Version**: 1.0.0
- **Date**: 2025-10-14
- **Status**: Draft
- **Authors**: Matt Caughman

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Component Specifications](#component-specifications)
4. [Configuration](#configuration)
5. [Data Flow](#data-flow)
6. [Template System](#template-system)
7. [Google Drive Integration](#google-drive-integration)
8. [Discord Integration](#discord-integration)
9. [Security Considerations](#security-considerations)
10. [Implementation Plan](#implementation-plan)
11. [Testing Strategy](#testing-strategy)

---

## Overview

### Purpose
This system extends BBOT's output capabilities to provide:
1. **Automated CSV export to Google Drive** for team collaboration and data persistence
2. **Technology-based methodology checklists** generated as markdown files
3. **Discord notifications** with links to methodology files and scan results
4. **Version-controlled templates** for standardized reconnaissance workflows

### Goals
- Reduce manual checklist creation for penetration testers
- Provide standardized methodology based on detected technologies
- Enable team collaboration through Google Drive integration
- Maintain version control for reconnaissance templates
- Integrate seamlessly with existing BBOT workflows

### Non-Goals
- Real-time streaming of results to Google Drive (batch upload at scan completion)
- Interactive checklist editing within BBOT
- Support for cloud storage providers other than Google Drive (future enhancement)

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         BBOT Scanner                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Modules    │→ │Event Engine  │→ │Output Modules│          │
│  │ (wappalyzer, │  │              │  │              │          │
│  │  httpx, etc) │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                        ↓         ↓               │
└────────────────────────────────────────┼─────────┼───────────────┘
                                         │         │
                    ┌────────────────────┴──┐   ┌──┴──────────────────────┐
                    │  google_drive.py      │   │ recon_methodology.py    │
                    │  (CSV Upload)         │   │ (Markdown Generator)    │
                    └───────────┬───────────┘   └──────────┬──────────────┘
                                │                           │
                                │                           │
                         ┌──────▼───────────────────────────▼──────┐
                         │      Google Drive API v3                │
                         │  ┌──────────────┐  ┌───────────────┐   │
                         │  │  CSV Files   │  │ Markdown Files│   │
                         │  │  (Results)   │  │ (Methodology) │   │
                         │  └──────────────┘  └───────────────┘   │
                         └──────────────────────────────────────────┘
                                         │
                                         │ (Share links)
                                         ↓
                         ┌────────────────────────────────┐
                         │      Discord Webhook           │
                         │  - CSV download link           │
                         │  - Methodology file links      │
                         │  - Scan summary                │
                         └────────────────────────────────┘

         ┌────────────────────────────────────────────────────┐
         │  External Template Repository (Git)                │
         │  bbot-recon-templates/                             │
         │    ├── templates/                                  │
         │    │   ├── web/                                    │
         │    │   ├── api/                                    │
         │    │   └── database/                               │
         │    └── config.yml                                  │
         └────────────────────────────────────────────────────┘
                           ↑
                           │ (git clone/pull)
                           │
                   ┌───────┴────────┐
                   │ Template Loader│
                   │ (in methodology│
                   │     module)    │
                   └────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Output |
|-----------|---------------|---------|
| `google_drive.py` | Upload CSV files to Google Drive | Shareable Drive link |
| `recon_methodology.py` | Generate methodology checklists | Markdown files per endpoint |
| `discord.py` (enhanced) | Post scan results with links | Discord messages |
| Template Repository | Store version-controlled templates | Markdown templates |
| Template Loader | Fetch and cache templates | Template objects |

---

## Component Specifications

### 1. Google Drive Output Module (`bbot/modules/output/google_drive.py`)

#### Class Definition
```python
class GoogleDrive(BaseOutputModule):
    watched_events = ["FINISHED"]
    flags = ["passive", "safe"]
    meta = {
        "description": "Upload scan results CSV to Google Drive",
        "created_date": "2025-10-14",
        "author": "@mcaughman",
    }
    options = {
        "credentials_file": "",
        "folder_id": "",
        "share_with": [],
        "make_public": False,
        "include_csv": True,
    }
```

#### Configuration Options
- `credentials_file`: Path to Google OAuth2 credentials JSON (service account or OAuth)
- `folder_id`: Google Drive folder ID to upload files to (optional, uses root if not specified)
- `share_with`: List of email addresses to share files with
- `make_public`: Boolean to generate public shareable links
- `include_csv`: Boolean to include CSV export (default: True)

#### Dependencies
- `google-api-python-client`: Google Drive API client
- `google-auth-httplib2`: Authentication
- `google-auth-oauthlib`: OAuth flow

#### Key Methods
```python
async def setup(self):
    """Initialize Google Drive API client and validate credentials"""

async def handle_event(self, event):
    """On FINISHED event, upload CSV file to Google Drive"""

async def upload_file(self, file_path, mime_type):
    """Upload a file to Google Drive and return shareable link"""

async def share_file(self, file_id, emails):
    """Share a file with specific users"""

async def get_or_create_folder(self, folder_name):
    """Get or create a folder in Google Drive"""
```

#### Error Handling
- Graceful degradation if credentials are invalid (warning, no upload)
- Retry logic for network failures (3 retries with exponential backoff)
- Detailed error messages for authentication issues

---

### 2. Recon Methodology Module (`bbot/modules/output/recon_methodology.py`)

#### Class Definition
```python
class ReconMethodology(BaseOutputModule):
    watched_events = ["*"]
    flags = ["passive", "safe"]
    meta = {
        "description": "Generate technology-based methodology checklists",
        "created_date": "2025-10-14",
        "author": "@mcaughman",
    }
    options = {
        "template_repo_url": "https://github.com/yourusername/bbot-recon-templates.git",
        "template_repo_branch": "main",
        "template_cache_dir": "",
        "output_dir": "",
        "upload_to_drive": False,
        "group_by": "host",  # or "technology"
        "include_technologies": [],
        "exclude_technologies": [],
    }
```

#### Configuration Options
- `template_repo_url`: Git URL for template repository
- `template_repo_branch`: Branch to use (default: main)
- `template_cache_dir`: Local directory to cache templates (default: ~/.bbot/templates)
- `output_dir`: Directory for generated markdown files (default: scan output dir)
- `upload_to_drive`: Boolean to upload markdown files to Google Drive
- `group_by`: Group checklists by "host" or "technology"
- `include_technologies`: Whitelist of technologies to generate checklists for
- `exclude_technologies`: Blacklist of technologies to skip

#### Key Methods
```python
async def setup(self):
    """Clone/update template repository and initialize storage"""

async def handle_event(self, event):
    """Collect events for later aggregation"""

async def report(self):
    """Generate all markdown files after scan completion"""

async def aggregate_results(self):
    """Group events by host/technology"""

async def generate_checklist(self, host, technologies, events):
    """Generate a single markdown checklist file"""

async def load_template(self, technology):
    """Load and parse template for a technology"""

async def substitute_variables(self, template, context):
    """Replace template variables with scan data"""
```

#### Data Aggregation
The module collects events throughout the scan and processes them at completion:

1. **Event Collection Phase** (during scan):
   - Store `URL`, `TECHNOLOGY`, `VULNERABILITY`, `FINDING` events
   - Map events to their parent hosts
   - Track technology detections per host

2. **Aggregation Phase** (on FINISHED event):
   - Group events by host or technology (based on config)
   - Identify applicable templates for each technology
   - Build context objects with scan data

3. **Generation Phase**:
   - Load templates from cache
   - Substitute variables with scan data
   - Write markdown files
   - Upload to Google Drive (if enabled)

#### Template Variable System
Templates support Jinja2-style variable substitution:

```markdown
# {{ host }} - {{ technology }} Reconnaissance Checklist

**Scan Date**: {{ scan_date }}
**Scanner**: BBOT {{ bbot_version }}

## Discovered Information
- **URL**: {{ url }}
- **IP Address**: {{ ip_address }}
- **Open Ports**: {{ ports }}

## Methodology Checklist
- [ ] Enumerate subdomains
- [ ] Check for {{ technology }}-specific vulnerabilities
- [ ] Test authentication mechanisms
...
```

Available variables:
- `host`: Target hostname
- `technology`: Detected technology name
- `url`: Full URL
- `ip_address`: Resolved IP address
- `ports`: List of open ports
- `scan_date`: Scan timestamp
- `bbot_version`: BBOT version
- `vulnerabilities`: List of detected vulnerabilities
- `findings`: List of findings
- `headers`: HTTP headers (if available)

---

### 3. Discord Integration Enhancement

#### Modify Existing Discord Module
Extend the existing `bbot/modules/output/discord.py` to include:

1. **New configuration options**:
```python
options = {
    "webhook_url": "",
    "event_types": ["VULNERABILITY", "FINDING"],
    "min_severity": "LOW",
    "retries": 10,
    "include_scan_summary": True,  # NEW
    "include_drive_links": True,   # NEW
}
```

2. **Enhanced message formatting**:
```python
async def format_scan_summary(self, scan_stats):
    """Format scan completion summary with links"""
    message = {
        "embeds": [
            {
                "title": f"Scan Complete: {scan.name}",
                "description": f"Scanned {scan_stats['targets']} targets",
                "fields": [
                    {"name": "Events", "value": scan_stats['total_events']},
                    {"name": "Vulnerabilities", "value": scan_stats['vulnerabilities']},
                    {"name": "CSV Report", "value": f"[Download]({csv_link})"},
                    {"name": "Methodology Files", "value": methodology_links},
                ],
                "color": 0x00ff00,
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
    }
    return message
```

3. **Integration with Google Drive module**:
   - Share Google Drive links between modules via scan context
   - Post summary message on scan completion

---

## Configuration

### BBOT Configuration File (`~/.config/bbot/bbot.yml`)

```yaml
# Google Drive Output Module
modules:
  google_drive:
    enabled: true
    credentials_file: /path/to/google-credentials.json
    folder_id: 1ABCxyz123...  # Optional: specific folder ID
    share_with:
      - team@example.com
      - pentester@example.com
    make_public: false
    include_csv: true

  # Recon Methodology Module
  recon_methodology:
    enabled: true
    template_repo_url: https://github.com/yourusername/bbot-recon-templates.git
    template_repo_branch: main
    template_cache_dir: ~/.bbot/templates
    output_dir: ""  # Uses scan output directory if not specified
    upload_to_drive: true
    group_by: host
    include_technologies: []  # Empty = all technologies
    exclude_technologies:
      - "Generic"  # Skip generic/unknown technologies

  # Discord Integration (Enhanced)
  discord:
    enabled: true
    webhook_url: https://discord.com/api/webhooks/...
    event_types:
      - VULNERABILITY
      - FINDING
    min_severity: MEDIUM
    include_scan_summary: true
    include_drive_links: true
```

### Google Drive Authentication Setup

#### Option 1: Service Account (Recommended for automated workflows)
1. Create a Google Cloud Project
2. Enable Google Drive API
3. Create a service account
4. Download JSON credentials
5. Share target Drive folder with service account email

#### Option 2: OAuth2 (For personal use)
1. Create OAuth2 credentials in Google Cloud Console
2. Run initial authentication flow to generate token
3. Store refresh token for future use

The module will support both methods and auto-detect based on credentials file format.

---

## Data Flow

### Scan Lifecycle Integration

```
1. SCAN START
   ├─> recon_methodology: Initialize event storage
   └─> google_drive: Validate credentials

2. DURING SCAN (Event Processing)
   ├─> Regular modules emit events
   │   └─> recon_methodology: Store relevant events
   └─> discord: Post real-time alerts (if configured)

3. SCAN FINISH (FINISHED event)
   ├─> recon_methodology:
   │   ├─> Aggregate collected events
   │   ├─> Generate markdown files
   │   └─> Upload to Google Drive (if enabled)
   │
   ├─> google_drive:
   │   ├─> Read CSV file from scan output
   │   ├─> Upload to Google Drive
   │   └─> Generate shareable links
   │
   └─> discord:
       ├─> Get links from google_drive context
       ├─> Format scan summary message
       └─> Post to Discord webhook
```

### Event Data Structure for Methodology Generation

```python
# Internal storage structure during scan
{
    "example.com": {
        "urls": [
            {"data": "https://example.com", "event_type": "URL"}
        ],
        "technologies": [
            {"name": "WordPress", "version": "6.2"},
            {"name": "PHP", "version": "8.1"},
            {"name": "Apache", "version": "2.4"}
        ],
        "vulnerabilities": [
            {
                "severity": "MEDIUM",
                "description": "WordPress plugin XYZ vulnerable to XSS",
                "cve": "CVE-2023-12345"
            }
        ],
        "findings": [
            {"description": "Exposed .git directory"}
        ],
        "ports": [80, 443, 8080],
        "ip_addresses": ["192.0.2.1"]
    }
}
```

---

## Template System

### Template Repository Structure

```
bbot-recon-templates/
├── README.md                     # Documentation
├── LICENSE                       # MIT or similar
├── config.yml                    # Template configuration
├── templates/
│   ├── web/
│   │   ├── default.md           # Fallback for unknown web tech
│   │   ├── wordpress.md         # WordPress-specific checklist
│   │   ├── drupal.md
│   │   ├── joomla.md
│   │   ├── nginx.md
│   │   ├── apache.md
│   │   ├── iis.md
│   │   ├── tomcat.md
│   │   └── node.md
│   ├── api/
│   │   ├── rest.md
│   │   ├── graphql.md
│   │   ├── soap.md
│   │   └── grpc.md
│   ├── framework/
│   │   ├── django.md
│   │   ├── flask.md
│   │   ├── rails.md
│   │   ├── laravel.md
│   │   ├── spring.md
│   │   └── express.md
│   ├── database/
│   │   ├── mysql.md
│   │   ├── postgresql.md
│   │   ├── mongodb.md
│   │   ├── redis.md
│   │   └── elasticsearch.md
│   ├── cloud/
│   │   ├── aws-s3.md
│   │   ├── azure-blob.md
│   │   ├── gcp-storage.md
│   │   └── cloudflare.md
│   └── misc/
│       ├── docker.md
│       ├── kubernetes.md
│       ├── jenkins.md
│       └── gitlab.md
└── .git/
```

### Template Configuration (`config.yml`)

```yaml
# Template metadata and mapping
templates:
  # Technology name patterns to template files
  mapping:
    # Web Servers
    - pattern: "(?i)nginx"
      template: "web/nginx.md"
      category: "web"
    - pattern: "(?i)apache"
      template: "web/apache.md"
      category: "web"
    - pattern: "(?i)wordpress"
      template: "web/wordpress.md"
      category: "cms"

    # Frameworks
    - pattern: "(?i)django"
      template: "framework/django.md"
      category: "framework"
    - pattern: "(?i)flask"
      template: "framework/flask.md"
      category: "framework"

    # Databases
    - pattern: "(?i)mysql|mariadb"
      template: "database/mysql.md"
      category: "database"
    - pattern: "(?i)postgres"
      template: "database/postgresql.md"
      category: "database"

  # Fallback templates by category
  fallbacks:
    web: "web/default.md"
    api: "api/rest.md"
    database: "database/default.md"
    framework: "web/default.md"

# Variable definitions
variables:
  # Required variables (must be provided by BBOT)
  required:
    - host
    - technology
    - scan_date

  # Optional variables (may be empty)
  optional:
    - url
    - ip_address
    - ports
    - vulnerabilities
    - findings
    - headers
    - version

# Template validation rules
validation:
  max_template_size: 102400  # 100KB max per template
  allowed_extensions: [".md", ".markdown"]
```

### Example Template: WordPress (`templates/web/wordpress.md`)

```markdown
# WordPress Reconnaissance: {{ host }}

**Scan Date**: {{ scan_date }}
**WordPress Version**: {{ version or "Unknown" }}
**URL**: {{ url }}
**IP Address**: {{ ip_address }}

## Automated Findings

### Detected Vulnerabilities
{% if vulnerabilities %}
{% for vuln in vulnerabilities %}
- **{{ vuln.severity }}**: {{ vuln.description }}
  {% if vuln.cve %}CVE: {{ vuln.cve }}{% endif %}
{% endfor %}
{% else %}
- No vulnerabilities detected by automated scan
{% endif %}

### Findings
{% if findings %}
{% for finding in findings %}
- {{ finding.description }}
{% endfor %}
{% else %}
- No significant findings from automated scan
{% endif %}

## Manual Testing Checklist

### 1. WordPress Core Enumeration
- [ ] Identify WordPress version (check readme.html, feeds, CSS/JS versions)
- [ ] Check for xmlrpc.php (XML-RPC enabled?)
- [ ] Test wp-cron.php accessibility
- [ ] Enumerate users via `/?author=1` or REST API `/wp-json/wp/v2/users`
- [ ] Check for exposed wp-config.php backups (wp-config.bak, wp-config.old, etc.)
- [ ] Review robots.txt and sitemap.xml
- [ ] Check for debug.log exposure

### 2. Plugin Enumeration & Testing
- [ ] Enumerate installed plugins (wp-content/plugins/)
- [ ] Check each plugin for known vulnerabilities
- [ ] Test for plugin upload/file inclusion vulnerabilities
- [ ] Look for unauthenticated plugin endpoints
- [ ] Check for exposed plugin config files

### 3. Theme Enumeration & Testing
- [ ] Identify active theme (wp-content/themes/)
- [ ] Check theme for known vulnerabilities
- [ ] Test theme for arbitrary file upload
- [ ] Look for theme-specific SQL injection points
- [ ] Check for exposed theme config/backup files

### 4. Authentication & Authorization
- [ ] Test for weak admin credentials (admin/admin, admin/password, etc.)
- [ ] Check for user enumeration vulnerabilities
- [ ] Test password reset functionality
- [ ] Check for broken authentication (session fixation, etc.)
- [ ] Test for privilege escalation (subscriber → admin)
- [ ] Test for authentication bypass vulnerabilities

### 5. WordPress REST API
- [ ] Enumerate REST API endpoints (/wp-json/)
- [ ] Test for unauthorized data exposure
- [ ] Check for IDOR in REST endpoints
- [ ] Test for unauthenticated content modification
- [ ] Look for API rate limiting

### 6. File Upload & Inclusion
- [ ] Test media upload functionality
- [ ] Check for unrestricted file upload
- [ ] Test for local file inclusion (LFI)
- [ ] Test for remote file inclusion (RFI)
- [ ] Check for zip upload → path traversal

### 7. SQL Injection
- [ ] Test search functionality for SQLi
- [ ] Test custom plugin/theme parameters
- [ ] Check REST API for SQLi
- [ ] Test wp-admin POST parameters
- [ ] Look for time-based blind SQLi

### 8. Cross-Site Scripting (XSS)
- [ ] Test comments for stored XSS
- [ ] Test search functionality for reflected XSS
- [ ] Test custom fields for XSS
- [ ] Check admin panel for XSS
- [ ] Test theme/plugin settings for XSS

### 9. Cross-Site Request Forgery (CSRF)
- [ ] Check for CSRF protection on sensitive actions
- [ ] Test plugin settings changes via CSRF
- [ ] Test user creation/deletion via CSRF
- [ ] Check nonce implementation

### 10. Information Disclosure
- [ ] Check for exposed backup files
- [ ] Look for .git, .svn, .env files
- [ ] Test for directory listing
- [ ] Check for error message disclosure
- [ ] Look for sensitive data in HTML comments

### 11. Advanced WordPress Attacks
- [ ] Test for Server-Side Request Forgery (SSRF)
- [ ] Check for XXE in XML processing
- [ ] Test for deserialization vulnerabilities
- [ ] Look for race conditions in critical operations
- [ ] Test for cache poisoning

## Tools & Commands

### WPScan
```bash
wpscan --url {{ url }} --enumerate u,p,t --api-token YOUR_TOKEN
wpscan --url {{ url }} --passwords /path/to/wordlist.txt --usernames admin
```

### Manual Enumeration
```bash
# Enumerate users
curl {{ url }}/wp-json/wp/v2/users

# Check xmlrpc
curl -X POST {{ url }}/xmlrpc.php -d '<methodCall><methodName>system.listMethods</methodName></methodCall>'

# Check version
curl {{ url }}/readme.html
```

### Nuclei Templates
```bash
nuclei -u {{ url }} -t wordpress/ -severity medium,high,critical
```

## References
- [WordPress Security Whitepaper](https://wordpress.org/about/security/)
- [WPScan Vulnerability Database](https://wpscan.com/vulnerabilities)
- [OWASP WordPress Security](https://owasp.org/www-project-wordpress-security/)
- [HackerOne WordPress Bugs](https://hackerone.com/wordpress)

## Notes
```
[Add your manual testing notes here]


```

---
*Generated by BBOT Recon Methodology Module*
*Template Version: 1.0*
```

### Template Loading Logic

```python
class TemplateLoader:
    def __init__(self, repo_url, branch, cache_dir):
        self.repo_url = repo_url
        self.branch = branch
        self.cache_dir = Path(cache_dir)
        self.templates = {}
        self.config = {}

    async def initialize(self):
        """Clone or update template repository"""
        if not self.cache_dir.exists():
            await self._clone_repo()
        else:
            await self._update_repo()
        await self._load_config()

    async def get_template(self, technology):
        """Get template for a technology, with fallback"""
        # Check cache
        if technology in self.templates:
            return self.templates[technology]

        # Match technology to template via regex patterns
        template_path = self._match_technology(technology)

        if not template_path:
            # Use fallback template
            category = self._guess_category(technology)
            template_path = self.config['templates']['fallbacks'].get(category, 'web/default.md')

        # Load and cache template
        template = await self._load_template_file(template_path)
        self.templates[technology] = template
        return template

    def _match_technology(self, technology):
        """Match technology name to template using patterns from config"""
        for mapping in self.config['templates']['mapping']:
            if re.search(mapping['pattern'], technology):
                return mapping['template']
        return None
```

---

## Google Drive Integration

### Authentication Flow

#### Service Account Setup
1. **Google Cloud Console**:
   - Create project
   - Enable Google Drive API
   - Create service account
   - Download JSON key

2. **BBOT Configuration**:
   ```yaml
   modules:
     google_drive:
       credentials_file: /path/to/service-account.json
   ```

3. **Folder Sharing**:
   - Share target Drive folder with service account email
   - Grant "Editor" permissions

#### OAuth2 Setup (Alternative)
1. **Google Cloud Console**:
   - Create OAuth2 credentials
   - Configure redirect URIs
   - Download client secrets

2. **Initial Authentication**:
   ```bash
   bbot-gdrive-auth --credentials /path/to/client_secret.json
   # Opens browser for authorization
   # Saves token to ~/.bbot/google_drive_token.json
   ```

3. **BBOT Configuration**:
   ```yaml
   modules:
     google_drive:
       credentials_file: ~/.bbot/google_drive_token.json
   ```

### API Operations

#### File Upload
```python
async def upload_file(self, file_path, folder_id=None):
    """Upload a file to Google Drive"""
    file_metadata = {
        'name': file_path.name,
        'parents': [folder_id] if folder_id else []
    }

    media = MediaFileUpload(
        str(file_path),
        mimetype='text/csv',
        resumable=True
    )

    file = self.drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink, webContentLink'
    ).execute()

    return file['webViewLink']
```

#### Permission Management
```python
async def share_file(self, file_id, email, role='reader'):
    """Share a file with a user"""
    permission = {
        'type': 'user',
        'role': role,
        'emailAddress': email
    }

    self.drive_service.permissions().create(
        fileId=file_id,
        body=permission,
        sendNotificationEmail=True
    ).execute()
```

#### Folder Management
```python
async def get_or_create_folder(self, folder_name, parent_id=None):
    """Get existing folder or create new one"""
    # Search for existing folder
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = self.drive_service.files().list(
        q=query,
        fields='files(id, name)'
    ).execute()

    if results.get('files'):
        return results['files'][0]['id']

    # Create new folder
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id] if parent_id else []
    }

    folder = self.drive_service.files().create(
        body=folder_metadata,
        fields='id'
    ).execute()

    return folder['id']
```

### Folder Organization

```
Google Drive Root
└── BBOT Scans/
    └── 2025-10-14_example-com_ABCD1234/
        ├── output.csv                          # Scan results CSV
        ├── methodology/
        │   ├── example.com_WordPress.md
        │   ├── example.com_Apache.md
        │   ├── api.example.com_GraphQL.md
        │   └── admin.example.com_Django.md
        └── scan_summary.txt                    # Optional: scan metadata
```

---

## Discord Integration

### Enhanced Message Format

#### Scan Completion Summary
```json
{
  "embeds": [
    {
      "title": "🎯 BBOT Scan Complete: example.com",
      "description": "Reconnaissance scan finished successfully",
      "color": 65280,
      "fields": [
        {
          "name": "📊 Statistics",
          "value": "**Targets**: 5\n**Events**: 1,247\n**Vulnerabilities**: 3\n**Findings**: 12",
          "inline": true
        },
        {
          "name": "⏱️ Duration",
          "value": "45 minutes",
          "inline": true
        },
        {
          "name": "📁 CSV Report",
          "value": "[Download Results](https://drive.google.com/file/d/xyz/view)",
          "inline": false
        },
        {
          "name": "📝 Methodology Checklists",
          "value": "• [example.com - WordPress](https://drive.google.com/file/d/abc/view)\n• [example.com - Apache](https://drive.google.com/file/d/def/view)\n• [api.example.com - GraphQL](https://drive.google.com/file/d/ghi/view)",
          "inline": false
        }
      ],
      "footer": {
        "text": "BBOT v4.2.0 | Scan ID: ABCD1234"
      },
      "timestamp": "2025-10-14T12:34:56.789Z"
    }
  ]
}
```

#### Vulnerability Alert (Existing functionality, enhanced)
```json
{
  "embeds": [
    {
      "title": "🚨 Vulnerability Found",
      "description": "WordPress plugin vulnerable to XSS",
      "color": 16711680,
      "fields": [
        {
          "name": "Severity",
          "value": "HIGH",
          "inline": true
        },
        {
          "name": "Host",
          "value": "example.com",
          "inline": true
        },
        {
          "name": "Details",
          "value": "Reflected XSS in search parameter",
          "inline": false
        },
        {
          "name": "Methodology",
          "value": "[Review WordPress checklist](https://drive.google.com/file/d/abc/view)",
          "inline": false
        }
      ]
    }
  ]
}
```

### Module Context Sharing

To enable Google Drive links in Discord messages, modules share data via scan context:

```python
# In google_drive.py
async def handle_event(self, event):
    if event.type == "FINISHED":
        csv_link = await self.upload_csv()
        # Share link via scan context
        self.scan.context['google_drive_csv_link'] = csv_link

# In recon_methodology.py
async def report(self):
    methodology_links = []
    for file in self.generated_files:
        link = await self.upload_to_drive(file)
        methodology_links.append({
            'name': file.stem,
            'link': link
        })
    self.scan.context['google_drive_methodology_links'] = methodology_links

# In discord.py (enhanced)
async def handle_event(self, event):
    if event.type == "FINISHED":
        csv_link = self.scan.context.get('google_drive_csv_link')
        methodology_links = self.scan.context.get('google_drive_methodology_links', [])
        await self.post_scan_summary(csv_link, methodology_links)
```

---

## Security Considerations

### Authentication & Credentials
1. **Never commit credentials to git**
   - Add credentials files to .gitignore
   - Use environment variables or secure config files

2. **Service Account Security**
   - Limit service account permissions to minimum required
   - Use separate service accounts per environment (dev/prod)
   - Rotate service account keys periodically

3. **OAuth Token Security**
   - Store refresh tokens securely (encrypted)
   - Implement token rotation
   - Revoke tokens when no longer needed

### Data Handling
1. **Sensitive Information in Scan Results**
   - Be cautious about uploading results containing credentials
   - Consider data sanitization before upload
   - Use private Drive folders with restricted access

2. **Template Repository**
   - Verify template repository authenticity (HTTPS, signed commits)
   - Review templates before using (no arbitrary code execution)
   - Use specific branches/tags instead of main

3. **Discord Webhooks**
   - Protect webhook URLs (treat as secrets)
   - Use HTTPS for all webhook communications
   - Implement rate limiting to prevent abuse

### Access Control
1. **Google Drive Permissions**
   - Default to private folders
   - Explicitly share with specific users
   - Avoid public links unless necessary
   - Regularly audit shared permissions

2. **Template Repository Access**
   - Use read-only access for template loading
   - Verify repository ownership
   - Pin to specific commits for production

### Input Validation
1. **Template Variables**
   - Sanitize all variables before substitution
   - Prevent template injection attacks
   - Validate template structure before loading

2. **Configuration Options**
   - Validate file paths (no directory traversal)
   - Validate URLs (prevent SSRF)
   - Validate email addresses for sharing

---

## Implementation Plan

### Phase 1: Foundation (Week 1)
1. **External Template Repository**
   - Create `bbot-recon-templates` repository
   - Implement 10 core templates (WordPress, Apache, Nginx, Django, Flask, MySQL, REST API, GraphQL, Generic Web, Generic Database)
   - Write template configuration (config.yml)
   - Document template creation guide

2. **Template Loader**
   - Implement git clone/update logic
   - Build template matching system
   - Add Jinja2 template rendering
   - Write unit tests for template loader

### Phase 2: Google Drive Integration (Week 2)
1. **Google Drive Module**
   - Implement BaseOutputModule extension
   - Add Google API authentication (service account + OAuth2)
   - Implement file upload functionality
   - Add folder management
   - Implement permission/sharing logic
   - Write unit tests with mocked Google API

2. **Configuration & Setup**
   - Document Google Cloud setup process
   - Create authentication helper script
   - Add configuration validation

### Phase 3: Methodology Generator (Week 3)
1. **Recon Methodology Module**
   - Implement event collection system
   - Build aggregation logic (group by host/technology)
   - Implement template loading and rendering
   - Add markdown file generation
   - Integrate with Google Drive upload (optional)
   - Write unit tests and integration tests

### Phase 4: Discord Integration (Week 4)
1. **Discord Enhancement**
   - Modify discord.py for scan summaries
   - Implement context sharing between modules
   - Add Drive link formatting
   - Test webhook message delivery
   - Write integration tests

### Phase 5: Testing & Documentation (Week 5)
1. **Comprehensive Testing**
   - End-to-end integration tests
   - Test all configuration combinations
   - Test error handling and edge cases
   - Performance testing (large scans)

2. **Documentation**
   - User guide for setup and configuration
   - Developer guide for template creation
   - API documentation
   - Troubleshooting guide

### Phase 6: Polish & Release (Week 6)
1. **Code Review & Refinement**
   - Address code review feedback
   - Optimize performance
   - Improve error messages

2. **Examples & Demos**
   - Create example configurations
   - Record demo videos
   - Write blog post

3. **Release**
   - Merge to dev branch
   - Create pull request to stable
   - Tag release version

---

## Testing Strategy

### Unit Tests

#### Template Loader Tests
```python
class TestTemplateLoader:
    async def test_clone_repository(self):
        """Test template repository cloning"""

    async def test_update_repository(self):
        """Test template repository updates"""

    async def test_match_technology_exact(self):
        """Test exact technology name matching"""

    async def test_match_technology_regex(self):
        """Test regex pattern matching"""

    async def test_fallback_template(self):
        """Test fallback template selection"""

    async def test_template_variable_substitution(self):
        """Test Jinja2 variable substitution"""
```

#### Google Drive Module Tests
```python
class TestGoogleDriveModule:
    async def test_authentication_service_account(self):
        """Test service account authentication"""

    async def test_authentication_oauth(self):
        """Test OAuth authentication"""

    async def test_upload_file(self):
        """Test file upload to Drive"""

    async def test_create_folder(self):
        """Test folder creation"""

    async def test_share_file(self):
        """Test file sharing"""

    async def test_handle_upload_failure(self):
        """Test upload failure handling"""
```

#### Methodology Module Tests
```python
class TestReconMethodology:
    async def test_event_collection(self):
        """Test event storage during scan"""

    async def test_event_aggregation_by_host(self):
        """Test grouping events by host"""

    async def test_event_aggregation_by_technology(self):
        """Test grouping events by technology"""

    async def test_checklist_generation(self):
        """Test markdown file generation"""

    async def test_template_not_found(self):
        """Test handling of missing templates"""

    async def test_variable_missing(self):
        """Test handling of missing variables"""
```

### Integration Tests

```python
class TestIntegration:
    async def test_full_scan_with_google_drive(self):
        """Test complete scan with Google Drive upload"""
        scan = Scanner("example.com", modules=["httpx", "wappalyzer"],
                      output_modules=["google_drive", "recon_methodology"])
        await scan.async_start()
        # Verify files uploaded to Drive

    async def test_methodology_generation_wordpress(self):
        """Test methodology generation for WordPress site"""

    async def test_discord_summary_with_links(self):
        """Test Discord summary includes Drive links"""

    async def test_module_context_sharing(self):
        """Test modules share data via scan context"""
```

### Manual Testing Checklist

- [ ] Test Google Drive authentication (service account)
- [ ] Test Google Drive authentication (OAuth2)
- [ ] Test file upload to Drive
- [ ] Test folder creation and organization
- [ ] Test file sharing with multiple users
- [ ] Test template repository cloning
- [ ] Test template repository updates
- [ ] Test WordPress template rendering
- [ ] Test methodology generation for 5+ technologies
- [ ] Test Discord summary message formatting
- [ ] Test Discord Drive link posting
- [ ] Test large scan (1000+ events)
- [ ] Test scan with no TECHNOLOGY events (fallback)
- [ ] Test network failure handling
- [ ] Test invalid credentials handling
- [ ] Test malformed template handling

---

## Future Enhancements

### Version 2.0 Features
1. **Multi-Cloud Support**
   - Azure Blob Storage integration
   - AWS S3 integration
   - Dropbox integration

2. **Interactive Checklists**
   - Web interface for checklist tracking
   - Progress tracking across team
   - Export to Jira/GitHub Issues

3. **AI-Powered Methodology**
   - GPT-4 integration for custom checklist generation
   - Context-aware recommendations
   - Automated vulnerability analysis

4. **Enhanced Templates**
   - Video walkthrough links
   - Tool installation scripts
   - Automated exploit PoC generation

5. **Collaboration Features**
   - Real-time checklist updates
   - Team assignment
   - Comments and annotations

### Version 3.0 Features
1. **Findings Management**
   - Track completed checklist items
   - Link findings to checklist items
   - Generate reports from checklists

2. **Custom Integrations**
   - Slack integration
   - Microsoft Teams integration
   - Email notifications

3. **Advanced Analytics**
   - Scan comparison across time
   - Technology trend analysis
   - Vulnerability pattern detection

---

## Appendices

### Appendix A: Template Variable Reference

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `host` | string | Target hostname | `example.com` |
| `technology` | string | Detected technology | `WordPress` |
| `version` | string | Technology version | `6.2` |
| `url` | string | Full URL | `https://example.com` |
| `ip_address` | string | Resolved IP | `192.0.2.1` |
| `ports` | list[int] | Open ports | `[80, 443, 8080]` |
| `scan_date` | string | Scan timestamp | `2025-10-14 12:34:56` |
| `bbot_version` | string | BBOT version | `4.2.0` |
| `vulnerabilities` | list[dict] | Detected vulnerabilities | See data structure |
| `findings` | list[dict] | Scan findings | See data structure |
| `headers` | dict | HTTP headers | `{"Server": "nginx"}` |

### Appendix B: Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `GDRIVE_AUTH_FAILED` | Google Drive authentication failed | Check credentials file |
| `GDRIVE_UPLOAD_FAILED` | File upload to Drive failed | Check network, retry |
| `TEMPLATE_REPO_CLONE_FAILED` | Failed to clone template repository | Check git URL, network |
| `TEMPLATE_NOT_FOUND` | No template for technology | Will use fallback template |
| `TEMPLATE_RENDER_ERROR` | Template rendering failed | Check template syntax |
| `DISCORD_WEBHOOK_FAILED` | Discord webhook delivery failed | Check webhook URL |

### Appendix C: Dependencies

```toml
[tool.poetry.dependencies]
# Existing BBOT dependencies...

# Google Drive Integration
google-api-python-client = "^2.100.0"
google-auth-httplib2 = "^0.1.1"
google-auth-oauthlib = "^1.1.0"

# Template Rendering
jinja2 = "^3.1.2"

# Git Operations (for template repository)
gitpython = "^3.1.37"
```

### Appendix D: Configuration Examples

#### Minimal Configuration
```yaml
modules:
  google_drive:
    credentials_file: /path/to/credentials.json
  recon_methodology:
    template_repo_url: https://github.com/username/bbot-recon-templates.git
  discord:
    webhook_url: https://discord.com/api/webhooks/...
```

#### Advanced Configuration
```yaml
modules:
  google_drive:
    credentials_file: /path/to/service-account.json
    folder_id: 1ABCxyz...
    share_with:
      - alice@example.com
      - bob@example.com
    make_public: false
    include_csv: true

  recon_methodology:
    template_repo_url: https://github.com/username/bbot-recon-templates.git
    template_repo_branch: production
    template_cache_dir: /opt/bbot/templates
    output_dir: /var/reports/methodologies
    upload_to_drive: true
    group_by: host
    include_technologies:
      - WordPress
      - Django
      - Flask
      - Apache
    exclude_technologies:
      - Generic

  discord:
    webhook_url: https://discord.com/api/webhooks/...
    event_types:
      - VULNERABILITY
      - FINDING
    min_severity: HIGH
    include_scan_summary: true
    include_drive_links: true
```

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-10-14 | Matt Caughman | Initial specification |

---

*This specification is a living document and will be updated as implementation progresses.*
