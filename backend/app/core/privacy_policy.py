"""
Privacy policy and terms of service management
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PolicyType(Enum):
    """Types of policies"""
    PRIVACY_POLICY = "privacy_policy"
    TERMS_OF_SERVICE = "terms_of_service"
    COOKIE_POLICY = "cookie_policy"
    DATA_PROCESSING_AGREEMENT = "data_processing_agreement"


class PolicyVersion:
    """Policy version with content and metadata"""
    
    def __init__(
        self,
        version: str,
        content: str,
        effective_date: datetime,
        created_at: datetime = None,
        summary_of_changes: str = None
    ):
        self.version = version
        self.content = content
        self.effective_date = effective_date
        self.created_at = created_at or datetime.now(timezone.utc)
        self.summary_of_changes = summary_of_changes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "version": self.version,
            "content": self.content,
            "effective_date": self.effective_date.isoformat(),
            "created_at": self.created_at.isoformat(),
            "summary_of_changes": self.summary_of_changes
        }


class PrivacyPolicyService:
    """Service for managing privacy policies and terms of service"""
    
    def __init__(self):
        self.policies: Dict[str, Dict[PolicyType, List[PolicyVersion]]] = {}  # org_id -> policy_type -> versions
        self._initialize_default_policies()
    
    def _initialize_default_policies(self):
        """Initialize default policy templates"""
        self.policy_templates = {
            PolicyType.PRIVACY_POLICY: self._get_privacy_policy_template(),
            PolicyType.TERMS_OF_SERVICE: self._get_terms_of_service_template(),
            PolicyType.COOKIE_POLICY: self._get_cookie_policy_template(),
            PolicyType.DATA_PROCESSING_AGREEMENT: self._get_dpa_template()
        }
    
    def _get_privacy_policy_template(self) -> str:
        """Get privacy policy template"""
        return """# Privacy Policy

**Effective Date:** {effective_date}
**Last Updated:** {last_updated}

## 1. Introduction

Welcome to Revive AI ("we," "our," or "us"). This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our customer review management and recovery platform.

## 2. Information We Collect

### 2.1 Personal Information
We collect personal information that you provide directly to us, including:
- **Account Information:** Name, email address, phone number, company information
- **Profile Information:** Job title, preferences, settings
- **Communication Data:** Messages, support tickets, feedback

### 2.2 Customer Data
When you use our services, we may collect information about your customers:
- **Review Data:** Customer reviews, ratings, feedback from various platforms
- **Contact Information:** Customer names, email addresses (when provided)
- **Interaction History:** Support tickets, recovery actions, communications

### 2.3 Technical Information
We automatically collect certain technical information:
- **Usage Data:** How you interact with our services, features used, time spent
- **Device Information:** IP address, browser type, operating system
- **Log Data:** Server logs, error reports, performance metrics

## 3. How We Use Your Information

We use the collected information for the following purposes:

### 3.1 Service Provision
- Provide and maintain our review management platform
- Process and analyze customer reviews
- Generate automated responses and recovery recommendations
- Facilitate customer support and communication

### 3.2 Business Operations
- Improve our services and develop new features
- Conduct analytics and research
- Ensure security and prevent fraud
- Comply with legal obligations

### 3.3 Communications
- Send service-related notifications
- Provide customer support
- Send marketing communications (with consent)
- Share product updates and announcements

## 4. Legal Basis for Processing (GDPR)

We process personal data based on the following legal grounds:
- **Contract Performance:** To provide our services as agreed
- **Legitimate Interests:** For business operations, security, and improvements
- **Consent:** For marketing communications and optional features
- **Legal Compliance:** To meet regulatory requirements

## 5. Data Sharing and Disclosure

### 5.1 Service Providers
We may share information with trusted third-party service providers:
- Cloud hosting and infrastructure providers
- Email and communication service providers
- Analytics and monitoring services
- Payment processors (if applicable)

### 5.2 Business Transfers
In case of merger, acquisition, or sale of assets, your information may be transferred to the new entity.

### 5.3 Legal Requirements
We may disclose information when required by law or to:
- Comply with legal processes
- Protect our rights and property
- Ensure user safety
- Prevent fraud or illegal activities

## 6. Data Security

