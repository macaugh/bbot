"""
Basic syntax and import tests for new output modules
These tests verify the modules can be imported and have correct structure
"""

import pytest
import importlib


class TestOutputModulesSyntax:
    """Test that new output modules have correct syntax and structure"""

    def test_google_drive_imports(self):
        """Test google_drive module can be imported"""
        try:
            from bbot.modules.output import google_drive
            assert google_drive is not None
            assert hasattr(google_drive, "GoogleDrive")
        except ImportError as e:
            pytest.fail(f"Failed to import google_drive module: {e}")

    def test_google_drive_class_structure(self):
        """Test GoogleDrive class has required attributes"""
        from bbot.modules.output.google_drive import GoogleDrive

        # Check class attributes
        assert hasattr(GoogleDrive, "watched_events")
        assert hasattr(GoogleDrive, "meta")
        assert hasattr(GoogleDrive, "options")
        assert hasattr(GoogleDrive, "options_desc")
        assert hasattr(GoogleDrive, "deps_pip")

        # Check watched events includes FINISHED
        assert "FINISHED" in GoogleDrive.watched_events

        # Check required methods exist
        assert hasattr(GoogleDrive, "setup")
        assert hasattr(GoogleDrive, "handle_event")

    def test_recon_methodology_imports(self):
        """Test recon_methodology module can be imported"""
        try:
            from bbot.modules.output import recon_methodology
            assert recon_methodology is not None
            assert hasattr(recon_methodology, "ReconMethodology")
        except ImportError as e:
            pytest.fail(f"Failed to import recon_methodology module: {e}")

    def test_recon_methodology_class_structure(self):
        """Test ReconMethodology class has required attributes"""
        from bbot.modules.output.recon_methodology import ReconMethodology

        # Check class attributes
        assert hasattr(ReconMethodology, "watched_events")
        assert hasattr(ReconMethodology, "meta")
        assert hasattr(ReconMethodology, "options")
        assert hasattr(ReconMethodology, "options_desc")
        assert hasattr(ReconMethodology, "deps_pip")

        # Check watches all events
        assert "*" in ReconMethodology.watched_events

        # Check required methods exist
        assert hasattr(ReconMethodology, "setup")
        assert hasattr(ReconMethodology, "handle_event")
        assert hasattr(ReconMethodology, "report")

    def test_recon_methodology_template_loader(self):
        """Test TemplateLoader class exists and has required methods"""
        from bbot.modules.output.recon_methodology import TemplateLoader

        assert hasattr(TemplateLoader, "__init__")
        assert hasattr(TemplateLoader, "initialize")
        assert hasattr(TemplateLoader, "get_template")

    def test_discord_enhanced(self):
        """Test Discord module still works after enhancements"""
        from bbot.modules.output.discord import Discord

        # Check class still has original attributes
        assert hasattr(Discord, "watched_events")
        assert hasattr(Discord, "options")

        # Check new options were added
        assert "include_scan_summary" in Discord.options
        assert "include_drive_links" in Discord.options

        # Check new method exists
        assert hasattr(Discord, "_post_scan_summary")

    def test_module_metadata(self):
        """Test modules have proper metadata"""
        from bbot.modules.output.google_drive import GoogleDrive
        from bbot.modules.output.recon_methodology import ReconMethodology

        # Check GoogleDrive metadata
        assert "description" in GoogleDrive.meta
        assert "created_date" in GoogleDrive.meta
        assert "author" in GoogleDrive.meta

        # Check ReconMethodology metadata
        assert "description" in ReconMethodology.meta
        assert "created_date" in ReconMethodology.meta
        assert "author" in ReconMethodology.meta

    def test_configuration_options(self):
        """Test modules have documented configuration options"""
        from bbot.modules.output.google_drive import GoogleDrive
        from bbot.modules.output.recon_methodology import ReconMethodology

        # GoogleDrive should have credentials_file option
        assert "credentials_file" in GoogleDrive.options
        assert "credentials_file" in GoogleDrive.options_desc

        # ReconMethodology should have template_repo_url option
        assert "template_repo_url" in ReconMethodology.options
        assert "template_repo_url" in ReconMethodology.options_desc

    def test_dependencies_declared(self):
        """Test modules declare their pip dependencies"""
        from bbot.modules.output.google_drive import GoogleDrive
        from bbot.modules.output.recon_methodology import ReconMethodology

        # GoogleDrive should have Google API dependencies
        assert len(GoogleDrive.deps_pip) > 0
        assert any("google" in dep.lower() for dep in GoogleDrive.deps_pip)

        # ReconMethodology should have gitpython and jinja2
        assert len(ReconMethodology.deps_pip) > 0
        assert any("git" in dep.lower() for dep in ReconMethodology.deps_pip)
        assert any("jinja" in dep.lower() for dep in ReconMethodology.deps_pip)
