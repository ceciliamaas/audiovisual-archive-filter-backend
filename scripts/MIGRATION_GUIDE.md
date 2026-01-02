# Storj Bucket Migration Guide

This guide helps you unify two Storj buckets into one with a homogeneous structure according to the project's naming conventions.

## Overview

The migration script will:

1. ✅ List all files from both source buckets
2. ✅ Analyze their structure and categorize them (videos, frames, objects, embeddings)
3. ✅ Normalize file paths according to `naming.py` conventions
4. ✅ Copy them to a unified target bucket
5. ✅ Provide detailed logs and statistics

## Expected Structure

After migration, your unified bucket will have this structure:

```
unified-bucket/
├── videos/
│   ├── video_name_1.mp4
│   └── video_name_2.mp4
├── frames/
│   ├── video_name_1/
│   │   ├── frame_00000.jpg
│   │   ├── frame_00001.jpg
│   │   └── ...
│   └── video_name_2/
│       └── ...
├── objects/
│   ├── video_name_1/
│   │   ├── frame_00000_obj_000.jpg
│   │   ├── frame_00000_obj_001.jpg
│   │   └── ...
│   └── video_name_2/
│       └── ...
└── embeddings/
    ├── frame_embeddings.pkl
    ├── frame_paths.pkl
    ├── object_embeddings.pkl
    └── object_paths.pkl
```

## Prerequisites

1. **Install dependencies** (if not already):

   ```bash
   pip install boto3
   ```

2. **Configure credentials** in `.env`:
   ```bash
   STORJ_ENDPOINT=https://gateway.storjshare.io
   STORJ_ACCESS_KEY=your-access-key
   STORJ_SECRET_KEY=your-secret-key
   ```

## Usage

### Step 1: Dry Run (Recommended)

First, run in dry-run mode to see what would happen without making changes:

```bash
python scripts/migrate_storj_buckets.py \
    --source-bucket-1 old-bucket-1 \
    --source-bucket-2 old-bucket-2 \
    --target-bucket unified-bucket \
    --dry-run
```

This will:

- Show you all the file mappings
- Display statistics about what will be migrated
- **NOT** make any actual changes

### Step 2: Review the Output

The script will show:

- Total number of files in each bucket
- Categorization (videos, frames, objects, embeddings, unknown)
- Mapping of old paths → new paths
- Any files that cannot be normalized (will be skipped)

Example output:

```
================================================================================
Migrating from old-bucket-1 to unified-bucket
Dry run: True
================================================================================

Found 1,234 objects in old-bucket-1

Source bucket structure:
  videos: 5 items
  frames: 800 items
  objects: 400 items
  embeddings: 4 items
  unknown: 25 items

[DRY RUN] Would copy: old-bucket-1/videos/my_video.mp4 -> unified-bucket/videos/my_video.mp4
[DRY RUN] Would copy: old-bucket-1/frames/my_video/frame_1.jpg -> unified-bucket/frames/my_video/frame_00001.jpg
...
```

### Step 3: Execute Migration

Once you're satisfied with the dry run, execute the actual migration:

```bash
python scripts/migrate_storj_buckets.py \
    --source-bucket-1 old-bucket-1 \
    --source-bucket-2 old-bucket-2 \
    --target-bucket unified-bucket \
    --execute
```

**⚠️ Important:** This will copy files to the target bucket. Original buckets remain unchanged.

## Advanced Options

### Custom Credentials

Override credentials from command line:

```bash
python scripts/migrate_storj_buckets.py \
    --source-bucket-1 old-bucket-1 \
    --source-bucket-2 old-bucket-2 \
    --target-bucket unified-bucket \
    --endpoint-url https://gateway.storjshare.io \
    --access-key YOUR_ACCESS_KEY \
    --secret-key YOUR_SECRET_KEY \
    --execute
```

### Video Name Mapping

If you want to rename videos during migration, modify the script to include a mapping:

```python
video_name_mapping = {
    'old_video_name': 'new_video_name',
    'another_old': 'another_new',
}

stats = migration.migrate_bucket(
    source_bucket,
    target_bucket,
    video_name_mapping=video_name_mapping,
    dry_run=dry_run
)
```

