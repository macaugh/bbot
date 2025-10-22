# Recon Methodology Module

The Recon Methodology module automatically generates technology-specific penetration testing checklists based on your scan results.

## Overview

Instead of manually creating testing checklists for each discovered technology, BBOT:

1. **Detects Technologies**: Via modules like `wappalyzer`, `httpx`, etc.
2. **Loads Templates**: From a git repository of methodology templates
3. **Generates Checklists**: Markdown files with technology-specific testing procedures
4. **Populates Data**: Automatically fills in scan data (URLs, IPs, vulnerabilities)
5. **Organizes Results**: By host or technology, based on your preference

## Features

- **80+ Technology Templates**: WordPress, Django, GraphQL, Apache, Nginx, and more
- **Automated Data Population**: Scan results auto-filled using Jinja2 templates
- **Version-Controlled Templates**: Git-based template repository
- **Customizable**: Create your own templates for internal tools
- **Flexible Grouping**: Generate one checklist per host or per technology
- **Include/Exclude Filters**: Focus on specific technologies
- **Google Drive Integration**: Automatically upload checklists to Drive

## Quick Start

### 1. Use Public Template Repository

```bash
# Basic usage with public templates
bbot -t example.com -p subdomain-enum -om recon_methodology \
  -c modules.recon_methodology.template_repo_url=https://github.com/blacklanternsecurity/bbot-recon-templates.git
```

### 2. Use Local Template Repository

```bash
# Clone templates locally first
git clone https://github.com/blacklanternsecurity/bbot-recon-templates.git ~/bbot-templates

# Use local templates
bbot -t example.com -p subdomain-enum -om recon_methodology \
  -c modules.recon_methodology.template_repo_url=file:///Users/you/bbot-templates
```

### 3. View Generated Checklists

```bash
# Results are saved in scan output directory
ls ~/.bbot/scans/example_com_*/methodology/

# Example files:
# example.com_WordPress.md
# example.com_Apache.md
# api.example.com_GraphQL.md
```

## Configuration

### Basic Configuration

Add to `~/.config/bbot/bbot.yml`:

```yaml
modules:
  recon_methodology:
    template_repo_url: https://github.com/user/bbot-recon-templates.git
    group_by: host
```

### Advanced Configuration

```yaml
modules:
  recon_methodology:
    # Git repository URL for templates (required)
    template_repo_url: https://github.com/user/bbot-recon-templates.git

    # Git branch to use (default: main)
    template_repo_branch: main

    # Local cache directory (default: ~/.bbot/templates)
    template_cache_dir: ~/.bbot/templates

    # Output directory for markdown files (default: scan_dir/methodology)
    output_dir: ""

    # Upload to Google Drive (requires google_drive module)
    upload_to_drive: false

    # Group checklists by 'host' or 'technology'
    group_by: host

    # Whitelist: Only generate for these technologies (empty = all)
    include_technologies:
      - WordPress
      - Django
      - GraphQL

    # Blacklist: Skip these technologies
    exclude_technologies:
      - Generic
      - Unknown
```

## Grouping Strategies

### Group by Host (Default)

Generate one checklist per host for each technology on that host.

```yaml
group_by: host
```

**Output**:
```
methodology/
├── example.com_WordPress.md
├── example.com_Apache.md
├── api.example.com_REST.md
└── admin.example.com_Django.md
```

**Use when**: Testing each host separately, separate penetration testing reports per host.

### Group by Technology

Generate one checklist per technology covering all hosts.

```yaml
group_by: technology
```

**Output**:
```
methodology/
├── WordPress_methodology.md     # Covers example.com, blog.example.com
├── Apache_methodology.md        # Covers example.com, www.example.com
└── Django_methodology.md        # Covers admin.example.com
```

**Use when**: Testing technologies across multiple hosts, technology-focused assessments.

## Template System

### Template Repository Structure

```
bbot-recon-templates/
├── README.md
├── config.yml           # Technology mappings
├── templates/
│   ├── web/
│   │   ├── wordpress.md
│   │   ├── drupal.md
│   │   ├── nginx.md
│   │   └── default.md
│   ├── api/
│   │   ├── rest.md
│   │   ├── graphql.md
│   │   └── soap.md
│   ├── framework/
│   │   ├── django.md
│   │   ├── flask.md
│   │   └── rails.md
│   └── database/
│       ├── mysql.md
│       └── postgresql.md
```

