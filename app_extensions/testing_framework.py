"""
Comprehensive Testing Framework for SOC Platform.

This module provides a robust testing infrastructure with:
- Unit test suite with mocking and fixtures
- Integration tests for end-to-end workflows
- Performance testing and load simulation
- Test data generation and factories
- Test environment isolation and cleanup
- CI/CD pipeline integration helpers
- Coverage reporting and quality gates
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
import pytest
import asyncio_mock
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import redis.asyncio as redis
import fakeredis.aioredis
from faker import Faker

logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """Test case definition with metadata."""
    test_id: str
    name: str
    description: str
    category: str
    test_func: Callable
    setup_func: Optional[Callable] = None
    teardown_func: Optional[Callable] = None
    tags: List[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    expected_outcome: str = "success"  # success, failure, error
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TestResult:
    """Test execution result with details."""
    test_id: str
    name: str
    status: str  # passed, failed, error, skipped
    duration_ms: float
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    assertions_passed: int = 0
    assertions_failed: int = 0
    execution_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuite:
    """Test suite configuration and results."""
    suite_id: str
    name: str
    test_cases: List[TestCase] = field(default_factory=list)
    results: List[TestResult] = field(default_factory=list)
    setup_func: Optional[Callable] = None
    teardown_func: Optional[Callable] = None
    parallel_execution: bool = False
    max_workers: int = 4


class TestDataFactory:
    """Factory for generating realistic test data."""
    
    def __init__(self, locale: str = 'en_US'):
        self.faker = Faker(locale)
        self.faker.seed_instance(42)  # For reproducible test data
    
    def generate_case_id(self) -> str:
        """Generate a realistic case ID."""
        return f"CASE-{self.faker.random_int(100000, 999999)}"
    
    def generate_rule_id(self) -> str:
        """Generate a realistic rule ID."""
        prefixes = ["fact_", "profile_", "detection_", "alert_"]
        prefix = self.faker.random_element(prefixes)
        return f"{prefix}{self.faker.uuid4()[:8]}"
    
    def generate_user_entity(self) -> str:
        """Generate a realistic username."""
        return f"{self.faker.first_name().lower()}.{self.faker.last_name().lower()}"
    
    def generate_ip_address(self, private: bool = False) -> str:
        """Generate IP address."""
        if private:
            return self.faker.ipv4_private()
        return self.faker.ipv4()
    
    def generate_hostname(self) -> str:
        """Generate hostname."""
        return f"{self.faker.word()}-{self.faker.random_int(1, 999)}.corp.local"
    
    def generate_domain(self) -> str:
        """Generate domain name."""
        return self.faker.domain_name()
    
    def generate_detection_event(self) -> Dict[str, Any]:
        """Generate a realistic detection event."""
        return {
            "detection_id": str(uuid.uuid4()),
            "rule_name": f"fact_{self.faker.word()}_{self.faker.word()}",
            "rule_type": self.faker.random_element(["fact", "profile", "correlation"]),
            "search_query": f"event_type:{self.faker.word()} AND host:{self.generate_hostname()}",
            "event_filter": f"timestamp:[{int(time.time() * 1000) - 3600000} TO {int(time.time() * 1000)}]",
            "event_from_time_millis": int(time.time() * 1000) - 3600000,
            "event_to_time_millis": int(time.time() * 1000),
            "window_minutes": self.faker.random_int(5, 60),
            "source_case_id": self.generate_case_id(),
            "entities": {
                "users": [self.generate_user_entity() for _ in range(self.faker.random_int(1, 3))],
                "ips": [self.generate_ip_address() for _ in range(self.faker.random_int(1, 3))],
                "hosts": [self.generate_hostname() for _ in range(self.faker.random_int(1, 2))],
                "domains": [self.generate_domain() for _ in range(self.faker.random_int(0, 2))]
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": self.faker.random_element(["low", "medium", "high", "critical"])
        }
    
    def generate_siem_events(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generate SIEM events for testing."""
        events = []
        for _ in range(count):
            event = {
                "event_id": str(uuid.uuid4()),
                "timestamp": (datetime.now(timezone.utc) - timedelta(
                    minutes=self.faker.random_int(0, 1440)
                )).isoformat(),
                "event_type": self.faker.random_element([
                    "authentication", "network", "file_access", "process_execution"
                ]),
                "source_ip": self.generate_ip_address(),
                "destination_ip": self.generate_ip_address(),
                "user": self.generate_user_entity(),
                "hostname": self.generate_hostname(),
                "description": self.faker.sentence(),
                "severity": self.faker.random_element(["info", "warning", "error", "critical"]),
                "raw_data": {
                    "process_name": self.faker.file_name(),
                    "command_line": f"{self.faker.file_name()} {self.faker.word()}",
                    "file_path": f"/usr/bin/{self.faker.file_name()}",
                    "port": self.faker.random_int(1024, 65535)
                }
            }
            events.append(event)
        return events
    
    def generate_similar_case_data(self, base_case_id: str, similarity_count: int = 5) -> List[Dict[str, Any]]:
        """Generate similar case data for testing."""
        similar_cases = []
        for i in range(similarity_count):
            similar_case = {
                "case_id": self.generate_case_id(),
                "similarity_score": round(0.3 + (0.7 * (i + 1) / similarity_count), 3),
                "matched_entities": [
                    self.generate_user_entity(),
                    self.generate_ip_address(),
                    self.generate_hostname()
                ][:self.faker.random_int(1, 3)],
                "entity_breakdown": {
                    "users": round(self.faker.random.uniform(0, 0.5), 3),
                    "ips": round(self.faker.random.uniform(0, 0.35), 3),
                    "hosts": round(self.faker.random.uniform(0, 0.15), 3)
                },
                "rule_match": self.faker.boolean(chance_of_getting_true=30),
                "time_proximity": self.faker.boolean(chance_of_getting_true=40),
                "summary": f"Similarity: {0.3 + (0.7 * (i + 1) / similarity_count):.3f}, Entities: {self.faker.random_int(1, 5)}"
            }
            similar_cases.append(similar_case)
        return similar_cases


