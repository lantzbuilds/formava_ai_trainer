import { useState } from 'react';
import { Button } from '../ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Checkbox } from '../ui/checkbox';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { Separator } from '../ui/separator';
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from '../ui/carousel';
import { ImageWithFallback } from '../figma/ImageWithFallback';
import { 
  Brain, 
  User, 
  Activity, 
  Database, 
  Loader2, 
  CheckCircle, 
  Target,
  Calendar,
  Clock,
  Dumbbell,
  Save
} from 'lucide-react';

export function AIRecommendationsPage() {
  const [generationPrefs, setGenerationPrefs] = useState({
    workoutSplit: '',
    timePeriod: '',
    includeCardio: false,
    routineFolderTitle: ''
  });
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedRoutine, setGeneratedRoutine] = useState<any>(null);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
  const [loadingMessage, setLoadingMessage] = useState('');

  const loadingMessages = [
    'Analyzing your fitness profile...',
    'Considering your injury history...',
    'Selecting optimal exercises...',
    'Calculating sets and reps...',
    'Personalizing your routine...',
    'Finalizing your AI workout...'
  ];

  // Mock user data
  const userProfile = {
    experience: 'Intermediate',
    goals: ['Muscle Gain', 'Strength Building'],
    schedule: '4 days per week, 60 minutes',
    injuries: ['Knee - Mild discomfort']
  };

  const workoutHistory = {
    totalWorkouts: 127,
    avgPerWeek: 3.2,
    lastWorkout: '2 days ago',
    favoriteExercises: ['Bench Press', 'Squats', 'Deadlifts']
  };

  const exerciseDatabase = {
    totalExercises: 847,
    categories: ['Chest', 'Back', 'Legs', 'Shoulders', 'Arms', 'Core', 'Cardio'],
    equipmentTypes: ['Barbell', 'Dumbbell', 'Machine', 'Bodyweight', 'Cable']
  };

  const handleGenerate = async () => {
    if (!generationPrefs.workoutSplit || !generationPrefs.timePeriod) {
      return;
    }

    setIsGenerating(true);
    setLoadingMessage(loadingMessages[0]);

    // Cycle through loading messages
    for (let i = 0; i < loadingMessages.length; i++) {
      setLoadingMessage(loadingMessages[i]);
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    // Simulate routine generation
    const mockRoutine = {
      title: generationPrefs.routineFolderTitle || 'AI Generated Routine',
      split: generationPrefs.workoutSplit,
      period: generationPrefs.timePeriod,
      workouts: [
        {
          day: 'Day 1: Upper Body Power',
          image: 'https://images.unsplash.com/photo-1734188341701-5a0b7575efbe?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx1cHBlciUyMGJvZHklMjB3b3Jrb3V0fGVufDF8fHx8MTc1ODU4MDg1Nnww&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
          exercises: [
            { name: 'Bench Press', sets: '4 sets', reps: '6-8 reps', rest: '2-3 min' },
            { name: 'Barbell Rows', sets: '4 sets', reps: '6-8 reps', rest: '2-3 min' },
            { name: 'Overhead Press', sets: '3 sets', reps: '8-10 reps', rest: '2 min' },
            { name: 'Pull-ups', sets: '3 sets', reps: 'To failure', rest: '2 min' },
            { name: 'Dips', sets: '3 sets', reps: '10-12 reps', rest: '90 sec' }
          ]
        },
        {
          day: 'Day 2: Lower Body Power',
          image: 'https://images.unsplash.com/photo-1623874307886-443c99baf1ed?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxsZWclMjBkYXklMjBzcXVhdHxlbnwxfHx8fDE3NTg1ODA4NTl8MA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
          exercises: [
            { name: 'Squats', sets: '4 sets', reps: '6-8 reps', rest: '3 min' },
            { name: 'Romanian Deadlifts', sets: '3 sets', reps: '8-10 reps', rest: '2-3 min' },
            { name: 'Bulgarian Split Squats', sets: '3 sets', reps: '10-12 each leg', rest: '2 min' },
            { name: 'Leg Curls', sets: '3 sets', reps: '12-15 reps', rest: '90 sec' },
            { name: 'Calf Raises', sets: '4 sets', reps: '15-20 reps', rest: '60 sec' }
          ]
        }
      ],
      notes: [
        'Knee-friendly modifications included for all lower body exercises',
        'Progressive overload: Increase weight by 2.5-5lbs when you can complete all sets with good form',
        'Rest 48-72 hours between training the same muscle groups'
      ]
    };

    setGeneratedRoutine(mockRoutine);
    setIsGenerating(false);
  };

  const handleSaveToHevy = async () => {
    setSaveStatus('saving');
    
    try {
      await new Promise(resolve => setTimeout(resolve, 2000));
      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch (error) {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2 flex items-center gap-3">
            <Brain className="h-8 w-8 text-[--fitness-primary]" />
            AI Workout Recommendations
          </h1>
          <p className="text-muted-foreground">
            Generate personalized workout routines powered by artificial intelligence
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Profile Summary Sidebar */}
          <div className="space-y-6">
            
            {/* Profile Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <User className="h-5 w-5" />
                  Your Profile
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm font-medium mb-1">Experience Level</p>
                  <Badge variant="secondary">{userProfile.experience}</Badge>
                </div>
                <div>
                  <p className="text-sm font-medium mb-2">Goals</p>
                  <div className="flex flex-wrap gap-1">
                    {userProfile.goals.map(goal => (
                      <Badge key={goal} variant="outline" className="text-xs">
                        {goal}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-sm font-medium mb-1">Schedule</p>
                  <p className="text-sm text-muted-foreground">{userProfile.schedule}</p>
                </div>
                <div>
                  <p className="text-sm font-medium mb-1">Active Injuries</p>
                  {userProfile.injuries.map(injury => (
                    <Badge key={injury} variant="outline" className="text-xs text-amber-700 border-amber-300">
                      {injury}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Workout History */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Activity className="h-5 w-5" />
                  Workout History
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm">Total Workouts</span>
                  <span className="text-sm font-medium">{workoutHistory.totalWorkouts}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Average/Week</span>
                  <span className="text-sm font-medium">{workoutHistory.avgPerWeek}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Last Workout</span>
                  <span className="text-sm font-medium">{workoutHistory.lastWorkout}</span>
                </div>
                <Separator />
                <div>
                  <p className="text-sm font-medium mb-1">Favorite Exercises</p>
                  <div className="space-y-1">
                    {workoutHistory.favoriteExercises.map(exercise => (
                      <p key={exercise} className="text-xs text-muted-foreground">• {exercise}</p>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Exercise Database */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Database className="h-5 w-5" />
                  Exercise Database
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm">Total Exercises</span>
                  <span className="text-sm font-medium">{exerciseDatabase.totalExercises}</span>
                </div>
                <div>
                  <p className="text-sm font-medium mb-2">Categories</p>
                  <div className="grid grid-cols-2 gap-1">
                    {exerciseDatabase.categories.map(category => (
                      <Badge key={category} variant="outline" className="text-xs text-center">
                        {category}
                      </Badge>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Generation Preferences */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-5 w-5" />
                  Generation Preferences
                </CardTitle>
                <CardDescription>
                  Customize your AI-generated workout routine
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Workout Split Type</Label>
                    <Select 
                      value={generationPrefs.workoutSplit} 
                      onValueChange={(value) => setGenerationPrefs(prev => ({...prev, workoutSplit: value}))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select split type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="auto">Auto (AI Chooses Best)</SelectItem>
                        <SelectItem value="full-body">Full Body</SelectItem>
                        <SelectItem value="upper-lower">Upper/Lower Split</SelectItem>
                        <SelectItem value="push-pull-legs">Push/Pull/Legs</SelectItem>
                        <SelectItem value="body-part">Body Part Split</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Time Period</Label>
                    <Select 
                      value={generationPrefs.timePeriod} 
                      onValueChange={(value) => setGenerationPrefs(prev => ({...prev, timePeriod: value}))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select period" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1-week">1 Week</SelectItem>
                        <SelectItem value="2-weeks">2 Weeks</SelectItem>
                        <SelectItem value="4-weeks">4 Weeks (1 Month)</SelectItem>
                        <SelectItem value="8-weeks">8 Weeks (2 Months)</SelectItem>
                        <SelectItem value="12-weeks">12 Weeks (3 Months)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="includeCardio"
                      checked={generationPrefs.includeCardio}
                      onCheckedChange={(checked) => setGenerationPrefs(prev => ({...prev, includeCardio: checked as boolean}))}
                    />
                    <Label htmlFor="includeCardio">Include cardio sessions</Label>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="routineTitle">Routine Folder Title (Optional)</Label>
                    <Input
                      id="routineTitle"
                      value={generationPrefs.routineFolderTitle}
                      onChange={(e) => setGenerationPrefs(prev => ({...prev, routineFolderTitle: e.target.value}))}
                      placeholder="e.g., Summer 2024 Strength Program"
                    />
                  </div>
                </div>

                {/* Generate Button */}
                <Button 
                  onClick={handleGenerate}
                  disabled={!generationPrefs.workoutSplit || !generationPrefs.timePeriod || isGenerating}
                  className="w-full bg-[--fitness-primary] hover:bg-blue-700"
                  size="lg"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Brain className="h-5 w-5 mr-2" />
                      Generate AI Workout
                    </>
                  )}
                </Button>

                {/* Loading Messages */}
                {isGenerating && (
                  <Alert>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <AlertDescription>{loadingMessage}</AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>

            {/* Generated Routine Display */}
            {generatedRoutine && (
              <Card className="border-2 border-[--fitness-primary]">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-2">
                      <CheckCircle className="h-5 w-5 text-[--fitness-success]" />
                      Generated Routine
                    </CardTitle>
                    <Badge variant="secondary" className="bg-green-100 text-green-700">
                      AI Generated
                    </Badge>
                  </div>
                  <CardDescription>
                    {generatedRoutine.title} • {generatedRoutine.split} • {generatedRoutine.period}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  
                  {/* Workouts Carousel */}
                  <Carousel className="w-full">
                    <CarouselContent>
                      {generatedRoutine.workouts.map((workout: any, index: number) => (
                        <CarouselItem key={index}>
                          <div className="p-4 border rounded-lg bg-muted/20">
                            {/* Workout Header with Image */}
                            <div className="relative mb-4 rounded-lg overflow-hidden">
                              <div className="aspect-[16/9] w-full">
                                <ImageWithFallback
                                  src={workout.image}
                                  alt={workout.day}
                                  className="w-full h-full object-cover"
                                />
                              </div>
                              <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />
                              <div className="absolute bottom-4 left-4">
                                <h4 className="text-white font-semibold text-lg flex items-center gap-2">
                                  <Calendar className="h-5 w-5" />
                                  {workout.day}
                                </h4>
                              </div>
                            </div>
                            
                            {/* Exercise List */}
                            <div className="space-y-3">
                              {workout.exercises.map((exercise: any, exerciseIndex: number) => (
                                <div key={exerciseIndex} className="flex items-center justify-between p-3 bg-white rounded border hover:bg-gray-50 transition-colors">
                                  <div className="flex items-center gap-3">
                                    <Dumbbell className="h-4 w-4 text-[--fitness-primary]" />
                                    <span className="font-medium">{exercise.name}</span>
                                  </div>
                                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                    <span className="bg-muted px-2 py-1 rounded text-xs">{exercise.sets}</span>
                                    <span className="bg-muted px-2 py-1 rounded text-xs">{exercise.reps}</span>
                                    <div className="flex items-center gap-1 bg-muted px-2 py-1 rounded text-xs">
                                      <Clock className="h-3 w-3" />
                                      <span>{exercise.rest}</span>
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        </CarouselItem>
                      ))}
                    </CarouselContent>
                    <CarouselPrevious />
                    <CarouselNext />
                  </Carousel>

                  {/* Notes */}
                  <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <h4 className="font-semibold mb-2 text-blue-800">Important Notes</h4>
                    <ul className="space-y-1 text-sm text-blue-700">
                      {generatedRoutine.notes.map((note: string, index: number) => (
                        <li key={index} className="flex items-start gap-2">
                          <span className="w-1 h-1 bg-blue-500 rounded-full mt-2 flex-shrink-0"></span>
                          <span>{note}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Save to Hevy */}
                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium">Save to Hevy</h4>
                        <p className="text-sm text-muted-foreground">
                          Export this routine directly to your Hevy app
                        </p>
                      </div>
                      <Button 
                        onClick={handleSaveToHevy}
                        disabled={saveStatus === 'saving'}
                        className="bg-[--fitness-secondary] hover:bg-green-700"
                      >
                        {saveStatus === 'saving' ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Saving...
                          </>
                        ) : saveStatus === 'success' ? (
                          <>
                            <CheckCircle className="h-4 w-4 mr-2" />
                            Saved!
                          </>
                        ) : (
                          <>
                            <Save className="h-4 w-4 mr-2" />
                            Save to Hevy
                          </>
                        )}
                      </Button>
                    </div>

                    {saveStatus === 'success' && (
                      <Alert className="mt-3 border-green-200 bg-green-50">
                        <CheckCircle className="h-4 w-4 text-green-600" />
                        <AlertDescription className="text-green-700">
                          Routine successfully saved to your Hevy app! You can now track your workouts.
                        </AlertDescription>
                      </Alert>
                    )}

                    {saveStatus === 'error' && (
                      <Alert variant="destructive" className="mt-3">
                        <AlertDescription>
                          Failed to save to Hevy. Please check your API key in settings.
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}