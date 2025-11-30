from pathlib import Path

# -----------------------------
# Configuration
# -----------------------------
FRAMES_DIR = Path("output_frames")  # Base directory containing the frames


# -----------------------------
# Rename Frames
# -----------------------------
def rename_frames():
    # Get all subdirectories (one for each video)
    video_folders = [folder for folder in FRAMES_DIR.iterdir() if folder.is_dir()]

    if not video_folders:
        print("No video folders found in output_frames.")
        return

    for video_index, video_folder in enumerate(sorted(video_folders), start=1):
        video_name = f"video_{video_index}"  # e.g., video_1, video_2, etc.
        print(f"Processing folder: {video_folder.name} -> Renaming to {video_name}")

        # Get all .jpg files in the current video folder
        frame_files = sorted(video_folder.glob("*.jpg"))

        for frame_index, frame_file in enumerate(frame_files, start=1):
            # Create the new filename
            new_name = f"{video_name}_frame_{frame_index:05d}.jpg"  # e.g., video_1_frame_00001.jpg
            new_path = video_folder / new_name

            # Rename the file
            frame_file.rename(new_path)
            print(f"Renamed: {frame_file.name} -> {new_name}")

    print("\nAll frames have been renamed.")


# -----------------------------
# Run the Script
# -----------------------------
if __name__ == "__main__":
    rename_frames()
