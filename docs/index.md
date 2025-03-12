# CDP Browser Documentation

Welcome to the CDP Browser documentation. This guide will help you understand, install, and use the CDP Browser project.

## What is CDP Browser?

CDP Browser is a lightweight Python client for Chrome DevTools Protocol (CDP) that works on ARM64 architecture. It enables browser automation without Selenium dependencies, making it suitable for environments where traditional browser automation tools might not work.

## Documentation Sections

### Setup
- [Installation Guide](setup/installation.md): Instructions for setting up CDP Browser with Docker

### Architecture
- [Architecture Overview](architecture/overview.md): Technical design and components of CDP Browser

### Development
- [Project Plan](development/project-plan.md): Current status and roadmap
- [Requirements](development/requirements.md): Functional and technical requirements
- [Developer Notes](development/notes.md): Implementation details and findings
- [Research](development/research.md): Background research and technical investigations
- [Code Review](development/code-review.md): Code review feedback and improvements

### Stealth Mode
- [Stealth Implementation Plan](stealth/implementation-plan.md): Plan for implementing bot detection avoidance features

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/pjaol/cdp-browser.git
cd cdp-browser
```

2. Set up with Docker:
```bash
cd docker
docker build -t cdp-browser .
docker run -d -p 9223:9223 cdp-browser
```

3. Run a simple example:
```python
import asyncio
from cdp_browser.browser import Browser

async def main():
    async with Browser(port=9223) as browser:
        async with await browser.create_page() as page:
            await page.navigate("https://example.com")
            content = await page.get_content()
            print(content)

asyncio.run(main())
```

Refer to the [Installation Guide](setup/installation.md) for more detailed setup instructions. 