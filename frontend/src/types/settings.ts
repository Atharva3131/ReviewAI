export interface Organization {
  id: string;
  name: string;
  slug: string;
  description?: string;
  website?: string;
  industry?: string;
  size?: 'startup' | 'small' | 'medium' | 'large' | 'enterprise';
  timezone: string;
  country: string;
  logo_url?: string;
  created_at: string;
  updated_at: string;
  settings: OrganizationSettings;
}

export interface OrganizationSettings {
  // General Settings
  business_hours: {
    enabled: boolean;
    timezone: string;
    schedule: {
      [key: string]: {
        enabled: boolean;
        start: string;
        end: string;
      };
    };
  };

  // Review Settings
  review_settings: {
    auto_response_enabled: boolean;
    response_delay_minutes: number;
    escalation_threshold: number;
    sentiment_threshold: number;
    require_approval: boolean;
  };

  // Recovery Settings
  recovery_settings: {
    auto_recovery_enabled: boolean;
    churn_threshold: number;
    recovery_delay_hours: number;
    max_recovery_attempts: number;
  };

  // Notification Settings
  notifications: {
    email_enabled: boolean;
    sms_enabled: boolean;
    slack_enabled: boolean;
    webhook_enabled: boolean;
    notification_types: {
      new_review: boolean;
      negative_review: boolean;
      high_risk_customer: boolean;
      recovery_success: boolean;
      system_alerts: boolean;
    };
  };

  // Branding
  branding: {
    primary_color: string;
    secondary_color: string;
    logo_url?: string;
    custom_css?: string;
  };
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'admin' | 'manager' | 'agent' | 'viewer';
  status: 'active' | 'inactive' | 'pending';
  avatar_url?: string;
  last_login?: string;
  created_at: string;
  updated_at: string;
  permissions: UserPermissions;
}

export interface UserPermissions {
  can_manage_users: boolean;
  can_manage_settings: boolean;
  can_view_analytics: boolean;
  can_respond_to_reviews: boolean;
  can_manage_customers: boolean;
  can_access_api: boolean;
  can_export_data: boolean;
}

export interface AgentConfiguration {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  settings: {
    // Response Generation
    response_generation: {
      enabled: boolean;
      model: 'gpt-4' | 'gpt-3.5-turbo' | 'claude-3' | 'gemini-pro';
      temperature: number;
      max_tokens: number;
      custom_prompts: {
        positive_review: string;
        neutral_review: string;
        negative_review: string;
      };
    };

    // Decision Making
    decision_making: {
      auto_escalation: boolean;
      escalation_rules: {
        rating_threshold: number;
        sentiment_threshold: number;
        keyword_triggers: string[];
      };
      approval_required: boolean;
    };

    // Recovery Actions
    recovery_actions: {
      auto_trigger: boolean;
      trigger_conditions: {
        churn_probability: number;
        days_since_last_review: number;
        negative_review_count: number;
      };
      action_types: {
        email: boolean;
        phone: boolean;
        sms: boolean;
        discount: boolean;
      };
    };
  };
  created_at: string;
  updated_at: string;
}

export interface APIKey {
  id: string;
  name: string;
  key: string;
  permissions: string[];
  last_used?: string;
  expires_at?: string;
  created_at: string;
  status: 'active' | 'inactive' | 'expired';
}

export interface Integration {
  id: string;
  type: 'email' | 'whatsapp' | 'crm' | 'slack' | 'webhook';
  name: string;
  enabled: boolean;
  configuration: Record<string, any>;
  status: 'connected' | 'disconnected' | 'error';
  last_sync?: string;
  created_at: string;
  updated_at: string;
}

export interface NotificationPreference {
  id: string;
  user_id: string;
  type: 'email' | 'sms' | 'push' | 'slack';
  enabled: boolean;
  settings: {
    frequency: 'immediate' | 'hourly' | 'daily' | 'weekly';
    quiet_hours: {
      enabled: boolean;
      start: string;
      end: string;
      timezone: string;
    };
    categories: {
      reviews: boolean;
      customers: boolean;
      system: boolean;
      recovery: boolean;
    };
  };
  created_at: string;
  updated_at: string;
}