We implement appropriate technical and organizational measures to protect your information:
- **Encryption:** Data encrypted in transit and at rest
- **Access Controls:** Limited access on a need-to-know basis
- **Security Monitoring:** Continuous monitoring for threats
- **Regular Audits:** Periodic security assessments

## 7. Data Retention

We retain personal information for as long as necessary to:
- Provide our services
- Comply with legal obligations
- Resolve disputes
- Enforce our agreements

**Specific Retention Periods:**
- Account data: 7 years after account closure
- Customer interaction data: 3 years after last interaction
- Review data: 7 years for business analysis
- Security logs: 1 year

## 8. Your Rights (GDPR)

If you are in the European Union, you have the following rights:

### 8.1 Access and Portability
- Request access to your personal data
- Receive a copy of your data in a portable format

### 8.2 Correction and Deletion
- Request correction of inaccurate data
- Request deletion of your personal data (right to be forgotten)

### 8.3 Processing Restrictions
- Request restriction of processing
- Object to processing based on legitimate interests
- Withdraw consent for consent-based processing

### 8.4 Exercising Your Rights
To exercise these rights, contact us at privacy@reviveai.com or use our data subject request form.

## 9. Cookies and Tracking

We use cookies and similar technologies to:
- Maintain user sessions
- Remember preferences
- Analyze usage patterns
- Provide personalized experiences

You can manage cookie preferences through our cookie banner or browser settings.

## 10. International Transfers

Your information may be transferred to and processed in countries other than your own. We ensure appropriate safeguards are in place:
- EU Standard Contractual Clauses
- Adequacy decisions
- Privacy Shield frameworks (where applicable)

## 11. Children's Privacy

Our services are not intended for children under 16. We do not knowingly collect personal information from children.

## 12. Changes to This Policy

We may update this Privacy Policy periodically. We will notify you of material changes by:
- Email notification
- Prominent notice on our website
- In-app notifications

## 13. Contact Information

For privacy-related questions or concerns:

**Email:** privacy@reviveai.com
**Address:** [Company Address]
**Data Protection Officer:** dpo@reviveai.com

## 14. Automated Decision-Making

We use automated systems for:
- **Review Sentiment Analysis:** Determining emotional tone of reviews
- **Urgency Classification:** Prioritizing reviews based on urgency
- **Response Generation:** Creating suggested responses using AI
- **Customer Risk Assessment:** Identifying at-risk customers

You have the right to request human review of automated decisions that significantly affect you.

---

This Privacy Policy is effective as of {effective_date} and was last updated on {last_updated}.
"""
    
    def _get_terms_of_service_template(self) -> str:
        """Get terms of service template"""
        return """# Terms of Service

**Effective Date:** {effective_date}
**Last Updated:** {last_updated}

## 1. Acceptance of Terms

By accessing or using Revive AI's services, you agree to be bound by these Terms of Service ("Terms"). If you do not agree to these Terms, do not use our services.

## 2. Description of Service

Revive AI provides a customer review management and recovery platform that helps businesses:
- Monitor and analyze customer reviews
- Generate automated responses
- Implement customer recovery strategies
- Track customer satisfaction metrics

## 3. User Accounts

### 3.1 Account Creation
- You must provide accurate and complete information
- You are responsible for maintaining account security
- You must be at least 18 years old to create an account
- One person or entity may not maintain multiple accounts

### 3.2 Account Responsibilities
- Keep your login credentials secure
- Notify us immediately of unauthorized access
- You are responsible for all activities under your account
- Comply with all applicable laws and regulations

## 4. Acceptable Use

### 4.1 Permitted Uses
- Use the service for legitimate business purposes
- Comply with all applicable laws and regulations
- Respect intellectual property rights
- Maintain data security and privacy

### 4.2 Prohibited Uses
- Violate any laws or regulations
- Infringe on intellectual property rights
- Transmit harmful or malicious content
- Attempt to gain unauthorized access
- Use the service for spam or unsolicited communications
- Reverse engineer or attempt to extract source code

## 5. Data and Privacy

### 5.1 Your Data
- You retain ownership of your business data
- You grant us license to process data to provide services
- You are responsible for the accuracy of data you provide
- You must have rights to share customer data with us

### 5.2 Data Protection
- We implement security measures to protect your data
- We comply with applicable data protection laws
- See our Privacy Policy for detailed information
- We may use aggregated, anonymized data for service improvement

