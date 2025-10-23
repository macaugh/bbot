# Quick Start: Team Collaboration with BBOT

Get your team up and running with automated reconnaissance, methodology generation, and Google Drive integration in minutes.

## What You'll Set Up

1. **Google Drive Integration** - Upload scan results automatically
2. **Recon Methodology Generation** - Technology-specific testing checklists
3. **Discord Notifications** - Alert team when scans complete

## Prerequisites

- BBOT installed ([Installation Guide](../installation.md))
- Google account (for Google Drive)
- Discord webhook URL (optional)

## 5-Minute Setup

### Step 1: Google Drive Setup (2 minutes)

#### Create Service Account

```bash
# 1. Go to https://console.cloud.google.com/
# 2. Create project or use existing
# 3. Enable "Google Drive API"
# 4. Create Service Account:
#    - Navigate to APIs & Services → Credentials
#    - Create Credentials → Service Account
#    - Name: bbot-scanner
#    - Download JSON key

# 5. Save credentials
mkdir -p ~/.bbot
mv ~/Downloads/credentials.json ~/.bbot/google-creds.json
chmod 600 ~/.bbot/google-creds.json
```

#### Share Drive Folder

```bash
# 1. Create folder in Google Drive: "BBOT Scans"
# 2. Share with service account email from JSON file
#    (e.g., bbot-scanner@project-123.iam.gserviceaccount.com)
# 3. Give "Editor" permissions
```

### Step 2: Configuration (1 minute)

Create `~/.config/bbot/bbot.yml`:

```yaml
modules:
  # Google Drive upload
  google_drive:
    credentials_file: ~/.bbot/google-creds.json
    share_with:
      - alice@example.com    # Your teammates
      - bob@example.com

  # Methodology generation
  recon_methodology:
    # Use public template repository
    template_repo_url: https://github.com/blacklanternsecurity/bbot-recon-templates.git
    group_by: host
    exclude_technologies:
      - Generic
      - Unknown

  # Discord notifications (optional)
  discord:
    webhook_url: https://discord.com/api/webhooks/YOUR_WEBHOOK_HERE
    include_scan_summary: true
    include_drive_links: true
    event_types:
      - VULNERABILITY
      - FINDING
    min_severity: MEDIUM
```

### Step 3: Your First Team Scan (1 minute)

```bash
# Run a complete reconnaissance scan
bbot -t example.com \
  -p subdomain-enum \
  -om google_drive,recon_methodology,discord
```

**What happens**:
1. ✅ Scans example.com for subdomains
2. ✅ Detects technologies (WordPress, Apache, etc.)
3. ✅ Generates methodology checklists
4. ✅ Uploads CSV + checklists to Google Drive
5. ✅ Shares with team members
6. ✅ Posts summary to Discord with links

### Step 4: View Results (30 seconds)

**Local**:
```bash
# View local results
cd ~/.bbot/scans/example_com_*/

# CSV results
cat output.csv

# Methodology checklists
ls methodology/
# example.com_WordPress.md
# example.com_Apache.md
# api.example.com_GraphQL.md
```

**Google Drive**:
1. Open Google Drive
2. Navigate to "BBOT Scans" folder
3. Find your scan folder
4. Download or view files online

**Discord** (if configured):
- Check your Discord channel for scan summary
- Click links to view files in Google Drive

## Common Workflows

### Daily Reconnaissance

```bash
# Quick subdomain enum with methodology
bbot -t example.com -p subdomain-enum -om google_drive,recon_methodology
```

### Deep Security Assessment

```bash
# Comprehensive scan with all tools
bbot -t example.com \
  -p subdomain-enum,web-thorough \
  -m nuclei wappalyzer \
  -om google_drive,recon_methodology,discord \
  --allow-deadly
```

### Multiple Targets

```bash
# Scan multiple domains
bbot -t example.com test.com demo.com \
  -p subdomain-enum \
  -om google_drive,recon_methodology
```

### Continuous Monitoring

```bash
# Set up cron job for daily scans
# /etc/cron.daily/bbot-scan.sh
#!/bin/bash
cd /opt/bbot
bbot -t example.com \
  -p subdomain-enum \
  -om google_drive,recon_methodology,discord \
  --force
```

