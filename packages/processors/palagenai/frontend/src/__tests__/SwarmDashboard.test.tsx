import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SwarmDashboard } from '../pages/SwarmDashboard';
import '@testing-library/jest-dom';

describe('SwarmDashboard', () => {
  let mockFetch: any;

  beforeEach(() => {
    mockFetch = vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders the dashboard', () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <SwarmDashboard />
      </QueryClientProvider>
    );

    expect(screen.getByText('Docker Swarm Dashboard')).toBeInTheDocument();
  });

  it('displays cluster information when data loads', async () => {
    mockFetch.mockResolvedValueOnce({
      json: async () => ({
        data: {
          swarm_id: 'test-swarm-123',
          node_count: 3,
          manager_count: 1,
          worker_count: 2,
          version: '1.0',
        },
      }),
    });

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <SwarmDashboard />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Cluster Information/i)).toBeInTheDocument();
    });
  });
});
