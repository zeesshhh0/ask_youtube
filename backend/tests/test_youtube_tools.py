import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.youtube_tools import YouTubeTools

def test_get_video_duration():
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Astley - Never Gonna Give You Up (3:33 = 213s)
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
    ]
    
    for url in urls:
        print(f"\nTesting URL: {url}")
        duration = YouTubeTools.get_video_duration(url)
        if duration is not None:
            print(f"SUCCESS: Retrieved duration: {duration} seconds")
            # Rick Astley's never gonna give you up is 212 or 213 seconds usually
            if 200 < duration < 230:
                print("Duration is in expected range.")
            else:
                print(f"WARNING: Duration {duration} seems outside expected range.")
        else:
            print("FAILED: Could not retrieve duration")

if __name__ == "__main__":
    test_get_video_duration()