## Team Best Practices

### 1. Shared Configuration

**Create team preset**: `~/.config/bbot/presets/team-standard.yml`

```yaml
description: Company standard reconnaissance

include:
  - subdomain-enum
  - web-basic

output_modules:
  - google_drive
  - recon_methodology
  - discord

config:
  modules:
    google_drive:
      credentials_file: ~/.bbot/google-creds.json
      share_with:
        - security-team@company.com

    recon_methodology:
      template_repo_url: https://github.com/company/internal-templates.git

    discord:
      webhook_url: ${DISCORD_WEBHOOK}  # From environment
```

**Usage**:
```bash
export DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
bbot -t example.com -p team-standard
```

### 2. Custom Methodology Templates

**Fork and customize**:

```bash
# 1. Fork template repository
git clone https://github.com/blacklanternsecurity/bbot-recon-templates.git company-templates
cd company-templates

# 2. Add company-specific templates
vim templates/internal/company-app.md

# 3. Update config.yml
vim config.yml
# Add:
#   - pattern: "(?i)CompanyApp"
#     template: "internal/company-app.md"

# 4. Push to company GitHub
git remote add origin git@github.com:company/recon-templates.git
git push -u origin main

# 5. Update BBOT config
# template_repo_url: https://github.com/company/recon-templates.git
```

### 3. Separate Credentials by Environment

**Dev environment**:
```yaml
# ~/.config/bbot/bbot.dev.yml
modules:
  google_drive:
    credentials_file: ~/.bbot/dev-creds.json
    folder_id: "dev-folder-id"
```

**Production environment**:
```yaml
# ~/.config/bbot/bbot.prod.yml
modules:
  google_drive:
    credentials_file: ~/.bbot/prod-creds.json
    folder_id: "prod-folder-id"
    share_with:
      - security-leads@company.com
```

**Usage**:
```bash
# Dev scan
bbot -t example.com -p subdomain-enum -om google_drive -c ~/.config/bbot/bbot.dev.yml

# Prod scan
bbot -t example.com -p subdomain-enum -om google_drive -c ~/.config/bbot/bbot.prod.yml
```

### 4. Methodology Review Workflow

1. **Initial Scan**: Automated reconnaissance
2. **Review Checklists**: Team reviews generated methodologies
3. **Manual Testing**: Follow checklists systematically
4. **Update Checklists**: Add notes and check off completed items
5. **Upload Results**: Save findings back to Google Drive

**Example**:
```bash
# 1. Initial scan
bbot -t example.com -p subdomain-enum -om google_drive,recon_methodology

# 2. Download checklists from Google Drive
# 3. Team reviews and performs manual testing
# 4. Updates markdown files with findings
# 5. Re-upload to Drive or commit to repo
```

## Advanced Configuration

### Conditional Methodology Generation

**Only generate for high-value technologies**:

```yaml
modules:
  recon_methodology:
    template_repo_url: https://github.com/user/templates.git
    include_technologies:
      - WordPress
      - Django
      - GraphQL
      - Jenkins
      - GitLab
```

### Technology-Based Grouping

**Generate one checklist per technology (multiple hosts)**:

```yaml
modules:
  recon_methodology:
    group_by: technology  # Instead of 'host'
```

**Result**: One `WordPress_methodology.md` covering all WordPress hosts.

### Automated Sharing Rules

**Share different results with different teams**:

```yaml
modules:
  google_drive:
    credentials_file: ~/.bbot/creds.json
    share_with:
      - security-team@company.com      # Everyone
      - pentest-leads@company.com      # Leads
      - compliance@company.com         # Compliance team
```

### Discord Alert Filtering

**Only alert on critical/high vulnerabilities**:

```yaml
modules:
  discord:
    webhook_url: https://discord.com/api/webhooks/...
    event_types:
      - VULNERABILITY
    min_severity: HIGH  # Only HIGH and CRITICAL
    include_scan_summary: true
```

## Troubleshooting

### Google Drive Not Working

