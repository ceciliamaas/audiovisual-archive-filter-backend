# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Image similarity search**: Users can now search the archive by uploading reference images
  - Upload custom images or select from example images
  - Uses CLIP embeddings for visual similarity matching
  - Searches both frames and detected objects
  - Results ranked by similarity score
- Image search UI in the search interface with file uploader and example images
- `SearchEngine.compute_image_embedding()` method for computing CLIP embeddings from images
- `SearchEngine.search_by_image()` method for performing image-based similarity search
- Documentation for image search feature in `docs/IMAGE_SEARCH.md`
- Test suite for image search in `tests/test_image_search.py`

### Changed

- Updated search interface to enable image search mode
- Enhanced results display to show appropriate headers for text vs image queries
- Improved `compute_image_embedding()` to properly handle image files with Replicate API
- Updated README with image search feature information

### Fixed

- Image path handling in `_render_image_search()` to properly maintain selected images
- Example image selection workflow with session state management

## [Previous Versions]

For changes in previous versions, see Git history.
