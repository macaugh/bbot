import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from .base import ModuleTestBase


class TestReconMethodology(ModuleTestBase):
    """Test Recon Methodology output module"""

    targets = ["example.com"]
    modules_overrides = ["httpx", "wappalyzer"]
    config_overrides = {
        "modules": {
            "recon_methodology": {
                "template_repo_url": "",  # Will be set in setup
                "group_by": "host",
            }
        }
    }

    async def setup_before_prep(self, module_test):
        """Setup mock template repository"""
        # Create temporary template repository
        self.temp_repo = tempfile.mkdtemp()
        repo_path = Path(self.temp_repo)

        # Create config.yml
        config_content = """
templates:
  mapping:
    - pattern: "(?i)wordpress"
      template: "web/wordpress.md"
      category: "cms"
    - pattern: "(?i)apache"
      template: "web/apache.md"
      category: "web"
  fallbacks:
    web: "web/default.md"
    default: "web/default.md"

variables:
  required:
    - host
    - technology
    - scan_date
  optional:
    - url
    - version
"""
        (repo_path / "config.yml").write_text(config_content)

        # Create templates directory
        templates_dir = repo_path / "templates" / "web"
        templates_dir.mkdir(parents=True)

        # Create WordPress template
        wordpress_template = """# WordPress Reconnaissance: {{ host }}

**Scan Date**: {{ scan_date }}
**WordPress Version**: {{ version or "Unknown" }}
**URL**: {{ url }}

## Automated Findings

### Detected Vulnerabilities
{% if vulnerabilities %}
{% for vuln in vulnerabilities %}
- **{{ vuln.severity }}**: {{ vuln.description }}
{% endfor %}
{% else %}
- No vulnerabilities detected
{% endif %}

## Manual Testing Checklist
- [ ] Enumerate plugins
- [ ] Test admin panel
- [ ] Check for known vulnerabilities
"""
        (templates_dir / "wordpress.md").write_text(wordpress_template)

        # Create Apache template
        apache_template = """# Apache Reconnaissance: {{ host }}

**Scan Date**: {{ scan_date }}
**URL**: {{ url }}

## Manual Testing Checklist
- [ ] Check server version
- [ ] Test for directory listing
- [ ] Review security headers
"""
        (templates_dir / "apache.md").write_text(apache_template)

        # Create default template
        default_template = """# Web Application Reconnaissance: {{ host }}

**Technology**: {{ technology }}
**Scan Date**: {{ scan_date }}

## Manual Testing Checklist
- [ ] Test authentication
- [ ] Check for XSS
- [ ] Test for SQL injection
"""
        (templates_dir / "default.md").write_text(default_template)

        # Update config to use file:// URL
        module_test.scan.config.modules.recon_methodology.template_repo_url = f"file://{repo_path}"

    async def setup_after_prep(self, module_test):
        """Inject test events to trigger methodology generation"""
        # We'll inject events during the scan via module hooks
        pass

    def check(self, module_test, events):
        """Verify methodology files were generated"""
        methodology_dir = module_test.scan.home / "methodology"

        # Check that methodology directory was created
        assert methodology_dir.exists(), "Methodology directory not created"

        # Check for generated markdown files
        md_files = list(methodology_dir.glob("*.md"))
        assert len(md_files) > 0, "No methodology files generated"

        # Verify file content contains expected elements
        for md_file in md_files:
            content = md_file.read_text()
            assert "Reconnaissance" in content, f"File {md_file.name} missing 'Reconnaissance' header"
            assert "Manual Testing Checklist" in content, f"File {md_file.name} missing checklist section"
            assert "example.com" in content, f"File {md_file.name} missing hostname"


