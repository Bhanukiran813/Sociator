import re
from typing import Any, Dict, List, Optional
import httpx
from fastapi import HTTPException, status
from app.core.config import settings

YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeService:
    """
    Service client for integrating with the official YouTube Data API v3.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.YOUTUBE_API_KEY

    def _ensure_api_key(self) -> None:
        if not self.api_key or not self.api_key.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "YouTube API key is not configured. "
                    "Please set YOUTUBE_API_KEY in backend/.env to interact with YouTube Data API."
                ),
            )

    @staticmethod
    def parse_identifier(raw_identifier: str) -> Dict[str, str]:
        """
        Parses a URL, handle, or channel ID into an identifier type and value.
        Handles handles with dots, custom URLs (/c/, /user/), and URL query strings.
        """
        cleaned = raw_identifier.strip()
        # Remove query parameters if present (e.g. ?si=... or ?sub_confirmation=1)
        if "?" in cleaned and ("youtube.com" in cleaned or "youtu.be" in cleaned):
            cleaned = cleaned.split("?")[0].rstrip("/")

        # e.g., https://www.youtube.com/@handle
        handle_match = re.search(r"youtube\.com/@([A-Za-z0-9_.-]+)", cleaned)
        if handle_match:
            return {"type": "handle", "value": handle_match.group(1)}

        # e.g., https://www.youtube.com/channel/(UC...)
        channel_match = re.search(r"youtube\.com/channel/([A-Za-z0-9_-]+)", cleaned)
        if channel_match:
            return {"type": "id", "value": channel_match.group(1)}

        # e.g., https://www.youtube.com/c/ChannelName or /user/UserName
        custom_match = re.search(r"youtube\.com/(?:c|user)/([A-Za-z0-9_.-]+)", cleaned)
        if custom_match:
            return {"type": "handle", "value": custom_match.group(1)}

        if cleaned.startswith("@"):
            return {"type": "handle", "value": cleaned[1:]}

        if cleaned.startswith("UC") and len(cleaned) >= 20:
            return {"type": "id", "value": cleaned}

        # Fallback to handle
        return {"type": "handle", "value": cleaned}

    @staticmethod
    def extract_video_id(raw_video: str) -> str:
        """
        Extracts the 11-character YouTube video ID from various URL formats or raw ID.
        Examples:
        - https://www.youtube.com/watch?v=dQw4w9WgXcQ
        - https://youtu.be/dQw4w9WgXcQ
        - https://www.youtube.com/shorts/dQw4w9WgXcQ
        - dQw4w9WgXcQ
        """
        cleaned = raw_video.strip()
        # youtu.be/<id>
        short_match = re.search(r"youtu\.be/([A-Za-z0-9_-]{11})", cleaned)
        if short_match:
            return short_match.group(1)

        # youtube.com/watch?v=<id>
        watch_match = re.search(r"[?&]v=([A-Za-z0-9_-]{11})", cleaned)
        if watch_match:
            return watch_match.group(1)

        # youtube.com/shorts/<id> or /embed/<id>
        embed_match = re.search(r"youtube\.com/(?:shorts|embed)/([A-Za-z0-9_-]{11})", cleaned)
        if embed_match:
            return embed_match.group(1)

        # Direct 11-char ID
        if len(cleaned) == 11 and re.match(r"^[A-Za-z0-9_-]{11}$", cleaned):
            return cleaned

        return cleaned

    async def get_channel_info(self, identifier: str) -> Dict[str, Any]:
        """
        Fetches channel metadata, statistics, and uploads playlist ID from YouTube.
        """
        self._ensure_api_key()
        parsed = self.parse_identifier(identifier)

        params: Dict[str, Any] = {
            "key": self.api_key,
            "part": "snippet,statistics,contentDetails",
        }
        if parsed["type"] == "handle":
            params["forHandle"] = parsed["value"]
        else:
            params["id"] = parsed["value"]

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{YOUTUBE_API_BASE_URL}/channels", params=params)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"YouTube API error: {response.text}",
                )

            data = response.json()
            items = data.get("items", [])
            if not items:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No YouTube channel found for '{identifier}'.",
                )

            item = items[0]
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            content_details = item.get("contentDetails", {})
            uploads_playlist_id = (
                content_details.get("relatedPlaylists", {}).get("uploads")
            )

            thumbnails = snippet.get("thumbnails", {})
            thumb_url = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url")
            )

            return {
                "channel_id": item.get("id"),
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "custom_url": snippet.get("customUrl"),
                "published_at": snippet.get("publishedAt"),
                "thumbnail_url": thumb_url,
                "country": snippet.get("country"),
                "view_count": int(stats.get("viewCount", 0)),
                "subscriber_count": int(stats.get("subscriberCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
                "uploads_playlist_id": uploads_playlist_id,
            }

    async def get_latest_videos(
        self,
        uploads_playlist_id: str,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Fetches the latest videos from a channel's uploads playlist and enriches them with statistics.
        """
        self._ensure_api_key()

        # 1. Fetch playlist items
        async with httpx.AsyncClient(timeout=15.0) as client:
            pl_params = {
                "key": self.api_key,
                "part": "snippet,contentDetails",
                "playlistId": uploads_playlist_id,
                "maxResults": min(max_results, 50),
            }
            pl_response = await client.get(
                f"{YOUTUBE_API_BASE_URL}/playlistItems",
                params=pl_params,
            )

            if pl_response.status_code != 200:
                raise HTTPException(
                    status_code=pl_response.status_code,
                    detail=f"YouTube playlist error: {pl_response.text}",
                )

            pl_items = pl_response.json().get("items", [])
            video_ids = [
                item.get("contentDetails", {}).get("videoId")
                for item in pl_items
                if item.get("contentDetails", {}).get("videoId")
            ]

            if not video_ids:
                return []

            # 2. Fetch full video statistics and content details
            vid_params = {
                "key": self.api_key,
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(video_ids),
            }
            vid_response = await client.get(
                f"{YOUTUBE_API_BASE_URL}/videos",
                params=vid_params,
            )

            if vid_response.status_code != 200:
                raise HTTPException(
                    status_code=vid_response.status_code,
                    detail=f"YouTube video error: {vid_response.text}",
                )

            vid_items = vid_response.json().get("items", [])
            results = []
            for item in vid_items:
                v_snippet = item.get("snippet", {})
                v_stats = item.get("statistics", {})
                v_details = item.get("contentDetails", {})
                v_thumbs = v_snippet.get("thumbnails", {})
                v_thumb_url = (
                    v_thumbs.get("high", {}).get("url")
                    or v_thumbs.get("medium", {}).get("url")
                    or v_thumbs.get("default", {}).get("url")
                )

                results.append({
                    "video_id": item.get("id"),
                    "title": v_snippet.get("title", ""),
                    "description": v_snippet.get("description", ""),
                    "published_at": v_snippet.get("publishedAt"),
                    "thumbnail_url": v_thumb_url,
                    "duration": v_details.get("duration"),
                    "view_count": int(v_stats.get("viewCount", 0)),
                    "like_count": int(v_stats.get("likeCount", 0)),
                    "comment_count": int(v_stats.get("commentCount", 0)),
                })

            return results

    async def get_video_info(self, raw_video: str) -> Dict[str, Any]:
        """
        Fetches detailed metadata, statistics, and channel ownership for a single video.
        """
        self._ensure_api_key()
        video_id = self.extract_video_id(raw_video)

        async with httpx.AsyncClient(timeout=15.0) as client:
            params = {
                "key": self.api_key,
                "part": "snippet,contentDetails,statistics",
                "id": video_id,
            }
            response = await client.get(
                f"{YOUTUBE_API_BASE_URL}/videos",
                params=params,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"YouTube video error: {response.text}",
                )

            items = response.json().get("items", [])
            if not items:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No YouTube video found for ID '{video_id}'.",
                )

            item = items[0]
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            details = item.get("contentDetails", {})
            thumbnails = snippet.get("thumbnails", {})
            thumb_url = (
                thumbnails.get("maxres", {}).get("url")
                or thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url")
            )

            return {
                "video_id": item.get("id"),
                "channel_id": snippet.get("channelId"),
                "channel_title": snippet.get("channelTitle"),
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt"),
                "thumbnail_url": thumb_url,
                "duration": details.get("duration"),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
            }

    async def search_channels(
        self,
        query: str,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Searches YouTube for channels matching a keyword query.
        """
        self._ensure_api_key()

        async with httpx.AsyncClient(timeout=15.0) as client:
            params = {
                "key": self.api_key,
                "part": "snippet",
                "type": "channel",
                "q": query,
                "maxResults": min(max_results, 25),
            }
            response = await client.get(
                f"{YOUTUBE_API_BASE_URL}/search",
                params=params,
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"YouTube search error: {response.text}",
                )

            items = response.json().get("items", [])
            results = []
            for item in items:
                snippet = item.get("snippet", {})
                thumbnails = snippet.get("thumbnails", {})
                thumb_url = (
                    thumbnails.get("high", {}).get("url")
                    or thumbnails.get("medium", {}).get("url")
                    or thumbnails.get("default", {}).get("url")
                )
                results.append({
                    "channel_id": item.get("id", {}).get("channelId"),
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "thumbnail_url": thumb_url,
                    "published_at": snippet.get("publishedAt"),
                })
            return results

    async def get_video_comments(
        self,
        raw_video: str,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-level comments for a video ordered by relevance.
        """
        self._ensure_api_key()
        video_id = self.extract_video_id(raw_video)

        async with httpx.AsyncClient(timeout=15.0) as client:
            params = {
                "key": self.api_key,
                "part": "snippet",
                "videoId": video_id,
                "maxResults": min(max_results, 100),
                "order": "relevance",
                "textFormat": "plainText",
            }
            response = await client.get(
                f"{YOUTUBE_API_BASE_URL}/commentThreads",
                params=params,
            )

            if response.status_code != 200:
                # 403 usually means comments are disabled for this video
                if response.status_code == 403:
                    return []
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"YouTube comments error: {response.text}",
                )

            items = response.json().get("items", [])
            comments = []
            for item in items:
                top_c = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                comments.append({
                    "comment_id": item.get("id"),
                    "author_name": top_c.get("authorDisplayName", "Unknown"),
                    "author_profile_image": top_c.get("authorProfileImageUrl"),
                    "text": top_c.get("textDisplay", ""),
                    "like_count": int(top_c.get("likeCount", 0)),
                    "published_at": top_c.get("publishedAt"),
                })
            return comments


youtube_service = YouTubeService()
