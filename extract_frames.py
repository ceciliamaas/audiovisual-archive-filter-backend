import cv2
from pathlib import Path


def extract_frames(video_path: str, output_dir: str, fps: int = 1):
    """
    Extract frames from a video at the specified FPS rate.
    Saves them as JPG files in output_dir.

    Args:
        video_path (str): Path to the video file.
        output_dir (str): Folder where frames will be saved.
        fps (int): How many frames per second to extract.
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # Load video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    if video_fps == 0:
        raise ValueError("The video FPS is zero. File may be corrupted.")

    # Extract 1 frame per second
    frame_interval = int(video_fps // fps)

    frame_index = 0
    saved_index = 0

    print(f"Extracting frames from: {video_path}")
    print(f"Video FPS: {video_fps}, capturing every {frame_interval} frames")

    while True:
        ret, frame = cap.read()
        if not ret:
            break  # End of video

        if frame_index % frame_interval == 0:
            frame_path = output / f"frame_{saved_index:05d}.jpg"
            cv2.imwrite(str(frame_path), frame)
            print(f"Saved: {frame_path}")
            saved_index += 1

        frame_index += 1

    cap.release()
    print(f"Done. Extracted {saved_index} frames.")


# run function
# List of video paths
video_paths = [
    "input_videos/Nueva marcha de jubilados en medio de un impresionante operativo de seguridad.mp4",
    "input_videos/TENSIÓN EN  EL CONGRESO： la Policía impide que los jubilados corten la calle y hay incidentes.mp4",
    "input_videos/MEGAOPERATIVO POLICIAL en la MARCHA de JUBILADOS.mp4",
]

# Output directory for extracted frames
output_base_dir = "output_frames"

# Frames per second to extract
fps = 1

# Process each video
for i, video_path in enumerate(video_paths):
    output_dir = f"{output_base_dir}/video_{i+1}"  # Separate folder for each video
    try:
        extract_frames(video_path, output_dir, fps=fps)
    except Exception as e:
        print(f"Error processing {video_path}: {e}")