## 6. Intellectual Property

### 6.1 Our Rights
- Revive AI owns all rights to the platform and technology
- Our trademarks, logos, and branding are protected
- You may not use our intellectual property without permission

### 6.2 Your Rights
- You retain rights to your business data and content
- You grant us necessary licenses to provide services
- You represent that you have rights to data you provide

## 7. Service Availability

### 7.1 Uptime
- We strive for high availability but cannot guarantee 100% uptime
- Scheduled maintenance will be announced in advance
- We are not liable for service interruptions beyond our control

### 7.2 Support
- Support is provided during business hours
- Response times vary based on issue severity
- We provide documentation and self-help resources

## 8. Fees and Payment

### 8.1 Subscription Fees
- Fees are based on your selected plan
- Fees are billed in advance
- All fees are non-refundable unless otherwise stated

### 8.2 Payment Terms
- Payment is due upon invoice
- Late payments may result in service suspension
- You are responsible for all taxes
- We may change fees with 30 days notice

## 9. Termination

### 9.1 Termination by You
- You may terminate your account at any time
- Termination does not relieve payment obligations
- Data export must be requested before termination

### 9.2 Termination by Us
- We may terminate for breach of these Terms
- We may terminate with 30 days notice for convenience
- We may suspend service immediately for security reasons

### 9.3 Effect of Termination
- Your access to the service will cease
- We may delete your data after a reasonable period
- Provisions that should survive will remain in effect

## 10. Disclaimers

### 10.1 Service Disclaimers
- Services are provided "as is" without warranties
- We do not guarantee specific results or outcomes
- AI-generated content may contain errors or inaccuracies
- You are responsible for reviewing and approving all communications

### 10.2 Third-Party Services
- We integrate with third-party platforms
- We are not responsible for third-party service availability
- Third-party terms may apply to integrated services

## 11. Limitation of Liability

### 11.1 Damages
- Our liability is limited to the amount you paid in the last 12 months
- We are not liable for indirect, consequential, or punitive damages
- Some jurisdictions may not allow these limitations

### 11.2 Indemnification
- You agree to indemnify us against claims arising from your use
- This includes claims related to your data or customer interactions
- We will notify you of claims and cooperate in defense

## 12. Dispute Resolution

### 12.1 Governing Law
- These Terms are governed by [Jurisdiction] law
- Disputes will be resolved in [Jurisdiction] courts
- You consent to jurisdiction and venue

### 12.2 Arbitration
- Disputes may be subject to binding arbitration
- Arbitration will be conducted under [Arbitration Rules]
- Class action waivers may apply

## 13. General Provisions

### 13.1 Entire Agreement
- These Terms constitute the entire agreement
- They supersede all prior agreements
- Modifications must be in writing

### 13.2 Severability
- If any provision is invalid, the rest remains in effect
- Invalid provisions will be replaced with valid equivalents

### 13.3 Assignment
- You may not assign these Terms without our consent
- We may assign these Terms to affiliates or successors

## 14. Changes to Terms

We may modify these Terms at any time by:
- Posting updated Terms on our website
- Sending email notification of material changes
- Providing in-app notifications

Continued use after changes constitutes acceptance.

## 15. Contact Information

For questions about these Terms:

**Email:** legal@reviveai.com
**Address:** [Company Address]
**Phone:** [Phone Number]

---

These Terms of Service are effective as of {effective_date} and were last updated on {last_updated}.
"""
    
    def _get_cookie_policy_template(self) -> str:
        """Get cookie policy template"""
        return """# Cookie Policy

**Effective Date:** {effective_date}
**Last Updated:** {last_updated}

## 1. What Are Cookies

Cookies are small text files stored on your device when you visit our website. They help us provide you with a better experience by remembering your preferences and analyzing how you use our services.

## 2. Types of Cookies We Use

### 2.1 Necessary Cookies
These cookies are essential for the website to function properly:
- **Authentication:** Keep you logged in
- **Security:** Protect against fraud and attacks
- **Session Management:** Maintain your session state
- **Load Balancing:** Distribute traffic efficiently

### 2.2 Functional Cookies
These cookies enhance your experience:
- **Preferences:** Remember your settings and choices
- **Language:** Store your language preference
- **Theme:** Remember your display preferences
- **Form Data:** Save form progress

