"""
Vector store service for the AI Personal Trainer application.
"""

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExerciseVectorStore:
    """Service for managing exercise embeddings and similarity search."""

    def __init__(self, persist_directory: str = "data/vectorstore"):
        """
        Initialize the vector store.

        Args:
            persist_directory: Directory to persist the vector store
        """
        self.persist_directory = persist_directory
        self._embeddings = None
        self._vectorstore = None
        logger.info(f"Vector store initialized (lazy loading)")

    @property
    def embeddings(self):
        """Lazy load the embeddings model with caching."""
        if self._embeddings is None:
            # Create a local file store for caching embeddings
            cache_dir = os.path.join(self.persist_directory, "embeddings_cache")
            os.makedirs(cache_dir, exist_ok=True)
            store = LocalFileStore(cache_dir)

            # Create the base embeddings
            base_embeddings = OpenAIEmbeddings()

            # Create cached embeddings
            self._embeddings = CacheBackedEmbeddings.from_bytes_store(
                base_embeddings, store, namespace="exercise_embeddings"
            )
            logger.info("Initialized embeddings with caching")
        return self._embeddings

    @property
    def vectorstore(self):
        """Lazy load the vector store."""
        if self._vectorstore is None:
            # First try to load from persistence
            try:
                self._vectorstore = Chroma(
                    collection_name="exercises",
                    embedding_function=self.embeddings,
                    persist_directory=self.persist_directory,
                )
                # Check if the collection has any documents
                collection = self._vectorstore._collection
                if collection.count() > 0:
                    logger.info(
                        f"Loaded existing vector store with {collection.count()} documents"
                    )
                else:
                    logger.info("No existing vector store found, creating new one")
                    # If no documents, we'll need to add them later
            except Exception as e:
                logger.warning(f"Error loading vector store: {e}")
                logger.info("Creating new vector store")
                self._vectorstore = Chroma(
                    collection_name="exercises",
                    embedding_function=self.embeddings,
                    persist_directory=self.persist_directory,
                )
        return self._vectorstore

    def add_exercises(self, exercises: List[Dict]) -> None:
        """
        Add exercises to the vector store.

        Args:
            exercises (List[Dict]): List of exercise dictionaries
        """
        try:
            # Convert exercises to documents
            documents = []
            metadatas = []
            ids = []

            # Define standard muscle group mappings
            muscle_group_mapping = {
                "upper_back": "back",
                "lower_back": "back",
                "middle_back": "back",
                "lats": "back",
                "traps": "back",
                "chest": "chest",
                "pectorals": "chest",
                "shoulders": "shoulders",
                "deltoids": "shoulders",
                "arms": "arms",
                "biceps": "arms",
                "triceps": "arms",
                "forearms": "arms",
                "legs": "legs",
                "quadriceps": "legs",
                "hamstrings": "legs",
                "calves": "legs",
                "glutes": "legs",
                "core": "core",
                "abs": "core",
                "abdominals": "core",
                "obliques": "core",
                "cardio": "cardio",
            }

            for exercise in exercises:
                # Get title from name if title is not present
                title = exercise.get("title") or exercise.get("name")

                # Skip if exercise is missing required fields
                if not title or not exercise.get("muscle_groups"):
                    logger.warning(
                        f"Skipping exercise due to missing required fields: {exercise}"
                    )
                    continue

                # Get primary and secondary muscle groups
                primary_muscles = set()  # Using set to prevent duplicates
                secondary_muscles = set()  # Using set to prevent duplicates

                for muscle in exercise.get("muscle_groups", []):
                    muscle_name = muscle.get("name", "").lower()
                    mapped_name = muscle_group_mapping.get(muscle_name, muscle_name)

                    if muscle.get("is_primary", False):
                        primary_muscles.add(muscle_name)  # Add specific muscle
                        primary_muscles.add(mapped_name)  # Add mapped category
                    else:
                        secondary_muscles.add(muscle_name)  # Add specific muscle
                        secondary_muscles.add(mapped_name)  # Add mapped category

                # If no primary muscles found, skip the exercise
                if not primary_muscles:
                    logger.warning(
                        f"Skipping exercise with no primary muscles: {exercise}"
                    )
                    continue

                # Convert sets back to lists for metadata
                primary_muscles = list(primary_muscles)
                secondary_muscles = list(secondary_muscles)

                # Get exercise ID
                exercise_id = exercise.get("id", str(uuid.uuid4()))

                # Get equipment
                equipment = []
                for item in exercise.get("equipment", []):
                    if item.get("name") and item.get("name") != "none":
                        equipment.append(item.get("name"))

                # Create document content with all muscle groups
                content = (
                    f"{title} - "
                    f"Primary muscles: {', '.join(primary_muscles)} - "
                    f"Secondary muscles: {', '.join(secondary_muscles)} - "
                    f"Equipment: {', '.join(equipment) if equipment else 'bodyweight'}"
                )

                # Create metadata with muscle groups as comma-separated strings
                metadata = {
                    "id": str(exercise_id),
                    "title": str(title),
                    "primary_muscles": ", ".join(primary_muscles),
                    "secondary_muscles": ", ".join(secondary_muscles),
                    "equipment": str(
                        ", ".join(equipment) if equipment else "bodyweight"
                    ),
                    "exercise_template_id": str(exercise_id),
                    "type": str(exercise.get("type", "weight_reps")),
                    "is_custom": bool(exercise.get("is_custom", False)),
                }

                documents.append(content)
                metadatas.append(metadata)
                ids.append(str(exercise_id))

            # Add to vector store
            self.vectorstore.add_texts(texts=documents, metadatas=metadatas, ids=ids)
            # Persist the vector store to disk
            self.vectorstore.persist()

            logger.info(f"Added {len(exercises)} exercises to vector store")
            if documents and metadatas:
                logger.info("Sample of added exercise:")
                logger.info(f"Content: {documents[0]}")
                logger.info(f"Metadata: {metadatas[0]}")
        except Exception as e:
            logger.error(f"Error adding exercises to vector store: {str(e)}")
            raise  # Re-raise the exception to see the full traceback

    def search_exercises(
        self,
        query: str,
        filter_criteria: Optional[Dict] = None,
        k: int = 5,
    ) -> List[Dict]:
        """
        Search for exercises using similarity search.

        Args:
            query (str): Search query
            filter_criteria (Optional[Dict]): Filter criteria for the search
            k (int): Number of results to return

        Returns:
            List[Dict]: List of exercise dictionaries
        """
        try:
            # Check if this is a general category search
            is_general_category = query.lower() in [
                "arms",
                "legs",
                "back",
                "chest",
                "shoulders",
                "core",
            ]

            # Standardize the query format
            if "Primary muscles:" not in query:
                if is_general_category:
                    # For general categories, only search primary muscles
                    query = f"Primary muscles: {query}"
                else:
                    # For specific muscles, search both primary and secondary
                    query = f"Primary muscles: {query} OR Secondary muscles: {query}"

            # Convert filter criteria to ChromaDB format
            where = {}
            if filter_criteria and "equipment" in filter_criteria:
                where["equipment"] = filter_criteria["equipment"]

            logger.info(f"Searching with query: {query}")
            logger.info(f"Filter criteria: {where}")

            # Perform similarity search
            results = self.vectorstore.similarity_search_with_score(
                query=query,
                k=k,
                filter=where if where else None,
            )

            logger.info(f"Found {len(results)} results")

            # Process results
            exercises = []
            for doc, score in results:
                try:
                    # Parse muscle groups from metadata
                    primary_muscles_str = doc.metadata.get("primary_muscles", "")
                    secondary_muscles_str = doc.metadata.get("secondary_muscles", "")

                    # Split strings into lists
                    primary_muscles = [
                        m.strip() for m in primary_muscles_str.split(",") if m.strip()
                    ]
                    secondary_muscles = [
                        m.strip() for m in secondary_muscles_str.split(",") if m.strip()
                    ]

                    # Create muscle groups list with primary/secondary flags
                    muscle_groups = []
                    for muscle in primary_muscles:
                        muscle_groups.append({"name": muscle, "is_primary": True})
                    for muscle in secondary_muscles:
                        muscle_groups.append({"name": muscle, "is_primary": False})

                    # Parse equipment from metadata
                    equipment_str = doc.metadata.get("equipment", "")
                    equipment = [
                        {"name": name.strip()} for name in equipment_str.split(",")
                    ]

                    exercise = {
                        "id": doc.metadata.get("id"),
                        "title": doc.metadata.get("title"),
                        "description": doc.metadata.get("description"),
                        "muscle_groups": muscle_groups,
                        "equipment": equipment,
                        "similarity_score": score,
                    }
                    exercises.append(exercise)

                    logger.info(f"Found exercise: {exercise['title']} (score: {score})")
                    logger.info(f"Muscle groups: {muscle_groups}")
                    logger.info(f"Equipment: {equipment}")
                except Exception as e:
                    logger.error(f"Error processing result: {str(e)}")
                    logger.error(f"Document metadata: {doc.metadata}")

            return exercises
        except Exception as e:
            logger.error(f"Error searching exercises: {str(e)}")
            return []

    def get_exercises_by_muscle_group(
        self, muscle_group: str, difficulty: Optional[str] = None, k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get exercises targeting a specific muscle group.

        Args:
            muscle_group: Target muscle group
            difficulty: Optional difficulty level
            k: Number of results to return

        Returns:
            List of exercise dictionaries
        """
        # For string metadata, we need to use a different filter approach
        # We'll use the search_exercises method with a specific query
        return self.search_exercises(f"exercises targeting {muscle_group}", k=k)

    def get_exercises_by_equipment(
        self, equipment: str, difficulty: Optional[str] = None, k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get exercises using specific equipment.

        Args:
            equipment: Required equipment
            difficulty: Optional difficulty level
            k: Number of results to return

        Returns:
            List of exercise dictionaries
        """
        # For string metadata, we need to use a different filter approach
        # We'll use the search_exercises method with a specific query
        return self.search_exercises(f"exercises using {equipment}", k=k)

    def get_exercise_by_id(self, exercise_id: str) -> Optional[Dict]:
        """
        Get an exercise by its ID.

        Args:
            exercise_id (str): The ID of the exercise to retrieve

        Returns:
            Optional[Dict]: The exercise data if found, None otherwise
        """
        try:
            results = self.vectorstore.get(
                where={"exercise_template_id": exercise_id},
                include=["metadatas", "documents"],
            )

            if not results or not results["metadatas"]:
                return None

            # Convert to exercise format
            metadata = results["metadatas"][0]
            return {
                "title": metadata.get("title"),
                "description": metadata.get("description", ""),
                "muscle_groups": metadata.get("muscle_groups", []),
                "equipment": metadata.get("equipment", []),
                "difficulty": metadata.get("difficulty", "beginner"),
                "exercise_template_id": exercise_id,
            }
        except Exception as e:
            logger.error(f"Error getting exercise by ID: {str(e)}")
            return None

    def search_exercises_by_title(self, title: str) -> List[Document]:
        """
        Search for exercises by exact title match.

        Args:
            title (str): The exact title to search for

        Returns:
            List[Document]: List of matching documents, or empty list if no match found
        """
        try:
            if not title:
                logger.warning("Empty title provided for search")
                return []

            # Use Chroma's where filter to search by title
            results = self.vectorstore.get(
                where={"title": title}, include=["metadatas", "documents"]
            )

            if not results or not results["metadatas"]:
                return []

            # Convert results to Document objects
            documents = []
            for metadata, doc in zip(results["metadatas"], results["documents"]):
                # Convert string metadata back to lists
                muscle_groups = (
                    metadata["muscle_groups"].split(", ")
                    if metadata["muscle_groups"]
                    else []
                )
                equipment = (
                    metadata["equipment"].split(", ") if metadata["equipment"] else []
                )

                # Create a new metadata dictionary with the correct structure
                new_metadata = {
                    "id": metadata.get("id", ""),
                    "title": metadata.get("title", ""),
                    "description": metadata.get("description", ""),
                    "muscle_groups": muscle_groups,
                    "equipment": equipment,
                    "difficulty": metadata.get("difficulty", "beginner"),
                    "is_custom": metadata.get("is_custom", False),
                    "exercise_template_id": metadata.get("exercise_template_id", ""),
                }

                documents.append(Document(page_content=doc, metadata=new_metadata))

            return documents
        except Exception as e:
            logger.error(f"Error searching exercises by title: {str(e)}")
            return []

    def search_exercises_by_goal(self, goal: str, limit: int = 5) -> List[Document]:
        """
        Search for exercises that match a specific fitness goal.

        Args:
            goal (str): The fitness goal to search for
            limit (int): Maximum number of exercises to return

        Returns:
            List[Document]: List of matching documents
        """
        try:
            # Map goals to relevant muscle groups
            goal_muscle_groups = {
                "strength": ["chest", "back", "legs", "shoulders", "arms"],
                "endurance": ["legs", "core"],
                "flexibility": ["core", "back", "legs"],
                "weight_loss": ["chest", "back", "legs", "shoulders", "arms", "core"],
            }

            # Get muscle groups for the goal
            muscle_groups = goal_muscle_groups.get(goal.lower(), ["all"])

            # Search for exercises
            exercises = []
            for muscle_group in muscle_groups:
                results = self.get_exercises_by_muscle_group(muscle_group, k=limit)
                exercises.extend(results)

            # Remove duplicates and limit results
            seen_names = set()
            unique_exercises = []
            for exercise in exercises:
                name = exercise.get("name")
                if name and name not in seen_names:
                    seen_names.add(name)
                    unique_exercises.append(
                        Document(
                            page_content=exercise.get("description", ""),
                            metadata=exercise,
                        )
                    )

            return unique_exercises[:limit]
        except Exception as e:
            logger.error(f"Error searching exercises by goal: {str(e)}")
            return []
