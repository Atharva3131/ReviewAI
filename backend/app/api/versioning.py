"""
API Versioning utilities and strategies
"""
from fastapi import Request, HTTPException, status
from typing import Optional, Dict, Any
import re
from enum import Enum


class APIVersion(str, Enum):
    """Supported API versions"""
    V1 = "v1"
    V2 = "v2"  # Future version


class VersioningStrategy(str, Enum):
    """API versioning strategies"""
    URL_PATH = "url_path"          # /api/v1/endpoint
    HEADER = "header"              # Accept: application/vnd.revive-ai.v1+json
    QUERY_PARAM = "query_param"    # /api/endpoint?version=v1


class APIVersionManager:
    """Manages API versioning across different strategies"""
    
    # Version compatibility matrix
    SUPPORTED_VERSIONS = {
        APIVersion.V1: {
            "status": "stable",
            "deprecated": False,
            "sunset_date": None,
            "description": "Initial stable API version"
        },
        APIVersion.V2: {
            "status": "development", 
            "deprecated": False,
            "sunset_date": None,
            "description": "Next generation API with enhanced features"
        }
    }
    
    DEFAULT_VERSION = APIVersion.V1
    CURRENT_VERSION = APIVersion.V1
    
    @classmethod
    def extract_version_from_path(cls, path: str) -> Optional[APIVersion]:
        """Extract version from URL path"""
        # Match patterns like /api/v1/endpoint or /v1/endpoint
        version_pattern = r'/(?:api/)?v(\d+)(?:/|$)'
        match = re.search(version_pattern, path)
        
        if match:
            version_num = match.group(1)
            version_str = f"v{version_num}"
            
            # Check if version is supported
            for version in APIVersion:
                if version.value == version_str:
                    return version
        
        return None
    
    @classmethod
    def extract_version_from_header(cls, request: Request) -> Optional[APIVersion]:
        """Extract version from Accept header"""
        accept_header = request.headers.get("accept", "")
        
        # Match patterns like application/vnd.revive-ai.v1+json
        version_pattern = r'application/vnd\.revive-ai\.v(\d+)\+json'
        match = re.search(version_pattern, accept_header)
        
        if match:
            version_num = match.group(1)
            version_str = f"v{version_num}"
            
            for version in APIVersion:
                if version.value == version_str:
                    return version
        
        return None
    
    @classmethod
    def extract_version_from_query(cls, request: Request) -> Optional[APIVersion]:
        """Extract version from query parameter"""
        version_param = request.query_params.get("version")
        
        if version_param:
            # Handle both 'v1' and '1' formats
            if not version_param.startswith('v'):
                version_param = f"v{version_param}"
            
            for version in APIVersion:
                if version.value == version_param:
                    return version
        
        return None
    
    @classmethod
    def determine_version(cls, request: Request) -> APIVersion:
        """Determine API version from request using multiple strategies"""
        
        # Strategy 1: URL Path (highest priority)
        version = cls.extract_version_from_path(request.url.path)
        if version:
            return version
        
        # Strategy 2: Accept Header
        version = cls.extract_version_from_header(request)
        if version:
            return version
        
        # Strategy 3: Query Parameter
        version = cls.extract_version_from_query(request)
        if version:
            return version
        
        # Default version
        return cls.DEFAULT_VERSION
    
    @classmethod
    def validate_version(cls, version: APIVersion) -> None:
        """Validate if version is supported and not deprecated"""
        version_info = cls.SUPPORTED_VERSIONS.get(version)
        
        if not version_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"API version '{version.value}' is not supported",
                headers={
                    "X-Supported-Versions": ", ".join([v.value for v in cls.SUPPORTED_VERSIONS.keys()])
                }
            )
        
        if version_info.get("deprecated", False):
            # Log deprecation warning but allow request
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"API version '{version.value}' is deprecated")
        
        if version_info.get("status") == "development":
            # Allow development versions but add warning header
            pass
    
    @classmethod
    def get_version_info(cls, version: APIVersion) -> Dict[str, Any]:
        """Get detailed information about a version"""
        return cls.SUPPORTED_VERSIONS.get(version, {})
    
    @classmethod
    def get_supported_versions(cls) -> Dict[str, Dict[str, Any]]:
        """Get all supported versions with their info"""
        return {v.value: info for v, info in cls.SUPPORTED_VERSIONS.items()}
    
    @classmethod
    def add_version_headers(cls, response, version: APIVersion) -> None:
        """Add version-related headers to response"""
        response.headers["X-API-Version"] = version.value
        response.headers["X-API-Current-Version"] = cls.CURRENT_VERSION.value
        response.headers["X-API-Supported-Versions"] = ", ".join([v.value for v in cls.SUPPORTED_VERSIONS.keys()])
        
        version_info = cls.get_version_info(version)
        if version_info.get("deprecated"):
            response.headers["X-API-Deprecated"] = "true"
            if version_info.get("sunset_date"):
                response.headers["X-API-Sunset"] = version_info["sunset_date"]


class VersionedResponse:
    """Utility for creating version-aware responses"""
    
    @staticmethod
    def format_response(data: Any, version: APIVersion) -> Dict[str, Any]:
        """Format response based on API version"""
        
        if version == APIVersion.V1:
            return {
                "data": data,
                "version": version.value,
                "timestamp": int(time.time())
            }
        
        elif version == APIVersion.V2:
            # Future version with enhanced response format
            return {
                "result": data,
                "meta": {
                    "version": version.value,
                    "timestamp": int(time.time()),
                    "request_id": None  # Will be populated by middleware
                }
            }
        
        # Default to V1 format
        return {
            "data": data,
            "version": version.value,
            "timestamp": int(time.time())
        }
    
    @staticmethod
    def format_error(error: str, version: APIVersion, details: Optional[Dict] = None) -> Dict[str, Any]:
        """Format error response based on API version"""
        
        if version == APIVersion.V1:
            response = {
                "error": error,
                "version": version.value,
                "timestamp": int(time.time())
            }
            if details:
                response["details"] = details
            return response
        
        elif version == APIVersion.V2:
            return {
                "error": {
                    "message": error,
                    "details": details or {}
                },
                "meta": {
                    "version": version.value,
                    "timestamp": int(time.time()),
                    "request_id": None
                }
            }
        
        # Default to V1 format
        response = {
            "error": error,
            "version": version.value,
            "timestamp": int(time.time())
        }
        if details:
            response["details"] = details
        return response


# Middleware for version handling
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time


class APIVersionMiddleware(BaseHTTPMiddleware):
    """Middleware for handling API versioning"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add version context"""
        
        # Determine API version
        try:
            version = APIVersionManager.determine_version(request)
            APIVersionManager.validate_version(version)
            
            # Add version to request state
            request.state.api_version = version
            
        except HTTPException as e:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=e.status_code,
                content=VersionedResponse.format_error(
                    e.detail, 
                    APIVersionManager.DEFAULT_VERSION
                ),
                headers=e.headers or {}
            )
        
        # Process request
        response = await call_next(request)
        
        # Add version headers
        APIVersionManager.add_version_headers(response, version)
        
        return response