class TestReconMethodology_WordPress(ModuleTestBase):
    """Test WordPress-specific methodology generation"""

    targets = ["wordpress.example.com"]
    modules_overrides = []  # Minimal modules
    config_overrides = {
        "modules": {
            "recon_methodology": {
                "template_repo_url": "",
                "group_by": "host",
            }
        }
    }

    async def setup_before_prep(self, module_test):
        """Setup template repository"""
        self.temp_repo = tempfile.mkdtemp()
        repo_path = Path(self.temp_repo)

        # Create config
        config_content = """
templates:
  mapping:
    - pattern: "(?i)wordpress"
      template: "web/wordpress.md"
      category: "cms"
  fallbacks:
    default: "web/default.md"
"""
        (repo_path / "config.yml").write_text(config_content)

        # Create WordPress template with variables
        templates_dir = repo_path / "templates" / "web"
        templates_dir.mkdir(parents=True)

        wordpress_template = """# WordPress: {{ host }}

**Version**: {{ version or "Unknown" }}
**URL**: {{ url }}

## Vulnerabilities
{% if vulnerabilities %}
{% for vuln in vulnerabilities %}
- {{ vuln.severity }}: {{ vuln.description }}
{% endfor %}
{% endif %}

## Checklist
- [ ] Test wp-admin
- [ ] Enumerate plugins
"""
        (templates_dir / "wordpress.md").write_text(wordpress_template)

        default_template = """# Default: {{ host }}

**Technology**: {{ technology }}
"""
        (templates_dir / "default.md").write_text(default_template)

        module_test.scan.config.modules.recon_methodology.template_repo_url = f"file://{repo_path}"

    async def setup_after_prep(self, module_test):
        """Inject WordPress TECHNOLOGY event"""
        # Get the recon_methodology module
        recon_module = None
        for mod in module_test.scan.modules.values():
            if mod.__class__.__name__ == "ReconMethodology":
                recon_module = mod
                break

        if recon_module:
            # Simulate technology detection
            from bbot.core.event import make_event

            # Create mock events
            tech_event = make_event(
                {"technology": "WordPress", "version": "6.2"},
                "TECHNOLOGY",
                module=module_test.scan.modules.get("httpx", list(module_test.scan.modules.values())[0]),
                scan=module_test.scan,
            )
            tech_event.host = "wordpress.example.com"

            url_event = make_event(
                "https://wordpress.example.com",
                "URL",
                module=module_test.scan.modules.get("httpx", list(module_test.scan.modules.values())[0]),
                scan=module_test.scan,
            )
            url_event.host = "wordpress.example.com"

            vuln_event = make_event(
                {"severity": "MEDIUM", "description": "WordPress plugin XYZ vulnerable"},
                "VULNERABILITY",
                module=module_test.scan.modules.get("httpx", list(module_test.scan.modules.values())[0]),
                scan=module_test.scan,
            )
            vuln_event.host = "wordpress.example.com"

            # Manually call handle_event
            await recon_module.handle_event(tech_event)
            await recon_module.handle_event(url_event)
            await recon_module.handle_event(vuln_event)

            # Trigger report generation
            await recon_module.report()

    def check(self, module_test, events):
        """Verify WordPress methodology was generated with correct content"""
        methodology_dir = module_test.scan.home / "methodology"
        assert methodology_dir.exists(), "Methodology directory not created"

        # Find WordPress methodology file
        wordpress_files = list(methodology_dir.glob("*WordPress*.md"))
        assert len(wordpress_files) > 0, "WordPress methodology file not found"

        wordpress_file = wordpress_files[0]
        content = wordpress_file.read_text()

        # Verify content
        assert "WordPress" in content, "Missing WordPress in content"
        assert "wordpress.example.com" in content, "Missing hostname"
        assert "wp-admin" in content, "Missing WordPress-specific checklist items"
        assert "Enumerate plugins" in content, "Missing plugin enumeration"


