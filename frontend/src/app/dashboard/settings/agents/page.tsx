'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Bot,
  Settings,
  Save,
  RotateCcw,
  Zap,
  Brain,
  MessageSquare,
  AlertTriangle,
  CheckCircle,
  Play,
  Pause,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AgentConfiguration } from '@/types/settings';
import api from '@/lib/api';

const LLM_MODELS = [
  { value: 'gpt-4', label: 'GPT-4', description: 'Most capable, higher cost' },
  { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo', description: 'Fast and cost-effective' },
  { value: 'claude-3', label: 'Claude 3', description: "Anthropic's latest model" },
  { value: 'gemini-pro', label: 'Gemini Pro', description: "Google's advanced model" },
];

export default function AgentConfigurationPage() {
  const [config, setConfig] = useState<AgentConfiguration | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('response');

  useEffect(() => {
    fetchAgentConfiguration();
  }, []);

  const fetchAgentConfiguration = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get('/agent-configuration');
      setConfig(response.data);
    } catch (err: any) {
      console.error('Error fetching agent configuration:', err);
      setError('Failed to load agent configuration');

      // Mock data for development
      const mockConfig: AgentConfiguration = {
        id: '1',
        name: 'ReviewAI Agent',
        description: 'Automated customer review response and recovery agent',
        enabled: true,
        settings: {
          response_generation: {
            enabled: true,
            model: 'gpt-4',
            temperature: 0.7,
            max_tokens: 500,
            custom_prompts: {
              positive_review:
                "Thank you so much for your wonderful review! We're thrilled to hear about your positive experience. Your feedback means the world to us and motivates our team to continue delivering excellent service.",
              neutral_review:
                'Thank you for taking the time to share your feedback. We appreciate your honest review and would love to learn more about how we can improve your experience. Please feel free to reach out to us directly.',
              negative_review:
                "Thank you for bringing this to our attention. We sincerely apologize that your experience didn't meet expectations. We take all feedback seriously and would appreciate the opportunity to make this right. Please contact us directly so we can address your concerns.",
            },
          },
          decision_making: {
            auto_escalation: true,
            escalation_rules: {
              rating_threshold: 2,
              sentiment_threshold: 0.3,
              keyword_triggers: ['terrible', 'awful', 'worst', 'disgusting', 'never again'],
            },
            approval_required: false,
          },
          recovery_actions: {
            auto_trigger: true,
            trigger_conditions: {
              churn_probability: 0.7,
              days_since_last_review: 30,
              negative_review_count: 2,
            },
            action_types: {
              email: true,
              phone: false,
              sms: true,
              discount: true,
            },
          },
        },
        created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
        updated_at: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
      };
      setConfig(mockConfig);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!config) {
      return;
    }

    setIsSaving(true);
    try {
      await api.put('/agent-configuration', config);
      // Show success message
    } catch (error) {
      console.error('Error saving agent configuration:', error);
      setError('Failed to save configuration');
    } finally {
      setIsSaving(false);
    }
  };

  const updateConfig = (updates: Partial<AgentConfiguration>) => {
    setConfig(prev => (prev ? { ...prev, ...updates } : null));
  };

  const updateSettings = (section: keyof AgentConfiguration['settings'], updates: any) => {
    setConfig(prev =>
      prev
        ? {
            ...prev,
            settings: {
              ...prev.settings,
              [section]: { ...prev.settings[section], ...updates },
            },
          }
        : null,
    );
  };

  const resetToDefaults = () => {
    if (
      confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')
    ) {
      fetchAgentConfiguration();
    }
  };

  const tabs = [
    { id: 'response', label: 'Response Generation', icon: MessageSquare },
    { id: 'decisions', label: 'Decision Making', icon: Brain },
    { id: 'recovery', label: 'Recovery Actions', icon: Zap },
  ];

  if (isLoading) {
    return (
      <div className='px-4 sm:px-6 lg:px-8'>
        <div className='animate-pulse space-y-6'>
          <div className='h-8 bg-gray-200 rounded w-1/4'></div>
          <div className='h-64 bg-gray-200 rounded'></div>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className='px-4 sm:px-6 lg:px-8'>
        <div className='text-center py-12'>
          <Bot className='h-12 w-12 text-gray-400 mx-auto mb-4' />
          <h2 className='text-lg font-medium text-gray-900 mb-2'>Configuration Unavailable</h2>
          <p className='text-gray-600'>{error || 'Unable to load agent configuration'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className='px-4 sm:px-6 lg:px-8'>
      {/* Header */}
      <div className='mb-8'>
        <div className='flex items-center justify-between'>
          <div>
            <h1 className='text-2xl font-bold text-gray-900'>Agent Configuration</h1>
            <p className='mt-1 text-sm text-gray-500'>
              Configure AI agent behavior and automation settings
            </p>
          </div>
          <div className='flex items-center space-x-2'>
            <Button variant='outline' onClick={resetToDefaults}>
              <RotateCcw className='h-4 w-4 mr-1' />
              Reset to Defaults
            </Button>
            <Button onClick={handleSave} disabled={isSaving}>
              <Save className='h-4 w-4 mr-1' />
              {isSaving ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </div>
      </div>

      {/* Agent Status */}
      <Card className='mb-6'>
        <CardContent className='p-6'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center space-x-4'>
              <div
                className={cn(
                  'w-12 h-12 rounded-full flex items-center justify-center',
                  config.enabled ? 'bg-green-100' : 'bg-gray-100',
                )}
              >
                <Bot
                  className={cn('h-6 w-6', config.enabled ? 'text-green-600' : 'text-gray-400')}
                />
              </div>
              <div>
                <h3 className='text-lg font-medium text-gray-900'>{config.name}</h3>
                <p className='text-sm text-gray-600'>{config.description}</p>
                <div className='flex items-center space-x-2 mt-1'>
                  {config.enabled ? (
                    <CheckCircle className='h-4 w-4 text-green-600' />
                  ) : (
                    <AlertTriangle className='h-4 w-4 text-yellow-600' />
                  )}
                  <span
                    className={cn(
                      'text-sm font-medium',
                      config.enabled ? 'text-green-600' : 'text-yellow-600',
                    )}
                  >
                    {config.enabled ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
            </div>

            <Button
              onClick={() => updateConfig({ enabled: !config.enabled })}
              variant={config.enabled ? 'outline' : 'default'}
            >
              {config.enabled ? (
                <>
                  <Pause className='h-4 w-4 mr-1' />
                  Disable Agent
                </>
              ) : (
                <>
                  <Play className='h-4 w-4 mr-1' />
                  Enable Agent
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className='grid grid-cols-1 lg:grid-cols-4 gap-8'>
        {/* Sidebar Navigation */}
        <div className='lg:col-span-1'>
          <nav className='space-y-1'>
            {tabs.map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                    activeTab === tab.id
                      ? 'bg-blue-100 text-blue-700'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50',
                  )}
                >
                  <Icon className='h-5 w-5 mr-3' />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Main Content */}
        <div className='lg:col-span-3'>
          {activeTab === 'response' && (
            <Card>
              <CardHeader>
                <CardTitle>Response Generation Settings</CardTitle>
                <CardDescription>
                  Configure how the AI generates responses to reviews
                </CardDescription>
              </CardHeader>
              <CardContent className='space-y-6'>
                <div className='flex items-center justify-between'>
                  <div>
                    <Label className='text-base font-medium'>Enable Response Generation</Label>
                    <p className='text-sm text-gray-600'>
                      Automatically generate responses to reviews
                    </p>
                  </div>
                  <input
                    type='checkbox'
                    checked={config.settings.response_generation.enabled}
                    onChange={e =>
                      updateSettings('response_generation', { enabled: e.target.checked })
                    }
                    className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                  />
                </div>

                <div>
                  <Label htmlFor='model'>Language Model</Label>
                  <select
                    id='model'
                    value={config.settings.response_generation.model}
                    onChange={e => updateSettings('response_generation', { model: e.target.value })}
                    className='w-full mt-1 p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                  >
                    {LLM_MODELS.map(model => (
                      <option key={model.value} value={model.value}>
                        {model.label} - {model.description}
                      </option>
                    ))}
                  </select>
                </div>

                <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
                  <div>
                    <Label htmlFor='temperature'>Temperature</Label>
                    <Input
                      id='temperature'
                      type='number'
                      min='0'
                      max='2'
                      step='0.1'
                      value={config.settings.response_generation.temperature}
                      onChange={e =>
                        updateSettings('response_generation', {
                          temperature: parseFloat(e.target.value),
                        })
                      }
                    />
                    <p className='text-sm text-gray-600 mt-1'>
                      Controls randomness (0.0 = deterministic, 2.0 = very creative)
                    </p>
                  </div>

                  <div>
                    <Label htmlFor='max-tokens'>Max Tokens</Label>
                    <Input
                      id='max-tokens'
                      type='number'
                      min='50'
                      max='2000'
                      value={config.settings.response_generation.max_tokens}
                      onChange={e =>
                        updateSettings('response_generation', {
                          max_tokens: parseInt(e.target.value),
                        })
                      }
                    />
                    <p className='text-sm text-gray-600 mt-1'>
                      Maximum length of generated responses
                    </p>
                  </div>
                </div>

                <div className='space-y-4'>
                  <h4 className='font-medium text-gray-900'>Custom Response Templates</h4>

                  <div>
                    <Label htmlFor='positive-prompt'>Positive Review Template</Label>
                    <textarea
                      id='positive-prompt'
                      className='w-full mt-1 p-3 border border-gray-300 rounded-md resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                      rows={3}
                      value={config.settings.response_generation.custom_prompts.positive_review}
                      onChange={e =>
                        updateSettings('response_generation', {
                          custom_prompts: {
                            ...config.settings.response_generation.custom_prompts,
                            positive_review: e.target.value,
                          },
                        })
                      }
                    />
                  </div>

                  <div>
                    <Label htmlFor='neutral-prompt'>Neutral Review Template</Label>
                    <textarea
                      id='neutral-prompt'
                      className='w-full mt-1 p-3 border border-gray-300 rounded-md resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                      rows={3}
                      value={config.settings.response_generation.custom_prompts.neutral_review}
                      onChange={e =>
                        updateSettings('response_generation', {
                          custom_prompts: {
                            ...config.settings.response_generation.custom_prompts,
                            neutral_review: e.target.value,
                          },
                        })
                      }
                    />
                  </div>

                  <div>
                    <Label htmlFor='negative-prompt'>Negative Review Template</Label>
                    <textarea
                      id='negative-prompt'
                      className='w-full mt-1 p-3 border border-gray-300 rounded-md resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                      rows={3}
                      value={config.settings.response_generation.custom_prompts.negative_review}
                      onChange={e =>
                        updateSettings('response_generation', {
                          custom_prompts: {
                            ...config.settings.response_generation.custom_prompts,
                            negative_review: e.target.value,
                          },
                        })
                      }
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'decisions' && (
            <Card>
              <CardHeader>
                <CardTitle>Decision Making Settings</CardTitle>
                <CardDescription>Configure when and how the agent makes decisions</CardDescription>
              </CardHeader>
              <CardContent className='space-y-6'>
                <div className='flex items-center justify-between'>
                  <div>
                    <Label className='text-base font-medium'>Auto Escalation</Label>
                    <p className='text-sm text-gray-600'>
                      Automatically escalate reviews based on rules
                    </p>
                  </div>
                  <input
                    type='checkbox'
                    checked={config.settings.decision_making.auto_escalation}
                    onChange={e =>
                      updateSettings('decision_making', { auto_escalation: e.target.checked })
                    }
                    className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                  />
                </div>

                <div className='space-y-4'>
                  <h4 className='font-medium text-gray-900'>Escalation Rules</h4>

                  <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
                    <div>
                      <Label htmlFor='rating-threshold'>Rating Threshold</Label>
                      <Input
                        id='rating-threshold'
                        type='number'
                        min='1'
                        max='5'
                        value={config.settings.decision_making.escalation_rules.rating_threshold}
                        onChange={e =>
                          updateSettings('decision_making', {
                            escalation_rules: {
                              ...config.settings.decision_making.escalation_rules,
                              rating_threshold: parseInt(e.target.value),
                            },
                          })
                        }
                      />
                      <p className='text-sm text-gray-600 mt-1'>
                        Escalate reviews with this rating or below
                      </p>
                    </div>

                    <div>
                      <Label htmlFor='sentiment-threshold'>Sentiment Threshold</Label>
                      <Input
                        id='sentiment-threshold'
                        type='number'
                        min='0'
                        max='1'
                        step='0.1'
                        value={config.settings.decision_making.escalation_rules.sentiment_threshold}
                        onChange={e =>
                          updateSettings('decision_making', {
                            escalation_rules: {
                              ...config.settings.decision_making.escalation_rules,
                              sentiment_threshold: parseFloat(e.target.value),
                            },
                          })
                        }
                      />
                      <p className='text-sm text-gray-600 mt-1'>
                        Escalate reviews below this sentiment score
                      </p>
                    </div>
                  </div>

                  <div>
                    <Label htmlFor='keyword-triggers'>Keyword Triggers</Label>
                    <Input
                      id='keyword-triggers'
                      value={config.settings.decision_making.escalation_rules.keyword_triggers.join(
                        ', ',
                      )}
                      onChange={e =>
                        updateSettings('decision_making', {
                          escalation_rules: {
                            ...config.settings.decision_making.escalation_rules,
                            keyword_triggers: e.target.value
                              .split(',')
                              .map(k => k.trim())
                              .filter(k => k),
                          },
                        })
                      }
                      placeholder='terrible, awful, worst, disgusting'
                    />
                    <p className='text-sm text-gray-600 mt-1'>
                      Comma-separated keywords that trigger escalation
                    </p>
                  </div>
                </div>

                <div className='flex items-center justify-between'>
                  <div>
                    <Label className='text-base font-medium'>Require Approval</Label>
                    <p className='text-sm text-gray-600'>
                      Require human approval before taking actions
                    </p>
                  </div>
                  <input
                    type='checkbox'
                    checked={config.settings.decision_making.approval_required}
                    onChange={e =>
                      updateSettings('decision_making', { approval_required: e.target.checked })
                    }
                    className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                  />
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'recovery' && (
            <Card>
              <CardHeader>
                <CardTitle>Recovery Actions Settings</CardTitle>
                <CardDescription>Configure automatic customer recovery actions</CardDescription>
              </CardHeader>
              <CardContent className='space-y-6'>
                <div className='flex items-center justify-between'>
                  <div>
                    <Label className='text-base font-medium'>Auto Trigger Recovery</Label>
                    <p className='text-sm text-gray-600'>
                      Automatically trigger recovery actions for at-risk customers
                    </p>
                  </div>
                  <input
                    type='checkbox'
                    checked={config.settings.recovery_actions.auto_trigger}
                    onChange={e =>
                      updateSettings('recovery_actions', { auto_trigger: e.target.checked })
                    }
                    className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                  />
                </div>

                <div className='space-y-4'>
                  <h4 className='font-medium text-gray-900'>Trigger Conditions</h4>

                  <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
                    <div>
                      <Label htmlFor='churn-probability'>Churn Probability</Label>
                      <Input
                        id='churn-probability'
                        type='number'
                        min='0'
                        max='1'
                        step='0.1'
                        value={
                          config.settings.recovery_actions.trigger_conditions.churn_probability
                        }
                        onChange={e =>
                          updateSettings('recovery_actions', {
                            trigger_conditions: {
                              ...config.settings.recovery_actions.trigger_conditions,
                              churn_probability: parseFloat(e.target.value),
                            },
                          })
                        }
                      />
                      <p className='text-sm text-gray-600 mt-1'>Minimum churn probability</p>
                    </div>

                    <div>
                      <Label htmlFor='days-since-review'>Days Since Last Review</Label>
                      <Input
                        id='days-since-review'
                        type='number'
                        min='1'
                        max='365'
                        value={
                          config.settings.recovery_actions.trigger_conditions.days_since_last_review
                        }
                        onChange={e =>
                          updateSettings('recovery_actions', {
                            trigger_conditions: {
                              ...config.settings.recovery_actions.trigger_conditions,
                              days_since_last_review: parseInt(e.target.value),
                            },
                          })
                        }
                      />
                      <p className='text-sm text-gray-600 mt-1'>Days of inactivity</p>
                    </div>

                    <div>
                      <Label htmlFor='negative-review-count'>Negative Review Count</Label>
                      <Input
                        id='negative-review-count'
                        type='number'
                        min='1'
                        max='10'
                        value={
                          config.settings.recovery_actions.trigger_conditions.negative_review_count
                        }
                        onChange={e =>
                          updateSettings('recovery_actions', {
                            trigger_conditions: {
                              ...config.settings.recovery_actions.trigger_conditions,
                              negative_review_count: parseInt(e.target.value),
                            },
                          })
                        }
                      />
                      <p className='text-sm text-gray-600 mt-1'>Number of negative reviews</p>
                    </div>
                  </div>
                </div>

                <div className='space-y-4'>
                  <h4 className='font-medium text-gray-900'>Enabled Action Types</h4>

                  <div className='grid grid-cols-2 md:grid-cols-4 gap-4'>
                    {Object.entries(config.settings.recovery_actions.action_types).map(
                      ([type, enabled]) => (
                        <div key={type} className='flex items-center space-x-2'>
                          <input
                            type='checkbox'
                            id={`action-${type}`}
                            checked={enabled}
                            onChange={e =>
                              updateSettings('recovery_actions', {
                                action_types: {
                                  ...config.settings.recovery_actions.action_types,
                                  [type]: e.target.checked,
                                },
                              })
                            }
                            className='h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                          />
                          <Label htmlFor={`action-${type}`} className='capitalize'>
                            {type}
                          </Label>
                        </div>
                      ),
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {error && (
        <div className='mt-8 bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-md'>
          <p className='text-sm'>{error} - Showing sample data for demonstration</p>
        </div>
      )}
    </div>
  );
}
