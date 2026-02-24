import {
  cn,
  formatDate,
  formatDateTime,
  formatRating,
  getSentimentColor,
  getUrgencyColor,
} from '../utils';

describe('utils', () => {
  describe('cn', () => {
    it('merges class names correctly', () => {
      expect(cn('px-2 py-1', 'px-4')).toBe('py-1 px-4');
    });

    it('handles conditional classes', () => {
      expect(cn('base-class', true && 'conditional-class', false && 'hidden-class')).toBe(
        'base-class conditional-class',
      );
    });

    it('handles arrays and objects', () => {
      expect(cn(['class1', 'class2'], { class3: true, class4: false })).toBe(
        'class1 class2 class3',
      );
    });

    it('handles undefined and null values', () => {
      expect(cn('base', undefined, null, 'end')).toBe('base end');
    });
  });

  describe('formatDate', () => {
    it('formats Date object correctly', () => {
      const date = new Date('2023-12-15T10:30:00Z');
      const formatted = formatDate(date);
      expect(formatted).toMatch(/Dec 15, 2023/);
    });

    it('formats date string correctly', () => {
      const formatted = formatDate('2023-12-15');
      expect(formatted).toMatch(/Dec 15, 2023/);
    });

    it('handles ISO date strings', () => {
      const formatted = formatDate('2023-12-15T10:30:00.000Z');
      expect(formatted).toMatch(/Dec 15, 2023/);
    });
  });

  describe('formatDateTime', () => {
    it('formats Date object with time', () => {
      const date = new Date('2023-12-15T10:30:00Z');
      const formatted = formatDateTime(date);
      expect(formatted).toMatch(/Dec 15, 2023/);
      expect(formatted).toMatch(/\d{1,2}:\d{2}\s?(AM|PM)/);
    });

    it('formats date string with time', () => {
      const formatted = formatDateTime('2023-12-15T14:30:00Z');
      expect(formatted).toMatch(/Dec 15, 2023/);
      expect(formatted).toMatch(/\d{1,2}:\d{2}\s?(AM|PM)/);
    });
  });

  describe('formatRating', () => {
    it('formats whole numbers correctly', () => {
      expect(formatRating(5)).toBe('5.0★');
      expect(formatRating(4)).toBe('4.0★');
    });

    it('formats decimal numbers correctly', () => {
      expect(formatRating(4.5)).toBe('4.5★');
      expect(formatRating(3.7)).toBe('3.7★');
    });

    it('rounds to one decimal place', () => {
      expect(formatRating(4.567)).toBe('4.6★');
      expect(formatRating(3.123)).toBe('3.1★');
    });

    it('handles edge cases', () => {
      expect(formatRating(0)).toBe('0.0★');
      expect(formatRating(5.0)).toBe('5.0★');
    });
  });

  describe('getSentimentColor', () => {
    it('returns green for positive sentiment', () => {
      expect(getSentimentColor(0.8)).toBe('text-green-600');
      expect(getSentimentColor(0.7)).toBe('text-green-600');
      expect(getSentimentColor(1.0)).toBe('text-green-600');
    });

    it('returns yellow for neutral sentiment', () => {
      expect(getSentimentColor(0.5)).toBe('text-yellow-600');
      expect(getSentimentColor(0.4)).toBe('text-yellow-600');
      expect(getSentimentColor(0.69)).toBe('text-yellow-600');
    });

    it('returns red for negative sentiment', () => {
      expect(getSentimentColor(0.3)).toBe('text-red-600');
      expect(getSentimentColor(0.1)).toBe('text-red-600');
      expect(getSentimentColor(0)).toBe('text-red-600');
    });

    it('handles boundary values correctly', () => {
      expect(getSentimentColor(0.7)).toBe('text-green-600');
      expect(getSentimentColor(0.69)).toBe('text-yellow-600');
      expect(getSentimentColor(0.4)).toBe('text-yellow-600');
      expect(getSentimentColor(0.39)).toBe('text-red-600');
    });
  });

  describe('getUrgencyColor', () => {
    it('returns correct colors for urgency levels', () => {
      expect(getUrgencyColor('high')).toBe('text-red-600 bg-red-50');
      expect(getUrgencyColor('medium')).toBe('text-yellow-600 bg-yellow-50');
      expect(getUrgencyColor('low')).toBe('text-green-600 bg-green-50');
    });

    it('returns default color for unknown levels', () => {
      expect(getUrgencyColor('unknown')).toBe('text-gray-600 bg-gray-50');
      expect(getUrgencyColor('')).toBe('text-gray-600 bg-gray-50');
      expect(getUrgencyColor('invalid')).toBe('text-gray-600 bg-gray-50');
    });

    it('handles case sensitivity', () => {
      expect(getUrgencyColor('HIGH')).toBe('text-gray-600 bg-gray-50');
      expect(getUrgencyColor('High')).toBe('text-gray-600 bg-gray-50');
    });
  });
});
