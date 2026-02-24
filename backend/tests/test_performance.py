"""
Performance Testing Suite

**Validates: Requirements 2.2, 4.2, 5.2, 6.2**

These tests validate system performance under various load conditions,
ensuring the system meets performance requirements and scales appropriately.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Dict, Any, List
import uuid
import time
import asyncio
import statistics
from concurrent.futures import ThreadPoolExecutor

from app.main import app
from app.core.database import get_async_db
from app.models.user import User
from app.models.organization import Organization
from app.models.review import Review
from app.models.customer import Customer


class TestAPIPerformance:
    """Test API endpoint performance under load"""
    
    @pytest_asyncio.async_test
    async def test_review_ingestion_performance(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: Dict[str, str]
    ):
        """
        Test review ingestion performance with concurrent requests
        
        **Validates: Requirements 4.1, 4.2**
        Performance target: < 500ms per review, handle 10 concurrent requests
        """
        # Test data template
        review_template = {
            "platform": "google",
            "customer_name": "Performance Test Customer",
            "customer_email": "perf.test@example.com",
            "title": "Performance Test Review",
            "content": "This is a performance test review with sufficient content to analyze sentiment and categorization properly.",
            "rating": 3,
            "review_date": datetime.utcnow().isoformat(),
            "reviewer_location": "Test City, TC"
        }
        
        # Test 1: Single request baseline
        start_time = time.time()
        
        single_review = review_template.copy()
        single_review["external_id"] = f"perf_single_{uuid.uuid4()}"
        
        response = await async_client.post(
            "/api/v1/reviews/ingest",
            json=single_review,
            headers=auth_headers
        )
        
        single_request_time = time.time() - start_time
        
        assert response.status_code == 200
        assert single_request_time < 0.5  # Should complete within 500ms
        
        # Test 2: Concurrent requests
        async def ingest_review(review_id: str) -> float:
            """Ingest a single review and return response time"""
            start = time.time()
            
            review_data = review_template.copy()
            review_data["external_id"] = f"perf_concurrent_{review_id}"
            
            response = await async_client.post(
                "/api/v1/reviews/ingest",
                json=review_data,
                headers=auth_headers
            )
            
            end = time.time()
            
            assert response.status_code == 200
            return end - start
        
        # Run 10 concurrent requests
        concurrent_start = time.time()
        
        tasks = [ingest_review(str(i)) for i in range(10)]
        response_times = await asyncio.gather(*tasks)
        
        concurrent_total_time = time.time() - concurrent_start
        
        # Performance assertions
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        
        assert avg_response_time < 1.0  # Average should be under 1 second
        assert max_response_time < 2.0  # Max should be under 2 seconds
        assert concurrent_total_time < 5.0  # All 10 should complete within 5 seconds
        
        # Test 3: Throughput test
        throughput_start = time.time()
        
        # Ingest 20 reviews sequentially to measure throughput
        for i in range(20):
            review_data = review_template.copy()
            review_data["external_id"] = f"perf_throughput_{i}"
            
            response = await async_client.post(
                "/api/v1/reviews/ingest",
                json=review_data,
                headers=auth_headers
            )
            assert response.status_code == 200
        
        throughput_time = time.time() - throughput_start
        throughput = 20 / throughput_time  # Reviews per second
        
        assert throughput > 2.0  # Should handle at least 2 reviews per second
    
    @pytest_asyncio.async_test
    async def test_review_analysis_performance(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: Dict[str, str],
        async_db: AsyncSession
    ):
        """
        Test review analysis performance
        
        **Validates: Requirements 4.2, 5.1**
        Performance target: < 2 seconds per analysis
        """
        # Create test reviews in database
        review_ids = []
        for i in range(5):
            review = Review(
                id=uuid.uuid4(),
                organization_id=test_organization.id,
                platform="google",
                external_id=f"perf_analysis_{i}",
                customer_name=f"Customer {i}",
                customer_email=f"customer{i}@example.com",
                title=f"Review {i}",
                content=f"This is review content {i} with various sentiments and issues to analyze properly for performance testing.",
                rating=(i % 5) + 1,
                review_date=datetime.utcnow(),
                processed=False
            )
            async_db.add(review)
            review_ids.append(str(review.id))
        
        await async_db.commit()
        
        # Test analysis performance
        analysis_times = []
        
        for review_id in review_ids:
            start_time = time.time()
            
            analysis_request = {"review_id": review_id}
            response = await async_client.post(
                "/api/v1/reviews/analyze",
                json=analysis_request,
                headers=auth_headers
            )
            
            analysis_time = time.time() - start_time
            analysis_times.append(analysis_time)
            
            assert response.status_code == 200
            
            # Verify processing time reported by API
            result = response.json()
            api_processing_time = result["processing_time_ms"] / 1000.0
            assert api_processing_time < 2.0  # API should report < 2 seconds
        
        # Performance assertions
        avg_analysis_time = statistics.mean(analysis_times)
        max_analysis_time = max(analysis_times)
        
        assert avg_analysis_time < 2.0  # Average should be under 2 seconds
        assert max_analysis_time < 3.0  # Max should be under 3 seconds
    
    @pytest_asyncio.async_test
    async def test_dashboard_metrics_performance(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: Dict[str, str],
        async_db: AsyncSession
    ):
        """
        Test dashboard metrics performance with substantial data
        
        **Validates: Requirements 2.2, 3.1**
        Performance target: < 3 seconds for dashboard load
        """
        # Create substantial test data
        # Create 50 reviews
        for i in range(50):
            review = Review(
                id=uuid.uuid4(),
                organization_id=test_organization.id,
                platform=["google", "yelp", "facebook"][i % 3],
                external_id=f"perf_dashboard_{i}",
                customer_name=f"Customer {i}",
                customer_email=f"customer{i}@example.com",
                title=f"Review {i}",
                content=f"Review content {i}",
                rating=(i % 5) + 1,
                sentiment_score=(i % 10) / 10.0,
                processed=True,
                review_date=datetime.utcnow() - timedelta(days=i % 30),
                created_at=datetime.utcnow() - timedelta(days=i % 30)
            )
            async_db.add(review)
        
        # Create 20 customers
        for i in range(20):
            customer = Customer(
                id=uuid.uuid4(),
                organization_id=test_organization.id,
                name=f"Customer {i}",
                email=f"customer{i}@example.com",
                churn_risk_score=(i % 10) / 10.0,
                bad_review_likelihood=(i % 8) / 10.0,
                risk_level=["low", "medium", "high"][i % 3]
            )
            async_db.add(customer)
        
        await async_db.commit()
        
        # Test dashboard performance
        start_time = time.time()
        
        response = await async_client.get(
            "/api/v1/dashboard/metrics?time_range=30d",
            headers=auth_headers
        )
        
        dashboard_time = time.time() - start_time
        
        assert response.status_code == 200
        assert dashboard_time < 3.0  # Should load within 3 seconds
        
        # Verify response structure
        result = response.json()
        assert "kpis" in result
        assert "charts" in result
        assert "activity_feed" in result
        
        # Test individual KPI endpoints performance
        kpi_endpoints = [
            "/api/v1/dashboard/kpis",
            "/api/v1/dashboard/activity",
            "/api/v1/dashboard/trends",
            "/api/v1/dashboard/alerts"
        ]
        
        for endpoint in kpi_endpoints:
            start_time = time.time()
            
            response = await async_client.get(endpoint, headers=auth_headers)
            
            endpoint_time = time.time() - start_time
            
            assert response.status_code == 200
            assert endpoint_time < 2.0  # Individual endpoints should be faster


class TestDatabasePerformance:
    """Test database query performance"""
    
    @pytest_asyncio.async_test
    async def test_large_dataset_queries(
        self,
        async_db: AsyncSession,
        test_organization: Organization
    ):
        """
        Test database performance with large datasets
        
        **Validates: Requirements 2.2**
        Performance target: Complex queries < 1 second
        """
        # Create large dataset
        reviews = []
        customers = []
        
        # Create 100 reviews
        for i in range(100):
            review = Review(
                id=uuid.uuid4(),
                organization_id=test_organization.id,
                platform=["google", "yelp", "facebook", "tripadvisor"][i % 4],
                external_id=f"large_dataset_{i}",
                customer_name=f"Customer {i}",
                customer_email=f"customer{i}@example.com",
                title=f"Review {i}",
                content=f"Review content {i} with various keywords and sentiments",
                rating=(i % 5) + 1,
                sentiment_score=(i % 100) / 100.0,
                urgency_level=["low", "medium", "high"][i % 3],
                issue_categories=["support", "pricing", "delivery", "quality"][i % 4:i % 4 + 2],
                processed=True,
                review_date=datetime.utcnow() - timedelta(days=i % 90),
                created_at=datetime.utcnow() - timedelta(days=i % 90)
            )
            reviews.append(review)
        
        # Create 50 customers
        for i in range(50):
            customer = Customer(
                id=uuid.uuid4(),
                organization_id=test_organization.id,
                name=f"Large Dataset Customer {i}",
                email=f"large_customer{i}@example.com",
                phone=f"+123456789{i:02d}",
                churn_risk_score=(i % 100) / 100.0,
                bad_review_likelihood=(i % 80) / 100.0,
                risk_level=["low", "medium", "high"][i % 3],
                total_reviews=i % 10 + 1,
                average_rating=(i % 5) + 1,
                support_tickets_count=i % 5,
                last_interaction=datetime.utcnow() - timedelta(days=i % 30)
            )
            customers.append(customer)
        
        # Bulk insert
        async_db.add_all(reviews + customers)
        await async_db.commit()
        
        # Test complex queries
        from sqlalchemy import select, func, and_, or_, desc
        
        # Query 1: Complex review aggregation
        start_time = time.time()
        
        query = select(
            func.count(Review.id).label("total_reviews"),
            func.avg(Review.rating).label("avg_rating"),
            func.avg(Review.sentiment_score).label("avg_sentiment"),
            Review.platform
        ).where(
            and_(
                Review.organization_id == test_organization.id,
                Review.created_at >= datetime.utcnow() - timedelta(days=30)
            )
        ).group_by(Review.platform)
        
        result = await async_db.execute(query)
        aggregation_time = time.time() - start_time
        
        assert aggregation_time < 1.0  # Should complete within 1 second
        
        # Query 2: Complex customer risk query
        start_time = time.time()
        
        query = select(Customer).where(
            and_(
                Customer.organization_id == test_organization.id,
                or_(
                    Customer.churn_risk_score >= 0.7,
                    Customer.bad_review_likelihood >= 0.6
                ),
                Customer.last_interaction >= datetime.utcnow() - timedelta(days=7)
            )
        ).order_by(desc(Customer.churn_risk_score)).limit(10)
        
        result = await async_db.execute(query)
        risk_query_time = time.time() - start_time
        
        assert risk_query_time < 1.0  # Should complete within 1 second
        
        # Query 3: Join query performance
        start_time = time.time()
        
        # This would be a join if we had foreign keys set up properly
        # For now, test a complex filter query
        query = select(Review).where(
            and_(
                Review.organization_id == test_organization.id,
                Review.rating <= 2,
                Review.sentiment_score <= 0.3,
                Review.urgency_level.in_(["medium", "high"]),
                Review.created_at >= datetime.utcnow() - timedelta(days=30)
            )
        ).order_by(desc(Review.created_at))
        
        result = await async_db.execute(query)
        join_query_time = time.time() - start_time
        
        assert join_query_time < 1.0  # Should complete within 1 second


class TestConcurrencyPerformance:
    """Test system performance under concurrent load"""
    
    @pytest_asyncio.async_test
    async def test_concurrent_user_sessions(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        async_db: AsyncSession
    ):
        """
        Test system performance with multiple concurrent user sessions
        
        **Validates: Requirements 3.1, 3.2**
        Performance target: Handle 5 concurrent users without degradation
        """
        from app.services.auth_service import AuthService
        
        # Create multiple test users
        auth_service = AuthService()
        users = []
        tokens = []
        
        for i in range(5):
            user_data = {
                "email": f"concurrent_user_{i}@example.com",
                "password": "password123",
                "full_name": f"Concurrent User {i}",
                "organization_id": str(test_organization.id)
            }
            user = await auth_service.create_user(async_db, **user_data)
            users.append(user)
            
            # Login to get token
            login_response = await async_client.post(
                "/api/v1/auth/login",
                json={"email": user_data["email"], "password": "password123"}
            )
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]
            tokens.append(token)
        
        # Test concurrent operations
        async def user_workflow(user_index: int, token: str) -> Dict[str, float]:
            """Simulate a complete user workflow and measure performance"""
            headers = {"Authorization": f"Bearer {token}"}
            times = {}
            
            # 1. Ingest a review
            start_time = time.time()
            review_data = {
                "platform": "google",
                "external_id": f"concurrent_{user_index}_{uuid.uuid4()}",
                "customer_name": f"Concurrent Customer {user_index}",
                "customer_email": f"concurrent{user_index}@example.com",
                "title": f"Concurrent Review {user_index}",
                "content": f"This is a concurrent review {user_index} for performance testing",
                "rating": (user_index % 5) + 1,
                "review_date": datetime.utcnow().isoformat()
            }
            
            response = await async_client.post(
                "/api/v1/reviews/ingest",
                json=review_data,
                headers=headers
            )
            assert response.status_code == 200
            review_id = response.json()["id"]
            times["ingest"] = time.time() - start_time
            
            # 2. Analyze the review
            start_time = time.time()
            analysis_request = {"review_id": review_id}
            response = await async_client.post(
                "/api/v1/reviews/analyze",
                json=analysis_request,
                headers=headers
            )
            assert response.status_code == 200
            times["analyze"] = time.time() - start_time
            
            # 3. Get dashboard metrics
            start_time = time.time()
            response = await async_client.get(
                "/api/v1/dashboard/metrics",
                headers=headers
            )
            assert response.status_code == 200
            times["dashboard"] = time.time() - start_time
            
            # 4. Get reviews list
            start_time = time.time()
            response = await async_client.get(
                "/api/v1/reviews/",
                headers=headers
            )
            assert response.status_code == 200
            times["list_reviews"] = time.time() - start_time
            
            return times
        
        # Run concurrent workflows
        start_time = time.time()
        
        tasks = [user_workflow(i, tokens[i]) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Analyze results
        all_ingest_times = [r["ingest"] for r in results]
        all_analyze_times = [r["analyze"] for r in results]
        all_dashboard_times = [r["dashboard"] for r in results]
        all_list_times = [r["list_reviews"] for r in results]
        
        # Performance assertions
        assert statistics.mean(all_ingest_times) < 2.0  # Average ingest time
        assert statistics.mean(all_analyze_times) < 3.0  # Average analysis time
        assert statistics.mean(all_dashboard_times) < 5.0  # Average dashboard time
        assert statistics.mean(all_list_times) < 2.0  # Average list time
        
        assert max(all_ingest_times) < 5.0  # Max ingest time
        assert max(all_analyze_times) < 8.0  # Max analysis time
        assert max(all_dashboard_times) < 10.0  # Max dashboard time
        
        assert total_time < 15.0  # All concurrent workflows should complete within 15 seconds


class TestMemoryPerformance:
    """Test memory usage and efficiency"""
    
    @pytest_asyncio.async_test
    async def test_memory_usage_under_load(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: Dict[str, str]
    ):
        """
        Test memory usage during intensive operations
        
        **Validates: Requirements 2.2, 4.2**
        Performance target: Memory usage should remain stable
        """
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform memory-intensive operations
        review_ids = []
        
        # Create 50 reviews to test memory usage
        for i in range(50):
            review_data = {
                "platform": "google",
                "external_id": f"memory_test_{i}",
                "customer_name": f"Memory Test Customer {i}",
                "customer_email": f"memory{i}@example.com",
                "title": f"Memory Test Review {i}",
                "content": f"This is a memory test review {i} with substantial content to test memory usage during processing. " * 10,  # Large content
                "rating": (i % 5) + 1,
                "review_date": datetime.utcnow().isoformat()
            }
            
            response = await async_client.post(
                "/api/v1/reviews/ingest",
                json=review_data,
                headers=auth_headers
            )
            assert response.status_code == 200
            review_ids.append(response.json()["id"])
        
        # Analyze all reviews
        for review_id in review_ids:
            analysis_request = {"review_id": review_id}
            response = await async_client.post(
                "/api/v1/reviews/analyze",
                json=analysis_request,
                headers=auth_headers
            )
            assert response.status_code == 200
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory should not increase excessively (allow up to 100MB increase)
        assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB, which is too much"
        
        # Test garbage collection by making multiple dashboard requests
        for _ in range(10):
            response = await async_client.get(
                "/api/v1/dashboard/metrics",
                headers=auth_headers
            )
            assert response.status_code == 200
        
        # Memory should not continue growing significantly
        gc_memory = process.memory_info().rss / 1024 / 1024  # MB
        gc_increase = gc_memory - final_memory
        
        assert gc_increase < 20, f"Memory increased by {gc_increase:.2f}MB during GC test"


class TestScalabilityPerformance:
    """Test system scalability characteristics"""
    
    @pytest_asyncio.async_test
    async def test_data_volume_scalability(
        self,
        async_client: AsyncClient,
        test_organization: Organization,
        test_user: User,
        auth_headers: Dict[str, str],
        async_db: AsyncSession
    ):
        """
        Test system performance as data volume increases
        
        **Validates: Requirements 2.2, 4.2**
        Performance target: Performance should degrade gracefully with data volume
        """
        # Test with increasing data volumes
        volumes = [10, 50, 100]  # Number of reviews to create
        performance_results = {}
        
        for volume in volumes:
            # Create test data
            for i in range(volume):
                review = Review(
                    id=uuid.uuid4(),
                    organization_id=test_organization.id,
                    platform=["google", "yelp", "facebook"][i % 3],
                    external_id=f"scalability_{volume}_{i}",
                    customer_name=f"Scalability Customer {i}",
                    customer_email=f"scalability{i}@example.com",
                    title=f"Scalability Review {i}",
                    content=f"Scalability test review content {i}",
                    rating=(i % 5) + 1,
                    sentiment_score=(i % 10) / 10.0,
                    processed=True,
                    review_date=datetime.utcnow() - timedelta(days=i % 30),
                    created_at=datetime.utcnow() - timedelta(days=i % 30)
                )
                async_db.add(review)
            
            await async_db.commit()
            
            # Test dashboard performance with this volume
            start_time = time.time()
            
            response = await async_client.get(
                "/api/v1/dashboard/metrics?time_range=30d",
                headers=auth_headers
            )
            
            dashboard_time = time.time() - start_time
            
            assert response.status_code == 200
            performance_results[volume] = dashboard_time
            
            # Test reviews list performance
            start_time = time.time()
            
            response = await async_client.get(
                "/api/v1/reviews/?limit=50",
                headers=auth_headers
            )
            
            list_time = time.time() - start_time
            
            assert response.status_code == 200
            performance_results[f"{volume}_list"] = list_time
        
        # Verify performance degrades gracefully (not exponentially)
        dashboard_10 = performance_results[10]
        dashboard_100 = performance_results[100]
        
        # Performance should not degrade more than 5x with 10x data
        degradation_factor = dashboard_100 / dashboard_10
        assert degradation_factor < 5.0, f"Performance degraded by {degradation_factor:.2f}x, which is too much"
        
        # All operations should still complete within reasonable time
        assert dashboard_100 < 10.0, f"Dashboard with 100 reviews took {dashboard_100:.2f}s, too slow"