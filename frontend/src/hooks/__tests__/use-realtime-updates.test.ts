import { renderHook, act, waitFor } from '@testing-library/react';
import {
  useRealtimeUpdates,
  useDashboardMetrics,
  useActivityFeed,
  useActionQueue,
} from '../use-realtime-updates';
import api from '@/lib/api';

// Mock the API
jest.mock('@/lib/api', () => ({
  get: jest.fn(),
}));

const mockApi = api as jest.Mocked<typeof api>;

describe('useRealtimeUpdates', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('initializes with loading state', () => {
    mockApi.get.mockResolvedValue({ data: null });

    const { result } = renderHook(() => useRealtimeUpdates({ endpoint: '/test' }));

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBe(null);
    expect(result.current.error).toBe(null);
    expect(result.current.lastUpdated).toBe(null);
  });

  it('fetches data successfully', async () => {
    const mockData = { id: 1, name: 'Test Data' };
    mockApi.get.mockResolvedValue({ data: mockData });

    const { result } = renderHook(() => useRealtimeUpdates({ endpoint: '/test' }));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual(mockData);
    expect(result.current.error).toBe(null);
    expect(result.current.lastUpdated).toBeInstanceOf(Date);
    expect(mockApi.get).toHaveBeenCalledWith('/test');
  });

  it('handles API errors', async () => {
    const errorMessage = 'API Error';
    mockApi.get.mockRejectedValue({
      response: { data: { detail: errorMessage } },
    });

    const { result } = renderHook(() => useRealtimeUpdates({ endpoint: '/test' }));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBe(null);
    expect(result.current.error).toBe(errorMessage);
    expect(result.current.lastUpdated).toBe(null);
  });

  it('handles generic errors', async () => {
    mockApi.get.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useRealtimeUpdates({ endpoint: '/test' }));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBe('Failed to fetch data');
  });

  it('polls data at specified interval', async () => {
    mockApi.get.mockResolvedValue({ data: 'test' });

    renderHook(() => useRealtimeUpdates({ endpoint: '/test', interval: 1000 }));

    // Initial call
    expect(mockApi.get).toHaveBeenCalledTimes(1);

    // Fast forward 1 second
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(mockApi.get).toHaveBeenCalledTimes(2);
    });

    // Fast forward another second
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    await waitFor(() => {
      expect(mockApi.get).toHaveBeenCalledTimes(3);
    });
  });

  it('does not fetch when disabled', () => {
    mockApi.get.mockResolvedValue({ data: 'test' });

    renderHook(() => useRealtimeUpdates({ endpoint: '/test', enabled: false }));

    expect(mockApi.get).not.toHaveBeenCalled();
  });

  it('stops polling when disabled', async () => {
    mockApi.get.mockResolvedValue({ data: 'test' });

    const { rerender } = renderHook(
      ({ enabled }) => useRealtimeUpdates({ endpoint: '/test', enabled }),
      { initialProps: { enabled: true } },
    );

    expect(mockApi.get).toHaveBeenCalledTimes(1);

    // Disable polling
    rerender({ enabled: false });

    // Fast forward time
    act(() => {
      jest.advanceTimersByTime(30000);
    });

    // Should not have made additional calls
    expect(mockApi.get).toHaveBeenCalledTimes(1);
  });

  it('provides refetch function', async () => {
    mockApi.get.mockResolvedValue({ data: 'test' });

    const { result } = renderHook(() => useRealtimeUpdates({ endpoint: '/test' }));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Clear previous calls
    mockApi.get.mockClear();

    // Call refetch
    await act(async () => {
      await result.current.refetch();
    });

    expect(mockApi.get).toHaveBeenCalledTimes(1);
    expect(mockApi.get).toHaveBeenCalledWith('/test');
  });

  it('cleans up interval on unmount', () => {
    const clearIntervalSpy = jest.spyOn(global, 'clearInterval');

    const { unmount } = renderHook(() => useRealtimeUpdates({ endpoint: '/test' }));

    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
    clearIntervalSpy.mockRestore();
  });

  it('updates endpoint correctly', async () => {
    mockApi.get.mockResolvedValue({ data: 'test' });

    const { rerender } = renderHook(({ endpoint }) => useRealtimeUpdates({ endpoint }), {
      initialProps: { endpoint: '/test1' },
    });

    expect(mockApi.get).toHaveBeenCalledWith('/test1');

    // Change endpoint
    rerender({ endpoint: '/test2' });

    await waitFor(() => {
      expect(mockApi.get).toHaveBeenCalledWith('/test2');
    });
  });
});

describe('specialized hooks', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApi.get.mockResolvedValue({ data: 'test' });
  });

  it('useDashboardMetrics uses correct endpoint and interval', () => {
    renderHook(() => useDashboardMetrics());

    expect(mockApi.get).toHaveBeenCalledWith('/dashboard/metrics');
  });

  it('useActivityFeed uses correct endpoint and interval', () => {
    renderHook(() => useActivityFeed());

    expect(mockApi.get).toHaveBeenCalledWith('/dashboard/activity');
  });

  it('useActionQueue uses correct endpoint and interval', () => {
    renderHook(() => useActionQueue());

    expect(mockApi.get).toHaveBeenCalledWith('/dashboard/actions');
  });
});