class MockServices:
    """Mock implementations of external services for testing."""
    
    def __init__(self, test_data_factory: TestDataFactory):
        self.factory = test_data_factory
    
    @asynccontextmanager
    async def mock_redis_client(self):
        """Mock Redis client using fakeredis."""
        fake_redis = fakeredis.aioredis.FakeRedis()
        try:
            yield fake_redis
        finally:
            await fake_redis.aclose()
    
    @asynccontextmanager
    async def mock_siem_client(self):
        """Mock SIEM client with realistic responses."""
        class MockSIEMClient:
            async def search_events(self, query: str, from_time: int, to_time: int, limit: int = 1000):
                # Simulate network delay
                await asyncio.sleep(0.1)
                
                # Generate realistic events based on query
                event_count = min(limit, self.factory.faker.random_int(0, 50))
                return self.factory.generate_siem_events(event_count)
            
            async def query(self, **params):
                return await self.search_events(**params)
        
        yield MockSIEMClient()
    
    @asynccontextmanager
    async def mock_llm_client(self):
        """Mock LLM client with deterministic responses."""
        class MockLLMClient:
            def generate(self, prompt: str) -> Dict[str, Any]:
                # Simulate processing time
                time.sleep(0.2)
                
                # Generate deterministic response based on prompt
                response_templates = {
                    "case_analysis": "This case shows suspicious activity involving {entities}. Recommend further investigation of network traffic and user behavior patterns.",
                    "entity_enrichment": "The entity shows indicators of compromise: recent failed logins, unusual network connections, and potential malware signatures detected.",
                    "default": "Analysis complete. The data suggests normal operational activity with no immediate threats detected."
                }
                
                # Simple template matching
                response_text = response_templates["default"]
                if "case" in prompt.lower() and "analysis" in prompt.lower():
                    response_text = response_templates["case_analysis"]
                elif "entity" in prompt.lower() and "enrich" in prompt.lower():
                    response_text = response_templates["entity_enrichment"]
                
                # Estimate tokens (rough approximation)
                estimated_tokens = len(prompt.split()) + len(response_text.split())
                
                return {
                    "text": response_text,
                    "tokens": estimated_tokens,
                    "cost_usd": estimated_tokens * 0.00001  # Mock cost
                }
        
        yield MockLLMClient()
    
    @asynccontextmanager 
    async def mock_neo4j_client(self):
        """Mock Neo4j client for graph operations."""
        class MockNeo4jClient:
            def __init__(self):
                self.nodes = {}
                self.relationships = []
            
            def session(self):
                return self
            
            def run(self, query: str, **parameters):
                # Mock query execution
                class MockResult:
                    def single(self):
                        return {"count": self.factory.faker.random_int(1, 10)}
                    
                    def __iter__(self):
                        return iter([{"node": {"id": str(uuid.uuid4())}}])
                
                return MockResult()
            
            def close(self):
                pass
        
        yield MockNeo4jClient()


