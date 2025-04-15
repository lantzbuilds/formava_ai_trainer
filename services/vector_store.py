"""
Vector store service for the AI Personal Trainer application.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

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
        """Lazy load the embeddings model."""
        if self._embeddings is None:
            self._embeddings = OpenAIEmbeddings()
        return self._embeddings

    @property
    def vectorstore(self):
        """Lazy load the vector store."""
        if self._vectorstore is None:
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

            for exercise in exercises:
                # Create document content
                content = (
                    f"{exercise.get('name', '')} - {exercise.get('description', '')}"
                )

                # Convert muscle groups to comma-separated string
                muscle_groups = exercise.get("muscle_groups", [])
                muscle_groups_str = ", ".join(
                    [
                        f"{mg['name']}({'primary' if mg.get('is_primary') else 'secondary'})"
                        for mg in muscle_groups
                    ]
                )

                # Convert equipment to comma-separated string
                equipment = exercise.get("equipment", [])
                equipment_str = ", ".join([eq.get("name", "") for eq in equipment])

                # Get exercise ID and use it as the exercise template ID
                exercise_id = exercise.get("id", str(uuid.uuid4()))

                # Create metadata with simple types
                metadata = {
                    "id": exercise_id,
                    "name": exercise.get("name", ""),
                    "title": exercise.get(
                        "name", ""
                    ),  # Keep both for backward compatibility
                    "description": exercise.get("description", ""),
                    "muscle_groups": muscle_groups_str,
                    "equipment": equipment_str,
                    "difficulty": exercise.get("difficulty", "beginner"),
                    "exercise_template_id": exercise_id,  # Use the exercise ID as the template ID
                }

                documents.append(content)
                metadatas.append(metadata)
                ids.append(exercise_id)

            # Add to vector store
            self.vectorstore.add_texts(texts=documents, metadatas=metadatas, ids=ids)

            logger.info(f"Added {len(exercises)} exercises to vector store")
        except Exception as e:
            logger.error(f"Error adding exercises to vector store: {str(e)}")

    def search_exercises(
        self, query: str, filter_criteria: Optional[Dict] = None, k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for exercises based on query and filter criteria.

        Args:
            query: Search query
            filter_criteria: Optional filter criteria
            k: Number of results to return

        Returns:
            List of exercise dictionaries
        """
        try:
            # Perform similarity search
            results = self.vectorstore.similarity_search_with_score(
                query, k=k, filter=filter_criteria
            )

            # Process results
            exercises = []
            for doc, score in results:
                # Parse muscle groups string back into list of dictionaries
                muscle_groups = []
                if doc.metadata["muscle_groups"]:
                    for mg_str in doc.metadata["muscle_groups"].split(", "):
                        if "(" in mg_str:
                            name, role = mg_str.split("(")
                            role = role.rstrip(")")
                            muscle_groups.append(
                                {"name": name, "is_primary": role == "primary"}
                            )
                        else:
                            muscle_groups.append({"name": mg_str, "is_primary": False})

                # Parse equipment string back into list of dictionaries
                equipment = []
                if doc.metadata["equipment"]:
                    equipment = [
                        {"name": name}
                        for name in doc.metadata["equipment"].split(", ")
                        if name
                    ]

                exercise = {
                    "id": doc.metadata.get("id", ""),
                    "name": doc.metadata.get("title", ""),
                    "muscle_groups": muscle_groups,
                    "equipment": equipment,
                    "difficulty": doc.metadata.get("difficulty", "beginner"),
                    "is_custom": doc.metadata.get("is_custom", False),
                    "exercise_template_id": doc.metadata.get(
                        "exercise_template_id", ""
                    ),
                    "similarity_score": score,
                }
                exercises.append(exercise)

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
