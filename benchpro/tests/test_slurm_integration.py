"""
Comprehensive integration tests for SLURM functionality using the mock SLURM system.

This module demonstrates how to test SLURM integration using the new centralized
mock SLURM testing infrastructure.
"""

import os
import time
import pytest
import tempfile

from benchpro.executor.scheduler import SlurmScheduler, SubmissionError, StatusCheckError
from benchpro.executor.components.execution import SlurmExecutionComponent
from benchpro.templates.script_generators import SlurmScriptGenerator
from benchpro.tests.fixtures.mock_slurm import JobState
from benchpro.tests.fixtures.slurm_fixtures import (
    create_minimal_slurm_script,
    assert_slurm_directives_present
)
from benchpro.tests.fixtures.test_data import (
    get_standard_template,
    get_standard_system_data,
    get_standard_application_profile
)


class TestSlurmSchedulerIntegration:
    """Test the SlurmScheduler class with mock SLURM system."""
    
    def test_submit_job_success(self, slurm_patched):
        """Test successful job submission."""
        # Create a test script
        script_content = """#!/bin/bash
#SBATCH -J test_submit_job
#SBATCH -N 1
#SBATCH -t 00:05:00

echo "Test job"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            # Create scheduler and submit job
            scheduler = SlurmScheduler()
            job_id = scheduler.submit_job(script_path)
            
            # Verify job was submitted
            assert job_id.isdigit(), f"Job ID should be numeric, got: {job_id}"
            
            # Verify job exists in mock system
            job = slurm_patched.get_job(job_id)
            assert job is not None, "Job should exist in mock system"
            assert job.job_name == "test_submit_job"
            assert job.nodes == 1
            assert job.time_limit == "00:05:00"
            
        finally:
            os.unlink(script_path)
    
    def test_submit_job_with_context(self, slurm_patched):
        """Test job submission with additional context."""
        script_content = """#!/bin/bash
#SBATCH -J context_test

echo "Context test job"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script_content)
            script_path = f.name
        
        try:
            scheduler = SlurmScheduler()
            context = {
                "sbatch_options": {
                    "partition": "gpu",
                    "account": "special_project"
                }
            }
            
            job_id = scheduler.submit_job(script_path, context)
            
            # Verify submission
            assert job_id.isdigit()
            job = slurm_patched.get_job(job_id)
            assert job is not None
            
        finally:
            os.unlink(script_path)
    
    def test_check_status_running_job(self, slurm_patched):
        """Test checking status of a running job."""
        # Submit a job first
        script_path = create_minimal_slurm_script("status_test", tempfile.gettempdir())
        
        try:
            scheduler = SlurmScheduler()
            job_id = scheduler.submit_job(script_path)
            
            # Wait for job to start running
            slurm_patched.wait_for_job_state(job_id, JobState.RUNNING, timeout=1.0)
            
            # Check status
            status = scheduler.check_status(job_id)
            assert status == "RUNNING"
            
        finally:
            os.unlink(script_path)
    
    def test_check_status_completed_job(self, slurm_patched):
        """Test checking status of a completed job."""
        script_path = create_minimal_slurm_script("completion_test", tempfile.gettempdir())
        
        try:
            scheduler = SlurmScheduler()
            job_id = scheduler.submit_job(script_path)
            
            # Wait for job to complete
            slurm_patched.wait_for_job_state(job_id, JobState.COMPLETED, timeout=2.0)
            
            # Check status
            status = scheduler.check_status(job_id)
            assert status == "COMPLETED"
            
        finally:
            os.unlink(script_path)
    
    def test_cancel_job(self, slurm_patched):
        """Test job cancellation."""
        script_path = create_minimal_slurm_script("cancel_test", tempfile.gettempdir())
        
        try:
            scheduler = SlurmScheduler()
            job_id = scheduler.submit_job(script_path)
            
            # Cancel the job
            result = scheduler.cancel_job(job_id)
            assert result is True
            
            # Verify job was cancelled
            job = slurm_patched.get_job(job_id)
            assert job.state == JobState.CANCELLED
            
        finally:
            os.unlink(script_path)
    
    def test_submit_nonexistent_script(self, slurm_patched):
        """Test handling of non-existent script submission."""
        scheduler = SlurmScheduler()
        
        fake_script = "/nonexistent/path/to/script.sh"
        
        with pytest.raises(SubmissionError) as exc_info:
            scheduler.submit_job(fake_script)
        
        # The mock system returns "Batch script not found" but it gets wrapped
        assert "Batch script not found" in str(exc_info.value) or "Failed to parse job ID" in str(exc_info.value)
    
    def test_status_check_invalid_job(self, slurm_patched):
        """Test status check for invalid job ID."""
        scheduler = SlurmScheduler()
        
        with pytest.raises(StatusCheckError):
            scheduler.check_status("invalid_job_id")