class TestReconMethodology_GroupByTechnology(ModuleTestBase):
    """Test grouping by technology instead of host"""

    targets = ["site1.example.com", "site2.example.com"]
    modules_overrides = []
    config_overrides = {
        "modules": {
            "recon_methodology": {
                "template_repo_url": "",
                "group_by": "technology",  # Group by tech, not host
            }
        }
    }

    async def setup_before_prep(self, module_test):
        """Setup template repository"""
        self.temp_repo = tempfile.mkdtemp()
        repo_path = Path(self.temp_repo)

        config_content = """
templates:
  mapping:
    - pattern: "(?i)nginx"
      template: "web/nginx.md"
  fallbacks:
    default: "web/default.md"
"""
        (repo_path / "config.yml").write_text(config_content)

        templates_dir = repo_path / "templates" / "web"
        templates_dir.mkdir(parents=True)

        nginx_template = """# Nginx: {{ technology }}

**Hosts**: {{ hosts | length if hosts else 0 }}

## Checklist
- [ ] Check Nginx version
"""
        (templates_dir / "nginx.md").write_text(nginx_template)

        (templates_dir / "default.md").write_text("# Default: {{ technology }}")

        module_test.scan.config.modules.recon_methodology.template_repo_url = f"file://{repo_path}"

    async def setup_after_prep(self, module_test):
        """Inject events for multiple hosts with same technology"""
        recon_module = None
        for mod in module_test.scan.modules.values():
            if mod.__class__.__name__ == "ReconMethodology":
                recon_module = mod
                break

        if recon_module:
            from bbot.core.event import make_event

            # Create Nginx tech events for both hosts
            for host in ["site1.example.com", "site2.example.com"]:
                tech_event = make_event(
                    {"technology": "Nginx", "version": "1.21"},
                    "TECHNOLOGY",
                    module=list(module_test.scan.modules.values())[0],
                    scan=module_test.scan,
                )
                tech_event.host = host

                url_event = make_event(
                    f"https://{host}",
                    "URL",
                    module=list(module_test.scan.modules.values())[0],
                    scan=module_test.scan,
                )
                url_event.host = host

                await recon_module.handle_event(tech_event)
                await recon_module.handle_event(url_event)

            await recon_module.report()

    def check(self, module_test, events):
        """Verify single methodology file for Nginx covering both hosts"""
        methodology_dir = module_test.scan.home / "methodology"
        assert methodology_dir.exists(), "Methodology directory not created"

        # Should have one Nginx methodology file (not per-host)
        nginx_files = list(methodology_dir.glob("*Nginx*.md"))
        assert len(nginx_files) == 1, f"Expected 1 Nginx file for both hosts, got {len(nginx_files)}"

        content = nginx_files[0].read_text()
        assert "Nginx" in content, "Missing Nginx in content"


class TestReconMethodology_IncludeExclude(ModuleTestBase):
    """Test include/exclude technology filters"""

    targets = ["example.com"]
    modules_overrides = []
    config_overrides = {
        "modules": {
            "recon_methodology": {
                "template_repo_url": "",
                "include_technologies": ["WordPress"],  # Only WordPress
                "exclude_technologies": ["Apache"],  # Exclude Apache
            }
        }
    }

    async def setup_before_prep(self, module_test):
        """Setup template repository"""
        self.temp_repo = tempfile.mkdtemp()
        repo_path = Path(self.temp_repo)

        config_content = """
templates:
  mapping:
    - pattern: "(?i)wordpress"
      template: "web/wordpress.md"
    - pattern: "(?i)apache"
      template: "web/apache.md"
    - pattern: "(?i)nginx"
      template: "web/nginx.md"
  fallbacks:
    default: "web/default.md"
"""
        (repo_path / "config.yml").write_text(config_content)

        templates_dir = repo_path / "templates" / "web"
        templates_dir.mkdir(parents=True)

        for tech in ["wordpress", "apache", "nginx", "default"]:
            (templates_dir / f"{tech}.md").write_text(f"# {tech.title()}: {{{{ host }}}}")

        module_test.scan.config.modules.recon_methodology.template_repo_url = f"file://{repo_path}"

    async def setup_after_prep(self, module_test):
        """Inject events for multiple technologies"""
        recon_module = None
        for mod in module_test.scan.modules.values():
            if mod.__class__.__name__ == "ReconMethodology":
                recon_module = mod
                break

        if recon_module:
            from bbot.core.event import make_event

            # Inject WordPress (should be included), Apache (excluded), Nginx (not in include)
            for tech in ["WordPress", "Apache", "Nginx"]:
                tech_event = make_event(
                    {"technology": tech},
                    "TECHNOLOGY",
                    module=list(module_test.scan.modules.values())[0],
                    scan=module_test.scan,
                )
                tech_event.host = "example.com"
                await recon_module.handle_event(tech_event)

            await recon_module.report()

    def check(self, module_test, events):
        """Verify only WordPress methodology was generated"""
        methodology_dir = module_test.scan.home / "methodology"
        assert methodology_dir.exists(), "Methodology directory not created"

        md_files = list(methodology_dir.glob("*.md"))

        # Should only have WordPress (included, not excluded)
        wordpress_files = [f for f in md_files if "WordPress" in f.name]
        assert len(wordpress_files) == 1, "WordPress methodology should exist"

        # Should NOT have Apache (excluded) or Nginx (not in include list)
        apache_files = [f for f in md_files if "Apache" in f.name]
        nginx_files = [f for f in md_files if "Nginx" in f.name]

        assert len(apache_files) == 0, "Apache methodology should not exist (excluded)"
        assert len(nginx_files) == 0, "Nginx methodology should not exist (not in include list)"


