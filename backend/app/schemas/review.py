"""
Review schemas for request/response validation
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

from app.models.review import ReviewPlatform, UrgencyLevel, ReviewStatus, IssueCategory


class ReviewIngest(BaseModel):
    """Review ingestion request schema"""
    platform: ReviewPlatform
    external_id: Optional[str] = None
    review_url: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    review_date: Optional[datetime] = None
    
    @field_validator('content')
    def validate_content(cls, v):
        if v and len(v.strip()) == 0:
            return None
        return v.strip() if v else None
    
    @field_validator('customer_email')
    def validate_email(cls, v):
        if v:
            return v.lower().strip()
        return None


class ReviewResponse(BaseModel):
    """Review response schema"""
    id: str
    platform: str
    external_id: Optional[str]
    review_url: Optional[str]
    customer_name: Optional[str]
    customer_email: Optional[str]
    rating: int
    title: Optional[str]
    content: Optional[str]
    sentiment_score: Optional[float]
    sentiment_label: str
    urgency_level: Optional[str]
    issue_categories: List[str]
    status: str
    requires_private_recovery: bool
    public_response: Optional[str]
    public_response_date: Optional[datetime]
    review_date: Optional[datetime]
    processed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    is_positive: bool
    is_negative: bool
    is_neutral: bool
    is_critical: bool
    days_since_posted: Optional[int]
    
    class Config:
        from_attributes = True
    
    @model_validator(mode='before')
    @classmethod
    def convert_uuids(cls, data):
        """Convert UUID fields to strings"""
        if isinstance(data, dict):
            if 'id' in data and data['id'] is not None:
                data['id'] = str(data['id'])
            return data
        # Handle SQLAlchemy model objects
        if hasattr(data, 'id') and data.id is not None:
            # Create a dict from the model
            result = {}
            for field in cls.model_fields:
                if hasattr(data, field):
                    value = getattr(data, field)
                    if field == 'id' and value is not None:
                        result[field] = str(value)
                    else:
                        result[field] = value
            return result
        return data
    
    @model_validator(mode='after')
    def set_sentiment_label(self) -> 'ReviewResponse':
        """Set sentiment label based on sentiment score"""
        if self.sentiment_label:
            return self
        
        if self.sentiment_score is None:
            self.sentiment_label = "Unknown"
            return self
        
        score = float(self.sentiment_score)
        if score >= 0.7:
            self.sentiment_label = "Very Positive"
        elif score >= 0.5:
            self.sentiment_label = "Positive"
        elif score >= 0.3:
            self.sentiment_label = "Neutral"
        elif score >= 0.1:
            self.sentiment_label = "Negative"
        else:
            self.sentiment_label = "Very Negative"
        
        return self
    
    @field_validator('issue_categories', mode='before')
    @classmethod
    def convert_issue_categories(cls, v):
        """Convert issue categories to list of strings"""
        if not v:
            return []
        if isinstance(v, list):
            return [cat.value if hasattr(cat, 'value') else str(cat) for cat in v]
        return []


class ReviewAnalysisRequest(BaseModel):
    """Review analysis request schema"""
    review_id: str


class ReviewAnalysisResponse(BaseModel):
    """Review analysis response schema"""
    review_id: str
    sentiment_score: float
    sentiment_label: str
    urgency_level: str
    issue_categories: List[str]
    confidence_scores: dict
    processing_time_ms: int
    recommendations: List[str]


class ReviewResponseRequest(BaseModel):
    """Review response request schema"""
    review_id: str
    response_type: str = Field(..., pattern="^(public|private)$")
    custom_instructions: Optional[str] = None
    tone: Optional[str] = Field("professional", pattern="^(professional|friendly|apologetic|formal)$")
    max_length: Optional[int] = Field(150, ge=50, le=500)


class ReviewResponseGenerated(BaseModel):
    """Generated review response schema"""
    review_id: str
    response_content: str
    response_type: str
    tone: str
    confidence_score: float
    requires_approval: bool
    generated_at: datetime


class SaveResponseRequest(BaseModel):
    """Save or publish response request schema"""
    content: str = Field(..., min_length=1, max_length=2000)
    action: str = Field("publish", pattern="^(save_draft|publish)$")


class ReviewFilter(BaseModel):
    """Review filtering schema"""
    platform: Optional[ReviewPlatform] = None
    rating_min: Optional[int] = Field(None, ge=1, le=5)
    rating_max: Optional[int] = Field(None, ge=1, le=5)
    sentiment_min: Optional[float] = Field(None, ge=0.0, le=1.0)
    sentiment_max: Optional[float] = Field(None, ge=0.0, le=1.0)
    urgency_level: Optional[UrgencyLevel] = None
    status: Optional[ReviewStatus] = None
    issue_categories: Optional[List[IssueCategory]] = None
    requires_private_recovery: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None


class ReviewStats(BaseModel):
    """Review statistics schema"""
    total_reviews: int
    avg_rating: float
    rating_distribution: dict
    sentiment_distribution: dict
    urgency_distribution: dict
    status_distribution: dict
    category_distribution: dict
    recent_reviews: int
    response_rate: float
    private_recovery_rate: float



class ReviewCreate(BaseModel):
    """Review creation schema"""
    platform: ReviewPlatform
    external_id: Optional[str] = None
    review_url: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    review_date: Optional[datetime] = None


class ReviewUpdate(BaseModel):
    """Review update schema"""
    status: Optional[ReviewStatus] = None
    public_response: Optional[str] = None
    requires_private_recovery: Optional[bool] = None


class ReviewAnalysis(BaseModel):
    """Review analysis result schema"""
    sentiment_score: float
    sentiment_label: str
    urgency_level: str
    issue_categories: List[str]
    confidence_scores: dict


class ReviewListFilter(BaseModel):
    """Review list filtering schema"""
    platform: Optional[str] = None
    rating_min: Optional[int] = Field(None, ge=1, le=5)
    rating_max: Optional[int] = Field(None, ge=1, le=5)
    status: Optional[str] = None
    search: Optional[str] = None


class BulkReviewUpdate(BaseModel):
    """Bulk review update schema"""
    review_ids: List[str]
    updates: ReviewUpdate
