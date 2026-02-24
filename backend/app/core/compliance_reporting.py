"""
Compliance reporting service for privacy and data protection
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_
from enum import Enum
import json
import logging

from app.core.database import get_db
from app.core.gdpr_compliance import get_gdpr_service
from app.core.consent_management import get_consent_service
from app.core.data_retention import get_retention_service
from app.core.privacy_policy import get_privacy_policy_service
from app.models.user import User
from app.models.customer import Customer
from app.models.organization import Organization

logger = logging.getLogger(__name__)


class ReportType(Enum):
    """Types of compliance reports"""
    GDPR_COMPLIANCE = "gdpr_compliance"
    CONSENT_MANAGEMENT = "consent_management"
    DATA_RETENTION = "data_retention"
    PRIVACY_POLICY = "privacy_policy"
    SECURITY_AUDIT = "security_audit"
    DATA_BREACH = "data_breach"
    COMPREHENSIVE = "comprehensive"


class ReportPeriod(Enum):
    """Report time periods"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class ComplianceMetric:
    """Individual compliance metric"""
    
    def __init__(
        self,
        name: str,
        value: Union[int, float, str],
        target: Union[int, float, str] = None,
        status: str = "unknown",
        description: str = None,
        trend: str = None
    ):
        self.name = name
        self.value = value
        self.target = target
        self.status = status  # "compliant", "non_compliant", "warning", "unknown"
        self.description = description
        self.trend = trend  # "improving", "declining", "stable"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "value": self.value,
            "target": self.target,
            "status": self.status,
            "description": self.description,
            "trend": self.trend
        }


class ComplianceReport:
    """Compliance report container"""
    
    def __init__(
        self,
        report_id: str,
        organization_id: str,
        report_type: ReportType,
        period_start: datetime,
        period_end: datetime,
        generated_at: datetime = None
    ):
        self.report_id = report_id
        self.organization_id = organization_id
        self.report_type = report_type
        self.period_start = period_start
        self.period_end = period_end
        self.generated_at = generated_at or datetime.now(timezone.utc)
        self.metrics: List[ComplianceMetric] = []
        self.summary: Dict[str, Any] = {}
        self.recommendations: List[str] = []
        self.issues: List[Dict[str, Any]] = []
    
    def add_metric(self, metric: ComplianceMetric):
        """Add metric to report"""
        self.metrics.append(metric)
    
    def add_issue(self, severity: str, title: str, description: str, recommendation: str = None):
        """Add compliance issue"""
        issue = {
            "severity": severity,  # "critical", "high", "medium", "low"
            "title": title,
            "description": description,
            "recommendation": recommendation,
            "identified_at": datetime.now(timezone.utc).isoformat()
        }
        self.issues.append(issue)
        
        if recommendation:
            self.recommendations.append(recommendation)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "report_id": self.report_id,
            "organization_id": self.organization_id,
            "report_type": self.report_type.value,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "generated_at": self.generated_at.isoformat(),
            "summary": self.summary,
            "metrics": [metric.to_dict() for metric in self.metrics],
            "issues": self.issues,
            "recommendations": self.recommendations,
            "compliance_score": self._calculate_compliance_score()
        }
    
    def _calculate_compliance_score(self) -> float:
        """Calculate overall compliance score"""
        if not self.metrics:
            return 0.0
        
        compliant_metrics = sum(1 for m in self.metrics if m.status == "compliant")
        total_metrics = len(self.metrics)
        
        base_score = (compliant_metrics / total_metrics) * 100
        
        # Adjust for issues
        critical_issues = sum(1 for i in self.issues if i["severity"] == "critical")
        high_issues = sum(1 for i in self.issues if i["severity"] == "high")
        
        penalty = (critical_issues * 10) + (high_issues * 5)
        
        return max(0.0, base_score - penalty)


