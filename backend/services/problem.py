import os
import json
from typing import List, Dict, Any, Optional

class ProblemService:
    """
    Handles dynamic discovery and ingestion of assessment challenges 
    from the filesystem.
    """
    def __init__(self, problems_dir: str):
        self.problems_dir = problems_dir

    def list_problems(self) -> List[Dict[str, Any]]:
        """
        Discovers and parses metadata for all available challenges.

        Returns:
            A list of dictionary objects containing problem metadata (title, difficulty, etc).
        """
        problems = []
        if not os.path.exists(self.problems_dir):
            return []
            
        for item in os.listdir(self.problems_dir):
            item_path = os.path.join(self.problems_dir, item)
            if os.path.isdir(item_path):
                metadata_path = os.path.join(item_path, "problem.json")
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            problems.append(json.load(f))
                    except Exception:
                        continue
        return problems

    def get_problem_description(self, project_name: str) -> str:
        """
        Args:
            project_name: Unique identifier of the problem project.

        Returns:
            The raw Markdown text as a string.
        """
        desc_path = os.path.join(self.problems_dir, project_name, "description.md")
        if os.path.exists(desc_path):
            with open(desc_path, 'r') as f:
                return f.read()
        return ""

    def get_problem_metadata(self, project_name: str) -> Dict[str, Any]:
        """
        Args:
            project_name: Unique identifier of the problem project.

        Returns:
            A dictionary of configuration attributes for the challenge.
        """
        metadata_path = os.path.join(self.problems_dir, project_name, "problem.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                return json.load(f)
        return {}

    def get_problem_initial_files(self, project_name: str) -> List[Dict[str, str]]:
        """
        Retrieves the baseline code files for the specified project.

        Args:
            project_name: Unique identifier of the problem project.

        Returns:
            A list of file objects containing the relative path and string content.
        """
        problem_path = os.path.join(self.problems_dir, project_name, "initial")
        if not os.path.exists(problem_path):
            return []
            
        initial_files = []
        for root, _, files in os.walk(problem_path):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, problem_path)
                with open(full_path, 'r') as f:
                    content = f.read()
                
                initial_files.append({
                    "filename": rel_path,
                    "content": content
                })
        return initial_files