```bash
# Test credentials
python3 -c "
from google.oauth2 import service_account
creds = service_account.Credentials.from_service_account_file(
    '~/.bbot/google-creds.json',
    scopes=['https://www.googleapis.com/auth/drive.file']
)
print('Credentials valid!')
"

# Check file permissions
ls -la ~/.bbot/google-creds.json
# Should be: -rw------- (600)

# Verify service account has access
# Go to Google Drive, check "Shared with me" for BBOT Scans folder
```

### Methodologies Not Generated

```bash
# Check TECHNOLOGY events are being detected
bbot -t example.com -m wappalyzer httpx -om python | grep TECHNOLOGY

# If no technologies detected, add more scanning modules
bbot -t example.com -p web-thorough -om recon_methodology

# Check template repository
git clone https://github.com/user/templates.git /tmp/test-templates
ls /tmp/test-templates/templates/
```

### Discord Not Posting

```bash
# Test webhook manually
curl -X POST https://discord.com/api/webhooks/YOUR_WEBHOOK \
  -H "Content-Type: application/json" \
  -d '{"content": "Test message from BBOT"}'

# Check webhook URL is correct
# Verify channel has webhook enabled
# Check Discord rate limits (if sending many alerts)
```

## Example: Complete Team Workflow

### Scenario
Security team scanning 10 domains daily, sharing results with stakeholders.

### Setup

**1. Create shared config**: `/opt/bbot/team-config.yml`

```yaml
modules:
  google_drive:
    credentials_file: /opt/bbot/prod-creds.json
    folder_id: "1ABC_company_folder_id"
    share_with:
      - security-team@company.com
      - executives@company.com

  recon_methodology:
    template_repo_url: https://github.com/company/internal-templates.git
    template_repo_branch: production
    group_by: host
    exclude_technologies:
      - Generic

  discord:
    webhook_url: ${DISCORD_WEBHOOK_SECURITY}
    include_scan_summary: true
    include_drive_links: true
    event_types:
      - VULNERABILITY
    min_severity: MEDIUM
```

**2. Create scan script**: `/opt/bbot/daily-scan.sh`

```bash
#!/bin/bash
set -e

TARGETS=(
  "example.com"
  "test.com"
  "demo.com"
  "api.company.com"
  "admin.company.com"
)

for target in "${TARGETS[@]}"; do
  echo "Scanning $target..."
  bbot -t "$target" \
    -p subdomain-enum,web-basic \
    -om google_drive,recon_methodology,discord \
    -c /opt/bbot/team-config.yml \
    --force
done

echo "All scans complete!"
```

**3. Schedule with cron**: `crontab -e`

```cron
# Daily scans at 2 AM
0 2 * * * /opt/bbot/daily-scan.sh >> /var/log/bbot-daily.log 2>&1
```

**4. Monitor in Discord**

Team receives daily notifications with:
- Scan completion status
- Vulnerability counts
- Links to Google Drive results
- Direct links to methodology checklists

### Benefits

✅ **Automated**: Runs daily without intervention
✅ **Collaborative**: Results shared with entire team
✅ **Organized**: Google Drive maintains scan history
✅ **Actionable**: Pre-generated checklists ready for testing
✅ **Visible**: Discord alerts keep team informed

## Next Steps

1. **Customize Templates**: Add internal tools and frameworks
2. **Refine Presets**: Create role-specific scan configurations
3. **Automate Further**: Integrate with ticketing systems (Jira, etc.)
4. **Train Team**: Share methodology templates and best practices
5. **Iterate**: Update templates based on findings and team feedback

## Resources

- [Google Drive Integration Guide](./google_drive_integration.md)
- [Recon Methodology Documentation](./recon_methodology.md)
- [Discord Integration](./discord.md)
- [Template Repository](https://github.com/blacklanternsecurity/bbot-recon-templates)
- [BBOT Presets](./presets.md)

## Support

- **Community Discord**: [Join Here](https://discord.com/invite/PZqkgxu5SA)
- **GitHub Issues**: [Report Bugs](https://github.com/blacklanternsecurity/bbot/issues)
- **Documentation**: [Full Docs](https://www.blacklanternsecurity.com/bbot/)

---

**You're all set!** Your team now has automated reconnaissance with Google Drive collaboration and methodology generation. Happy hacking! 🚀
