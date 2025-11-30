from extract_frames import extract_frames


def main():
    video_path = "input_videos/video.mp4"  # <--- put your video filename here
    output_dir = "output_frames"  # frames will be saved here

    extract_frames(video_path, output_dir, fps=1)


if __name__ == "__main__":
    main()