### Available Variables

Templates use Jinja2 syntax. Available variables:

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `{{ host }}` | string | Target hostname | `example.com` |
| `{{ technology }}` | string | Technology name | `WordPress` |
| `{{ version }}` | string | Version (if detected) | `6.2` |
| `{{ url }}` | string | Full URL | `https://example.com` |
| `{{ ip_address }}` | string | Resolved IP | `192.0.2.1` |
| `{{ ports }}` | list | Open ports | `[80, 443, 8080]` |
| `{{ scan_date }}` | string | Scan timestamp | `2025-10-14 12:34:56` |
| `{{ bbot_version }}` | string | BBOT version | `4.2.0` |
| `{{ vulnerabilities }}` | list | Detected vulns | See below |
| `{{ findings }}` | list | Scan findings | See below |
| `{{ headers }}` | dict | HTTP headers | `{"Server": "nginx"}` |

### Vulnerability Structure

```python
{
    "severity": "HIGH",
    "description": "WordPress plugin XYZ vulnerable to XSS",
    "cve": "CVE-2023-12345"  # Optional
}
```

### Using Variables in Templates

```markdown
# {{ technology }} Reconnaissance: {{ host }}

**Scan Date**: {{ scan_date }}
**Version**: {{ version or "Unknown" }}
**URL**: {{ url }}

## Automated Findings

### Vulnerabilities
{% if vulnerabilities %}
{% for vuln in vulnerabilities %}
- **{{ vuln.severity }}**: {{ vuln.description }}
  {% if vuln.cve %}CVE: {{ vuln.cve }}{% endif %}
{% endfor %}
{% else %}
- No vulnerabilities detected by automated scan
{% endif %}

## Manual Testing Checklist
- [ ] Test authentication mechanisms
- [ ] Check for {{ technology }}-specific vulnerabilities
- [ ] Enumerate plugins/extensions
```

## Creating Custom Templates

### 1. Fork Template Repository

```bash
git clone https://github.com/blacklanternsecurity/bbot-recon-templates.git
cd bbot-recon-templates
```

### 2. Create New Template

```bash
# Create template file
vim templates/web/myframework.md
```

### 3. Template Structure

```markdown
# {{ technology }} Reconnaissance: {{ host }}

**Scan Date**: {{ scan_date }}
**URL**: {{ url }}

## Automated Findings

### Vulnerabilities
{% if vulnerabilities %}
{% for vuln in vulnerabilities %}
- {{ vuln.severity }}: {{ vuln.description }}
{% endfor %}
{% endif %}

## Manual Testing Checklist

### 1. Authentication
- [ ] Test for weak credentials
- [ ] Check password policy
- [ ] Test 2FA implementation

### 2. Technology-Specific Tests
- [ ] Check MyFramework version
- [ ] Test for known CVEs
- [ ] Enumerate installed plugins

### 3. Common Vulnerabilities
- [ ] SQL Injection
- [ ] XSS
- [ ] CSRF

## Tools & Commands

\`\`\`bash
# Scan with my-scanner
my-scanner --url {{ url }}

# Check version
curl {{ url }}/version.txt
\`\`\`

## References
- [Official Documentation](https://myframework.com/docs)
- [Security Guide](https://myframework.com/security)

## Notes
\`\`\`
[Add your testing notes here]
\`\`\`
```

### 4. Add to config.yml

```yaml
templates:
  mapping:
    - pattern: "(?i)myframework"
      template: "web/myframework.md"
      category: "web"
      description: "MyFramework testing"
```

### 5. Test Your Template

```bash
# Use your local repository
bbot -t example.com -p subdomain-enum -om recon_methodology \
  -c modules.recon_methodology.template_repo_url=file:///path/to/your/templates
```

### 6. Commit and Use

```bash
git add templates/web/myframework.md config.yml
git commit -m "Add MyFramework template"
git push

# Use remote repository
bbot -t example.com -p subdomain-enum -om recon_methodology \
  -c modules.recon_methodology.template_repo_url=https://github.com/you/bbot-recon-templates.git
```