### 2.3 Analytics Cookies
These cookies help us understand how you use our services:
- **Usage Analytics:** Track page views and user interactions
- **Performance Monitoring:** Identify slow or problematic areas
- **Feature Usage:** Understand which features are most popular
- **Error Tracking:** Identify and fix technical issues

### 2.4 Marketing Cookies
These cookies are used for marketing purposes (with your consent):
- **Advertising:** Show relevant advertisements
- **Campaign Tracking:** Measure marketing effectiveness
- **Social Media:** Enable social sharing features
- **Personalization:** Customize content based on interests

## 3. Third-Party Cookies

We may use third-party services that set their own cookies:

### 3.1 Analytics Services
- **Google Analytics:** Website usage analytics
- **Mixpanel:** User behavior tracking
- **Hotjar:** User experience analysis

### 3.2 Support Services
- **Intercom:** Customer support chat
- **Zendesk:** Help desk functionality

### 3.3 Marketing Services
- **Google Ads:** Advertising and remarketing
- **Facebook Pixel:** Social media advertising
- **LinkedIn Insight:** Professional network advertising

## 4. Cookie Consent

### 4.1 Consent Management
- We obtain consent before setting non-essential cookies
- You can withdraw consent at any time
- Consent is recorded and can be reviewed
- Different consent levels are available for different cookie types

### 4.2 Managing Consent
You can manage your cookie preferences:
- **Cookie Banner:** Initial consent when you first visit
- **Preference Center:** Detailed control over cookie types
- **Account Settings:** Manage preferences when logged in
- **Browser Settings:** Control cookies at the browser level

## 5. How Long Cookies Last

### 5.1 Session Cookies
- Deleted when you close your browser
- Used for temporary functionality
- Essential for basic website operation

### 5.2 Persistent Cookies
- **Short-term:** 1-30 days for temporary preferences
- **Medium-term:** 1-12 months for user preferences
- **Long-term:** 1-2 years for analytics and marketing

## 6. Managing Cookies

### 6.1 Browser Controls
Most browsers allow you to:
- View cookies stored on your device
- Delete existing cookies
- Block future cookies
- Set preferences for different websites

### 6.2 Browser-Specific Instructions

**Chrome:**
1. Settings > Privacy and Security > Cookies and other site data
2. Choose your preferred cookie settings

**Firefox:**
1. Settings > Privacy & Security > Cookies and Site Data
2. Manage your cookie preferences

**Safari:**
1. Preferences > Privacy > Manage Website Data
2. Control cookie storage and deletion

**Edge:**
1. Settings > Cookies and site permissions
2. Configure cookie behavior

### 6.3 Opt-Out Tools
- **Google Analytics:** Use Google's opt-out browser add-on
- **Marketing Cookies:** Use industry opt-out tools
- **Do Not Track:** Enable browser Do Not Track settings

## 7. Impact of Disabling Cookies

Disabling cookies may affect your experience:

### 7.1 Necessary Cookies
- Cannot be disabled without affecting functionality
- Website may not work properly
- Security features may be compromised

### 7.2 Other Cookies
- **Functional:** May need to re-enter preferences
- **Analytics:** Won't affect your experience
- **Marketing:** May see less relevant advertisements

## 8. Mobile Apps

Our mobile applications may use similar technologies:
- **App Analytics:** Track app usage and performance
- **Push Notifications:** Send relevant updates
- **Crash Reporting:** Identify and fix app issues
- **User Preferences:** Remember your settings

## 9. Updates to This Policy

We may update this Cookie Policy to reflect:
- Changes in our cookie usage
- New legal requirements
- Technology updates
- Service improvements

We will notify you of significant changes through:
- Email notifications
- Website banners
- In-app notifications

## 10. Contact Information

For questions about our use of cookies:

**Email:** privacy@reviveai.com
**Data Protection Officer:** dpo@reviveai.com
**Address:** [Company Address]

## 11. Cookie List

### Current Cookies Used

