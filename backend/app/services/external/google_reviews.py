"""
Google Reviews API integration service
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.core.config import settings

from .base_service import BaseExternalService, RetryConfig, ServiceResponse

logger = logging.getLogger(__name__)


@dataclass
class GoogleReview:
    """Google Review data structure"""

    review_id: str
    customer_name: str
    rating: int
    content: str
    created_at: datetime
    platform: str = "google"
    location_id: Optional[str] = None
    reviewer_profile_url: Optional[str] = None
    response: Optional[str] = None
    response_date: Optional[datetime] = None


class GoogleReviewsService(BaseExternalService):
    """
    Google Reviews API integration service

    Note: This is a simulation since Google My Business API has limited access.
    In production, this would integrate with Google My Business API or use
    webhook notifications from Google.
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            service_name="google_reviews",
            base_url="https://mybusiness.googleapis.com/v4",
            api_key=api_key or settings.GOOGLE_REVIEWS_API_KEY,
            timeout=30,
            retry_config=RetryConfig(max_retries=3, base_delay=2.0),
        )
        self.location_ids: List[str] = []

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get Google API authentication headers"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Goog-User-Project": settings.GOOGLE_PROJECT_ID,
        }

    async def test_connection(self) -> ServiceResponse:
        """Test connection to Google My Business API"""
        try:
            # Test with a simple account info request
            response = await self._make_request("GET", "/accounts")

            if response.success:
                logger.info("Google Reviews API connection successful")
                return ServiceResponse(
                    success=True,
                    data={
                        "message": "Connection successful",
                        "accounts": response.data,
                    },
                )
            else:
                logger.error(f"Google Reviews API connection failed: {response.error}")
                return response

        except Exception as e:
            logger.error(f"Google Reviews API test connection error: {e}")
            return ServiceResponse(success=False, error=str(e))

    async def get_locations(self, account_id: str) -> ServiceResponse:
        """Get business locations for an account"""
        try:
            endpoint = f"/accounts/{account_id}/locations"
            response = await self._make_request("GET", endpoint)

            if response.success and response.data:
                locations = response.data.get("locations", [])
                self.location_ids = [
                    loc.get("name", "").split("/")[-1] for loc in locations
                ]

                logger.info(f"Retrieved {len(locations)} locations from Google")
                return ServiceResponse(
                    success=True, data={"locations": locations, "count": len(locations)}
                )

            return response

        except Exception as e:
            logger.error(f"Error getting Google locations: {e}")
            return ServiceResponse(success=False, error=str(e))

    async def get_reviews(
        self, location_id: str, page_size: int = 50, order_by: str = "updateTime desc"
    ) -> ServiceResponse:
        """Get reviews for a specific location"""
        try:
            endpoint = f"/accounts/{settings.GOOGLE_ACCOUNT_ID}/locations/{location_id}/reviews"
            params = {"pageSize": page_size, "orderBy": order_by}

            response = await self._make_request("GET", endpoint, params=params)

            if response.success and response.data:
                reviews_data = response.data.get("reviews", [])
                reviews = []

                for review_data in reviews_data:
                    try:
                        review = self._parse_google_review(review_data, location_id)
                        reviews.append(review)
                    except Exception as e:
                        logger.warning(f"Failed to parse Google review: {e}")
                        continue

                logger.info(
                    f"Retrieved {len(reviews)} reviews from Google location {location_id}"
                )
                return ServiceResponse(
                    success=True,
                    data={
                        "reviews": [self._review_to_dict(r) for r in reviews],
                        "count": len(reviews),
                        "location_id": location_id,
                    },
                )

            return response

        except Exception as e:
            logger.error(f"Error getting Google reviews: {e}")
            return ServiceResponse(success=False, error=str(e))

    async def get_all_reviews(
        self, since_date: Optional[datetime] = None
    ) -> ServiceResponse:
        """Get reviews from all configured locations"""
        try:
            all_reviews = []
            errors = []

            if not self.location_ids:
                # Try to get locations first
                account_response = await self.get_locations(settings.GOOGLE_ACCOUNT_ID)
                if not account_response.success:
                    return ServiceResponse(
                        success=False,
                        error="No locations configured and failed to retrieve locations",
                    )

            for location_id in self.location_ids:
                try:
                    response = await self.get_reviews(location_id)
                    if response.success and response.data:
                        location_reviews = response.data.get("reviews", [])

                        # Filter by date if specified
                        if since_date:
                            location_reviews = [
                                review
                                for review in location_reviews
                                if datetime.fromisoformat(
                                    review["created_at"].replace("Z", "+00:00")
                                )
                                >= since_date
                            ]

                        all_reviews.extend(location_reviews)
                    else:
                        errors.append(f"Location {location_id}: {response.error}")

                except Exception as e:
                    errors.append(f"Location {location_id}: {str(e)}")
                    continue

            logger.info(
                f"Retrieved {len(all_reviews)} total reviews from {len(self.location_ids)} locations"
            )

            return ServiceResponse(
                success=True,
                data={
                    "reviews": all_reviews,
                    "count": len(all_reviews),
                    "locations_processed": len(self.location_ids),
                    "errors": errors if errors else None,
                },
            )

        except Exception as e:
            logger.error(f"Error getting all Google reviews: {e}")
            return ServiceResponse(success=False, error=str(e))

    async def respond_to_review(
        self, location_id: str, review_id: str, response_text: str
    ) -> ServiceResponse:
        """Respond to a Google review"""
        try:
            endpoint = f"/accounts/{settings.GOOGLE_ACCOUNT_ID}/locations/{location_id}/reviews/{review_id}/reply"
            data = {"comment": response_text}

            response = await self._make_request("PUT", endpoint, data=data)

            if response.success:
                logger.info(f"Successfully responded to Google review {review_id}")
                return ServiceResponse(
                    success=True,
                    data={
                        "review_id": review_id,
                        "location_id": location_id,
                        "response": response_text,
                        "responded_at": datetime.utcnow().isoformat(),
                    },
                )

            return response

        except Exception as e:
            logger.error(f"Error responding to Google review: {e}")
            return ServiceResponse(success=False, error=str(e))

    def _parse_google_review(
        self, review_data: Dict[str, Any], location_id: str
    ) -> GoogleReview:
        """Parse Google review data into standardized format"""

        # Extract review ID
        review_id = (
            review_data.get("reviewId") or review_data.get("name", "").split("/")[-1]
        )

        # Extract reviewer info
        reviewer = review_data.get("reviewer", {})
        customer_name = reviewer.get("displayName", "Anonymous")
        reviewer_profile_url = reviewer.get("profilePhotoUrl")

        # Extract rating and content
        rating = int(review_data.get("starRating", 0))
        content = review_data.get("comment", "")

        # Parse dates
        create_time = review_data.get("createTime", "")
        created_at = self._parse_google_timestamp(create_time)

        # Extract response if exists
        reply = review_data.get("reviewReply", {})
        response_text = reply.get("comment") if reply else None
        response_date = None
        if reply and reply.get("updateTime"):
            response_date = self._parse_google_timestamp(reply["updateTime"])

        return GoogleReview(
            review_id=review_id,
            customer_name=customer_name,
            rating=rating,
            content=content,
            created_at=created_at,
            location_id=location_id,
            reviewer_profile_url=reviewer_profile_url,
            response=response_text,
            response_date=response_date,
        )

    def _parse_google_timestamp(self, timestamp_str: str) -> datetime:
        """Parse Google timestamp format"""
        try:
            # Google uses RFC3339 format
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str[:-1] + "+00:00"
            return datetime.fromisoformat(timestamp_str)
        except Exception:
            # Fallback to current time if parsing fails
            return datetime.utcnow()

    def _review_to_dict(self, review: GoogleReview) -> Dict[str, Any]:
        """Convert GoogleReview to dictionary"""
        return {
            "review_id": review.review_id,
            "customer_name": review.customer_name,
            "rating": review.rating,
            "content": review.content,
            "created_at": review.created_at.isoformat(),
            "platform": review.platform,
            "location_id": review.location_id,
            "reviewer_profile_url": review.reviewer_profile_url,
            "response": review.response,
            "response_date": (
                review.response_date.isoformat() if review.response_date else None
            ),
        }


