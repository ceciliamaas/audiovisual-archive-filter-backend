"""
Base class for pipeline steps.

All pipeline steps inherit from PipelineStep and implement:
- validate_input: Check if prerequisites are met
- execute: Perform the actual work
- validate_output: Verify the step completed successfully
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

from ..state import PipelineState, VideoStatus


class PipelineStep(ABC):
    """Base class for all pipeline steps."""
    
    def __init__(self, state: PipelineState, config: Optional[Dict[str, Any]] = None):
        """Initialize pipeline step.
        
        Args:
            state: Current pipeline state for the video
            config: Optional configuration dictionary
        """
        self.state = state
        self.config = config or {}
        self.video_name = state.video_name
    
    @property
    @abstractmethod
    def step_name(self) -> str:
        """Name of this step (e.g., 'download', 'extract_frames')."""
        pass
    
    @property
    @abstractmethod
    def step_status_in_progress(self) -> VideoStatus:
        """Status to set when step is running."""
        pass
    
    @property
    @abstractmethod
    def step_status_completed(self) -> VideoStatus:
        """Status to set when step is complete."""
        pass
    
    @abstractmethod
    def validate_input(self) -> tuple[bool, Optional[str]]:
        """Validate that prerequisites for this step are met.
        
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if step can proceed
            - error_message: None if valid, error description if not
        """
        pass
    
    @abstractmethod
    def execute(self) -> bool:
        """Execute the step.
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_output(self) -> tuple[bool, Optional[str]]:
        """Validate that the step completed successfully.
        
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if output is valid
            - error_message: None if valid, error description if not
        """
        pass
    
    def should_skip(self) -> bool:
        """Check if this step should be skipped (already completed).
        
        Returns:
            True if step is already completed
        """
        return self.state.is_step_completed(self.step_name)
    
    def run(self, force: bool = False) -> bool:
        """Run the complete step with validation.
        
        Args:
            force: If True, run even if already completed
            
        Returns:
            True if successful, False otherwise
        """
        # Check if should skip
        if not force and self.should_skip():
            print(f"  ✓ {self.step_name} already completed, skipping")
            return True
        
        # Validate input
        input_valid, input_error = self.validate_input()
        if not input_valid:
            error_msg = f"Input validation failed: {input_error}"
            print(f"  ✗ {error_msg}")
            self.state.update_status(VideoStatus.FAILED, error_msg)
            self.state.save()
            return False
        
        # Update status to in-progress
        print(f"  → {self.step_name}...")
        self.state.update_status(self.step_status_in_progress)
        self.state.save()
        
        # Execute
        try:
            success = self.execute()
            if not success:
                error_msg = f"{self.step_name} execution failed"
                print(f"  ✗ {error_msg}")
                self.state.update_status(VideoStatus.FAILED, error_msg)
                self.state.save()
                return False
        except Exception as e:
            error_msg = f"{self.step_name} raised exception: {str(e)}"
            print(f"  ✗ {error_msg}")
            self.state.update_status(VideoStatus.FAILED, error_msg)
            self.state.save()
            raise
        
        # Validate output
        output_valid, output_error = self.validate_output()
        if not output_valid:
            error_msg = f"Output validation failed: {output_error}"
            print(f"  ✗ {error_msg}")
            self.state.update_status(VideoStatus.FAILED, error_msg)
            self.state.save()
            return False
        
        # Mark as completed
        self.state.update_status(self.step_status_completed)
        self.state.mark_step_completed(self.step_name)
        self.state.save()
        print(f"  ✓ {self.step_name} complete")
        
        return True
    
    def _path_exists(self, path: Path) -> bool:
        """Helper to check if a path exists.
        
        Args:
            path: Path to check
            
        Returns:
            True if exists
        """
        return path.exists()
    
    def _get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)