## Usage Examples

### Basic Reconnaissance

```bash
# Generate methodologies for all detected technologies
bbot -t example.com \
  -p subdomain-enum \
  -m wappalyzer httpx \
  -om recon_methodology \
  -c modules.recon_methodology.template_repo_url=https://github.com/user/templates.git
```

### Focus on Specific Technologies

```bash
# Only generate WordPress and Django checklists
bbot -t example.com \
  -p subdomain-enum \
  -om recon_methodology \
  -c modules.recon_methodology.template_repo_url=https://github.com/user/templates.git \
  -c modules.recon_methodology.include_technologies=WordPress,Django
```

### Exclude Generic Results

```bash
# Skip generic/unknown technologies
bbot -t example.com \
  -p subdomain-enum \
  -om recon_methodology \
  -c modules.recon_methodology.template_repo_url=https://github.com/user/templates.git \
  -c modules.recon_methodology.exclude_technologies=Generic,Unknown
```

### Group by Technology

```bash
# Generate one checklist per technology (not per host)
bbot -t example.com subdomain1.example.com subdomain2.example.com \
  -p subdomain-enum \
  -om recon_methodology \
  -c modules.recon_methodology.template_repo_url=https://github.com/user/templates.git \
  -c modules.recon_methodology.group_by=technology
```

### With Google Drive Upload

```bash
# Generate and upload to Google Drive
bbot -t example.com \
  -p subdomain-enum \
  -om google_drive,recon_methodology \
  -c modules.google_drive.credentials_file=~/.bbot/creds.json \
  -c modules.recon_methodology.template_repo_url=https://github.com/user/templates.git
```

### Python API

```python
from bbot.scanner import Scanner

config = {
    "modules": {
        "recon_methodology": {
            "template_repo_url": "https://github.com/user/templates.git",
            "group_by": "host",
            "exclude_technologies": ["Generic"],
        }
    }
}

scan = Scanner(
    "example.com",
    presets=["subdomain-enum"],
    modules=["wappalyzer", "httpx"],
    output_modules=["recon_methodology"],
    config=config
)

for event in scan.start():
    if event.type == "TECHNOLOGY":
        print(f"Detected: {event.data}")

# Find generated methodology files
methodology_dir = scan.home / "methodology"
for md_file in methodology_dir.glob("*.md"):
    print(f"Generated: {md_file}")
```

## Integration Examples

### Full Workflow: Scan → Methodologies → Drive → Discord

```bash
bbot -t example.com \
  -p subdomain-enum \
  -m wappalyzer httpx nuclei \
  -om google_drive,recon_methodology,discord \
  -c modules.google_drive.credentials_file=~/.bbot/creds.json \
  -c modules.google_drive.share_with=team@example.com \
  -c modules.recon_methodology.template_repo_url=https://github.com/user/templates.git \
  -c modules.discord.webhook_url=https://discord.com/api/webhooks/... \
  -c modules.discord.include_drive_links=true
```

**What happens**:
1. BBOT scans example.com for subdomains
2. Detects technologies with wappalyzer
3. Finds vulnerabilities with nuclei
4. Generates technology-specific checklists
5. Uploads CSV and checklists to Google Drive
6. Shares with team@example.com
7. Posts summary to Discord with Drive links

### Organization Presets

Create a preset for your organization:

**~/.config/bbot/presets/company-recon.yml**:
```yaml
description: Company standard reconnaissance workflow

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
      credentials_file: ~/.bbot/company-creds.json
      share_with:
        - security-team@company.com

    recon_methodology:
      template_repo_url: https://github.com/company/internal-templates.git
      template_repo_branch: production
      exclude_technologies:
        - Generic
        - Unknown

    discord:
      webhook_url: https://discord.com/api/webhooks/company/webhook
      include_scan_summary: true
      include_drive_links: true
```

**Usage**:
```bash
bbot -t example.com -p company-recon
```

## Template Best Practices

### ✅ DO

- **Include comprehensive checklists**: Cover all major vulnerability categories
- **Use clear section headers**: Organize tests logically
- **Add tool commands**: Provide specific commands with examples
- **Include references**: Link to official docs and security resources
- **Use conditional logic**: Handle optional variables gracefully
- **Test templates**: Verify rendering with real scan data

