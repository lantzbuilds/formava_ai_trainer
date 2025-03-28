def create_workout_views(db):
    """Create all necessary views for workout queries."""

    # View for finding workouts by date range
    date_range_view = {
        "map": """
        function(doc) {
            if (doc.start_time) {
                emit(doc.start_time, {
                    id: doc._id,
                    title: doc.title,
                    description: doc.description,
                    start_time: doc.start_time,
                    end_time: doc.end_time,
                    exercise_count: doc.exercises.length
                });
            }
        }
        """,
        "reduce": "_stats",
    }

    # View for finding workouts by exercise
    exercise_view = {
        "map": """
        function(doc) {
            if (doc.exercises) {
                doc.exercises.forEach(function(exercise) {
                    emit([exercise.exercise_template_id, doc.start_time], {
                        workout_id: doc._id,
                        workout_title: doc.title,
                        exercise_title: exercise.title,
                        sets: exercise.sets,
                        start_time: doc.start_time
                    });
                });
            }
        }
        """,
        "reduce": "_stats",
    }

    # View for workout statistics
    stats_view = {
        "map": """
        function(doc) {
            if (doc.exercises) {
                var totalSets = 0;
                var totalExercises = doc.exercises.length;
                var totalWeight = 0;
                var totalReps = 0;
                
                doc.exercises.forEach(function(exercise) {
                    exercise.sets.forEach(function(set) {
                        totalSets++;
                        if (set.weight_kg) totalWeight += set.weight_kg;
                        if (set.reps) totalReps += set.reps;
                    });
                });

                emit(doc.start_time, {
                    workout_id: doc._id,
                    title: doc.title,
                    total_exercises: totalExercises,
                    total_sets: totalSets,
                    total_weight: totalWeight,
                    total_reps: totalReps,
                    duration: (new Date(doc.end_time) - new Date(doc.start_time)) / 1000 / 60 // in minutes
                });
            }
        }
        """,
        "reduce": "_stats",
    }

    # Create the design document with all views
    design_doc = {
        "_id": "_design/workouts",
        "views": {
            "by_date": date_range_view,
            "by_exercise": exercise_view,
            "stats": stats_view,
        },
    }

    try:
        db.save(design_doc)
        return True
    except Exception as e:
        print(f"Error creating views: {e}")
        return False


def create_user_views(db):
    """Create all necessary views for user profile queries."""

    # View for finding users by username
    username_view = {
        "map": """
        function(doc) {
            if (doc.username) {
                emit(doc.username, {
                    id: doc._id,
                    email: doc.email,
                    created_at: doc.created_at,
                    updated_at: doc.updated_at,
                    has_hevy_key: !!doc.hevy_api_key
                });
            }
        }
        """,
        "reduce": "_stats",
    }

    # View for finding users by fitness goals
    fitness_goals_view = {
        "map": """
        function(doc) {
            if (doc.fitness_goals) {
                doc.fitness_goals.forEach(function(goal) {
                    emit([goal, doc.created_at], {
                        user_id: doc._id,
                        username: doc.username,
                        fitness_goals: doc.fitness_goals,
                        experience_level: doc.experience_level
                    });
                });
            }
        }
        """,
        "reduce": "_stats",
    }

    # View for finding users by injuries
    injuries_view = {
        "map": """
        function(doc) {
            if (doc.injuries) {
                doc.injuries.forEach(function(injury) {
                    if (injury.is_active) {
                        emit([injury.body_part, injury.severity], {
                            user_id: doc._id,
                            username: doc.username,
                            injury_description: injury.description,
                            date_injured: injury.date_injured,
                            notes: injury.notes
                        });
                    }
                });
            }
        }
        """,
        "reduce": "_stats",
    }

    # Create the design document with all views
    design_doc = {
        "_id": "_design/users",
        "views": {
            "by_username": username_view,
            "by_fitness_goals": fitness_goals_view,
            "by_injuries": injuries_view,
        },
    }

    try:
        db.save(design_doc)
        return True
    except Exception as e:
        print(f"Error creating views: {e}")
        return False