| Cookie Name | Purpose | Type | Duration | Third Party |
|-------------|---------|------|----------|-------------|
| session_id | User session | Necessary | Session | No |
| auth_token | Authentication | Necessary | 30 days | No |
| preferences | User settings | Functional | 1 year | No |
| _ga | Google Analytics | Analytics | 2 years | Yes |
| _gid | Google Analytics | Analytics | 1 day | Yes |
| intercom-session | Support chat | Functional | 1 week | Yes |

---

This Cookie Policy is effective as of {effective_date} and was last updated on {last_updated}.
"""
    
    def _get_dpa_template(self) -> str:
        """Get data processing agreement template"""
        return """# Data Processing Agreement

**Effective Date:** {effective_date}
**Last Updated:** {last_updated}

This Data Processing Agreement ("DPA") forms part of the Terms of Service between you ("Customer") and Revive AI ("Processor") and governs the processing of personal data in connection with the services.

## 1. Definitions

- **Personal Data:** Any information relating to an identified or identifiable natural person
- **Processing:** Any operation performed on personal data
- **Data Subject:** The individual to whom personal data relates
- **Controller:** The entity that determines the purposes and means of processing
- **Processor:** The entity that processes personal data on behalf of the Controller

## 2. Scope and Roles

### 2.1 Scope
This DPA applies to the processing of personal data by Revive AI on behalf of Customer in connection with the services.

### 2.2 Roles
- **Customer** acts as the Data Controller
- **Revive AI** acts as the Data Processor
- Customer determines the purposes and means of processing
- Revive AI processes data only on Customer's instructions

## 3. Processing Instructions

### 3.1 Authorized Processing
Revive AI will process personal data only:
- As necessary to provide the services
- According to Customer's documented instructions
- In compliance with applicable data protection laws
- As described in this DPA and the Privacy Policy

### 3.2 Processing Activities
The processing includes:
- **Collection:** Receiving customer review data
- **Storage:** Storing data in secure systems
- **Analysis:** Analyzing sentiment and urgency
- **Communication:** Generating responses and notifications
- **Reporting:** Creating analytics and reports

## 4. Data Categories and Subjects

### 4.1 Categories of Data Subjects
- Customer's end customers
- Review authors
- Support ticket creators
- Website visitors

### 4.2 Categories of Personal Data
- **Identity Data:** Names, email addresses
- **Contact Data:** Phone numbers, addresses
- **Communication Data:** Review content, messages
- **Technical Data:** IP addresses, device information
- **Usage Data:** Interaction patterns, preferences

## 5. Security Measures

### 5.1 Technical Measures
- Encryption of data in transit and at rest
- Access controls and authentication
- Network security and firewalls
- Regular security monitoring
- Secure data centers

### 5.2 Organizational Measures
- Staff training on data protection
- Access on a need-to-know basis
- Regular security assessments
- Incident response procedures
- Vendor management programs

## 6. Sub-Processing

### 6.1 Authorized Sub-Processors
Customer authorizes the use of sub-processors listed in Annex A, subject to the conditions in this section.

### 6.2 Sub-Processor Requirements
All sub-processors must:
- Provide adequate security guarantees
- Be bound by data protection obligations
- Process data only for authorized purposes
- Implement appropriate technical and organizational measures

### 6.3 Changes to Sub-Processors
- We will notify Customer of new sub-processors
- Customer may object within 30 days
- If objection cannot be resolved, Customer may terminate

## 7. Data Subject Rights

### 7.1 Assistance with Rights Requests
Revive AI will assist Customer in responding to data subject requests for:
- Access to personal data
- Rectification of inaccurate data
- Erasure of personal data
- Restriction of processing
- Data portability
- Objection to processing

### 7.2 Response Timeframe
- We will respond to assistance requests within 30 days
- Urgent requests will be prioritized
- We may charge reasonable fees for extensive requests

## 8. Data Transfers

### 8.1 International Transfers
Personal data may be transferred to countries outside the EEA with appropriate safeguards:
- EU Standard Contractual Clauses
- Adequacy decisions
- Binding Corporate Rules
- Certification schemes

### 8.2 Transfer Safeguards
All international transfers include:
- Contractual data protection obligations
- Technical and organizational security measures
- Rights for data subjects
- Effective remedies

## 9. Data Retention and Deletion

### 9.1 Retention Periods
Personal data will be retained according to:
- Customer's instructions
- Legal requirements
- Legitimate business needs
- Data retention policies

