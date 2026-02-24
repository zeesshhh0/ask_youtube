import json
import re
import asyncio
from urllib.parse import urlparse, parse_qs, urlencode
from urllib.request import urlopen
from typing import Optional, List
from datetime import datetime

from fastapi import HTTPException
from dotenv import load_dotenv


try:
    load_dotenv()
    print(f"[{datetime.now()}] Environment variables loaded from .env file")
except ImportError:
    print(f"[{datetime.now()}] load_env.py not found - using system environment variables only")
except Exception as e:
    print(f"[{datetime.now()}] Error loading .env file: {e}")

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.proxies import WebshareProxyConfig
    print(f"[{datetime.now()}] Successfully imported YouTubeTranscriptApi and WebshareProxyConfig")
except ImportError:
    print(f"[{datetime.now()}] ERROR: Failed to import youtube_transcript_api")
    raise ImportError(
        "`youtube_transcript_api` not installed. Please install using `pip install youtube_transcript_api`"
    )

class YouTubeTools:
    @staticmethod
    def get_youtube_video_id(url: str) -> Optional[str]:
        """Function to get the video ID from a YouTube URL."""
        print(f"[{datetime.now()}] get_youtube_video_id called with URL: {url}")

        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        print(f"[{datetime.now()}] Parsed hostname: {hostname}")

        if hostname == "youtu.be":
            video_id = parsed_url.path[1:]
            print(f"[{datetime.now()}] Extracted video ID from youtu.be: {video_id}")
            return video_id
        if hostname in ("www.youtube.com", "youtube.com"):
            if parsed_url.path == "/watch":
                query_params = parse_qs(parsed_url.query)
                video_id = query_params.get("v", [None])[0]
                print(f"[{datetime.now()}] Extracted video ID from watch URL: {video_id}")
                return video_id
            if parsed_url.path.startswith("/embed/"):
                video_id = parsed_url.path.split("/")[2]
                print(f"[{datetime.now()}] Extracted video ID from embed URL: {video_id}")
                return video_id
            if parsed_url.path.startswith("/v/"):
                video_id = parsed_url.path.split("/")[2]
                print(f"[{datetime.now()}] Extracted video ID from /v/ URL: {video_id}")
                return video_id

        print(f"[{datetime.now()}] ERROR: Could not extract video ID from URL: {url}")
        return None

    @staticmethod
    def get_video_data(url: str) -> dict:
        """Function to get video data from a YouTube URL."""
        print(f"[{datetime.now()}] get_video_data called with URL: {url}")

        if not url:
            print(f"[{datetime.now()}] ERROR: No URL provided to get_video_data")
            raise HTTPException(status_code=400, detail="No URL provided")

        try:
            video_id = YouTubeTools.get_youtube_video_id(url)
            if not video_id:
                print(f"[{datetime.now()}] ERROR: Invalid YouTube URL: {url}")
                raise HTTPException(status_code=400, detail="Invalid YouTube URL")
            print(f"[{datetime.now()}] Video ID extracted: {video_id}")
        except Exception as e:
            print(f"[{datetime.now()}] ERROR: Exception while getting video ID: {str(e)}")
            raise HTTPException(status_code=400, detail="Error getting video ID from URL")

        try:
            params = {"format": "json", "url": f"https://www.youtube.com/watch?v={video_id}"}
            oembed_url = "https://www.youtube.com/oembed"
            query_string = urlencode(params)
            full_url = oembed_url + "?" + query_string
            print(f"[{datetime.now()}] Making request to oEmbed API: {full_url}")

            with urlopen(full_url) as response:
                response_text = response.read()
                print(f"[{datetime.now()}] Received response from oEmbed API")
                video_data = json.loads(response_text.decode())
                print(f"[{datetime.now()}] Successfully parsed video data JSON")

                clean_data = {
                    "title": video_data.get("title"),
                    "author_name": video_data.get("author_name"),
                    "author_url": video_data.get("author_url"),
                    "type": video_data.get("type"),
                    "height": video_data.get("height"),
                    "width": video_data.get("width"),
                    "version": video_data.get("version"),
                    "provider_name": video_data.get("provider_name"),
                    "provider_url": video_data.get("provider_url"),
                    "thumbnail_url": video_data.get("thumbnail_url"),
                }
                print(f"[{datetime.now()}] Video data retrieved: Title='{clean_data.get('title')}', Author='{clean_data.get('author_name')}'")
                return clean_data
        except Exception as e:
            print(f"[{datetime.now()}] ERROR: Exception while getting video data: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error getting video data: {str(e)}")

    @staticmethod
    def get_video_duration(url: str) -> Optional[int]:
        """Function to get the video duration in seconds from a YouTube URL."""
        print(f"[{datetime.now()}] get_video_duration called with URL: {url}")
        
        try:
            video_id = YouTubeTools.get_youtube_video_id(url)
            if not video_id:
                print(f"[{datetime.now()}] WARNING: Could not extract video ID for duration")
                return None
                
            # Construct standard watch URL for reliable duration scraping
            fetch_url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"[{datetime.now()}] Fetching duration from: {fetch_url}")

            # Using urllib to fetch the page content
            with urlopen(fetch_url) as response:
                html = response.read().decode('utf-8')
                
                # Search for lengthSeconds in the HTML content
                match = re.search(r'\"lengthSeconds\":\"(\d+)\"', html)
                if match:
                    duration = int(match.group(1))
                    print(f"[{datetime.now()}] Video duration found: {duration} seconds")
                    return duration
            
            print(f"[{datetime.now()}] WARNING: Could not find lengthSeconds in HTML")
            return None
        except Exception as e:
            print(f"[{datetime.now()}] ERROR: Exception while getting video duration: {str(e)}")
            return None

    @staticmethod
    def _create_youtube_api():
        """Create a YouTubeTranscriptApi instance with proxy config."""
        
        return YouTubeTranscriptApi()

    @staticmethod
    def _get_transcript_with_fallback(video_id: str, languages: Optional[List[str]] = None):
        """Get transcript with language fallback logic."""
        ytt_api = YouTubeTools._create_youtube_api()

        
        transcript_list = ytt_api.list(video_id)
        available_languages = [t.language_code for t in transcript_list]

        
        if languages:
            
            for lang in languages:
                if lang in available_languages:
                    fetched_transcript = ytt_api.fetch(video_id, languages=[lang])
                    return fetched_transcript, available_languages
            
            fetched_transcript = ytt_api.fetch(video_id, languages=[available_languages[0]])
            return fetched_transcript, available_languages
        else:
            
            if 'en' in available_languages:
                fetched_transcript = ytt_api.fetch(video_id, languages=['en'])
                return fetched_transcript, available_languages
            else:
                fetched_transcript = ytt_api.fetch(video_id, languages=[available_languages[0]])
                return fetched_transcript, available_languages

    @staticmethod
    async def get_video_captions(url: str, languages: Optional[List[str]] = None) -> str:
        """Get captions from a YouTube video using the new API."""
        print(f"[{datetime.now()}] get_video_captions called with URL: {url}, languages: {languages}")

        if not url:
            print(f"[{datetime.now()}] ERROR: No URL provided to get_video_captions")
            raise HTTPException(status_code=400, detail="No URL provided")

        try:
            video_id = YouTubeTools.get_youtube_video_id(url)
            if not video_id:
                print(f"[{datetime.now()}] ERROR: Invalid YouTube URL: {url}")
                raise HTTPException(status_code=400, detail="Invalid YouTube URL")
            print(f"[{datetime.now()}] Video ID extracted: {video_id}")
        except Exception as e:
            print(f"[{datetime.now()}] ERROR: Exception while getting video ID: {str(e)}")
            raise HTTPException(status_code=400, detail="Error getting video ID from URL")

        try:
            print(f"[{datetime.now()}] Fetching transcript in background thread...")

            
            fetched_transcript, available_languages = await asyncio.to_thread(
                YouTubeTools._get_transcript_with_fallback, video_id, languages
            )

            print(f"[{datetime.now()}] Available transcript languages: {available_languages}")

            if fetched_transcript:
                print(f"[{datetime.now()}] Transcript fetched successfully")
                print(f"[{datetime.now()}] Transcript info - Language: {fetched_transcript.language}, Code: {fetched_transcript.language_code}, Generated: {fetched_transcript.is_generated}")
                print(f"[{datetime.now()}] Number of snippets: {len(fetched_transcript)}")

                
                caption_text = " ".join(snippet.text for snippet in fetched_transcript)
                print(f"[{datetime.now()}] Combined caption text length: {len(caption_text)} characters")
                return caption_text

            print(f"[{datetime.now()}] WARNING: No captions found for video")
            return "No captions found for video"
        except Exception as e:
            print(f"[{datetime.now()}] ERROR: Exception while getting captions: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error getting captions for video: {str(e)}")

    @staticmethod
    async def get_video_timestamps(url: str, languages: Optional[List[str]] = None) -> str:
        """Generate timestamps for a YouTube video based on captions using the new API."""
        print(f"[{datetime.now()}] get_video_timestamps called with URL: {url}, languages: {languages}")

        if not url:
            print(f"[{datetime.now()}] ERROR: No URL provided to get_video_timestamps")
            raise HTTPException(status_code=400, detail="No URL provided")

        try:
            video_id = YouTubeTools.get_youtube_video_id(url)
            if not video_id:
                print(f"[{datetime.now()}] ERROR: Invalid YouTube URL: {url}")
                raise HTTPException(status_code=400, detail="Invalid YouTube URL")
            print(f"[{datetime.now()}] Video ID extracted: {video_id}")
        except Exception as e:
            print(f"[{datetime.now()}] ERROR: Exception while getting video ID: {str(e)}")
            raise HTTPException(status_code=400, detail="Error getting video ID from URL")

        try:
            print(f"[{datetime.now()}] Fetching transcript in background thread...")

            
            fetched_transcript, available_languages = await asyncio.to_thread(
                YouTubeTools._get_transcript_with_fallback, video_id, languages
            )

            print(f"[{datetime.now()}] Available transcript languages: {available_languages}")
            print(f"[{datetime.now()}] Transcript fetched successfully")
            print(f"[{datetime.now()}] Processing {len(fetched_transcript)} snippets into timestamps")

            timestamps = []
            for i, snippet in enumerate(fetched_transcript):
                start = int(snippet.start)
                minutes, seconds = divmod(start, 60)
                timestamp = f"{minutes}:{seconds:02d} - {snippet.text}"
                timestamps.append(timestamp)

                if i < 5:  
                    print(f"[{datetime.now()}] Sample timestamp [{i}]: {timestamp}")

            print(f"[{datetime.now()}] Generated {len(timestamps)} timestamps")
            timestamps = ", ".join(timestamps)
            return timestamps
        except Exception as e:
            print(f"[{datetime.now()}] ERROR: Exception while generating timestamps: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error generating timestamps: {str(e)}")

    @staticmethod
    async def get_video_transcript_languages(url: str) -> List[dict]:
        """List available transcript languages for a video."""
        print(f"[{datetime.now()}] get_video_transcript_languages called with URL: {url}")

        if not url:
            print(f"[{datetime.now()}] ERROR: No URL provided")
            raise HTTPException(status_code=400, detail="No URL provided")

        try:
            video_id = YouTubeTools.get_youtube_video_id(url)
            if not video_id:
                print(f"[{datetime.now()}] ERROR: Invalid YouTube URL: {url}")
                raise HTTPException(status_code=400, detail="Invalid YouTube URL")
            print(f"[{datetime.now()}] Video ID extracted: {video_id}")
        except Exception as e:
            print(f"[{datetime.now()}] ERROR: Exception while getting video ID: {str(e)}")
            raise HTTPException(status_code=400, detail="Error getting video ID from URL")

        try:
            print(f"[{datetime.now()}] Listing available transcripts in background thread...")

            def list_transcripts(video_id):
                ytt_api = YouTubeTools._create_youtube_api()
                return ytt_api.list(video_id)

            
            transcript_list = await asyncio.to_thread(list_transcripts, video_id)

            languages_info = []
            for transcript in transcript_list:
                lang_info = {
                    "language": transcript.language,
                    "language_code": transcript.language_code,
                    "is_generated": transcript.is_generated,
                    "is_translatable": transcript.is_translatable
                }
                languages_info.append(lang_info)
                print(f"[{datetime.now()}] Found transcript: {transcript.language} ({transcript.language_code}) - Generated: {transcript.is_generated}")

            print(f"[{datetime.now()}] Found {len(languages_info)} available transcript languages")
            return languages_info

        except Exception as e:
            print(f"[{datetime.now()}] ERROR: Exception while listing transcript languages: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error listing transcript languages: {str(e)}")