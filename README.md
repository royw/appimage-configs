# AppImage Configs

A repository of pre-configured application metadata for use with [appimage-updater](https://github.com/royw/appimage-updater).

## Overview

This repository contains JSON configuration files that define how to download and update various AppImage applications. The repository stores **only metadata** — the actual AppImage files are downloaded directly from their upstream sources (GitHub, GitLab, SourceForge, etc.).

## Usage

With `appimage-updater` configured to use this repository:

```bash
# Install an app by name
appimage-updater add OrcaSlicer

# List available apps
appimage-updater list --available

# Update config to latest version from repo
appimage-updater update OrcaSlicer
```

## Repository Structure

```text
configs/
├── OrcaSlicer.json
├── FreeCAD.json
├── Inkscape.json
└── ...
```

Each `.json` file contains the configuration needed to download and update that application.

## Configuration Schema

Each config file follows this structure:

```json
{
  "name": "AppName",
  "url": "https://github.com/owner/repo",
  "pattern": "(?i)AppName.*\\.AppImage$",
  "download_dir": "/path/to/downloads",
  "symlink_dir": "/path/to/symlinks",
  "prerelease": false,
  "rotation": 2
}
```

### Required Fields

| Field | Description |
|-------|-------------|
| `name` | Application name (must match filename) |
| `url` | Repository URL (GitHub, GitLab, SourceForge) |
| `pattern` | Regex pattern to match AppImage assets |
| `download_dir` | Directory for downloaded AppImages |

### Optional Fields

| Field | Default | Description |
|-------|---------|-------------|
| `symlink_dir` | none | Directory for version-less symlinks |
| `prerelease` | `false` | Include prerelease/nightly builds |
| `rotation` | `0` | Number of old versions to keep |
| `checksum` | `false` | Verify checksums if available |
| `basename` | auto | Override base filename |

## Contributing

To add a new application:

1. Fork this repository
2. Create `configs/AppName.json` with the required fields
3. Test with `appimage-updater` to verify it works
4. Submit a pull request

### Guidelines

- Use the exact application name as the filename
- Test the pattern against actual release assets
- Set `prerelease: true` only for nightly/development builds
- Include only actively maintained applications

## License

MIT License - See [LICENSE](LICENSE) for details.

## Related

- [appimage-updater](https://github.com/royw/appimage-updater) - The CLI tool that uses these configs
- [AppImage](https://appimage.org/) - Linux app distribution format