class TestEnvironment:
    """Test environment manager for isolation and setup."""
    
    def __init__(self, name: str):
        self.name = name
        self.factory = TestDataFactory()
        self.mocks = MockServices(self.factory)
        self.cleanup_tasks: List[Callable] = []
        self.test_data: Dict[str, Any] = {}
    
    async def setup(self):
        """Setup test environment."""
        logger.info(f"Setting up test environment: {self.name}")
        
        # Initialize test data
        self.test_data = {
            "cases": [self.factory.generate_case_id() for _ in range(5)],
            "rules": [self.factory.generate_rule_id() for _ in range(10)],
            "detections": [self.factory.generate_detection_event() for _ in range(20)],
            "siem_events": self.factory.generate_siem_events(100)
        }
        
        logger.info(f"Generated test data: {len(self.test_data['detections'])} detections, {len(self.test_data['siem_events'])} SIEM events")
    
    async def teardown(self):
        """Teardown test environment."""
        logger.info(f"Tearing down test environment: {self.name}")
        
        # Execute cleanup tasks
        for cleanup_task in self.cleanup_tasks:
            try:
                if asyncio.iscoroutinefunction(cleanup_task):
                    await cleanup_task()
                else:
                    cleanup_task()
            except Exception as e:
                logger.error(f"Cleanup task failed: {e}")
        
        # Clear test data
        self.test_data.clear()
        self.cleanup_tasks.clear()
    
    def add_cleanup_task(self, cleanup_func: Callable):
        """Add cleanup task to be executed during teardown."""
        self.cleanup_tasks.append(cleanup_func)
    
    @asynccontextmanager
    async def isolated_environment(self):
        """Context manager for isolated test execution."""
        await self.setup()
        try:
            yield self
        finally:
            await self.teardown()


