/**
 * TypeScript types for the Formava AI Trainer application
 * These types mirror the Python models in app/models/
 */

export interface User {
  id: string;
  username: string;
  email: string;
}

export interface UserProfile {
  _id: string;
  username: string;
  email: string;
  age?: number;
  sex?: 'male' | 'female' | 'other';
  height_feet?: number;
  height_inches?: number;
  weight_lbs?: number;
  experience?: 'beginner' | 'intermediate' | 'advanced';
  preferred_units?: 'metric' | 'imperial';
  goals?: FitnessGoal[];
  workout_days?: number;
  workout_duration?: number;
  hevy_username?: string;
  hevy_api_key?: string;
  injuries?: Injury[];
  created_at?: string;
  updated_at?: string;
}

export interface FitnessGoal {
  id: string;
  name: string;
  description?: string;
  target_date?: string;
  is_achieved?: boolean;
}

export interface Injury {
  id: string;
  name: string;
  description?: string;
  severity: InjurySeverity;
  affected_body_parts: string[];
  recovery_date?: string;
  is_active: boolean;
}

export type InjurySeverity = 'mild' | 'moderate' | 'severe';

export interface Workout {
  id: string;
  user_id: string;
  title: string;
  date: string;
  duration_minutes?: number;
  exercises: Exercise[];
  notes?: string;
  hevy_workout_id?: string;
}

export interface Exercise {
  id: string;
  name: string;
  category: string;
  muscle_groups: string[];
  equipment?: string;
  instructions?: string[];
  sets: ExerciseSet[];
}

export interface ExerciseSet {
  reps?: number;
  weight?: number;
  duration?: number; // for time-based exercises
  distance?: number; // for cardio exercises
  rest_time?: number;
  notes?: string;
}

export interface DashboardData {
  total_workouts: number;
  avg_workouts_per_week: number;
  last_workout?: Workout;
  current_streak: number;
  goals: FitnessGoal[];
  active_injuries: Injury[];
}

export interface AIRecommendation {
  id: string;
  title: string;
  description: string;
  routine_type: string;
  duration_weeks: number;
  exercises: Exercise[];
  created_at: string;
}

export interface SyncStatus {
  is_syncing: boolean;
  last_sync?: string;
  sync_type?: 'recent' | 'full';
  progress?: number;
  message?: string;
}

export interface ApiError {
  message: string;
  code?: string;
  details?: unknown;
}

// Form types for UI components
export interface LoginForm {
  username: string;
  password: string;
}

export interface RegisterForm {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export interface ProfileForm {
  age?: number;
  sex?: 'male' | 'female' | 'other';
  height_feet?: number;
  height_inches?: number;
  weight_lbs?: number;
  experience?: 'beginner' | 'intermediate' | 'advanced';
  preferred_units?: 'metric' | 'imperial';
  workout_days?: number;
  workout_duration?: number;
  hevy_username?: string;
  hevy_api_key?: string;
}

// Navigation and UI state types
export type Page = 'landing' | 'login' | 'register' | 'dashboard' | 'ai_recs' | 'profile';

export interface AppState {
  currentPage: Page;
  user: User | null;
  isLoading: boolean;
  error: string | null;
}