### ❌ DON'T

- **Hardcode values**: Use variables instead of static data
- **Create overly generic templates**: Be specific to the technology
- **Skip descriptions**: Explain why tests are important
- **Ignore fallbacks**: Always provide `or "Unknown"` for optional vars
- **Forget notes section**: Leave space for manual notes

### Template Checklist

- [ ] Clear title with hostname
- [ ] Scan metadata (date, version, URL)
- [ ] Automated findings section (vulnerabilities, findings)
- [ ] Structured manual testing checklist
- [ ] Tools & commands with examples
- [ ] References to official documentation
- [ ] Notes section for manual additions
- [ ] Proper Jinja2 syntax (tested)
- [ ] All variables have fallbacks

## Troubleshooting

### Template Repository Issues

**Error**: `Failed to clone template repository`

**Solutions**:
1. Check URL is correct
2. Verify network connectivity
3. For private repos, use SSH URL with configured keys
4. Try file:// URL for local testing

**Error**: `Template config.yml not found`

**Solutions**:
1. Ensure config.yml exists in repository root
2. Check file is named exactly `config.yml` (case-sensitive)
3. Verify YAML syntax is valid

### Template Rendering Issues

**Error**: `Template rendering error`

**Solutions**:
1. Check Jinja2 syntax is correct
2. Verify all `{% %}` blocks are closed
3. Use `{{ variable or "default" }}` for optional variables
4. Test template with minimal variables first

### No Methodologies Generated

**Possible Causes**:
1. No TECHNOLOGY events detected → Add more modules (wappalyzer, httpx)
2. All technologies filtered out → Check include/exclude lists
3. No matching templates → Check config.yml patterns
4. Template repository not loaded → Verify repo URL and credentials

**Debug**:
```bash
# Run with debug logging
bbot -t example.com -p subdomain-enum -om recon_methodology --debug

# Check for TECHNOLOGY events
bbot -t example.com -m wappalyzer -om python | grep TECHNOLOGY
```

### Permission Issues

**Error**: `Permission denied` when accessing templates

**Solutions**:
1. Check cache directory permissions: `chmod 755 ~/.bbot/templates`
2. Verify git can access repository
3. For private repos, ensure SSH keys are configured

## Performance Considerations

### Template Caching

- **First run**: Clones repository (~2-5 seconds)
- **Subsequent runs**: Updates existing clone (~1-2 seconds)
- Templates cached in memory after first load

### Generation Time

- **Template loading**: ~100ms per template
- **Rendering**: ~50-200ms per file
- **Total**: Usually <5 seconds for typical scans

### Large Scans

For scans with 100+ hosts and many technologies:
- Consider `group_by: technology` (fewer files)
- Use `include_technologies` to focus on priorities
- Enable `upload_to_drive: false` if not needed

## FAQ

**Q: Can I use private git repositories?**
A: Yes, use SSH URLs and configure SSH keys, or use HTTPS with credentials.

**Q: How do I update templates?**
A: Delete cache directory or use `git pull` in cache directory. BBOT auto-updates on scan start.

**Q: Can I use multiple template repositories?**
A: Not directly, but you can combine templates in one repository.

**Q: What if a technology has no matching template?**
A: BBOT uses the fallback template (usually `web/default.md`).

**Q: Can I disable methodology generation temporarily?**
A: Yes, don't include `recon_methodology` in output modules.

**Q: Do I need internet access?**
A: Only for cloning remote repositories. Use `file://` URLs for offline work.

**Q: Can I contribute templates back?**
A: Yes! Fork the repository, add templates, and submit a pull request.

## Related Documentation

- [Google Drive Integration](./google_drive_integration.md)
- [Discord Integration](./discord.md)
- [Output Modules Overview](./output.md)
- [Creating Custom Modules](../dev/module_howto.md)

## Support

- **Template Repository**: [bbot-recon-templates](https://github.com/blacklanternsecurity/bbot-recon-templates)
- **Issues**: [GitHub Issues](https://github.com/blacklanternsecurity/bbot/issues)
- **Discord**: [BBOT Community](https://discord.com/invite/PZqkgxu5SA)
