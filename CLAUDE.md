# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**BBOT (BEE·bot)** is a recursive, event-driven OSINT automation framework for reconnaissance, bug bounties, and attack surface management (ASM). Built in Python 3.9+, BBOT is inspired by Spiderfoot and features 100+ modules that recursively discover and enumerate targets.

**Critical:** This is a defensive security tool for authorized security testing, vulnerability research, and attack surface management only.

## Architecture

### Event-Driven Recursive System

BBOT's core philosophy is **recursive, event-driven discovery**. Modules consume Events, discover new information, and produce new Events that feed other modules. This creates a recursive web of discovery where enabling a single module can exponentially increase results.

Key components:

- **Scanner** (`bbot/scanner/scanner.py`): Main scan orchestration, manages module lifecycle and event flow
- **Events** (`bbot/core/event/base.py`): Data containers (DNS_NAME, IP_ADDRESS, URL, etc.) that flow between modules
- **Modules** (`bbot/modules/`): Self-contained discovery units that consume and produce events
- **Presets** (`bbot/presets/`): YAML configurations that combine modules for specific scan types
- **Engine** (`bbot/core/engine.py`): Event distribution and module execution coordination
- **Helpers** (`bbot/core/helpers/`): Reusable utilities (DNS, HTTP, command execution, etc.)

### Module Architecture

Modules inherit from `BaseModule` (`bbot/modules/base.py`) and define:

- `watched_events`: Event types to consume (e.g., `["DNS_NAME"]`)
- `produced_events`: Event types to produce (e.g., `["URL"]`)
- `flags`: Module classification (`passive`/`active`, `safe`/`aggressive`)
- `handle_event()`: Main logic that processes events
- `setup()`: One-time initialization (API key validation, dependency checks)

Example module structure:
```python
class mymodule(BaseModule):
    watched_events = ["DNS_NAME"]
    produced_events = ["URL"]
    flags = ["passive", "safe"]
    options = {"api_key": ""}

    async def setup(self):
        # Validate config, return None/"reason" to soft-fail
        return True

    async def handle_event(self, event):
        # Process event.data, discover new information
        await self.emit_event(new_data, "URL", parent=event)
```

### Directory Structure

```
bbot/
├── core/              # Core engine, event system, configuration
│   ├── event/         # Event base classes and helpers
│   ├── helpers/       # DNS, web, command, file utilities
│   │   ├── dns/       # DNS resolution, brute-forcing
│   │   ├── web/       # HTTP client, SSL handling
│   │   └── depsinstaller/ # Ansible-based dependency installation
│   ├── config/        # Configuration and logging
│   ├── engine.py      # Event distribution engine
│   └── modules.py     # Module loading and management
├── scanner/           # Scan orchestration
│   ├── scanner.py     # Main Scanner class
│   ├── preset/        # Preset system
│   ├── target.py      # Target parsing and scope management
│   └── manager.py     # Event ingress/egress management
├── modules/           # 100+ scan modules (subdomains, ports, APIs, etc.)
├── presets/           # YAML preset configurations
├── db/                # Database models (SQL output)
├── test/              # Pytest test suite
├── cli.py             # Command-line interface
└── defaults.yml       # Default configuration values
```

## Development Setup

### Installation with Poetry

```bash
# Clone and setup
git clone git@github.com/<username>/bbot.git
cd bbot

# Install poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies and pre-commit hooks
poetry install
poetry run pre-commit install

# Enter virtual environment
poetry shell
bbot --help
```

### Running Tests

```bash
# Format code
ruff format

# Lint code
ruff check

# Run all tests
./bbot/test/run_tests.sh

# Run specific module tests
./bbot/test/run_tests.sh test_module_name
```

Tests use pytest with async support. Key test settings in `pyproject.toml`:
- `BBOT_TESTING=True` environment variable
- `asyncio_mode = "auto"` for async tests
- Coverage reporting enabled

## Common Commands

### Basic Scanning

```bash
# Subdomain enumeration (passive + DNS brute-force)
bbot -t evilcorp.com -p subdomain-enum

# Web spidering
bbot -t evilcorp.com -p spider

# Comprehensive scan (all modules)
bbot -t evilcorp.com -p kitchen-sink --allow-deadly

# Run specific modules
bbot -t evilcorp.com -m subfinder httpx nuclei

# Multiple targets
bbot -t evilcorp.com evilcorp.org 1.2.3.0/24 -p subdomain-enum

# Custom output directory
bbot -t evilcorp.com -p subdomain-enum -o /path/to/output
```

### Python API

Synchronous:
```python
from bbot.scanner import Scanner

scan = Scanner("evilcorp.com", presets=["subdomain-enum"])
for event in scan.start():
    print(event)
```

Asynchronous:
```python
from bbot.scanner import Scanner

async def main():
    scan = Scanner("evilcorp.com", presets=["subdomain-enum"])
    async for event in scan.async_start():
        print(event.json())
```

### Configuration

Config priority: CLI args > `~/.config/bbot/bbot.yml` > defaults in `bbot/defaults.yml`

Set API keys in `~/.config/bbot/bbot.yml`:
```yaml
modules:
  shodan_dns:
    api_key: your_key_here
  virustotal:
    api_key: your_key_here
```

Or via CLI:
```bash
bbot -c modules.virustotal.api_key=YOUR_KEY -t evilcorp.com -m virustotal
```

## Writing a Module

1. Create `bbot/modules/mymodule.py`
2. Inherit from `BaseModule`
3. Define `watched_events`, `produced_events`, `flags`
4. Implement `handle_event()` method
5. Class name must match filename (case-insensitive)