### 9.2 Data Deletion
Upon termination or Customer request:
- Data will be deleted within 90 days
- Backups will be securely destroyed
- Certificates of deletion can be provided
- Legal hold requirements will be respected

## 10. Data Breach Notification

### 10.1 Notification to Customer
In case of a personal data breach:
- Customer will be notified within 72 hours
- Notification will include breach details
- Assessment of likely consequences
- Measures taken or proposed

### 10.2 Assistance with Notifications
We will assist Customer with:
- Regulatory breach notifications
- Data subject notifications
- Breach impact assessments
- Remediation measures

## 11. Data Protection Impact Assessments

### 11.1 DPIA Assistance
We will provide reasonable assistance with Data Protection Impact Assessments when:
- Processing is likely to result in high risk
- Customer requests assistance
- New processing activities are introduced

### 11.2 Information Provided
Assistance may include:
- Description of processing activities
- Security measures implemented
- Risk assessment information
- Mitigation recommendations

## 12. Audits and Compliance

### 12.1 Audit Rights
Customer may audit compliance through:
- Review of compliance documentation
- Third-party audit reports
- On-site inspections (with reasonable notice)
- Questionnaires and certifications

### 12.2 Compliance Documentation
We maintain documentation of:
- Processing activities
- Security measures
- Staff training records
- Incident reports
- Sub-processor agreements

## 13. Liability and Indemnification

### 13.1 Liability Allocation
- Each party is liable for its own data protection violations
- Liability is subject to limitations in the main agreement
- Customer is responsible for lawfulness of processing instructions

### 13.2 Indemnification
Customer will indemnify Revive AI against claims arising from:
- Unlawful processing instructions
- Customer's violation of data protection laws
- Inaccurate or misleading information provided

## 14. Term and Termination

### 14.1 Term
This DPA remains in effect for the duration of the main agreement.

### 14.2 Survival
The following provisions survive termination:
- Data deletion obligations
- Confidentiality requirements
- Liability and indemnification
- Audit rights (for reasonable period)

## 15. Amendments

This DPA may be amended:
- To comply with applicable laws
- To reflect changes in processing activities
- By mutual written agreement
- With 30 days notice for non-material changes

---

**Annex A: Sub-Processors**

| Sub-Processor | Service | Location | Safeguards |
|---------------|---------|----------|------------|
| AWS | Cloud hosting | US/EU | Standard Contractual Clauses |
| SendGrid | Email services | US | Privacy Shield successor |
| Google | Analytics | US | Data Processing Amendment |

---