class ComplianceReportingService:
    """Service for generating compliance reports"""
    
    def __init__(self):
        self.reports: Dict[str, ComplianceReport] = {}  # report_id -> report
    
    async def generate_gdpr_compliance_report(
        self,
        organization_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> ComplianceReport:
        """Generate GDPR compliance report"""
        
        import uuid
        report_id = str(uuid.uuid4())
        
        report = ComplianceReport(
            report_id=report_id,
            organization_id=organization_id,
            report_type=ReportType.GDPR_COMPLIANCE,
            period_start=period_start,
            period_end=period_end
        )
        
        # Get GDPR service
        gdpr_service = get_gdpr_service()
        
        # Data subject requests metrics
        await self._add_gdpr_request_metrics(report, gdpr_service)
        
        # Data processing purposes
        await self._add_processing_purposes_metrics(report, gdpr_service)
        
        # Data retention compliance
        await self._add_data_retention_metrics(report, organization_id)
        
        # Rights fulfillment metrics
        await self._add_rights_fulfillment_metrics(report, gdpr_service)
        
        # Summary
        report.summary = {
            "total_data_subjects": await self._count_data_subjects(organization_id),
            "active_processing_purposes": len(gdpr_service.get_processing_purposes()),
            "gdpr_requests_period": len([r for r in gdpr_service.pending_requests.values() 
                                       if period_start <= r.created_at <= period_end]),
            "compliance_status": "compliant" if report._calculate_compliance_score() >= 80 else "non_compliant"
        }
        
        self.reports[report_id] = report
        logger.info(f"Generated GDPR compliance report {report_id} for organization {organization_id}")
        
        return report
    
    async def generate_consent_management_report(
        self,
        organization_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> ComplianceReport:
        """Generate consent management report"""
        
        import uuid
        report_id = str(uuid.uuid4())
        
        report = ComplianceReport(
            report_id=report_id,
            organization_id=organization_id,
            report_type=ReportType.CONSENT_MANAGEMENT,
            period_start=period_start,
            period_end=period_end
        )
        
        # Get consent service
        consent_service = get_consent_service()
        
        # Consent rates by type
        await self._add_consent_rate_metrics(report, consent_service, organization_id)
        
        # Consent withdrawal rates
        await self._add_consent_withdrawal_metrics(report, consent_service, organization_id)
        
        # Consent expiry tracking
        await self._add_consent_expiry_metrics(report, consent_service, organization_id)
        
        # Consent method effectiveness
        await self._add_consent_method_metrics(report, consent_service, organization_id)
        
        # Generate consent report
        consent_report = consent_service.generate_consent_report(organization_id)
        
        # Summary
        report.summary = {
            "total_users_with_consent": consent_report["total_users"],
            "total_consent_records": consent_report["total_records"],
            "consent_statistics": consent_report["consent_statistics"],
            "average_consent_rate": self._calculate_average_consent_rate(consent_report)
        }
        
        self.reports[report_id] = report
        logger.info(f"Generated consent management report {report_id} for organization {organization_id}")
        
        return report
    
    async def generate_data_retention_report(
        self,
        organization_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> ComplianceReport:
        """Generate data retention report"""
        
        import uuid
        report_id = str(uuid.uuid4())
        
        report = ComplianceReport(
            report_id=report_id,
            organization_id=organization_id,
            report_type=ReportType.DATA_RETENTION,
            period_start=period_start,
            period_end=period_end
        )
        
        # Get retention service
        retention_service = get_retention_service()
        
        # Retention policy compliance
        await self._add_retention_policy_metrics(report, retention_service, organization_id)
        
        # Data cleanup metrics
        await self._add_data_cleanup_metrics(report, retention_service, period_start, period_end)
        
        # Legal hold status
        await self._add_legal_hold_metrics(report, retention_service, organization_id)
        
        # Storage metrics
        await self._add_storage_metrics(report, organization_id)
        
        # Generate retention report
        retention_report = retention_service.get_retention_report()
        
        # Summary
        report.summary = {
            "total_policies": retention_report["total_policies"],
            "auto_delete_policies": retention_report["auto_delete_policies"],
            "legal_holds_active": len(retention_report["legal_holds"]),
            "retention_compliance_score": await self._calculate_retention_compliance_score(organization_id)
        }
        
        self.reports[report_id] = report
        logger.info(f"Generated data retention report {report_id} for organization {organization_id}")
        
        return report
    
    async def generate_comprehensive_report(
        self,
        organization_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> ComplianceReport:
        """Generate comprehensive compliance report"""
        
        import uuid
        report_id = str(uuid.uuid4())
        
        report = ComplianceReport(
            report_id=report_id,
            organization_id=organization_id,
            report_type=ReportType.COMPREHENSIVE,
            period_start=period_start,
            period_end=period_end
        )
        
        # Generate individual reports
        gdpr_report = await self.generate_gdpr_compliance_report(organization_id, period_start, period_end)
        consent_report = await self.generate_consent_management_report(organization_id, period_start, period_end)
        retention_report = await self.generate_data_retention_report(organization_id, period_start, period_end)
        
        # Combine metrics
        report.metrics.extend(gdpr_report.metrics)
        report.metrics.extend(consent_report.metrics)
        report.metrics.extend(retention_report.metrics)
        
        # Combine issues
        report.issues.extend(gdpr_report.issues)
        report.issues.extend(consent_report.issues)
        report.issues.extend(retention_report.issues)
        
        # Combine recommendations
        report.recommendations.extend(gdpr_report.recommendations)
        report.recommendations.extend(consent_report.recommendations)
        report.recommendations.extend(retention_report.recommendations)
        
        # Remove duplicates
        report.recommendations = list(set(report.recommendations))
        
        # Comprehensive summary
        report.summary = {
            "gdpr_compliance": gdpr_report.summary,
            "consent_management": consent_report.summary,
            "data_retention": retention_report.summary,
            "overall_compliance_score": report._calculate_compliance_score(),
            "critical_issues": len([i for i in report.issues if i["severity"] == "critical"]),
            "high_priority_issues": len([i for i in report.issues if i["severity"] == "high"]),
            "total_recommendations": len(report.recommendations)
        }
        
        self.reports[report_id] = report
        logger.info(f"Generated comprehensive compliance report {report_id} for organization {organization_id}")
        
        return report
    
    async def _add_gdpr_request_metrics(self, report: ComplianceReport, gdpr_service):
        """Add GDPR request metrics to report"""
        
        # Count requests by type
        request_counts = {}
        response_times = []
        
        for request in gdpr_service.pending_requests.values():
            if request.organization_id == report.organization_id:
                request_type = request.request_type.value
                request_counts[request_type] = request_counts.get(request_type, 0) + 1
                
                # Calculate response time if completed
                if request.completed_at and request.created_at:
                    response_time = (request.completed_at - request.created_at).total_seconds() / 3600  # hours
                    response_times.append(response_time)
        
        # Add metrics
        total_requests = sum(request_counts.values())
        report.add_metric(ComplianceMetric(
            name="Total GDPR Requests",
            value=total_requests,
            target=None,
            status="compliant" if total_requests >= 0 else "unknown",
            description="Total number of GDPR data subject requests received"
        ))
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            report.add_metric(ComplianceMetric(
                name="Average Response Time (hours)",
                value=round(avg_response_time, 2),
                target=720,  # 30 days in hours
                status="compliant" if avg_response_time <= 720 else "non_compliant",
                description="Average time to complete GDPR requests (target: 30 days)"
            ))
            
            if avg_response_time > 720:
                report.add_issue(
                    severity="high",
                    title="GDPR Response Time Exceeded",
                    description=f"Average response time ({avg_response_time:.1f} hours) exceeds 30-day requirement",
                    recommendation="Implement automated processing and dedicated GDPR team"
                )
    
    async def _add_processing_purposes_metrics(self, report: ComplianceReport, gdpr_service):
        """Add data processing purposes metrics"""
        
        purposes = gdpr_service.get_processing_purposes()
        
        report.add_metric(ComplianceMetric(
            name="Documented Processing Purposes",
            value=len(purposes),
            target=None,
            status="compliant" if len(purposes) > 0 else "non_compliant",
            description="Number of documented data processing purposes"
        ))
        
        # Check for consent-based processing
        consent_based = sum(1 for p in purposes.values() if p["lawful_basis"] == "consent")
        report.add_metric(ComplianceMetric(
            name="Consent-Based Processing Activities",
            value=consent_based,
            target=None,
            status="compliant",
            description="Number of processing activities based on consent"
        ))
    
    async def _add_data_retention_metrics(self, report: ComplianceReport, organization_id: str):
        """Add data retention metrics"""
        
        retention_service = get_retention_service()
        
        # Check for expired data
        total_expired = 0
        for policy_name in retention_service.policies.keys():
            expired_data = await retention_service.get_expired_data(policy_name)
            total_expired += len(expired_data)
        
        report.add_metric(ComplianceMetric(
            name="Expired Data Records",
            value=total_expired,
            target=0,
            status="compliant" if total_expired == 0 else "warning",
            description="Number of data records past retention period"
        ))
        
        if total_expired > 0:
            report.add_issue(
                severity="medium",
                title="Expired Data Found",
                description=f"{total_expired} records found past retention period",
                recommendation="Run automated data cleanup process"
            )
    
    async def _add_rights_fulfillment_metrics(self, report: ComplianceReport, gdpr_service):
        """Add data subject rights fulfillment metrics"""
        
        completed_requests = [
            r for r in gdpr_service.pending_requests.values()
            if r.organization_id == report.organization_id and r.status == "completed"
        ]
        
        total_requests = [
            r for r in gdpr_service.pending_requests.values()
            if r.organization_id == report.organization_id
        ]
        
        if total_requests:
            fulfillment_rate = (len(completed_requests) / len(total_requests)) * 100
            report.add_metric(ComplianceMetric(
                name="Rights Fulfillment Rate (%)",
                value=round(fulfillment_rate, 1),
                target=95.0,
                status="compliant" if fulfillment_rate >= 95 else "non_compliant",
                description="Percentage of data subject rights requests fulfilled"
            ))
    
    async def _add_consent_rate_metrics(self, report: ComplianceReport, consent_service, organization_id: str):
        """Add consent rate metrics"""
        
        consent_report = consent_service.generate_consent_report(organization_id)
        
        for consent_type, stats in consent_report["consent_statistics"].items():
            if stats["total"] > 0:
                consent_rate = stats["consent_rate"]
                report.add_metric(ComplianceMetric(
                    name=f"{consent_type.title()} Consent Rate (%)",
                    value=round(consent_rate, 1),
                    target=None,
                    status="compliant" if consent_rate >= 0 else "unknown",
                    description=f"Percentage of users who granted {consent_type} consent"
                ))
    
    async def _add_consent_withdrawal_metrics(self, report: ComplianceReport, consent_service, organization_id: str):
        """Add consent withdrawal metrics"""
        
        # This would require tracking withdrawal rates over time
        # For now, we'll add a placeholder metric
        report.add_metric(ComplianceMetric(
            name="Consent Withdrawal Requests",
            value=0,  # Would be calculated from actual data
            target=None,
            status="compliant",
            description="Number of consent withdrawal requests processed"
        ))
    
    async def _add_consent_expiry_metrics(self, report: ComplianceReport, consent_service, organization_id: str):
        """Add consent expiry tracking metrics"""
        
        expired_count = await consent_service.expire_old_consent()
        
        report.add_metric(ComplianceMetric(
            name="Expired Consent Records",
            value=expired_count,
            target=0,
            status="compliant" if expired_count == 0 else "warning",
            description="Number of consent records that have expired"
        ))
    
    async def _add_consent_method_metrics(self, report: ComplianceReport, consent_service, organization_id: str):
        """Add consent method effectiveness metrics"""
        
        # This would analyze which consent collection methods are most effective
        # For now, we'll add placeholder metrics
        report.add_metric(ComplianceMetric(
            name="Consent Collection Methods",
            value=3,  # Number of different methods used
            target=None,
            status="compliant",
            description="Number of different consent collection methods in use"
        ))
    
    async def _add_retention_policy_metrics(self, report: ComplianceReport, retention_service, organization_id: str):
        """Add retention policy metrics"""
        
        retention_report = retention_service.get_retention_report()
        
        report.add_metric(ComplianceMetric(
            name="Active Retention Policies",
            value=retention_report["total_policies"],
            target=None,
            status="compliant" if retention_report["total_policies"] > 0 else "non_compliant",
            description="Number of active data retention policies"
        ))
        
        report.add_metric(ComplianceMetric(
            name="Automated Deletion Policies",
            value=retention_report["auto_delete_policies"],
            target=None,
            status="compliant",
            description="Number of policies with automated deletion enabled"
        ))
    
    async def _add_data_cleanup_metrics(self, report: ComplianceReport, retention_service, period_start: datetime, period_end: datetime):
        """Add data cleanup metrics"""
        
        # Run retention cleanup to get metrics
        cleanup_results = await retention_service.run_retention_cleanup(dry_run=True)
        
        report.add_metric(ComplianceMetric(
            name="Records Eligible for Deletion",
            value=cleanup_results["total_records_found"],
            target=0,
            status="warning" if cleanup_results["total_records_found"] > 0 else "compliant",
            description="Number of records eligible for deletion based on retention policies"
        ))
    
    async def _add_legal_hold_metrics(self, report: ComplianceReport, retention_service, organization_id: str):
        """Add legal hold metrics"""
        
        has_legal_hold = retention_service.has_legal_hold(organization_id)
        
        report.add_metric(ComplianceMetric(
            name="Legal Hold Status",
            value="Active" if has_legal_hold else "None",
            target=None,
            status="compliant",
            description="Current legal hold status for the organization"
        ))
    
    async def _add_storage_metrics(self, report: ComplianceReport, organization_id: str):
        """Add storage and data volume metrics"""
        
        # This would query actual database sizes
        # For now, we'll add placeholder metrics
        report.add_metric(ComplianceMetric(
            name="Total Data Records",
            value=await self._count_total_records(organization_id),
            target=None,
            status="compliant",
            description="Total number of data records stored"
        ))
    
    async def _count_data_subjects(self, organization_id: str) -> int:
        """Count unique data subjects for organization"""
        db = next(get_db())
        try:
            # Count unique users and customers
            user_count = db.query(User).filter(User.organization_id == organization_id).count()
            customer_count = db.query(Customer).filter(Customer.organization_id == organization_id).count()
            
            # Remove duplicates (users who are also customers)
            # This is a simplified approach
            return user_count + customer_count
        finally:
            db.close()
    
    async def _count_total_records(self, organization_id: str) -> int:
        """Count total records for organization"""
        db = next(get_db())
        try:
            total = 0
            
            # Count records from various tables
            total += db.query(User).filter(User.organization_id == organization_id).count()
            total += db.query(Customer).filter(Customer.organization_id == organization_id).count()
            
            # Add other model counts as needed
            
            return total
        finally:
            db.close()
    
    def _calculate_average_consent_rate(self, consent_report: Dict[str, Any]) -> float:
        """Calculate average consent rate across all consent types"""
        rates = []
        for stats in consent_report["consent_statistics"].values():
            if stats["total"] > 0:
                rates.append(stats["consent_rate"])
        
        return sum(rates) / len(rates) if rates else 0.0
    
    async def _calculate_retention_compliance_score(self, organization_id: str) -> float:
        """Calculate retention compliance score"""
        retention_service = get_retention_service()
        
        # Check for expired data across all policies
        total_expired = 0
        total_policies = 0
        
        for policy_name in retention_service.policies.keys():
            expired_data = await retention_service.get_expired_data(policy_name)
            total_expired += len(expired_data)
            total_policies += 1
        
        # Score based on expired data
        if total_expired == 0:
            return 100.0
        elif total_expired < 100:
            return 80.0
        elif total_expired < 1000:
            return 60.0
        else:
            return 40.0
    
    def get_report(self, report_id: str) -> Optional[ComplianceReport]:
        """Get report by ID"""
        return self.reports.get(report_id)
    
    def list_reports(self, organization_id: str) -> List[Dict[str, Any]]:
        """List all reports for organization"""
        org_reports = [
            {
                "report_id": report.report_id,
                "report_type": report.report_type.value,
                "period_start": report.period_start.isoformat(),
                "period_end": report.period_end.isoformat(),
                "generated_at": report.generated_at.isoformat(),
                "compliance_score": report._calculate_compliance_score()
            }
            for report in self.reports.values()
            if report.organization_id == organization_id
        ]
        
        return sorted(org_reports, key=lambda r: r["generated_at"], reverse=True)
    
    async def schedule_automated_reports(
        self,
        organization_id: str,
        report_types: List[ReportType],
        frequency: ReportPeriod
    ):
        """Schedule automated report generation"""
        
        # This would integrate with a task scheduler like Celery
        # For now, we'll just log the scheduling
        logger.info(f"Scheduled automated reports for {organization_id}: {[rt.value for rt in report_types]} every {frequency.value}")
        
        # In a real implementation, this would:
        # 1. Create scheduled tasks
        # 2. Store scheduling configuration
        # 3. Set up periodic execution
        # 4. Handle report delivery (email, dashboard, etc.)


# Global compliance reporting service instance
_compliance_reporting_service = None


def get_compliance_reporting_service() -> ComplianceReportingService:
    """Get global compliance reporting service instance"""
    global _compliance_reporting_service
    
    if _compliance_reporting_service is None:
        _compliance_reporting_service = ComplianceReportingService()
    
    return _compliance_reporting_service
