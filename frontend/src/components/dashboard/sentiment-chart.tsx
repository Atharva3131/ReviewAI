'use client';

import { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface SentimentData {
  date: string;
  sentiment: number;
  reviews: number;
}

export function SentimentChart() {
  const [data, setData] = useState<SentimentData[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Generate mock data with current dates (last 14 days)
    const generateMockData = () => {
      const data: SentimentData[] = [];
      const today = new Date();

      for (let i = 13; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);

        // Generate realistic sentiment scores (0.5 to 0.9)
        const sentiment = 0.5 + Math.random() * 0.4;
        // Generate review counts (10 to 30)
        const reviews = Math.floor(10 + Math.random() * 20);

        data.push({
          date: date.toISOString().split('T')[0],
          sentiment: parseFloat(sentiment.toFixed(2)),
          reviews,
        });
      }

      return data;
    };

    // Simulate API call delay
    setTimeout(() => {
      setData(generateMockData());
      setIsLoading(false);
    }, 1000);
  }, []);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const formatSentiment = (value: number) => {
    return `${(value * 100).toFixed(0)}%`;
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className='bg-white p-3 border border-gray-200 rounded-lg shadow-lg'>
          <p className='text-sm font-medium text-gray-900'>{formatDate(label)}</p>
          <p className='text-sm text-blue-600'>Sentiment: {formatSentiment(payload[0].value)}</p>
          <p className='text-sm text-gray-600'>Reviews: {payload[0].payload.reviews}</p>
        </div>
      );
    }
    return null;
  };

  if (isLoading) {
    return (
      <div className='h-80 flex items-center justify-center'>
        <div className='animate-pulse'>
          <div className='h-4 bg-gray-200 rounded w-32 mb-4'></div>
          <div className='space-y-2'>
            {[...Array(6)].map((_, i) => (
              <div key={i} className='h-3 bg-gray-200 rounded w-full'></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className='h-80'>
      <ResponsiveContainer width='100%' height='100%'>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray='3 3' stroke='#f0f0f0' />
          <XAxis dataKey='date' tickFormatter={formatDate} stroke='#6b7280' fontSize={12} />
          <YAxis domain={[0, 1]} tickFormatter={formatSentiment} stroke='#6b7280' fontSize={12} />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type='monotone'
            dataKey='sentiment'
            stroke='#3b82f6'
            strokeWidth={2}
            dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6, stroke: '#3b82f6', strokeWidth: 2 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