class TestReconMethodology_NoTemplateRepo(ModuleTestBase):
    """Test graceful handling when no template repository is configured"""

    targets = ["example.com"]
    modules_overrides = []
    config_overrides = {"modules": {"recon_methodology": {"template_repo_url": ""}}}  # No repo

    async def setup_after_prep(self, module_test):
        """No setup needed"""
        pass

    def check(self, module_test, events):
        """Verify module handles missing template repository gracefully"""
        methodology_dir = module_test.scan.home / "methodology"

        # Directory should be created but empty
        if methodology_dir.exists():
            md_files = list(methodology_dir.glob("*.md"))
            assert len(md_files) == 0, "No files should be generated without template repository"


class TestReconMethodology_TemplateFallback(ModuleTestBase):
    """Test fallback to default template for unknown technologies"""

    targets = ["example.com"]
    modules_overrides = []
    config_overrides = {"modules": {"recon_methodology": {"template_repo_url": ""}}}

    async def setup_before_prep(self, module_test):
        """Setup template repository with only default template"""
        self.temp_repo = tempfile.mkdtemp()
        repo_path = Path(self.temp_repo)

        config_content = """
templates:
  mapping: []  # No specific mappings
  fallbacks:
    web: "web/default.md"
    default: "web/default.md"
"""
        (repo_path / "config.yml").write_text(config_content)

        templates_dir = repo_path / "templates" / "web"
        templates_dir.mkdir(parents=True)

        default_template = """# {{ technology }}: {{ host }}

**Technology**: {{ technology }}

## Checklist
- [ ] Generic testing
"""
        (templates_dir / "default.md").write_text(default_template)

        module_test.scan.config.modules.recon_methodology.template_repo_url = f"file://{repo_path}"

    async def setup_after_prep(self, module_test):
        """Inject unknown technology event"""
        recon_module = None
        for mod in module_test.scan.modules.values():
            if mod.__class__.__name__ == "ReconMethodology":
                recon_module = mod
                break

        if recon_module:
            from bbot.core.event import make_event

            # Create event for unknown technology
            tech_event = make_event(
                {"technology": "UnknownFramework9000"},
                "TECHNOLOGY",
                module=list(module_test.scan.modules.values())[0],
                scan=module_test.scan,
            )
            tech_event.host = "example.com"
            await recon_module.handle_event(tech_event)

            await recon_module.report()

    def check(self, module_test, events):
        """Verify fallback template was used"""
        methodology_dir = module_test.scan.home / "methodology"
        assert methodology_dir.exists(), "Methodology directory not created"

        md_files = list(methodology_dir.glob("*.md"))
        assert len(md_files) > 0, "No methodology files generated (should use fallback)"

        # Check that file contains the unknown technology name
        content = md_files[0].read_text()
        assert "UnknownFramework9000" in content, "Fallback template should include technology name"
        assert "Generic testing" in content, "Fallback template content missing"
