# sub-attachment-extract

Extract attachments from MKV files and organize them into categorized directories.

## Description

`sub-attachment-extract` extracts all attachments (fonts, cover images, and other files) from MKV files and organizes them into `Covers/`, `Fonts/`, and `Others/` directories based on their MIME types.

## Features

- Automatic categorization into Covers, Fonts, and Others directories
- Parallel processing support
- Skips duplicate files (by filename)
- Dry-run mode for preview
- Detailed extraction statistics

## Requirements

### System Dependencies

- **mkvmerge** (from MKVToolNix) - for identifying attachments
- **mkvextract** (from MKVToolNix) - for extracting attachments

### Python Dependencies

None (uses only standard library).

## Installation

1. Install MKVToolNix:

   ```bash
   # Arch Linux
   sudo pacman -S mkvtoolnix-cli

   # Ubuntu/Debian
   sudo apt install mkvtoolnix

   # macOS
   brew install mkvtoolnix
   ```

2. Make the script executable:

   ```bash
   chmod +x sub-attachment-extract.py
   ```

## Usage

```bash
# Extract from all MKVs in current directory
sub-attachment-extract.py

# Extract from a specific directory
sub-attachment-extract.py /path/to/videos

# Extract from a single MKV file
sub-attachment-extract.py Movie.mkv

# Use 8 parallel workers
sub-attachment-extract.py -p 8

# Specify output directory
sub-attachment-extract.py -o /path/to/output

# Preview without extracting
sub-attachment-extract.py --dry-run

# Quiet mode (suppress verbose output)
sub-attachment-extract.py -q
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `path` | MKV file, directory containing MKVs, or current directory if omitted |
| `--dry-run` | Show what would be extracted without actually extracting files |
| `-q, --quiet` | Suppress verbose output |
| `-p, --parallel N` | Number of parallel workers (default: 4) |
| `-o, --output DIR` | Output directory for extracted attachments (must exist) |

## Output Structure

```
output_directory/
├── Covers/     # Cover images (JPEG, PNG, etc.)
├── Fonts/      # Font files (TTF, OTF, TTC, WOFF, WOFF2)
└── Others/     # Other attachments
```

## Categorization Rules

### Fonts

- MIME types starting with `font/`
- MIME types: `application/vnd.ms-opentype`, `application/x-font-otf`, `application/x-font-ttf`, `application/x-truetype-font`
- File extensions: `.ttf`, `.otf`, `.ttc`, `.woff`, `.woff2`

### Covers

- MIME types starting with `image/`
- File extensions: `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tif`, `.tiff`
- Filenames containing "cover" or "poster"

### Others

- All other attachments