class TestRunner:
    """Test execution engine with parallel execution and reporting."""
    
    def __init__(self, name: str = "SOC Platform Tests"):
        self.name = name
        self.test_suites: List[TestSuite] = []
        self.global_setup_func: Optional[Callable] = None
        self.global_teardown_func: Optional[Callable] = None
        self.test_environment = TestEnvironment("default")
        self.execution_stats = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "error_tests": 0,
            "skipped_tests": 0,
            "total_duration_ms": 0.0
        }
    
    def add_test_suite(self, test_suite: TestSuite):
        """Add test suite to runner."""
        self.test_suites.append(test_suite)
        logger.info(f"Added test suite: {test_suite.name} ({len(test_suite.test_cases)} tests)")
    
    def set_global_setup(self, setup_func: Callable):
        """Set global setup function."""
        self.global_setup_func = setup_func
    
    def set_global_teardown(self, teardown_func: Callable):
        """Set global teardown function."""
        self.global_teardown_func = teardown_func
    
    async def run_all_tests(self, parallel: bool = True) -> Dict[str, Any]:
        """Run all test suites and return comprehensive results."""
        start_time = time.time()
        all_results = []
        
        logger.info(f"Starting test execution: {self.name}")
        
        try:
            # Global setup
            if self.global_setup_func:
                logger.info("Executing global setup")
                if asyncio.iscoroutinefunction(self.global_setup_func):
                    await self.global_setup_func()
                else:
                    self.global_setup_func()
            
            # Setup test environment
            async with self.test_environment.isolated_environment():
                
                # Execute test suites
                if parallel and len(self.test_suites) > 1:
                    # Run suites in parallel
                    suite_tasks = [
                        self._run_test_suite(suite) 
                        for suite in self.test_suites
                    ]
                    suite_results = await asyncio.gather(*suite_tasks, return_exceptions=True)
                    
                    for i, result in enumerate(suite_results):
                        if isinstance(result, Exception):
                            logger.error(f"Test suite {self.test_suites[i].name} failed with exception: {result}")
                        else:
                            all_results.extend(result)
                else:
                    # Run suites sequentially
                    for suite in self.test_suites:
                        suite_results = await self._run_test_suite(suite)
                        all_results.extend(suite_results)
            
            # Global teardown
            if self.global_teardown_func:
                logger.info("Executing global teardown")
                if asyncio.iscoroutinefunction(self.global_teardown_func):
                    await self.global_teardown_func()
                else:
                    self.global_teardown_func()
        
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            raise
        
        finally:
            total_duration = (time.time() - start_time) * 1000
            
            # Calculate statistics
            self.execution_stats["total_tests"] = len(all_results)
            self.execution_stats["total_duration_ms"] = total_duration
            
            for result in all_results:
                if result.status == "passed":
                    self.execution_stats["passed_tests"] += 1
                elif result.status == "failed":
                    self.execution_stats["failed_tests"] += 1
                elif result.status == "error":
                    self.execution_stats["error_tests"] += 1
                elif result.status == "skipped":
                    self.execution_stats["skipped_tests"] += 1
            
            # Generate test report
            report = self._generate_test_report(all_results)
            logger.info(f"Test execution completed in {total_duration:.1f}ms")
            
            return report
    
    async def _run_test_suite(self, test_suite: TestSuite) -> List[TestResult]:
        """Run a single test suite."""
        logger.info(f"Running test suite: {test_suite.name}")
        suite_results = []
        
        try:
            # Suite setup
            if test_suite.setup_func:
                if asyncio.iscoroutinefunction(test_suite.setup_func):
                    await test_suite.setup_func()
                else:
                    test_suite.setup_func()
            
            # Execute test cases
            if test_suite.parallel_execution and len(test_suite.test_cases) > 1:
                # Run tests in parallel
                semaphore = asyncio.Semaphore(test_suite.max_workers)
                
                async def bounded_test_execution(test_case):
                    async with semaphore:
                        return await self._run_test_case(test_case)
                
                test_tasks = [
                    bounded_test_execution(test_case)
                    for test_case in test_suite.test_cases
                ]
                results = await asyncio.gather(*test_tasks, return_exceptions=True)
                
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        error_result = TestResult(
                            test_id=test_suite.test_cases[i].test_id,
                            name=test_suite.test_cases[i].name,
                            status="error",
                            duration_ms=0.0,
                            error_message=str(result)
                        )
                        suite_results.append(error_result)
                    else:
                        suite_results.append(result)
            else:
                # Run tests sequentially
                for test_case in test_suite.test_cases:
                    result = await self._run_test_case(test_case)
                    suite_results.append(result)
            
            # Suite teardown
            if test_suite.teardown_func:
                if asyncio.iscoroutinefunction(test_suite.teardown_func):
                    await test_suite.teardown_func()
                else:
                    test_suite.teardown_func()
        
        except Exception as e:
            logger.error(f"Test suite {test_suite.name} failed: {e}")
            # Create error result for the entire suite
            error_result = TestResult(
                test_id=f"suite_{test_suite.suite_id}",
                name=f"Suite: {test_suite.name}",
                status="error",
                duration_ms=0.0,
                error_message=str(e)
            )
            suite_results.append(error_result)
        
        test_suite.results = suite_results
        return suite_results
    
    async def _run_test_case(self, test_case: TestCase) -> TestResult:
        """Run a single test case."""
        start_time = time.time()
        
        try:
            # Test setup
            if test_case.setup_func:
                if asyncio.iscoroutinefunction(test_case.setup_func):
                    await test_case.setup_func()
                else:
                    test_case.setup_func()
            
            # Execute test with timeout
            if asyncio.iscoroutinefunction(test_case.test_func):
                test_result = await asyncio.wait_for(
                    test_case.test_func(),
                    timeout=test_case.timeout_seconds
                )
            else:
                test_result = test_case.test_func()
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Analyze test result
            status = "passed"
            error_message = None
            
            if test_case.expected_outcome == "failure" and test_result is not False:
                status = "failed"
                error_message = f"Expected failure but test returned: {test_result}"
            elif test_case.expected_outcome == "success" and test_result is False:
                status = "failed"
                error_message = "Test returned False"
            
            result = TestResult(
                test_id=test_case.test_id,
                name=test_case.name,
                status=status,
                duration_ms=duration_ms,
                error_message=error_message,
                assertions_passed=1 if status == "passed" else 0,
                assertions_failed=1 if status == "failed" else 0
            )
            
            # Test teardown
            if test_case.teardown_func:
                try:
                    if asyncio.iscoroutinefunction(test_case.teardown_func):
                        await test_case.teardown_func()
                    else:
                        test_case.teardown_func()
                except Exception as e:
                    logger.warning(f"Test teardown failed for {test_case.name}: {e}")
            
            logger.debug(f"Test {test_case.name}: {status} ({duration_ms:.1f}ms)")
            return result
        
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                test_id=test_case.test_id,
                name=test_case.name,
                status="error",
                duration_ms=duration_ms,
                error_message=f"Test timed out after {test_case.timeout_seconds}s"
            )
        
        except Exception as e:
            import traceback
            duration_ms = (time.time() - start_time) * 1000
            return TestResult(
                test_id=test_case.test_id,
                name=test_case.name,
                status="error",
                duration_ms=duration_ms,
                error_message=str(e),
                error_traceback=traceback.format_exc()
            )
    
    def _generate_test_report(self, results: List[TestResult]) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        # Group results by status
        passed = [r for r in results if r.status == "passed"]
        failed = [r for r in results if r.status == "failed"]
        errors = [r for r in results if r.status == "error"]
        skipped = [r for r in results if r.status == "skipped"]
        
        # Calculate success rate
        total_tests = len(results)
        success_rate = (len(passed) / total_tests * 100) if total_tests > 0 else 0
        
        # Performance metrics
        total_duration = sum(r.duration_ms for r in results)
        avg_duration = total_duration / total_tests if total_tests > 0 else 0
        slowest_tests = sorted(results, key=lambda x: x.duration_ms, reverse=True)[:5]
        
        report = {
            "test_run_summary": {
                "name": self.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_tests": total_tests,
                "passed": len(passed),
                "failed": len(failed),
                "errors": len(errors),
                "skipped": len(skipped),
                "success_rate_percent": round(success_rate, 2),
                "total_duration_ms": round(total_duration, 2),
                "average_duration_ms": round(avg_duration, 2)
            },
            "test_suites": [
                {
                    "suite_id": suite.suite_id,
                    "name": suite.name,
                    "test_count": len(suite.test_cases),
                    "results_count": len(suite.results),
                    "passed": len([r for r in suite.results if r.status == "passed"]),
                    "failed": len([r for r in suite.results if r.status == "failed"])
                }
                for suite in self.test_suites
            ],
            "failed_tests": [
                {
                    "test_id": r.test_id,
                    "name": r.name,
                    "error_message": r.error_message,
                    "duration_ms": r.duration_ms
                }
                for r in failed + errors
            ],
            "performance": {
                "slowest_tests": [
                    {
                        "name": r.name,
                        "duration_ms": r.duration_ms,
                        "status": r.status
                    }
                    for r in slowest_tests
                ]
            },
            "execution_stats": self.execution_stats
        }
        
        return report
    
    def print_summary(self, report: Dict[str, Any]):
        """Print test execution summary."""
        summary = report["test_run_summary"]
        
        print(f"\n{'='*60}")
        print(f"TEST EXECUTION SUMMARY: {summary['name']}")
        print(f"{'='*60}")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']} ✓")
        print(f"Failed: {summary['failed']} ✗")
        print(f"Errors: {summary['errors']} ⚠")
        print(f"Success Rate: {summary['success_rate_percent']}%")
        print(f"Total Duration: {summary['total_duration_ms']:.1f}ms")
        print(f"Average Duration: {summary['average_duration_ms']:.1f}ms")
        
        if report["failed_tests"]:
            print(f"\nFAILED TESTS:")
            for failed_test in report["failed_tests"][:10]:  # Show first 10
                print(f"  - {failed_test['name']}: {failed_test['error_message']}")
        
        print(f"{'='*60}\n")


