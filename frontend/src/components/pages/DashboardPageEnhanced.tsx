import { useState } from 'react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Alert, AlertDescription } from '../ui/alert';
import { Skeleton } from '../ui/skeleton';
import { 
  BarChart3, 
  Calendar, 
  TrendingUp, 
  Flame, 
  Target, 
  AlertTriangle, 
  RefreshCw, 
  CheckCircle,
  Activity,
  Clock,
  Trophy
} from 'lucide-react';
import { useDashboard } from '@/hooks/useDashboard';
import { useSyncHevy, useSyncStatus } from '@/hooks/useSync';
import { useAuth } from '@/contexts/AuthContext';

export function DashboardPageEnhanced() {
  const { user } = useAuth();
  const { data: dashboardData, isLoading, isError, error } = useDashboard(user?.id);
  const { data: syncStatus } = useSyncStatus(user?.id);
  const syncMutation = useSyncHevy(user?.id);

  const handleSyncRecent = () => {
    syncMutation.mutate('recent');
  };

  const handleSyncFull = () => {
    syncMutation.mutate('full');
  };

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (isError) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            Failed to load dashboard data: {error?.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            No dashboard data available
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const stats = [
    {
      title: 'Total Workouts',
      value: dashboardData.total_workouts.toString(),
      subtitle: `${dashboardData.recent_workouts} this month`,
      icon: BarChart3,
      color: 'text-primary',
      bgColor: 'bg-primary/10'
    },
    {
      title: 'Weekly Average',
      value: dashboardData.avg_workouts_per_week.toString(),
      subtitle: 'workouts per week',
      icon: TrendingUp,
      color: 'text-green-600',
      bgColor: 'bg-green-100'
    },
    {
      title: 'Current Streak',
      value: dashboardData.current_streak.toString(),
      subtitle: 'days',
      icon: Flame,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100'
    },
    {
      title: 'Last Workout',
      value: dashboardData.last_workout_date || 'Never',
      subtitle: 'most recent session',
      icon: Calendar,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100'
    }
  ];

  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      {/* Welcome Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">
            {dashboardData.welcome_message}
          </h1>
          <p className="text-muted-foreground mt-1">
            Track your fitness journey and stay motivated
          </p>
        </div>
        
        {/* Sync Controls */}
        <div className="flex gap-2">
          <Button
            onClick={handleSyncRecent}
            disabled={syncMutation.isPending || syncStatus?.status === 'syncing'}
            variant="outline"
            size="sm"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
            Sync Recent
          </Button>
          <Button
            onClick={handleSyncFull}
            disabled={syncMutation.isPending || syncStatus?.status === 'syncing'}
            variant="outline"
            size="sm"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
            Sync Full
          </Button>
        </div>
      </div>

      {/* Sync Status */}
      {syncStatus && (
        <Alert className={syncStatus.status === 'error' ? 'border-red-200 bg-red-50' : ''}>
          {syncStatus.status === 'syncing' ? (
            <RefreshCw className="h-4 w-4 animate-spin" />
          ) : syncStatus.status === 'complete' ? (
            <CheckCircle className="h-4 w-4 text-green-600" />
          ) : (
            <AlertTriangle className="h-4 w-4" />
          )}
          <AlertDescription>
            {syncStatus.message}
          </AlertDescription>
        </Alert>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <Card key={index} className="relative overflow-hidden">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
              <div className={`p-2 rounded-full ${stat.bgColor}`}>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-foreground">
                {stat.value}
              </div>
              <p className="text-xs text-muted-foreground">
                {stat.subtitle}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Goals and Injuries */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Fitness Goals */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="h-5 w-5 text-primary" />
              Fitness Goals
            </CardTitle>
            <CardDescription>
              Your current fitness objectives
            </CardDescription>
          </CardHeader>
          <CardContent>
            {dashboardData.fitness_goals.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {dashboardData.fitness_goals.map((goal, index) => (
                  <Badge key={index} variant="secondary" className="capitalize">
                    {goal.replace('_', ' ')}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">
                No goals set yet. Set your fitness goals in your profile.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Active Injuries */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-orange-600" />
              Active Injuries
            </CardTitle>
            <CardDescription>
              Current injury status
            </CardDescription>
          </CardHeader>
          <CardContent>
            {dashboardData.active_injuries.length > 0 ? (
              <div className="space-y-3">
                {dashboardData.active_injuries.map((injury, index) => (
                  <div key={index} className="p-3 bg-orange-50 border border-orange-200 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-orange-900">
                        {injury.body_part}
                      </span>
                      <Badge variant="outline" className="text-orange-700 border-orange-300">
                        {injury.severity}
                      </Badge>
                    </div>
                    <p className="text-sm text-orange-800 mt-1">
                      {injury.description}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4">
                <CheckCircle className="h-8 w-8 text-green-600 mx-auto mb-2" />
                <p className="text-muted-foreground text-sm">
                  No active injuries reported
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      {/* Header Skeleton */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-9 w-24" />
        </div>
      </div>

      {/* Stats Grid Skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 4 }).map((_, index) => (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-8 rounded-full" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16 mb-2" />
              <Skeleton className="h-3 w-20" />
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Goals and Injuries Skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48" />
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              <Skeleton className="h-6 w-20" />
              <Skeleton className="h-6 w-24" />
              <Skeleton className="h-6 w-16" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-4 w-48" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-20 w-full" />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