This Data Processing Agreement is effective as of {effective_date} and was last updated on {last_updated}.
"""
    
    def create_policy(
        self,
        organization_id: str,
        policy_type: PolicyType,
        version: str = "1.0",
        custom_content: str = None,
        effective_date: datetime = None,
        summary_of_changes: str = None
    ) -> PolicyVersion:
        """Create a new policy version"""
        
        if effective_date is None:
            effective_date = datetime.now(timezone.utc)
        
        # Use custom content or template
        if custom_content:
            content = custom_content
        else:
            template = self.policy_templates[policy_type]
            content = template.format(
                effective_date=effective_date.strftime("%B %d, %Y"),
                last_updated=datetime.now(timezone.utc).strftime("%B %d, %Y")
            )
        
        # Create policy version
        policy_version = PolicyVersion(
            version=version,
            content=content,
            effective_date=effective_date,
            summary_of_changes=summary_of_changes
        )
        
        # Store policy
        if organization_id not in self.policies:
            self.policies[organization_id] = {}
        
        if policy_type not in self.policies[organization_id]:
            self.policies[organization_id][policy_type] = []
        
        self.policies[organization_id][policy_type].append(policy_version)
        
        logger.info(f"Created {policy_type.value} v{version} for organization {organization_id}")
        
        return policy_version
    
    def get_current_policy(
        self,
        organization_id: str,
        policy_type: PolicyType
    ) -> Optional[PolicyVersion]:
        """Get the current (latest) version of a policy"""
        
        if (organization_id not in self.policies or 
            policy_type not in self.policies[organization_id]):
            return None
        
        versions = self.policies[organization_id][policy_type]
        if not versions:
            return None
        
        # Return the most recent version
        return max(versions, key=lambda v: v.effective_date)
    
    def get_policy_history(
        self,
        organization_id: str,
        policy_type: PolicyType
    ) -> List[PolicyVersion]:
        """Get all versions of a policy"""
        
        if (organization_id not in self.policies or 
            policy_type not in self.policies[organization_id]):
            return []
        
        versions = self.policies[organization_id][policy_type]
        return sorted(versions, key=lambda v: v.effective_date, reverse=True)
    
    def update_policy(
        self,
        organization_id: str,
        policy_type: PolicyType,
        new_content: str,
        version: str,
        effective_date: datetime = None,
        summary_of_changes: str = None
    ) -> PolicyVersion:
        """Update a policy with a new version"""
        
        return self.create_policy(
            organization_id=organization_id,
            policy_type=policy_type,
            version=version,
            custom_content=new_content,
            effective_date=effective_date,
            summary_of_changes=summary_of_changes
        )
    
    def get_policy_for_display(
        self,
        organization_id: str,
        policy_type: PolicyType,
        format_type: str = "html"
    ) -> Optional[Dict[str, Any]]:
        """Get policy formatted for display"""
        
        policy = self.get_current_policy(organization_id, policy_type)
        if not policy:
            return None
        
        # Convert markdown to HTML if requested
        content = policy.content
        if format_type == "html":
            # In a real implementation, use a markdown parser
            content = self._markdown_to_html(content)
        
        return {
            "type": policy_type.value,
            "version": policy.version,
            "content": content,
            "effective_date": policy.effective_date.isoformat(),
            "last_updated": policy.created_at.isoformat(),
            "format": format_type
        }
    
    def _markdown_to_html(self, markdown_content: str) -> str:
        """Convert markdown to HTML (simplified)"""
        # This is a very basic conversion - in production, use a proper markdown parser
        html = markdown_content
        
        # Headers
        html = html.replace("# ", "<h1>").replace("\n\n", "</h1>\n\n")
        html = html.replace("## ", "<h2>").replace("\n\n", "</h2>\n\n")
        html = html.replace("### ", "<h3>").replace("\n\n", "</h3>\n\n")
        
        # Bold text
        html = html.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
        
        # Paragraphs
        paragraphs = html.split("\n\n")
        html_paragraphs = []
        
        for para in paragraphs:
            if para.strip():
                if not para.startswith("<h") and not para.startswith("<"):
                    para = f"<p>{para}</p>"
                html_paragraphs.append(para)
        
        return "\n\n".join(html_paragraphs)
    
    def generate_policy_summary(self, organization_id: str) -> Dict[str, Any]:
        """Generate summary of all policies for an organization"""
        
        if organization_id not in self.policies:
            return {
                "organization_id": organization_id,
                "policies": {},
                "total_policies": 0,
                "last_updated": None
            }
        
        policy_summary = {}
        last_updated = None
        
        for policy_type, versions in self.policies[organization_id].items():
            if versions:
                current = max(versions, key=lambda v: v.effective_date)
                policy_summary[policy_type.value] = {
                    "current_version": current.version,
                    "effective_date": current.effective_date.isoformat(),
                    "total_versions": len(versions),
                    "last_updated": current.created_at.isoformat()
                }
                
                if last_updated is None or current.created_at > last_updated:
                    last_updated = current.created_at
        
        return {
            "organization_id": organization_id,
            "policies": policy_summary,
            "total_policies": len(policy_summary),
            "last_updated": last_updated.isoformat() if last_updated else None
        }
    
    def initialize_default_policies_for_org(self, organization_id: str):
        """Initialize default policies for a new organization"""
        
        effective_date = datetime.now(timezone.utc)
        
        for policy_type in PolicyType:
            self.create_policy(
                organization_id=organization_id,
                policy_type=policy_type,
                version="1.0",
                effective_date=effective_date,
                summary_of_changes="Initial policy creation"
            )
        
        logger.info(f"Initialized default policies for organization {organization_id}")


# Global privacy policy service instance
_privacy_policy_service = None


def get_privacy_policy_service() -> PrivacyPolicyService:
    """Get global privacy policy service instance"""
    global _privacy_policy_service
    
    if _privacy_policy_service is None:
        _privacy_policy_service = PrivacyPolicyService()
    
    return _privacy_policy_service