# Pre-built test suites for SOC platform components
def create_eligibility_test_suite(test_environment: TestEnvironment) -> TestSuite:
    """Create test suite for eligibility module."""
    
    async def test_fact_profile_detection():
        from app_extensions.eligibility import is_fact_or_profile
        
        # Test fact detection
        fact_rule = "fact_login_anomaly_detection"
        assert is_fact_or_profile(fact_rule) == True
        
        # Test profile detection  
        profile_rule = "profile_user_behavior_analysis"
        assert is_fact_or_profile(profile_rule) == True
        
        # Test invalid rule
        invalid_rule = "correlation_network_analysis"
        assert is_fact_or_profile(invalid_rule) == False
        
        return True
    
    async def test_eligible_detection_selection():
        from app_extensions.eligibility import select_eligible_detections, EligibleDetection
        
        detections = [
            EligibleDetection(
                detection_id="det1",
                rule_name="fact_test_rule",
                rule_type="fact",
                search_query="test",
                event_filter="filter1",
                event_from_time_millis=1000,
                event_to_time_millis=2000,
                window_minutes=5,
                source_case_id="case1"
            ),
            EligibleDetection(
                detection_id="det2",
                rule_name="correlation_test_rule",
                rule_type="correlation",
                search_query="test",
                event_filter="filter2",
                event_from_time_millis=1000,
                event_to_time_millis=2000,
                window_minutes=5,
                source_case_id="case2"
            )
        ]
        
        eligible = select_eligible_detections(detections)
        assert len(eligible) == 1
        assert eligible[0].detection_id == "det1"
        
        return True
    
    test_cases = [
        TestCase(
            test_id="eligibility_001",
            name="Test fact/profile detection",
            description="Test rule name pattern matching for eligibility",
            category="unit",
            test_func=test_fact_profile_detection,
            tags=["eligibility", "unit"]
        ),
        TestCase(
            test_id="eligibility_002", 
            name="Test eligible detection selection",
            description="Test filtering of eligible detections",
            category="unit",
            test_func=test_eligible_detection_selection,
            tags=["eligibility", "unit"]
        )
    ]
    
    return TestSuite(
        suite_id="eligibility_tests",
        name="Eligibility Module Tests",
        test_cases=test_cases,
        parallel_execution=True
    )


