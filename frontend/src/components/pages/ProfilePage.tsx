import { useState, useEffect } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Checkbox } from '../ui/checkbox';
import { Textarea } from '../ui/textarea';
import { Slider } from '../ui/slider';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { Separator } from '../ui/separator';
import { 
  User, 
  Activity, 
  Target, 
  Calendar, 
  AlertTriangle, 
  Smartphone,
  CheckCircle,
  X,
  Plus,
  Save,
  Eye,
  EyeOff
} from 'lucide-react';

export function ProfilePage() {
  const [profile, setProfile] = useState({
    // Personal Info (read-only)
    username: 'alex_trainer',
    email: 'alex@example.com',
    age: 28,
    sex: 'male',
    
    // Physical Stats (editable)
    heightFeet: '5',
    heightInches: '10',
    weight: '175',
    
    // Fitness Information (editable)
    experienceLevel: 'intermediate',
    preferredUnits: 'imperial',
    fitnessGoals: ['Muscle Gain', 'Strength Building', 'General Fitness'],
    
    // Workout Preferences (editable)
    daysPerWeek: [4],
    workoutDuration: [60],
    
    // Hevy Integration
    heavyApiKey: '',
    heavyConnected: false
  });

  const [injuries, setInjuries] = useState([
    {
      id: 1,
      description: 'Minor knee discomfort during squats',
      bodyPart: 'Knee',
      severity: 'Mild',
      date: '2024-09-15',
      notes: 'Occurred after heavy squat session',
      isActive: true
    }
  ]);

  const [newInjury, setNewInjury] = useState({
    description: '',
    bodyPart: '',
    severity: '',
    date: '',
    notes: ''
  });

  const [showApiKey, setShowApiKey] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
  const [showAddInjury, setShowAddInjury] = useState(false);

  const fitnessGoalOptions = [
    'Weight Loss', 'Muscle Gain', 'Strength Building', 'Endurance', 
    'General Fitness', 'Sports Performance', 'Rehabilitation', 'Flexibility'
  ];

  const bodyParts = [
    'Knee', 'Shoulder', 'Back', 'Wrist', 'Ankle', 'Hip', 'Neck', 'Elbow', 'Other'
  ];

  const severityLevels = [
    'Mild - Minor discomfort',
    'Moderate - Noticeable limitation', 
    'Severe - Significant restriction'
  ];

  // Auto-save functionality
  useEffect(() => {
    const timer = setTimeout(() => {
      if (saveStatus === 'idle') {
        autoSave();
      }
    }, 2000);

    return () => clearTimeout(timer);
  }, [profile]);

  const autoSave = async () => {
    setSaveStatus('saving');
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));
      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (error) {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    }
  };

  const handleProfileChange = (field: string, value: any) => {
    setProfile(prev => ({ ...prev, [field]: value }));
  };

  const handleGoalToggle = (goal: string) => {
    setProfile(prev => ({
      ...prev,
      fitnessGoals: prev.fitnessGoals.includes(goal)
        ? prev.fitnessGoals.filter(g => g !== goal)
        : [...prev.fitnessGoals, goal]
    }));
  };

  const handleAddInjury = () => {
    if (!newInjury.description || !newInjury.bodyPart || !newInjury.severity) {
      return;
    }

    const injury = {
      id: Date.now(),
      ...newInjury,
      date: newInjury.date || new Date().toISOString().split('T')[0],
      isActive: true
    };

    setInjuries(prev => [...prev, injury]);
    setNewInjury({ description: '', bodyPart: '', severity: '', date: '', notes: '' });
    setShowAddInjury(false);
  };

  const toggleInjuryStatus = (id: number) => {
    setInjuries(prev => prev.map(injury => 
      injury.id === id ? { ...injury, isActive: !injury.isActive } : injury
    ));
  };

  const deleteInjury = (id: number) => {
    setInjuries(prev => prev.filter(injury => injury.id !== id));
  };

  const testHeavyConnection = async () => {
    try {
      // Simulate API test
      await new Promise(resolve => setTimeout(resolve, 1500));
      setProfile(prev => ({ ...prev, heavyConnected: true }));
    } catch (error) {
      setProfile(prev => ({ ...prev, heavyConnected: false }));
    }
  };

  // Convert height for display
  const heightInCm = Math.round((parseInt(profile.heightFeet) * 12 + parseInt(profile.heightInches || '0')) * 2.54);
  const weightInKg = Math.round(parseInt(profile.weight) * 0.453592);

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground mb-2 flex items-center gap-3">
            <User className="h-8 w-8 text-[--fitness-primary]" />
            Profile Settings
          </h1>
          <p className="text-muted-foreground">
            Manage your personal information and preferences
          </p>
          
          {/* Save Status */}
          {saveStatus !== 'idle' && (
            <Alert className={`mt-4 ${saveStatus === 'success' ? 'border-green-200 bg-green-50' : 
                                     saveStatus === 'error' ? 'border-red-200 bg-red-50' : 
                                     'border-blue-200 bg-blue-50'}`}>
              <CheckCircle className={`h-4 w-4 ${saveStatus === 'success' ? 'text-green-600' : 
                                                  saveStatus === 'error' ? 'text-red-600' : 
                                                  'text-blue-600'}`} />
              <AlertDescription className={saveStatus === 'success' ? 'text-green-700' : 
                                         saveStatus === 'error' ? 'text-red-700' : 
                                         'text-blue-700'}>
                {saveStatus === 'saving' && 'Auto-saving changes...'}
                {saveStatus === 'success' && 'Changes saved successfully!'}
                {saveStatus === 'error' && 'Failed to save changes. Please try again.'}
              </AlertDescription>
            </Alert>
          )}
        </div>

        <div className="space-y-8">
          
          {/* Personal Information */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Personal Information
              </CardTitle>
              <CardDescription>
                Basic account details (read-only)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Username</Label>
                  <Input value={profile.username} disabled />
                </div>
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input value={profile.email} disabled />
                </div>
                <div className="space-y-2">
                  <Label>Age</Label>
                  <Input value={profile.age} disabled />
                </div>
                <div className="space-y-2">
                  <Label>Sex</Label>
                  <Input value={profile.sex.charAt(0).toUpperCase() + profile.sex.slice(1)} disabled />
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
                Update your physical measurements
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <Label>Height</Label>
                  <div className="flex gap-2">
                    <Select 
                      value={profile.heightFeet} 
                      onValueChange={(value) => handleProfileChange('heightFeet', value)}
                    >
                      <SelectTrigger className="w-20">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {[4, 5, 6, 7].map(ft => (
                          <SelectItem key={ft} value={ft.toString()}>{ft}'</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Select 
                      value={profile.heightInches} 
                      onValueChange={(value) => handleProfileChange('heightInches', value)}
                    >
                      <SelectTrigger className="w-20">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Array.from({length: 12}, (_, i) => (
                          <SelectItem key={i} value={i.toString()}>{i}"</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <span className="text-sm text-muted-foreground self-center">({heightInCm} cm)</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="weight">Weight (lbs)</Label>
                  <Input
                    id="weight"
                    type="number"
                    value={profile.weight}
                    onChange={(e) => handleProfileChange('weight', e.target.value)}
                    placeholder="175"
                  />
                  <p className="text-sm text-muted-foreground">≈ {weightInKg} kg</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Fitness Information */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="h-5 w-5" />
                Fitness Information
              </CardTitle>
              <CardDescription>
                Update your fitness profile and goals
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label>Experience Level</Label>
                  <Select 
                    value={profile.experienceLevel} 
                    onValueChange={(value) => handleProfileChange('experienceLevel', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="beginner">Beginner (0-6 months)</SelectItem>
                      <SelectItem value="intermediate">Intermediate (6 months - 2 years)</SelectItem>
                      <SelectItem value="advanced">Advanced (2+ years)</SelectItem>
                      <SelectItem value="expert">Expert (5+ years)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Preferred Units</Label>
                  <Select 
                    value={profile.preferredUnits} 
                    onValueChange={(value) => handleProfileChange('preferredUnits', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="imperial">Imperial (lbs, ft/in)</SelectItem>
                      <SelectItem value="metric">Metric (kg, cm)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-3">
                <Label>Fitness Goals</Label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {fitnessGoalOptions.map(goal => (
                    <div key={goal} className="flex items-center space-x-2">
                      <Checkbox
                        id={goal}
                        checked={profile.fitnessGoals.includes(goal)}
                        onCheckedChange={() => handleGoalToggle(goal)}
                      />
                      <Label htmlFor={goal} className="text-sm cursor-pointer">{goal}</Label>
                    </div>
                  ))}
                </div>
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
                <Label>Days per week: {profile.daysPerWeek[0]} days</Label>
                <Slider
                  value={profile.daysPerWeek}
                  onValueChange={(value) => handleProfileChange('daysPerWeek', value)}
                  max={7}
                  min={1}
                  step={1}
                  className="w-full"
                />
              </div>

              <div className="space-y-3">
                <Label>Workout duration: {profile.workoutDuration[0]} minutes</Label>
                <Slider
                  value={profile.workoutDuration}
                  onValueChange={(value) => handleProfileChange('workoutDuration', value)}
                  max={120}
                  min={15}
                  step={15}
                  className="w-full"
                />
              </div>
            </CardContent>
          </Card>

          {/* Hevy API Integration */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Smartphone className="h-5 w-5" />
                Hevy API Integration
              </CardTitle>
              <CardDescription>
                Connect your Hevy account for workout tracking integration
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${profile.heavyConnected ? 'bg-green-500' : 'bg-gray-400'}`}></div>
                  <div>
                    <p className="font-medium">
                      {profile.heavyConnected ? 'Connected' : 'Not Connected'}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Hevy API Status
                    </p>
                  </div>
                </div>
                {profile.heavyConnected && (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="heavyApiKey">API Key</Label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Input
                      id="heavyApiKey"
                      type={showApiKey ? 'text' : 'password'}
                      value={profile.heavyApiKey}
                      onChange={(e) => handleProfileChange('heavyApiKey', e.target.value)}
                      placeholder="Enter your Hevy API key"
                    />
                    <button
                      type="button"
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  <Button onClick={testHeavyConnection} variant="outline">
                    Test Connection
                  </Button>
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
                Track current injuries and physical limitations
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              
              {/* Current Injuries */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium">Current Injuries</h4>
                  <Button 
                    onClick={() => setShowAddInjury(true)}
                    size="sm"
                    className="bg-[--fitness-primary] hover:bg-blue-700"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Injury
                  </Button>
                </div>

                {injuries.length === 0 ? (
                  <p className="text-muted-foreground text-center py-4">
                    No injuries recorded. Stay safe and injury-free! 🎉
                  </p>
                ) : (
                  <div className="space-y-3">
                    {injuries.map(injury => (
                      <div 
                        key={injury.id} 
                        className={`p-4 border rounded-lg ${injury.isActive ? 'bg-amber-50 border-amber-200' : 'bg-gray-50 border-gray-200'}`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <Badge 
                                variant={injury.isActive ? 'default' : 'secondary'}
                                className={injury.isActive ? 'bg-amber-500' : ''}
                              >
                                {injury.bodyPart}
                              </Badge>
                              <Badge variant="outline" className="text-xs">
                                {injury.severity.split(' - ')[0]}
                              </Badge>
                              <span className="text-xs text-muted-foreground">{injury.date}</span>
                            </div>
                            <p className="text-sm mb-1">{injury.description}</p>
                            {injury.notes && (
                              <p className="text-xs text-muted-foreground">Notes: {injury.notes}</p>
                            )}
                          </div>
                          <div className="flex items-center gap-2 ml-4">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => toggleInjuryStatus(injury.id)}
                              className="text-xs"
                            >
                              {injury.isActive ? 'Mark Healed' : 'Mark Active'}
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => deleteInjury(injury.id)}
                              className="text-xs text-destructive hover:text-destructive"
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Add New Injury Form */}
              {showAddInjury && (
                <div className="p-4 border-2 border-dashed border-[--fitness-primary] rounded-lg space-y-4">
                  <h4 className="font-medium">Add New Injury</h4>
                  
                  <div className="space-y-3">
                    <div className="space-y-2">
                      <Label htmlFor="newInjuryDescription">Description *</Label>
                      <Textarea
                        id="newInjuryDescription"
                        value={newInjury.description}
                        onChange={(e) => setNewInjury(prev => ({...prev, description: e.target.value}))}
                        placeholder="Describe your injury or limitation..."
                        rows={2}
                      />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="space-y-2">
                        <Label>Affected Body Part *</Label>
                        <Select 
                          value={newInjury.bodyPart} 
                          onValueChange={(value) => setNewInjury(prev => ({...prev, bodyPart: value}))}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select body part" />
                          </SelectTrigger>
                          <SelectContent>
                            {bodyParts.map(part => (
                              <SelectItem key={part} value={part}>{part}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label>Severity Level *</Label>
                        <Select 
                          value={newInjury.severity} 
                          onValueChange={(value) => setNewInjury(prev => ({...prev, severity: value}))}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select severity" />
                          </SelectTrigger>
                          <SelectContent>
                            {severityLevels.map(level => (
                              <SelectItem key={level} value={level}>{level}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="space-y-2">
                        <Label htmlFor="newInjuryDate">Date Occurred</Label>
                        <Input
                          id="newInjuryDate"
                          type="date"
                          value={newInjury.date}
                          onChange={(e) => setNewInjury(prev => ({...prev, date: e.target.value}))}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="newInjuryNotes">Additional Notes</Label>
                        <Input
                          id="newInjuryNotes"
                          value={newInjury.notes}
                          onChange={(e) => setNewInjury(prev => ({...prev, notes: e.target.value}))}
                          placeholder="Optional notes..."
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button 
                      onClick={handleAddInjury}
                      disabled={!newInjury.description || !newInjury.bodyPart || !newInjury.severity}
                      className="bg-[--fitness-primary] hover:bg-blue-700"
                    >
                      <Save className="h-4 w-4 mr-2" />
                      Save Injury
                    </Button>
                    <Button 
                      variant="outline" 
                      onClick={() => setShowAddInjury(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}