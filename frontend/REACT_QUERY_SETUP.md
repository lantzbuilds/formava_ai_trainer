# React Query (TanStack Query) Setup

## Installation

First, install the required packages:

```bash
cd frontend
npm install @tanstack/react-query @tanstack/react-query-devtools
```

## What's Been Set Up

### 1. Query Client Configuration (`src/lib/queryClient.ts`)
- Configured with sensible defaults:
  - 5-minute stale time
  - 10-minute cache time
  - Automatic refetch on window focus and reconnect
  - Retry logic for failed requests

### 2. Query Provider (`src/providers/QueryProvider.tsx`)
- Wraps the app with QueryClientProvider
- Includes React Query Devtools (development only)
- Already added to `layout.tsx`

### 3. API Client Updates (`src/lib/api/client.ts`)
- Updated to point to FastAPI (port 8000)
- Automatic JWT token injection from localStorage
- Better error message parsing from API responses

### 4. Custom Hooks

#### Authentication (`src/hooks/useAuth.ts`)
- `useLogin()` - Login mutation
- `useRegister()` - Registration mutation
- `useDemoLogin()` - Demo account login mutation
- `useLogout()` - Logout mutation

All auth hooks automatically:
- Store JWT tokens in localStorage
- Invalidate user-related queries on success
- Clear cache on logout

#### Dashboard (`src/hooks/useDashboard.ts`)
- `useDashboard(userId)` - Fetch dashboard data
  - Auto-refetches on window focus
  - 2-minute stale time
  - Includes: workouts, goals, injuries, streak

#### AI Recommendations (`src/hooks/useAIRecs.ts`)
- `useAIRecsSummary(userId)` - Fetch AI recs page summary
- `useGenerateRoutine(userId)` - Generate workout routine (mutation)
- `useSaveToHevy(userId)` - Save routine to Hevy (mutation)

#### Sync (`src/hooks/useSync.ts`)
- `useSyncStatus(userId)` - Get sync status
  - **Automatic polling** while syncing (every 2 seconds)
  - Stops polling when sync completes
- `useSyncHevy(userId)` - Trigger Hevy sync (mutation)
  - Invalidates dashboard data after sync

## Usage Examples

### Login Form
```tsx
import { useLogin } from '@/hooks/useAuth';

function LoginForm() {
  const loginMutation = useLogin();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loginMutation.mutate({ username: '...', password: '...' });
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* form fields */}
      <button disabled={loginMutation.isPending}>
        {loginMutation.isPending ? 'Logging in...' : 'Login'}
      </button>
      {loginMutation.isError && (
        <p className="error">{loginMutation.error.message}</p>
      )}
    </form>
  );
}
```

### Dashboard Component
```tsx
import { useDashboard } from '@/hooks/useDashboard';
import { useAuth } from '@/contexts/AuthContext';

function Dashboard() {
  const { user } = useAuth();
  const { data, isLoading, isError, error } = useDashboard(user?.id);

  if (isLoading) return <div>Loading...</div>;
  if (isError) return <div>Error: {error.message}</div>;

  return (
    <div>
      <h1>{data.welcome_message}</h1>
      <p>Total Workouts: {data.total_workouts}</p>
      <p>Current Streak: {data.current_streak} days</p>
      {/* ... */}
    </div>
  );
}
```

### AI Routine Generation
```tsx
import { useGenerateRoutine } from '@/hooks/useAIRecs';

function AIRecsPage() {
  const { user } = useAuth();
  const generateMutation = useGenerateRoutine(user?.id);

  const handleGenerate = () => {
    generateMutation.mutate({
      split_type: 'auto',
      period: 'week',
      include_cardio: true,
    });
  };

  return (
    <div>
      <button 
        onClick={handleGenerate} 
        disabled={generateMutation.isPending}
      >
        {generateMutation.isPending ? 'Generating...' : 'Generate Routine'}
      </button>
      
      {generateMutation.isSuccess && (
        <div>{/* Display generated routine */}</div>
      )}
    </div>
  );
}
```

### Sync with Automatic Polling
```tsx
import { useSyncHevy, useSyncStatus } from '@/hooks/useSync';

function SyncControls() {
  const { user } = useAuth();
  const syncMutation = useSyncHevy(user?.id);
  const { data: syncStatus } = useSyncStatus(user?.id);
  
  // syncStatus automatically polls every 2 seconds while status === 'syncing'

  return (
    <div>
      <button onClick={() => syncMutation.mutate('recent')}>
        Sync Recent Workouts
      </button>
      <button onClick={() => syncMutation.mutate('full')}>
        Sync Full History
      </button>
      <p>{syncStatus?.message}</p>
    </div>
  );
}
```

## React Query Dev Tools

The dev tools are automatically included in development mode. Open them by clicking the React Query icon in the bottom corner of your browser.

Features:
- View all active queries and their state
- Inspect cached data
- Manually trigger refetches
- See query timings and network requests

## Benefits You Get

1. **Automatic Caching** - Data is cached and reused across components
2. **Background Refetching** - Fresh data without user interaction
3. **Loading/Error States** - Built-in state management
4. **Optimistic Updates** - Instant UI feedback
5. **Automatic Retry** - Failed requests retry automatically
6. **Request Deduplication** - Multiple components requesting same data = 1 request
7. **Smart Polling** - Sync status polls only while syncing
8. **Cache Invalidation** - Related data refreshes after mutations

## Next Steps

1. **Install the packages** (see Installation section)
2. **Build your page components** using the hooks
3. **Integrate Figma components** with React Query data fetching
4. **Test with the FastAPI backend** running on port 8000