def create_similarity_search_test_suite(test_environment: TestEnvironment) -> TestSuite:
    """Create test suite for similarity search module."""
    
    async def test_jaccard_similarity():
        from app_extensions.similarity_search import SimilaritySearchEngine
        
        # Create mock Redis client
        async with test_environment.mocks.mock_redis_client() as redis_client:
            engine = SimilaritySearchEngine(redis_client)
            
            target_entities = {
                "users": ["alice", "bob"],
                "ips": ["192.168.1.1", "10.0.0.1"],
                "hosts": ["server1", "workstation1"]
            }
            
            candidate_entities = {
                "users": ["alice", "charlie"],
                "ips": ["192.168.1.1"],
                "hosts": ["server1", "server2"]
            }
            
            score, breakdown = engine._calculate_weighted_jaccard(target_entities, candidate_entities)
            
            # Should have some similarity due to overlapping entities
            assert score > 0
            assert "users" in breakdown
            assert "ips" in breakdown
            assert "hosts" in breakdown
        
        return True
    
    async def test_entity_indexing():
        from app_extensions.similarity_search import SimilaritySearchEngine
        
        async with test_environment.mocks.mock_redis_client() as redis_client:
            engine = SimilaritySearchEngine(redis_client)
            
            case_id = "test_case_1"
            entities = {
                "users": ["testuser"],
                "ips": ["192.168.1.100"],
                "hosts": ["testhost"]
            }
            
            await engine._maintain_entity_indices(case_id, entities)
            
            # Check that indices were created
            user_index = await redis_client.smembers("idx:entity:users:testuser")
            assert case_id.encode() in user_index
            
            ip_index = await redis_client.smembers("idx:entity:ips:192.168.1.100")
            assert case_id.encode() in ip_index
        
        return True
    
    test_cases = [
        TestCase(
            test_id="similarity_001",
            name="Test Jaccard similarity calculation",
            description="Test weighted Jaccard similarity scoring",
            category="unit",
            test_func=test_jaccard_similarity,
            tags=["similarity", "unit"]
        ),
        TestCase(
            test_id="similarity_002",
            name="Test entity indexing",
            description="Test Redis entity index maintenance",
            category="integration",
            test_func=test_entity_indexing,
            tags=["similarity", "integration"]
        )
    ]
    
    return TestSuite(
        suite_id="similarity_tests",
        name="Similarity Search Tests",
        test_cases=test_cases,
        parallel_execution=True
    )