class TestSlurmExecutionComponent:
    """Test the SlurmExecutionComponent with mock SLURM system."""
    
    def test_execute_success(self, slurm_patched):
        """Test successful script execution."""
        script_path = create_minimal_slurm_script("execution_test", tempfile.gettempdir())
        
        try:
            component = SlurmExecutionComponent()
            success, job_id = component.execute(script_path)
            
            assert success is True
            assert job_id is not None
            assert job_id.isdigit()
            
            # Verify job exists
            job = slurm_patched.get_job(job_id)
            assert job is not None
            
        finally:
            os.unlink(script_path)
    
    def test_execute_nonexistent_script(self, slurm_patched):
        """Test execution with nonexistent script."""
        component = SlurmExecutionComponent()
        
        with pytest.raises(Exception):  # Should raise ExecutionError
            component.execute("/nonexistent/script.sh")
    
    def test_get_status(self, slurm_patched):
        """Test getting job status."""
        script_path = create_minimal_slurm_script("status_component_test", tempfile.gettempdir())
        
        try:
            component = SlurmExecutionComponent()
            success, job_id = component.execute(script_path)
            assert success is True
            
            # Wait for job to complete
            slurm_patched.wait_for_job_state(job_id, JobState.COMPLETED, timeout=2.0)
            
            # Check status
            status = component.get_status(job_id)
            assert status == "COMPLETED"
            
        finally:
            os.unlink(script_path)


class TestSlurmScriptGenerator:
    """Test the SlurmScriptGenerator with mock SLURM system."""
    
    def test_generate_script_with_slurm_directives(self, slurm_with_standardized_env):
        """Test script generation includes SLURM directives."""
        # Use a standard template
        template_content = get_standard_template("hello_world.j2")
        template_path = os.path.join(slurm_with_standardized_env["temp_dir"], "test_template.j2")
        
        with open(template_path, "w") as f:
            f.write(template_content)
        
        # Create script generator
        generator = SlurmScriptGenerator()
        
        # Generate script with SLURM job configuration
        variables = {
            "job": {
                "name": "test_generation",
                "nodes": 2,
                "tasks_per_node": 16,
                "time_limit": "02:00:00",
                "queue": "compute",
                "account": "test_account"
            },
            "workspace": {
                "logs_dir": "/test/logs"
            },
            "system": get_standard_system_data(),
            "environment": {
                "variables": {
                    "SYSTEM_TYPE": "test_environment"
                }
            }
        }
        
        script_content = generator.generate_script(template_path, variables)
        
        # Verify SLURM directives are present
        expected_directives = {
            "J": "test_generation",
            "N": "2",
            "ntasks-per-node": "16",
            "t": "02:00:00",
            "p": "compute",
            "A": "test_account"
        }
        
        assert_slurm_directives_present(script_content, expected_directives)
        
        # Verify the script can be submitted
        script_path = os.path.join(slurm_with_standardized_env["temp_dir"], "generated_script.sh")
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        
        try:
            # Submit the generated script
            mock_slurm = slurm_with_standardized_env["mock_slurm"]
            output = mock_slurm.submit_job(script_path)
            job_id = output.split()[-1]
            
            # Verify job was created with correct properties
            job = mock_slurm.get_job(job_id)
            assert job.job_name == "test_generation"
            assert job.nodes == 2
            assert job.tasks_per_node == 16
            assert job.time_limit == "02:00:00"
            
        finally:
            if os.path.exists(script_path):
                os.unlink(script_path)


class TestSlurmErrorHandling:
    """Test error handling scenarios with mock SLURM system."""
    
    def test_network_failure_simulation(self, slurm_patched):
        """Test handling of network failures."""
        from benchpro.tests.fixtures.slurm_fixtures import SlurmTestHelper
        
        helper = SlurmTestHelper(slurm_patched)
        
        # Simulate network failure
        helper.simulate_network_failure()
        
        # Test that commands fail appropriately
        scheduler = SlurmScheduler()
        
        script_path = create_minimal_slurm_script("network_test", tempfile.gettempdir())
        
        try:
            with pytest.raises(SubmissionError) as exc_info:
                scheduler.submit_job(script_path)
            
            assert "Connection timeout" in str(exc_info.value)
            
        finally:
            helper.restore_normal_operation()
            os.unlink(script_path)
    
    def test_job_failure_simulation(self, slurm_patched):
        """Test handling of job failures."""
        from benchpro.tests.fixtures.slurm_fixtures import SlurmTestHelper
        
        helper = SlurmTestHelper(slurm_patched)
        
        # Submit a job
        job_id = helper.submit_test_job()
        
        # Simulate job failure
        helper.simulate_job_failure(job_id)
        
        # Verify job state
        helper.assert_job_reached_state(job_id, JobState.FAILED)
        
        # Test status check
        scheduler = SlurmScheduler()
        status = scheduler.check_status(job_id)
        assert status == "FAILED"


