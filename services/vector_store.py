"""
Vector store service for the AI Personal Trainer application.
"""

import logging
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

    def add_exercises(self, exercises: List[Dict[str, Any]]) -> None:
        """
        Add exercises to the vector store.

        Args:
            exercises: List of exercise dictionaries
        """
        try:
            # Process exercises into documents with metadata
            documents = []
            metadatas = []

            for exercise in exercises:
                # Check if exercise already has an embedding
                if exercise.get("embedding"):
                    # Use the existing embedding
                    embedding = exercise["embedding"]
                    logger.info(
                        f"Using existing embedding for exercise: {exercise.get('name', 'Unknown')}"
                    )
                else:
                    # Generate a new embedding
                    logger.info(
                        f"Generating new embedding for exercise: {exercise.get('name', 'Unknown')}"
                    )
                    # Create a rich text representation
                    doc = f"""
                    Exercise: {exercise['name']}
                    Description: {exercise.get('description', '')}
                    Instructions: {exercise.get('instructions', '')}
                    Primary Muscles: {', '.join([m['name'] for m in exercise['muscle_groups'] if m['is_primary']])}
                    Secondary Muscles: {', '.join([m['name'] for m in exercise['muscle_groups'] if not m['is_primary']])}
                    Equipment: {', '.join([e['name'] for e in exercise['equipment']])}
                    Difficulty: {exercise.get('difficulty', '')}
                    """

                    # Generate embedding
                    embedding = self.embeddings.embed_query(doc)
                    logger.info(
                        f"Generated embedding for exercise: {exercise.get('name', 'Unknown')}"
                    )

                    # Update the exercise with the embedding
                    exercise["embedding"] = embedding
                    logger.info(
                        f"Added embedding to exercise: {exercise.get('name', 'Unknown')}"
                    )

                # Create metadata - convert lists to strings
                metadata = {
                    "id": exercise["id"],
                    "name": exercise["name"],
                    "muscle_groups": ", ".join(
                        [m["name"] for m in exercise["muscle_groups"]]
                    ),
                    "equipment": ", ".join([e["name"] for e in exercise["equipment"]]),
                    "difficulty": exercise.get("difficulty", ""),
                    "is_custom": exercise.get("is_custom", False),
                }

                # Create document with embedding
                doc = Document(
                    page_content=f"Exercise: {exercise['name']}",
                    metadata=metadata,
                    embedding=embedding,
                )

                documents.append(doc)

            # Add to vector store
            self.vectorstore.add_documents(documents)
            self.vectorstore.persist()
            logger.info(f"Added {len(exercises)} exercises to vector store")

        except Exception as e:
            logger.error(f"Error adding exercises to vector store: {str(e)}")
            raise

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
                # Convert string metadata back to lists
                muscle_groups = (
                    doc.metadata["muscle_groups"].split(", ")
                    if doc.metadata["muscle_groups"]
                    else []
                )
                equipment = (
                    doc.metadata["equipment"].split(", ")
                    if doc.metadata["equipment"]
                    else []
                )

                exercise = {
                    "id": doc.metadata["id"],
                    "name": doc.metadata["name"],
                    "muscle_groups": muscle_groups,
                    "equipment": equipment,
                    "difficulty": doc.metadata["difficulty"],
                    "is_custom": doc.metadata["is_custom"],
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