Testing:
```bash
bbot -t evilcorp.com -m mymodule
```

### Module Class Attributes

- `watched_events`: List of event types to consume
- `produced_events`: List of event types to produce
- `flags`: `["passive"/"active", "safe"/"aggressive"]` (required)
- `meta`: `{"description": "...", "auth_required": bool}`
- `options`: `{"option_name": default_value}`
- `options_desc`: `{"option_name": "Description"}`
- `deps_pip`: Python dependencies
- `deps_apt`: APT package dependencies
- `deps_shell`: Shell command dependencies
- `deps_ansible`: Ansible task dependencies
- `per_domain_only`: Run once per domain (bool)
- `per_host_only`: Run once per host (bool)
- `scope_distance_modifier`: Modify scope acceptance (int)

### Module Methods

- `async def setup()`: One-time initialization, return `True`/`None`/`False`
- `async def handle_event(event)`: Main logic, called for each watched event
- `async def handle_batch(events)`: Batch processing (set `batch_size > 1`)
- `async def filter_event(event)`: Pre-filter events before handle_event
- `async def cleanup()`: Cleanup resources after scan

### Helper Methods

- `self.helpers.request(url)`: HTTP request
- `self.helpers.dns.resolve(domain)`: DNS resolution
- `self.helpers.run(command)`: Execute shell command
- `await self.emit_event(data, type, parent)`: Emit new event
- `self.hugesuccess()`, `self.hugeinfo()`, `self.hugewarning()`: Colored logging

## Event System

Event types include: `DNS_NAME`, `IP_ADDRESS`, `OPEN_TCP_PORT`, `URL`, `HTTP_RESPONSE`, `VULNERABILITY`, `EMAIL_ADDRESS`, `TECHNOLOGY`, `FINDING`, etc.

Event attributes:
- `event.data`: Main data (string or dict)
- `event.type`: Event type
- `event.host`: Associated host/IP
- `event.scope_distance`: Hops from target (0 = in-scope)
- `event.parent`: Parent event that discovered this
- `event.module`: Module that created the event
- `event.tags`: Set of descriptive tags

## Presets

Presets are YAML files in `bbot/presets/` that define module combinations:

```yaml
description: Quick subdomain enumeration

flags:
  - subdomain-enum  # Enable all modules with this flag

output_modules:
  - subdomains  # Output unique subdomains to file

config:
  dns:
    threads: 25
  modules:
    github:
      api_key: ""
```

Include other presets:
```yaml
include:
  - subdomain-enum
  - web-basic
```

## Configuration System

Key config sections in `bbot/defaults.yml`:

- `home`: BBOT working directory (`~/.bbot`)
- `scope`: Scope strictness and search distance
- `dns`: DNS resolution, brute-forcing, wildcard detection
- `web`: HTTP settings (proxy, user-agent, spider limits)
- `modules`: Per-module configuration

Important DNS settings:
- `dns.threads`: Concurrent DNS resolution (default: 25)
- `dns.brute_threads`: Massdns brute-force threads (default: 1000)
- `dns.search_distance`: DNS resolution depth (default: 1)
- `dns.wildcard_tests`: Wildcard detection tests (default: 10)

Web spidering:
- `web.spider_distance`: How many links to follow (default: 0)
- `web.spider_depth`: Max directory depth (default: 4)

## Code Quality

- **Formatter**: Ruff (`ruff format`)
- **Linter**: Ruff (`ruff check`)
- **Line length**: 119 characters
- **Pre-commit hooks**: Auto-format, linting, validation
- **Test coverage**: Pytest with coverage reporting

## Git Workflow

- Main branch: `stable`
- Development branch: `dev`
- PRs should target `dev` branch
- Pre-commit hooks enforce formatting/linting
- All tests must pass before merge

## Key Design Patterns

### Scope Management

BBOT uses `scope_distance` to track event proximity to targets:
- `0` = in-scope (exact target)
- `1` = one hop away (subdomain of target domain)
- `2+` = multiple hops away

Modules can set `scope_distance_modifier` to accept events further from scope.

### Dependency Installation

BBOT auto-installs dependencies using Ansible:
- `deps_pip`: Python packages via pip
- `deps_apt`: System packages via apt
- `deps_shell`: Shell commands
- `deps_ansible`: Full Ansible playbooks

Dependencies are checked/installed at scan start.

### Event Flow Control

- `accept_dupes`: Accept duplicate incoming events (default: False)
- `suppress_dupes`: Suppress duplicate outgoing events (default: True)
- `_qsize`: Outgoing event queue size (default: 1000)
- `_priority`: Module priority, lower = higher priority (default: 3)

### Module Threading

- `module_threads`: Max concurrent `handle_event()` calls (default: 1)
- `batch_size`: Events per `handle_batch()` call (default: 1)

## Important Notes

- BBOT scans can be **very noisy** - always obtain authorization
- Use `-p subdomain-enum -rf passive` for passive-only reconnaissance
- The `--allow-deadly` flag enables potentially dangerous modules
- Output is in `~/.bbot/scans/<scan_name>/` by default
- Events are deduplicated by hash of (type + data)
- Wildcard DNS detection prevents runaway subdomain discovery

## Documentation

- Full docs: https://www.blacklanternsecurity.com/bbot/
- Module writing guide: https://www.blacklanternsecurity.com/bbot/Stable/dev/module_howto
- Discord: https://discord.com/invite/PZqkgxu5SA