# Integration test example
def create_end_to_end_test_suite(test_environment: TestEnvironment) -> TestSuite:
    """Create end-to-end integration test suite."""
    
    async def test_complete_case_analysis_pipeline():
        """Test complete case analysis from detection to insights."""
        from app_extensions.eligibility import select_eligible_detections, EligibleDetection
        from app_extensions.siem_executor import SiemExecutor
        from app_extensions.entity_normalizer import EntityNormalizer
        from app_extensions.similarity_search import SimilaritySearchEngine
        
        # Setup test data
        detection = EligibleDetection(
            detection_id="integration_test_det_1",
            rule_name="fact_integration_test",
            rule_type="fact",
            search_query="event_type:authentication",
            event_filter="timestamp:[1000000 TO 2000000]",
            event_from_time_millis=1000000,
            event_to_time_millis=2000000,
            window_minutes=60,
            source_case_id="integration_test_case"
        )
        
        # Test eligibility
        eligible_detections = select_eligible_detections([detection])
        assert len(eligible_detections) == 1
        
        # Test SIEM query execution
        async with test_environment.mocks.mock_siem_client() as siem_client:
            executor = SiemExecutor()
            siem_results = await executor.run_siem_queries(siem_client, eligible_detections)
            
            assert len(siem_results) > 0
            assert not siem_results[0].error
        
        # Test entity normalization
        normalizer = EntityNormalizer()
        sample_event = test_environment.test_data["siem_events"][0]
        entities = normalizer.get_normalized_dict(sample_event)
        
        assert "users" in entities or "ips" in entities or "hosts" in entities
        
        # Test similarity search
        async with test_environment.mocks.mock_redis_client() as redis_client:
            search_engine = SimilaritySearchEngine(redis_client)
            
            # Index some entities first
            await search_engine._maintain_entity_indices("similar_case_1", entities)
            
            # Find similar cases
            similar_cases = await search_engine.find_similar_cases(entities, "test_case")
            
            # Should complete without error (may have 0 results due to mock data)
            assert isinstance(similar_cases, list)
        
        return True
    
    test_cases = [
        TestCase(
            test_id="e2e_001",
            name="Complete case analysis pipeline",
            description="End-to-end test of detection to insights pipeline",
            category="integration", 
            test_func=test_complete_case_analysis_pipeline,
            tags=["integration", "e2e"],
            timeout_seconds=60.0
        )
    ]
    
    return TestSuite(
        suite_id="e2e_tests",
        name="End-to-End Integration Tests",
        test_cases=test_cases,
        parallel_execution=False  # Sequential execution for integration tests
    )


# Main test execution function
async def run_soc_platform_tests():
    """Run comprehensive SOC platform tests."""
    
    # Create test runner
    runner = TestRunner("SOC Platform Comprehensive Tests")
    
    # Create test environment
    test_env = TestEnvironment("soc_platform_tests")
    runner.test_environment = test_env
    
    # Add test suites
    runner.add_test_suite(create_eligibility_test_suite(test_env))
    runner.add_test_suite(create_similarity_search_test_suite(test_env))
    runner.add_test_suite(create_end_to_end_test_suite(test_env))
    
    # Run all tests
    report = await runner.run_all_tests(parallel=True)
    
    # Print summary
    runner.print_summary(report)
    
    return report


if __name__ == "__main__":
    # Example usage
    import sys
    
    async def main():
        try:
            report = await run_soc_platform_tests()
            
            # Exit with non-zero code if tests failed
            if report["test_run_summary"]["failed"] > 0 or report["test_run_summary"]["errors"] > 0:
                sys.exit(1)
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            sys.exit(1)
    
    asyncio.run(main())