class TestSlurmJobLifecycle:
    """Test complete SLURM job lifecycle scenarios."""
    
    def test_complete_job_lifecycle(self, slurm_patched):
        """Test a complete job from submission to completion."""
        from benchpro.tests.fixtures.slurm_fixtures import SlurmTestHelper
        
        helper = SlurmTestHelper(slurm_patched)
        scheduler = SlurmScheduler()
        
        # Submit job
        job_id = helper.submit_test_job()
        
        # Verify job starts as PENDING
        helper.assert_job_reached_state(job_id, JobState.PENDING)
        
        # Wait for job to start running
        assert helper.mock_system.wait_for_job_state(job_id, JobState.RUNNING, timeout=1.0)
        status = scheduler.check_status(job_id)
        assert status == "RUNNING"
        
        # Wait for job to complete
        assert helper.wait_for_completion(job_id, timeout=2.0)
        status = scheduler.check_status(job_id)
        assert status == "COMPLETED"
        
        # Verify command history
        helper.assert_command_called("sbatch", times=1)
        helper.assert_command_called("squeue")  # At least one status check
    
    def test_job_cancellation_lifecycle(self, slurm_patched):
        """Test job cancellation lifecycle."""
        from benchpro.tests.fixtures.slurm_fixtures import SlurmTestHelper
        
        helper = SlurmTestHelper(slurm_patched)
        scheduler = SlurmScheduler()
        
        # Submit job
        job_id = helper.submit_test_job()
        
        # Wait for job to start
        slurm_patched.wait_for_job_state(job_id, JobState.RUNNING, timeout=1.0)
        
        # Cancel job
        result = scheduler.cancel_job(job_id)
        assert result is True
        
        # Verify cancellation
        helper.assert_job_reached_state(job_id, JobState.CANCELLED)
        
        # Verify command history
        helper.assert_command_called("scancel", times=1)


class TestSlurmIntegrationWithTemplateSystem:
    """Test SLURM integration with the template system."""
    
    def test_end_to_end_script_generation_and_submission(self, slurm_with_standardized_env):
        """Test complete workflow from template to job submission."""
        # Get a standard application profile configured for SLURM
        config = get_standard_application_profile("test_app")
        config["job"]["scheduler"] = "slurm"
        config["job"]["nodes"] = 2
        config["job"]["tasks_per_node"] = 8
        config["job"]["time_limit"] = "01:30:00"
        config["job"]["queue"] = "batch"
        config["job"]["account"] = "test_project"
        
        # Generate script using SlurmScriptGenerator
        generator = SlurmScriptGenerator()
        template_path = os.path.join(
            slurm_with_standardized_env["inputs_app_dir"], 
            "hello_world.j2"
        )
        
        variables = {
            "job": config["job"],
            "workspace": {
                "logs_dir": slurm_with_standardized_env["temp_dir"]
            },
            "build": config["build"],
            "environment": config["environment"],
            "system": get_standard_system_data(),
            "name": config["name"],
            "version": config["version"]
        }
        
        script_content = generator.generate_script(template_path, variables)
        
        # Save script to file
        script_path = os.path.join(slurm_with_standardized_env["temp_dir"], "integration_test.sh")
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        
        try:
            # Submit using SlurmExecutionComponent
            component = SlurmExecutionComponent()
            success, job_id = component.execute(script_path)
            
            assert success is True
            assert job_id is not None
            
            # Verify job properties match configuration
            mock_slurm = slurm_with_standardized_env["mock_slurm"]
            job = mock_slurm.get_job(job_id)
            
            assert job.nodes == 2
            assert job.tasks_per_node == 8
            assert job.time_limit == "01:30:00"
            assert job.partition == "batch"
            assert job.account == "test_project"
            
            # Wait for completion
            mock_slurm.wait_for_job_state(job_id, JobState.COMPLETED, timeout=2.0)
            
            # Verify final status
            status = component.get_status(job_id)
            assert status == "COMPLETED"
            
        finally:
            if os.path.exists(script_path):
                os.unlink(script_path) 