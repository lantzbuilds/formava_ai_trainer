def create_workout_views(db):
    """Create all necessary views for workout queries."""

    # View for finding workouts by date range
    date_range_view = {
        "map": """
        function(doc) {
            if (doc.type === 'workout' && doc.start_time) {
                emit(doc.start_time, {
                    id: doc._id,
                    title: doc.title,
                    description: doc.description,
                    start_time: doc.start_time,
                    end_time: doc.end_time,
                    exercise_count: doc.exercise_count || (doc.exercises ? doc.exercises.length : 0)
                });
            }
        }
        """,
    }

    # View for finding workouts by exercise
    exercise_view = {
        "map": """
        function(doc) {
            if (doc.type === 'workout' && doc.exercises) {
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
    }

    # View for workout statistics (latest version)
    stats_view = {
        "map": """
        function(doc) {
            if (doc.type === 'workout' && doc.user_id && doc.start_time && doc.exercises) {
                var totalSets = 0;
                var totalExercises = doc.exercises.length;
                var totalWeight = 0;
                var totalReps = 0;
                var lastWorkoutDate = doc.start_time;
                doc.exercises.forEach(function(exercise) {
                    exercise.sets.forEach(function(set) {
                        totalSets++;
                        if (set.weight_kg) totalWeight += set.weight_kg;
                        if (set.reps) totalReps += set.reps;
                    });
                });
                emit([doc.user_id, doc.start_time], {
                    workout_id: doc._id,
                    title: doc.title,
                    total_exercises: totalExercises,
                    total_sets: totalSets,
                    total_weight: totalWeight,
                    total_reps: totalReps,
                    duration: (new Date(doc.end_time) - new Date(doc.start_time)) / 1000 / 60,
                    count: 1,
                    last_workout_date: lastWorkoutDate
                });
            }
        }
        """,
        "reduce": """
       function(keys, values, rereduce) {
            var result = {
                total_workouts: 0,
                total_exercises: 0,
                total_sets: 0,
                total_weight: 0,
                total_reps: 0,
                total_duration: 0,
                last_workout_date: null
            };
            values.forEach(function(value) {
                result.total_workouts += value.count || value.total_workouts || 1;
                result.total_exercises += value.total_exercises || 0;
                result.total_sets += value.total_sets || 0;
                result.total_weight += value.total_weight || 0;
                result.total_reps += value.total_reps || 0;
                result.total_duration += value.duration || value.total_duration || 0;
                var date = value.last_workout_date;
                if (!result.last_workout_date || (date && date > result.last_workout_date)) {
                    result.last_workout_date = date;
                }
            });
            return result;
        }
        """,
    }

    # View for finding workouts by Hevy ID
    hevy_id_view = {
        "map": """
        function(doc) {
            if (doc.type === 'workout' && doc.hevy_id) {
                emit(doc.hevy_id, doc);
            }
        }
        """,
    }

    # View for finding workouts by user ID
    user_view = {
        "map": """
        function(doc) {
            if (doc.type === 'workout' && doc.user_id && doc.start_time) {
                emit([doc.user_id, doc.start_time], doc);
            }
        }
        """,
    }

    # Create the design document with all views
    design_doc = {
        "_id": "_design/workouts",
        "views": {
            "by_date": date_range_view,
            "by_exercise": exercise_view,
            "stats": stats_view,
            "by_hevy_id": hevy_id_view,
            "by_user": user_view,
        },
    }

    try:
        db.save(design_doc)
        return True
    except Exception as e:
        print(f"Error creating workout views: {e}")
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
        print(f"Error creating user views: {e}")
        return False


def create_exercise_views(db):
    """Create all necessary views for exercise queries."""
    by_hevy_id_view = {
        "map": """
        function(doc) {
            if (doc.type === 'exercise' && doc.hevy_id) {
                emit(doc.hevy_id, {id: doc._id, title: doc.title, muscle_groups: doc.muscle_groups, equipment: doc.equipment});
            }
        }
        """,
    }
    by_muscle_group_view = {
        "map": """
        function(doc) {
            if (doc.type === 'exercise' && doc.muscle_groups) {
                doc.muscle_groups.forEach(function(mg) {
                    emit(mg.name, {id: doc._id, title: doc.title, is_primary: mg.is_primary, equipment: doc.equipment});
                });
            }
        }
        """,
    }
    all_view = {
        "map": """
        function(doc) {
            if (doc.type === 'exercise') {
                emit(doc._id, {id: doc._id, title: doc.title, muscle_groups: doc.muscle_groups, equipment: doc.equipment});
            }
        }
        """,
    }
    design_doc = {
        "_id": "_design/exercises",
        "views": {
            "by_hevy_id": by_hevy_id_view,
            "by_muscle_group": by_muscle_group_view,
            "all": all_view,
        },
    }
    try:
        db.save(design_doc)
        return True
    except Exception as e:
        print(f"Error creating exercise views: {e}")
        return False
