import { useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Checkbox } from '../ui/checkbox';
import { Textarea } from '../ui/textarea';
import { Slider } from '../ui/slider';
import { Badge } from '../ui/badge';
import { Separator } from '../ui/separator';
import { Alert, AlertDescription } from '../ui/alert';
import { Dumbbell, User, Activity, Target, Calendar, AlertTriangle, Smartphone } from 'lucide-react';

interface RegistrationPageProps {
  onPageChange: (page: 'login') => void;
}

export function RegistrationPage({ onPageChange }: RegistrationPageProps) {
  const [formData, setFormData] = useState({
    // Personal Info
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    
    // Physical Stats
    heightFeet: '',
    heightInches: '',
    weight: '',
    age: '',
    sex: '',
    
    // Fitness Profile
    experienceLevel: '',
    preferredUnits: 'imperial',
    fitnessGoals: [] as string[],
    
    // Workout Preferences
    daysPerWeek: [3],
    workoutDuration: [45],
    
    // Injury Management
    hasInjuries: false,
    injuryDescription: '',
    injuryBodyPart: '',
    injurySeverity: '',
    
    // Hevy Integration
    heavyApiKey: ''
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  const fitnessGoalOptions = [
    'Weight Loss',
    'Muscle Gain',
    'Strength Building',
    'Endurance',
    'General Fitness',
    'Sports Performance',
    'Rehabilitation',
    'Flexibility'
  ];

  const bodyParts = [
    'Knee', 'Shoulder', 'Back', 'Wrist', 'Ankle', 'Hip', 'Neck', 'Elbow', 'Other'
  ];

  const severityLevels = [
    'Mild - Minor discomfort',
    'Moderate - Noticeable limitation',
    'Severe - Significant restriction'
  ];

  const handleInputChange = (field: string, value: string | number | boolean | string[]) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear specific field error
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleGoalToggle = (goal: string) => {
    setFormData(prev => ({
      ...prev,
      fitnessGoals: prev.fitnessGoals.includes(goal)
        ? prev.fitnessGoals.filter(g => g !== goal)
        : [...prev.fitnessGoals, goal]
    }));
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    // Personal Info validation
    if (!formData.username.trim()) newErrors.username = 'Username is required';
    if (!formData.email.trim()) newErrors.email = 'Email is required';
    if (!formData.email.includes('@')) newErrors.email = 'Valid email is required';
    if (!formData.password) newErrors.password = 'Password is required';
    if (formData.password.length < 6) newErrors.password = 'Password must be at least 6 characters';
    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    // Physical Stats validation
    if (!formData.heightFeet) newErrors.heightFeet = 'Height is required';
    if (!formData.weight) newErrors.weight = 'Weight is required';
    if (!formData.age) newErrors.age = 'Age is required';
    if (!formData.sex) newErrors.sex = 'Sex is required';

    // Fitness Profile validation
    if (!formData.experienceLevel) newErrors.experienceLevel = 'Experience level is required';
    if (formData.fitnessGoals.length === 0) newErrors.fitnessGoals = 'Select at least one fitness goal';

    // Injury validation
    if (formData.hasInjuries && !formData.injuryDescription.trim()) {
      newErrors.injuryDescription = 'Injury description is required';
    }
    if (formData.hasInjuries && !formData.injuryBodyPart) {
      newErrors.injuryBodyPart = 'Body part is required';
    }
    if (formData.hasInjuries && !formData.injurySeverity) {
      newErrors.injurySeverity = 'Severity level is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    setLoading(true);
    
    try {
      // Simulate registration
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // In real app, would redirect to dashboard
    } catch (error) {
      
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[--fitness-primary]/5 to-[--fitness-secondary]/5 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <Dumbbell className="h-10 w-10 text-[--fitness-primary]" />
            <h1 className="text-3xl font-bold">Join Formava AI</h1>
          </div>
          <p className="text-muted-foreground">
            Create your personalized fitness profile to get started with AI-powered training
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="space-y-8">
            
            {/* Personal Information */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  Personal Information
                </CardTitle>
                <CardDescription>
                  Basic account details and login credentials
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="username">Username *</Label>
                    <Input
                      id="username"
                      value={formData.username}
                      onChange={(e) => handleInputChange('username', e.target.value)}
                      placeholder="Choose a username"
                    />
                    {errors.username && <p className="text-sm text-destructive">{errors.username}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email *</Label>
                    <Input
                      id="email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => handleInputChange('email', e.target.value)}
                      placeholder="your@email.com"
                    />
                    {errors.email && <p className="text-sm text-destructive">{errors.email}</p>}
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="password">Password *</Label>
                    <Input
                      id="password"
                      type="password"
                      value={formData.password}
                      onChange={(e) => handleInputChange('password', e.target.value)}
                      placeholder="Minimum 6 characters"
                    />
                    {errors.password && <p className="text-sm text-destructive">{errors.password}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="confirmPassword">Confirm Password *</Label>
                    <Input
                      id="confirmPassword"
                      type="password"
                      value={formData.confirmPassword}
                      onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                      placeholder="Repeat password"
                    />
                    {errors.confirmPassword && <p className="text-sm text-destructive">{errors.confirmPassword}</p>}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Physical Stats */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Physical Stats
                </CardTitle>
                <CardDescription>
                  Help us understand your physical profile for personalized recommendations
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="space-y-2">
                    <Label>Height (ft) *</Label>
                    <Select value={formData.heightFeet} onValueChange={(value: string) => handleInputChange('heightFeet', value)}>
                      <SelectTrigger>
                        <SelectValue placeholder="Feet" />
                      </SelectTrigger>
                      <SelectContent>
                        {[4, 5, 6, 7].map(ft => (
                          <SelectItem key={ft} value={ft.toString()}>{ft}'</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {errors.heightFeet && <p className="text-sm text-destructive">{errors.heightFeet}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label>Height (in)</Label>
                    <Select value={formData.heightInches} onValueChange={(value: string) => handleInputChange('heightInches', value)}>
                      <SelectTrigger>
                        <SelectValue placeholder="Inches" />
                      </SelectTrigger>
                      <SelectContent>
                        {Array.from({length: 12}, (_, i) => (
                          <SelectItem key={i} value={i.toString()}>{i}"</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="weight">Weight (lbs) *</Label>
                    <Input
                      id="weight"
                      type="number"
                      value={formData.weight}
                      onChange={(e) => handleInputChange('weight', e.target.value)}
                      placeholder="150"
                    />
                    {errors.weight && <p className="text-sm text-destructive">{errors.weight}</p>}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="age">Age *</Label>
                    <Input
                      id="age"
                      type="number"
                      value={formData.age}
                      onChange={(e) => handleInputChange('age', e.target.value)}
                      placeholder="25"
                    />
                    {errors.age && <p className="text-sm text-destructive">{errors.age}</p>}
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Sex *</Label>
                  <Select value={formData.sex} onValueChange={(value: string) => handleInputChange('sex', value)}>
                    <SelectTrigger className="w-full md:w-48">
                      <SelectValue placeholder="Select sex" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="male">Male</SelectItem>
                      <SelectItem value="female">Female</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                  {errors.sex && <p className="text-sm text-destructive">{errors.sex}</p>}
                </div>
              </CardContent>
            </Card>

            {/* Fitness Profile */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-5 w-5" />
                  Fitness Profile
                </CardTitle>
                <CardDescription>
                  Tell us about your fitness experience and goals
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label>Experience Level *</Label>
                  <Select value={formData.experienceLevel} onValueChange={(value: string) => handleInputChange('experienceLevel', value)}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select your experience level" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="beginner">Beginner (0-6 months)</SelectItem>
                      <SelectItem value="intermediate">Intermediate (6 months - 2 years)</SelectItem>
                      <SelectItem value="advanced">Advanced (2+ years)</SelectItem>
                      <SelectItem value="expert">Expert (5+ years)</SelectItem>
                    </SelectContent>
                  </Select>
                  {errors.experienceLevel && <p className="text-sm text-destructive">{errors.experienceLevel}</p>}
                </div>

                <div className="space-y-3">
                  <Label>Fitness Goals * (Select all that apply)</Label>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {fitnessGoalOptions.map(goal => (
                      <div key={goal} className="flex items-center space-x-2">
                        <Checkbox
                          id={goal}
                          checked={formData.fitnessGoals.includes(goal)}
                          onCheckedChange={() => handleGoalToggle(goal)}
                        />
                        <Label htmlFor={goal} className="text-sm cursor-pointer">{goal}</Label>
                      </div>
                    ))}
                  </div>
                  {errors.fitnessGoals && <p className="text-sm text-destructive">{errors.fitnessGoals}</p>}
                </div>

                <div className="space-y-2">
                  <Label>Preferred Units</Label>
                  <Select value={formData.preferredUnits} onValueChange={(value: string) => handleInputChange('preferredUnits', value)}>
                    <SelectTrigger className="w-full md:w-48">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="imperial">Imperial (lbs, ft/in)</SelectItem>
                      <SelectItem value="metric">Metric (kg, cm)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            {/* Workout Preferences */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5" />
                  Workout Preferences
                </CardTitle>
                <CardDescription>
                  Configure your ideal workout schedule
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-3">
                  <Label>Days per week: {formData.daysPerWeek[0]} days</Label>
                  <Slider
                    value={formData.daysPerWeek}
                    onValueChange={(value: number[]) => handleInputChange('daysPerWeek', value.map(String))}
                    max={7}
                    min={1}
                    step={1}
                    className="w-full"
                  />
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>1 day</span>
                    <span>7 days</span>
                  </div>
                </div>

                <div className="space-y-3">
                  <Label>Workout duration: {formData.workoutDuration[0]} minutes</Label>
                  <Slider
                    value={formData.workoutDuration}
                    onValueChange={(value: number[]) => handleInputChange('workoutDuration', value.map(String))}
                    max={120}
                    min={15}
                    step={15}
                    className="w-full"
                  />
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>15 min</span>
                    <span>2 hours</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Injury Management */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5" />
                  Injury Management
                </CardTitle>
                <CardDescription>
                  Help us create safe workouts by tracking any current injuries
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="hasInjuries"
                    checked={formData.hasInjuries}
                    onCheckedChange={(checked: boolean) => handleInputChange('hasInjuries', checked)}
                  />
                  <Label htmlFor="hasInjuries">I currently have injuries or physical limitations</Label>
                </div>

                {formData.hasInjuries && (
                  <div className="space-y-4 p-4 border rounded-lg bg-muted/20">
                    <div className="space-y-2">
                      <Label htmlFor="injuryDescription">Injury Description *</Label>
                      <Textarea
                        id="injuryDescription"
                        value={formData.injuryDescription}
                        onChange={(e) => handleInputChange('injuryDescription', e.target.value)}
                        placeholder="Describe your injury or limitation..."
                        rows={3}
                      />
                      {errors.injuryDescription && <p className="text-sm text-destructive">{errors.injuryDescription}</p>}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Affected Body Part *</Label>
                        <Select value={formData.injuryBodyPart} onValueChange={(value: string) => handleInputChange('injuryBodyPart', value)}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select body part" />
                          </SelectTrigger>
                          <SelectContent>
                            {bodyParts.map(part => (
                              <SelectItem key={part} value={part}>{part}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {errors.injuryBodyPart && <p className="text-sm text-destructive">{errors.injuryBodyPart}</p>}
                      </div>

                      <div className="space-y-2">
                        <Label>Severity Level *</Label>
                        <Select value={formData.injurySeverity} onValueChange={(value: string) => handleInputChange('injurySeverity', value)}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select severity" />
                          </SelectTrigger>
                          <SelectContent>
                            {severityLevels.map(level => (
                              <SelectItem key={level} value={level}>{level}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {errors.injurySeverity && <p className="text-sm text-destructive">{errors.injurySeverity}</p>}
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Hevy Integration */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Smartphone className="h-5 w-5" />
                  Hevy Integration
                </CardTitle>
                <CardDescription>
                  Optionally connect your Hevy account for workout tracking integration
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      <strong>Optional:</strong> You can add your Hevy API key later in settings. 
                      Formava AI works great as a standalone app too!
                    </AlertDescription>
                  </Alert>

                  <div className="space-y-2">
                    <Label htmlFor="heavyApiKey">Hevy API Key (Optional)</Label>
                    <Input
                      id="heavyApiKey"
                      type="password"
                      value={formData.heavyApiKey}
                      onChange={(e) => handleInputChange('heavyApiKey', e.target.value)}
                      placeholder="Enter your Hevy API key"
                    />
                    <p className="text-sm text-muted-foreground">
                      Get your API key from Hevy app settings to sync workouts automatically
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Submit Button */}
            <div className="flex flex-col gap-4">
              <Button 
                type="submit" 
                size="lg" 
                className="w-full bg-[--fitness-primary] hover:bg-blue-700"
                disabled={loading}
              >
                {loading ? 'Creating Your Account...' : 'Create Account'}
              </Button>
              
              <div className="text-center text-sm text-muted-foreground">
                Already have an account?{' '}
                <button type="button" className="text-[--fitness-primary] hover:underline">
                  Sign in here
                </button>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}