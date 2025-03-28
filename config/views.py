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
