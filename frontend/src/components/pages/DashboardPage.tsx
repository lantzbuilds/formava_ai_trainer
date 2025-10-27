import { useState } from 'react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Alert, AlertDescription } from '../ui/alert';
import { ImageWithFallback } from '../figma/ImageWithFallback';
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

export function DashboardPage() {
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'success' | 'error'>('idle');
  const [lastSyncTime, setLastSyncTime] = useState('2 hours ago');

  // Mock user data
  const userData = {
    name: 'Alex',
    totalWorkouts: 127,
    totalWorkoutsLast30: 12,
    avgWorkoutsPerWeek: 3.2,
    lastWorkoutDate: 'September 20, 2024',
    currentStreak: 5,
    goals: ['Muscle Gain', 'Strength Building', 'General Fitness'],
    activeInjuries: [
      {
        bodyPart: 'Knee',
        severity: 'Mild',
        description: 'Minor discomfort during squats'
      }
    ]
  };

  const stats = [
    {
      title: 'Total Workouts',
      value: userData.totalWorkouts.toString(),
      subtitle: `${userData.totalWorkoutsLast30} this month`,
      icon: BarChart3,
      color: 'text-[--fitness-primary]',
      bgColor: 'bg-blue-50'
    },
    {
      title: 'Weekly Average',
      value: userData.avgWorkoutsPerWeek.toString(),
      subtitle: 'workouts per week',
      icon: Calendar,
      color: 'text-[--fitness-secondary]',
      bgColor: 'bg-green-50'
    },
    {
      title: 'Current Streak',
      value: userData.currentStreak.toString(),
      subtitle: 'days in a row',
      icon: Flame,
      color: 'text-[--fitness-accent]',
      bgColor: 'bg-orange-50'
    },
    {
      title: 'Last Workout',
      value: 'Sep 20',
      subtitle: userData.lastWorkoutDate,
      icon: Clock,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50'
    }
  ];

  const handleSync = async (type: 'recent' | 'full') => {
    setSyncStatus('syncing');
    
    try {
      // Simulate sync process
      await new Promise(resolve => setTimeout(resolve, 2000));
      setSyncStatus('success');
      setLastSyncTime('Just now');
      
      // Reset status after 3 seconds
      setTimeout(() => setSyncStatus('idle'), 3000);
    } catch (error) {
      setSyncStatus('error');
      setTimeout(() => setSyncStatus('idle'), 3000);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Welcome Section */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2">
            Welcome back, {userData.name}! 💪
          </h1>
          <p className="text-muted-foreground">
            Here's your fitness overview and recent activity
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <Card key={index} className="border-2 hover:border-[--fitness-primary] transition-colors">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-12 h-12 rounded-lg ${stat.bgColor} flex items-center justify-center`}>
                      <Icon className={`h-6 w-6 ${stat.color}`} />
                    </div>
                    <TrendingUp className="h-4 w-4 text-[--fitness-success]" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-foreground mb-1">{stat.value}</p>
                    <p className="text-sm text-muted-foreground">{stat.title}</p>
                    <p className="text-xs text-muted-foreground mt-1">{stat.subtitle}</p>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Goals Section */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-5 w-5" />
                  Your Fitness Goals
                </CardTitle>
                <CardDescription>
                  Current objectives you're working towards
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {userData.goals.map(goal => (
                    <Badge key={goal} variant="secondary" className="px-3 py-1">
                      {goal}
                    </Badge>
                  ))}
                </div>
                <div className="mt-4 p-4 bg-muted/50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Trophy className="h-4 w-4 text-[--fitness-accent]" />
                    <span className="text-sm font-medium">This Week's Progress</span>
                  </div>
                  <Progress value={65} className="mb-2" />
                  <p className="text-xs text-muted-foreground">
                    3 of 4 planned workouts completed
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Active Injuries Section */}
            {userData.activeInjuries.length > 0 && (
              <Card className="border-amber-200 bg-amber-50/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-amber-700">
                    <AlertTriangle className="h-5 w-5" />
                    Active Injuries
                  </CardTitle>
                  <CardDescription>
                    Current injuries being tracked for safe workout planning
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {userData.activeInjuries.map((injury, index) => (
                    <div key={index} className="flex items-start gap-3 p-3 bg-white rounded-lg border border-amber-200">
                      <div className="w-2 h-2 bg-amber-500 rounded-full mt-2"></div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-amber-800">{injury.bodyPart}</span>
                          <Badge variant="outline" className="text-xs border-amber-300 text-amber-700">
                            {injury.severity}
                          </Badge>
                        </div>
                        <p className="text-sm text-amber-700">{injury.description}</p>
                      </div>
                    </div>
                  ))}
                  <div className="mt-4">
                    <Button variant="outline" size="sm" className="border-amber-300 text-amber-700 hover:bg-amber-100">
                      Manage Injuries
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Sync Controls */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Hevy Sync Control
                </CardTitle>
                <CardDescription>
                  Synchronize your workout data with Hevy app
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  
                  {/* Sync Status */}
                  <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${
                        syncStatus === 'success' ? 'bg-green-500' :
                        syncStatus === 'syncing' ? 'bg-yellow-500 animate-pulse' :
                        syncStatus === 'error' ? 'bg-red-500' :
                        'bg-gray-400'
                      }`}></div>
                      <div>
                        <p className="text-sm font-medium">
                          {syncStatus === 'success' ? 'Sync Complete' :
                           syncStatus === 'syncing' ? 'Syncing...' :
                           syncStatus === 'error' ? 'Sync Failed' :
                           'Ready to Sync'}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Last sync: {lastSyncTime}
                        </p>
                      </div>
                    </div>
                    {syncStatus === 'success' && (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    )}
                  </div>

                  {/* Sync Buttons */}
                  <div className="flex flex-col sm:flex-row gap-3">
                    <Button 
                      onClick={() => handleSync('recent')}
                      disabled={syncStatus === 'syncing'}
                      className="flex items-center gap-2 bg-[--fitness-primary] hover:bg-blue-700"
                    >
                      <RefreshCw className={`h-4 w-4 ${syncStatus === 'syncing' ? 'animate-spin' : ''}`} />
                      Sync Recent Workouts
                    </Button>
                    <Button 
                      variant="outline"
                      onClick={() => handleSync('full')}
                      disabled={syncStatus === 'syncing'}
                      className="flex items-center gap-2"
                    >
                      <RefreshCw className={`h-4 w-4 ${syncStatus === 'syncing' ? 'animate-spin' : ''}`} />
                      Sync Full History
                    </Button>
                  </div>

                  {syncStatus === 'error' && (
                    <Alert variant="destructive">
                      <AlertTriangle className="h-4 w-4" />
                      <AlertDescription>
                        Failed to sync with Hevy. Check your API key in settings.
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            
            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
                <CardDescription>
                  Jump to key features
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button className="w-full justify-start gap-3 bg-[--fitness-primary] hover:bg-blue-700">
                  <Target className="h-4 w-4" />
                  Generate AI Workout
                </Button>
                <Button variant="outline" className="w-full justify-start gap-3">
                  <BarChart3 className="h-4 w-4" />
                  View Progress
                </Button>
                <Button variant="outline" className="w-full justify-start gap-3">
                  <AlertTriangle className="h-4 w-4" />
                  Update Injuries
                </Button>
              </CardContent>
            </Card>

            {/* Recent Activity */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Activity</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                    <div className="w-2 h-2 bg-[--fitness-success] rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Upper Body Workout</p>
                      <p className="text-xs text-muted-foreground">September 20</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                    <div className="w-2 h-2 bg-[--fitness-primary] rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">AI Routine Generated</p>
                      <p className="text-xs text-muted-foreground">September 19</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50">
                    <div className="w-2 h-2 bg-[--fitness-accent] rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm font-medium">Profile Updated</p>
                      <p className="text-xs text-muted-foreground">September 18</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Motivational Quote */}
            <Card className="bg-gradient-to-br from-[--fitness-primary] to-[--fitness-secondary] text-white overflow-hidden">
              <div className="relative">
                <div className="absolute inset-0 opacity-30">
                  <ImageWithFallback
                    src="https://images.unsplash.com/photo-1584827387179-355517d8a5fb?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxneW0lMjB3b3Jrb3V0JTIwZXF1aXBtZW50fGVufDF8fHx8MTc1ODUwNzY3MHww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral"
                    alt="Gym workout motivation"
                    className="w-full h-full object-cover"
                  />
                </div>
                <CardContent className="relative p-6 text-center">
                  <h3 className="font-semibold mb-2">Daily Motivation</h3>
                  <p className="text-sm text-blue-100 italic">
                    "The only bad workout is the one that didn't happen."
                  </p>
                </CardContent>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}