## Naming Conventions

The script follows these conventions from `scripts/pipeline/naming.py`:

### Videos

- **Format**: `videos/{video_name}.mp4`
- **Example**: `videos/reconstruccion_jonathan.mp4`

### Frames

- **Format**: `frames/{video_name}/frame_{index:05d}.jpg`
- **Example**: `frames/reconstruccion_jonathan/frame_00042.jpg`

### Objects

- **Format**: `objects/{video_name}/frame_{frame_idx:05d}_obj_{obj_idx:03d}.jpg`
- **Example**: `objects/reconstruccion_jonathan/frame_00042_obj_003.jpg`

### Embeddings

- **Files**:
  - `embeddings/frame_embeddings.pkl`
  - `embeddings/frame_paths.pkl`
  - `embeddings/object_embeddings.pkl`
  - `embeddings/object_paths.pkl`

### Video Names

- Automatically sanitized to be filesystem-safe:
  - Spaces → underscores
  - Special characters removed
  - Lowercase
  - No leading/trailing underscores

## Troubleshooting

### Files Marked as "unknown"

If files appear in the "unknown" category, they don't match expected patterns. Check:

- Are they using non-standard naming?
- Are they metadata files that should be excluded?
- Do they need manual handling?

### Files Cannot Be Normalized

Some files might not be auto-normalized. For these, you have options:

1. Manually organize them after migration
2. Update the `normalize_key()` function in the script
3. Skip them (they'll be logged)

### Migration Fails Midway

The script uses S3's copy operation, which is atomic per file. If it fails:

- Check the logs to see which files succeeded
- The script can be re-run (it will copy everything again, S3 will overwrite)
- Consider running for one bucket at a time

### Different File Formats

If your frames/objects use different formats (e.g., `.png` instead of `.jpg`):

1. Modify the script's parsing logic
2. Or convert them before/after migration

## Post-Migration

After successful migration:

1. **Verify the structure:**

   ```bash
   # List a sample of files
   aws s3 ls s3://unified-bucket/videos/ --endpoint-url=https://gateway.storjshare.io
   aws s3 ls s3://unified-bucket/frames/ --endpoint-url=https://gateway.storjshare.io
   ```

2. **Update your application configuration:**

   - Update `STORJ_BUCKET_NAME` in `.env` to point to the new unified bucket
   - Test that the application can read from the new bucket

3. **Test the application:**

   ```bash
   python main.py
   ```

   - Try searching for frames/objects
   - Verify embeddings load correctly

4. **Keep backups:**

   - Don't delete original buckets until you've verified everything works
   - Storj charges for storage, so plan accordingly

5. **Clean up old buckets** (optional):
   ```bash
   # After verifying everything works
   aws s3 rb s3://old-bucket-1 --force --endpoint-url=https://gateway.storjshare.io
   aws s3 rb s3://old-bucket-2 --force --endpoint-url=https://gateway.storjshare.io
   ```

## Cost Considerations

- **Egress**: Reading from source buckets may incur egress charges
- **Storage**: Target bucket will duplicate data during migration
- **Operations**: S3 API calls (copy, list) may have costs
- **Recommendation**: Keep the migration window short and delete old buckets once verified

## Example Workflow

```bash
# 1. Dry run to preview
python scripts/migrate_storj_buckets.py \
    --source-bucket-1 archive-old \
    --source-bucket-2 archive-backup \
    --target-bucket archive-unified \
    --dry-run

# 2. Review output, verify mappings look correct

# 3. Execute migration
python scripts/migrate_storj_buckets.py \
    --source-bucket-1 archive-old \
    --source-bucket-2 archive-backup \
    --target-bucket archive-unified \
    --execute

# 4. Update .env
# STORJ_BUCKET_NAME=archive-unified

# 5. Test application
python main.py

# 6. Verify search works correctly

# 7. Delete old buckets (after confirming everything works)
```

## Support

If you encounter issues:

1. Check the logs for detailed error messages
2. Verify credentials and bucket permissions
3. Test with a small subset first (manually copy a few files)
4. Review the naming conventions in `scripts/pipeline/naming.py`