class GoogleReviewsWebhookSimulator:
    """
    Webhook simulator for Google Reviews

    Since Google My Business API has limited webhook support,
    this simulates webhook notifications for testing and development.
    """

    def __init__(self, google_service: GoogleReviewsService):
        self.google_service = google_service
        self.last_check: Optional[datetime] = None
        self.polling_interval = 300  # 5 minutes

    async def simulate_webhook_polling(self) -> List[Dict[str, Any]]:
        """Simulate webhook by polling for new reviews"""
        try:
            # Use last check time or default to 1 hour ago
            since_date = self.last_check or (datetime.utcnow() - timedelta(hours=1))

            # Get new reviews
            response = await self.google_service.get_all_reviews(since_date)

            if response.success and response.data:
                new_reviews = response.data.get("reviews", [])

                # Update last check time
                self.last_check = datetime.utcnow()

                # Generate webhook-style events
                webhook_events = []
                for review in new_reviews:
                    webhook_events.append(
                        {
                            "event_type": "review.created",
                            "timestamp": datetime.utcnow().isoformat(),
                            "data": review,
                            "source": "google_reviews_webhook_simulation",
                        }
                    )

                logger.info(
                    f"Simulated {len(webhook_events)} Google review webhook events"
                )
                return webhook_events

            return []

        except Exception as e:
            logger.error(f"Error in Google reviews webhook simulation: {e}")
            return []

    async def generate_test_review_event(
        self, rating: int = 5, content: str = None
    ) -> Dict[str, Any]:
        """Generate a test review event for development"""
        import uuid

        test_review = {
            "review_id": str(uuid.uuid4()),
            "customer_name": "Test Customer",
            "rating": rating,
            "content": content
            or f"This is a test {rating}-star review for development purposes.",
            "created_at": datetime.utcnow().isoformat(),
            "platform": "google",
            "location_id": "test_location_123",
        }

        return {
            "event_type": "review.created",
            "timestamp": datetime.utcnow().isoformat(),
            "data": test_review,
            "source": "google_reviews_test_generator",
        }


# Factory function to create Google Reviews service
def create_google_reviews_service() -> GoogleReviewsService:
    """Create and configure Google Reviews service"""
    service = GoogleReviewsService()

    # Register with the external service manager
    from .base_service import external_service_manager

    external_service_manager.register_service(service)

    return service


# Create webhook simulator
def create_webhook_simulator(
    google_service: GoogleReviewsService,
) -> GoogleReviewsWebhookSimulator:
    """Create webhook simulator for Google Reviews"""
    return GoogleReviewsWebhookSimulator(google_service)
