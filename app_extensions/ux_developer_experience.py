"""
UX Improvements and Developer Experience Enhancements for SOC Platform.

This module provides comprehensive improvements for:
- Fast analyst workflows with hotkeys and shortcuts
- Rich CLI interface with progress bars and status
- Developer tools with debugging and profiling
- Auto-completion and intelligent suggestions
- Configuration management and validation
- Documentation generation and help systems
- Performance optimization and caching
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import click
import rich
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.panel import Panel
from rich.tree import Tree
from rich.syntax import Syntax
from rich.markdown import Markdown
import yaml
import configparser
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter, PathCompleter
from prompt_toolkit.shortcuts import confirm
from prompt_toolkit.formatted_text import HTML
import jinja2

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """Individual workflow step definition."""
    step_id: str
    name: str
    description: str
    action_func: Callable
    hotkey: Optional[str] = None
    confirmation_required: bool = False
    parameters: Dict[str, Any] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)
    estimated_duration_ms: int = 1000


@dataclass
class AnalystWorkflow:
    """Complete analyst workflow definition."""
    workflow_id: str
    name: str
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)
    shortcuts: Dict[str, str] = field(default_factory=dict)  # hotkey -> step_id
    auto_advance: bool = False
    progress_tracking: bool = True


@dataclass
class CLITheme:
    """CLI theme configuration."""
    primary_color: str = "blue"
    success_color: str = "green"
    warning_color: str = "yellow"
    error_color: str = "red"
    info_color: str = "cyan"
    progress_color: str = "magenta"
    table_style: str = "simple"
    panel_style: str = "rounded"


class FastAnalystInterface:
    """
    High-speed analyst interface with hotkeys and shortcuts.
    """
    
    def __init__(self, theme: Optional[CLITheme] = None):
        self.console = Console()
        self.theme = theme or CLITheme()
        self.workflows: Dict[str, AnalystWorkflow] = {}
        self.active_workflow: Optional[str] = None
        self.current_step: int = 0
        self.workflow_context: Dict[str, Any] = {}
        self.command_history: List[str] = []
        
        # Auto-completion data
        self.command_completions = WordCompleter([
            'start-workflow', 'step', 'skip', 'back', 'status', 'help',
            'case-analyze', 'entity-enrich', 'similarity-search', 'timeline-build',
            'export-report', 'exit'
        ])
        
        # Performance tracking
        self.step_timings: Dict[str, float] = {}
    
    def register_workflow(self, workflow: AnalystWorkflow):
        """Register analyst workflow."""
        self.workflows[workflow.workflow_id] = workflow
        logger.info(f"Registered workflow: {workflow.name}")
    
    def display_welcome_screen(self):
        """Display welcome screen with available workflows."""
        welcome_text = """
        # SOC Platform - Fast Analyst Interface
        
        Welcome to the enhanced SOC analyst interface. Use hotkeys and shortcuts for rapid investigation workflows.
        """
        
        self.console.print(Panel(
            Markdown(welcome_text),
            title="[bold blue]SOC Platform[/bold blue]",
            style=self.theme.panel_style
        ))
        
        # Display available workflows
        workflow_table = Table(title="Available Workflows", style=self.theme.table_style)
        workflow_table.add_column("ID", style="cyan")
        workflow_table.add_column("Name", style="magenta") 
        workflow_table.add_column("Steps", justify="center")
        workflow_table.add_column("Hotkeys", style="yellow")
        
        for workflow_id, workflow in self.workflows.items():
            hotkeys = ", ".join([f"{key}→{step}" for key, step in workflow.shortcuts.items()])
            workflow_table.add_row(
                workflow_id,
                workflow.name,
                str(len(workflow.steps)),
                hotkeys if hotkeys else "None"
            )
        
        self.console.print(workflow_table)
    
    async def start_interactive_session(self):
        """Start interactive analyst session with auto-completion."""
        self.display_welcome_screen()
        
        while True:
            try:
                # Get user input with auto-completion
                user_input = prompt(
                    HTML('<b>soc></b> '),
                    completer=self.command_completions,
                    complete_style='column'
                )
                
                if not user_input.strip():
                    continue
                
                self.command_history.append(user_input)
                
                # Parse and execute command
                await self.execute_command(user_input.strip())
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'exit' to quit properly[/yellow]")
            except EOFError:
                break
    
    async def execute_command(self, command: str):
        """Execute analyst command."""
        parts = command.split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        try:
            if cmd == 'start-workflow':
                if not args:
                    self.console.print("[red]Usage: start-workflow <workflow_id>[/red]")
                    return
                await self.start_workflow(args[0])
            
            elif cmd == 'step':
                await self.execute_current_step()
            
            elif cmd == 'skip':
                await self.skip_current_step()
            
            elif cmd == 'back':
                await self.go_back_step()
            
            elif cmd == 'status':
                self.display_workflow_status()
            
            elif cmd == 'case-analyze':
                if not args:
                    self.console.print("[red]Usage: case-analyze <case_id>[/red]")
                    return
                await self.quick_case_analysis(args[0])
            
            elif cmd == 'entity-enrich':
                if len(args) < 2:
                    self.console.print("[red]Usage: entity-enrich <type> <value>[/red]")
                    return
                await self.quick_entity_enrichment(args[0], args[1])
            
            elif cmd == 'similarity-search':
                if not args:
                    self.console.print("[red]Usage: similarity-search <case_id>[/red]")
                    return
                await self.quick_similarity_search(args[0])
            
            elif cmd == 'timeline-build':
                if not args:
                    self.console.print("[red]Usage: timeline-build <case_id>[/red]")
                    return
                await self.quick_timeline_build(args[0])
            
            elif cmd == 'export-report':
                if not args:
                    self.console.print("[red]Usage: export-report <format> [output_file][/red]")
                    return
                output_file = args[1] if len(args) > 1 else None
                await self.export_report(args[0], output_file)
            
            elif cmd == 'help':
                self.display_help()
            
            elif cmd == 'exit':
                self.console.print("[green]Goodbye! 👋[/green]")
                return False
            
            else:
                self.console.print(f"[red]Unknown command: {cmd}[/red]")
                self.display_help()
        
        except Exception as e:
            self.console.print(f"[red]Command failed: {str(e)}[/red]")
    
    async def start_workflow(self, workflow_id: str):
        """Start analyst workflow."""
        if workflow_id not in self.workflows:
            self.console.print(f"[red]Workflow not found: {workflow_id}[/red]")
            return
        
        self.active_workflow = workflow_id
        self.current_step = 0
        self.workflow_context.clear()
        
        workflow = self.workflows[workflow_id]
        
        self.console.print(Panel(
            f"[bold]{workflow.name}[/bold]\n{workflow.description}",
            title="[blue]Starting Workflow[/blue]",
            style=self.theme.panel_style
        ))
        
        if workflow.progress_tracking:
            self.display_workflow_progress()
    
    async def execute_current_step(self):
        """Execute current workflow step."""
        if not self.active_workflow:
            self.console.print("[red]No active workflow[/red]")
            return
        
        workflow = self.workflows[self.active_workflow]
        
        if self.current_step >= len(workflow.steps):
            self.console.print("[green]Workflow completed! ✓[/green]")
            return
        
        step = workflow.steps[self.current_step]
        
        # Check prerequisites
        if not await self.check_prerequisites(step):
            return
        
        # Confirm if required
        if step.confirmation_required:
            if not confirm(f"Execute step: {step.name}?"):
                self.console.print("[yellow]Step skipped[/yellow]")
                return
        
        # Execute step with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task(f"Executing: {step.name}", total=100)
            
            start_time = time.time()
            
            try:
                # Execute step function
                if asyncio.iscoroutinefunction(step.action_func):
                    result = await step.action_func(**step.parameters, progress=progress, task=task)
                else:
                    result = step.action_func(**step.parameters)
                
                duration_ms = (time.time() - start_time) * 1000
                self.step_timings[step.step_id] = duration_ms
                
                progress.update(task, completed=100)
                
                self.console.print(f"[green]Step completed: {step.name} ({duration_ms:.1f}ms)[/green]")
                
                # Store result in context
                if result:
                    self.workflow_context[step.step_id] = result
                
                # Auto-advance if enabled
                if workflow.auto_advance:
                    self.current_step += 1
                    if self.current_step < len(workflow.steps):
                        await asyncio.sleep(0.5)  # Brief pause
                        await self.execute_current_step()
                else:
                    self.current_step += 1
                
            except Exception as e:
                self.console.print(f"[red]Step failed: {str(e)}[/red]")
    
    async def check_prerequisites(self, step: WorkflowStep) -> bool:
        """Check if step prerequisites are met."""
        for prereq in step.prerequisites:
            if prereq not in self.workflow_context:
                self.console.print(f"[red]Prerequisite not met: {prereq}[/red]")
                return False
        return True
    
    def display_workflow_progress(self):
        """Display workflow progress."""
        if not self.active_workflow:
            return
        
        workflow = self.workflows[self.active_workflow]
        
        progress_table = Table(title=f"Workflow Progress: {workflow.name}")
        progress_table.add_column("Step", style="cyan")
        progress_table.add_column("Status", justify="center")
        progress_table.add_column("Duration", justify="right")
        
        for i, step in enumerate(workflow.steps):
            if i < self.current_step:
                status = "[green]✓ Complete[/green]"
                duration = f"{self.step_timings.get(step.step_id, 0):.1f}ms"
            elif i == self.current_step:
                status = "[yellow]→ Current[/yellow]"
                duration = "-"
            else:
                status = "[dim]○ Pending[/dim]"
                duration = "-"
            
            progress_table.add_row(step.name, status, duration)
        
        self.console.print(progress_table)
    
    def display_workflow_status(self):
        """Display current workflow status."""
        if not self.active_workflow:
            self.console.print("[yellow]No active workflow[/yellow]")
            return
        
        workflow = self.workflows[self.active_workflow]
        
        status_panel = f"""
        **Active Workflow:** {workflow.name}
        **Progress:** {self.current_step}/{len(workflow.steps)} steps
        **Context Variables:** {len(self.workflow_context)}
        """
        
        self.console.print(Panel(
            Markdown(status_panel),
            title="[blue]Workflow Status[/blue]"
        ))
        
        self.display_workflow_progress()
    
    async def quick_case_analysis(self, case_id: str):
        """Quick case analysis command."""
        with Progress(
            SpinnerColumn(),
            TextColumn("Analyzing case..."),
            console=self.console
        ) as progress:
            task = progress.add_task("Case Analysis", total=100)
            
            # Mock analysis - replace with actual implementation
            await asyncio.sleep(2)
            progress.update(task, completed=50)
            
            # Simulate analysis result
            analysis_result = {
                "case_id": case_id,
                "risk_score": 7.5,
                "entities_found": 15,
                "similar_cases": 3,
                "recommendations": [
                    "Review user authentication logs",
                    "Investigate network connections",
                    "Check for lateral movement"
                ]
            }
            
            progress.update(task, completed=100)
        
        # Display results
        result_table = Table(title=f"Case Analysis: {case_id}")
        result_table.add_column("Metric", style="cyan")
        result_table.add_column("Value", style="green")
        
        result_table.add_row("Risk Score", f"{analysis_result['risk_score']}/10")
        result_table.add_row("Entities Found", str(analysis_result['entities_found']))
        result_table.add_row("Similar Cases", str(analysis_result['similar_cases']))
        
        self.console.print(result_table)
        
        # Display recommendations
        rec_panel = "\n".join([f"• {rec}" for rec in analysis_result['recommendations']])
        self.console.print(Panel(
            rec_panel,
            title="[blue]Recommendations[/blue]"
        ))
    
    async def quick_entity_enrichment(self, entity_type: str, entity_value: str):
        """Quick entity enrichment command."""
        self.console.print(f"[cyan]Enriching {entity_type}: {entity_value}[/cyan]")
        
        # Mock enrichment - replace with actual implementation
        await asyncio.sleep(1)
        
        enrichment_data = {
            "reputation": "Unknown",
            "first_seen": "2024-01-15T10:30:00Z",
            "threat_indicators": ["Unusual login patterns"],
            "risk_level": "Medium"
        }
        
        # Display enrichment results
        enrichment_tree = Tree(f"[bold]{entity_type.upper()}: {entity_value}[/bold]")
        for key, value in enrichment_data.items():
            enrichment_tree.add(f"[cyan]{key}:[/cyan] {value}")
        
        self.console.print(enrichment_tree)
    
    def display_help(self):
        """Display help information."""
        help_text = """
        # SOC Platform - Command Reference
        
        ## Workflow Commands
        - `start-workflow <id>` - Start an analyst workflow
        - `step` - Execute current workflow step
        - `skip` - Skip current step
        - `back` - Go back one step
        - `status` - Show workflow status
        
        ## Quick Analysis Commands
        - `case-analyze <case_id>` - Quick case analysis
        - `entity-enrich <type> <value>` - Entity enrichment
        - `similarity-search <case_id>` - Find similar cases
        - `timeline-build <case_id>` - Build event timeline
        
        ## Utility Commands
        - `export-report <format>` - Export analysis report
        - `help` - Show this help
        - `exit` - Exit the interface
        
        ## Hotkeys (when available)
        - `Ctrl+C` - Interrupt current operation
        - `Tab` - Auto-complete commands
        - `Up/Down` - Command history
        """
        
        self.console.print(Panel(
            Markdown(help_text),
            title="[blue]Help - Command Reference[/blue]"
        ))


class DeveloperToolkit:
    """
    Developer experience tools and utilities.
    """
    
    def __init__(self):
        self.console = Console()
        self.config_manager = ConfigurationManager()
        self.doc_generator = DocumentationGenerator()
        self.profiler = PerformanceProfiler()
    
    def create_development_workspace(self, workspace_path: str):
        """Create development workspace with templates and tools."""
        workspace = Path(workspace_path)
        workspace.mkdir(exist_ok=True)
        
        # Create directory structure
        directories = [
            "tests", "docs", "configs", "templates", 
            "scripts", "logs", "data/samples"
        ]
        
        for directory in directories:
            (workspace / directory).mkdir(parents=True, exist_ok=True)
        
        # Create template files
        templates = {
            "tests/test_template.py": self._get_test_template(),
            "configs/development.yaml": self._get_dev_config_template(),
            "scripts/run_tests.sh": self._get_test_script_template(),
            "README.md": self._get_readme_template(),
            ".gitignore": self._get_gitignore_template()
        }
        
        for file_path, content in templates.items():
            full_path = workspace / file_path
            if not full_path.exists():
                full_path.write_text(content)
        
        self.console.print(f"[green]Development workspace created: {workspace_path}[/green]")
        
        # Display workspace tree
        self.display_workspace_tree(workspace)
    
    def display_workspace_tree(self, workspace_path: Path):
        """Display workspace directory tree."""
        tree = Tree(f"[bold blue]{workspace_path.name}[/bold blue]")
        
        def add_directory(tree_node, directory):
            for item in sorted(directory.iterdir()):
                if item.is_dir():
                    dir_node = tree_node.add(f"[blue]📁 {item.name}[/blue]")
                    if len(list(item.iterdir())) > 0:
                        add_directory(dir_node, item)
                else:
                    tree_node.add(f"📄 {item.name}")
        
        add_directory(tree, workspace_path)
        self.console.print(tree)
    
    def _get_test_template(self) -> str:
        return '''"""
Test template for SOC platform components.
"""
import pytest
import asyncio
from app_extensions.testing_framework import TestDataFactory, MockServices

class TestExample:
    """Example test class."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.factory = TestDataFactory()
    
    def test_example_function(self):
        """Example test method."""
        # Arrange
        test_data = self.factory.generate_case_id()
        
        # Act
        result = len(test_data) > 0
        
        # Assert
        assert result is True
    
    @pytest.mark.asyncio
    async def test_async_example(self):
        """Example async test method."""
        # Arrange
        mock_services = MockServices(self.factory)
        
        # Act
        async with mock_services.mock_redis_client() as redis:
            result = await redis.ping()
        
        # Assert
        assert result is True

if __name__ == "__main__":
    pytest.main([__file__])
'''
    
    def _get_dev_config_template(self) -> str:
        return '''# Development Configuration
debug: true
log_level: DEBUG

redis:
  host: localhost
  port: 6379
  db: 0

neo4j:
  uri: bolt://localhost:7687
  username: neo4j
  password: dev_password

siem:
  mock_mode: true
  mock_events: 100

llm:
  mock_mode: true
  provider: openai
  model: gpt-3.5-turbo

testing:
  parallel_execution: true
  timeout_seconds: 30
  generate_coverage: true
'''
    
    def _get_test_script_template(self) -> str:
        return '''#!/bin/bash
# Test execution script

set -e

echo "Running SOC Platform Tests..."

# Install dependencies
pip install -r requirements-dev.txt

# Run linting
echo "Running linting..."
flake8 app_extensions/ --max-line-length=120

# Run type checking
echo "Running type checking..."
mypy app_extensions/

# Run unit tests
echo "Running unit tests..."
pytest tests/ -v --cov=app_extensions --cov-report=html

# Run integration tests
echo "Running integration tests..."
python -m app_extensions.testing_framework

echo "All tests completed successfully!"
'''
    
    def _get_readme_template(self) -> str:
        return '''# SOC Platform Development

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

2. Start development services:
   ```bash
   docker-compose up -d redis neo4j
   ```

3. Run tests:
   ```bash
   ./scripts/run_tests.sh
   ```

## Development Workflow

1. Create feature branch
2. Write tests first (TDD)
3. Implement feature
4. Run full test suite
5. Submit pull request

## Architecture

- `app_extensions/` - Enhanced platform modules
- `tests/` - Test suite
- `configs/` - Configuration files
- `docs/` - Documentation

## Key Components

- **Eligibility**: Rule gating for SIEM queries
- **SIEM Executor**: Query execution with controls
- **Entity Normalizer**: Clean entity extraction
- **Similarity Search**: Fast case correlation
- **Timeline Builder**: Event normalization
- **Observability**: Monitoring and reliability

## Contributing

See CONTRIBUTING.md for detailed guidelines.
'''
    
    def _get_gitignore_template(self) -> str:
        return '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
env.bak/
venv.bak/

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# Coverage
htmlcov/
.coverage
.pytest_cache/

# Data
data/
*.db
*.sqlite

# Config
local_config.yaml
.env
'''


class ConfigurationManager:
    """Configuration management and validation."""
    
    def __init__(self):
        self.console = Console()
        self.config_schema = self._define_config_schema()
    
    def _define_config_schema(self) -> Dict[str, Any]:
        """Define configuration schema for validation."""
        return {
            "redis": {
                "host": {"type": "string", "required": True},
                "port": {"type": "integer", "required": True},
                "db": {"type": "integer", "default": 0}
            },
            "neo4j": {
                "uri": {"type": "string", "required": True},
                "username": {"type": "string", "required": True},
                "password": {"type": "string", "required": True}
            },
            "siem": {
                "endpoint": {"type": "string", "required": False},
                "timeout": {"type": "integer", "default": 30}
            },
            "llm": {
                "provider": {"type": "string", "required": True},
                "model": {"type": "string", "required": True},
                "max_tokens": {"type": "integer", "default": 2000}
            }
        }
    
    def validate_config(self, config_path: str) -> bool:
        """Validate configuration file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            errors = []
            for section, section_schema in self.config_schema.items():
                if section not in config:
                    errors.append(f"Missing section: {section}")
                    continue
                
                section_config = config[section]
                for key, key_schema in section_schema.items():
                    if key_schema.get("required", False) and key not in section_config:
                        errors.append(f"Missing required key: {section}.{key}")
            
            if errors:
                self.console.print("[red]Configuration validation failed:[/red]")
                for error in errors:
                    self.console.print(f"  • {error}")
                return False
            
            self.console.print("[green]Configuration is valid ✓[/green]")
            return True
            
        except Exception as e:
            self.console.print(f"[red]Configuration validation error: {e}[/red]")
            return False


class DocumentationGenerator:
    """Automatic documentation generation."""
    
    def __init__(self):
        self.console = Console()
        self.jinja_env = jinja2.Environment(
            loader=jinja2.DictLoader({}),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
    
    def generate_api_docs(self, modules: List[str], output_dir: str):
        """Generate API documentation from modules."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        self.console.print(f"[cyan]Generating API documentation...[/cyan]")
        
        for module_name in modules:
            try:
                # Import module dynamically
                module = __import__(module_name)
                
                # Extract classes and functions
                doc_data = self._extract_module_docs(module, module_name)
                
                # Generate markdown documentation
                doc_content = self._generate_module_markdown(doc_data)
                
                # Write to file
                doc_file = output_path / f"{module_name.replace('.', '_')}.md"
                doc_file.write_text(doc_content)
                
                self.console.print(f"  Generated: {doc_file.name}")
                
            except Exception as e:
                self.console.print(f"[red]Failed to generate docs for {module_name}: {e}[/red]")
        
        # Generate index
        self._generate_docs_index(output_path, modules)
        
        self.console.print(f"[green]Documentation generated in: {output_dir}[/green]")
    
    def _extract_module_docs(self, module, module_name: str) -> Dict[str, Any]:
        """Extract documentation from module."""
        doc_data = {
            "module_name": module_name,
            "module_doc": getattr(module, "__doc__", ""),
            "classes": [],
            "functions": []
        }
        
        for item_name in dir(module):
            if item_name.startswith('_'):
                continue
            
            item = getattr(module, item_name)
            
            if isinstance(item, type):  # Class
                class_doc = {
                    "name": item_name,
                    "doc": getattr(item, "__doc__", ""),
                    "methods": []
                }
                
                for method_name in dir(item):
                    if method_name.startswith('_'):
                        continue
                    
                    method = getattr(item, method_name)
                    if callable(method):
                        class_doc["methods"].append({
                            "name": method_name,
                            "doc": getattr(method, "__doc__", "")
                        })
                
                doc_data["classes"].append(class_doc)
            
            elif callable(item):  # Function
                doc_data["functions"].append({
                    "name": item_name,
                    "doc": getattr(item, "__doc__", "")
                })
        
        return doc_data
    
    def _generate_module_markdown(self, doc_data: Dict[str, Any]) -> str:
        """Generate markdown documentation for module."""
        md_content = f"""# {doc_data['module_name']}

{doc_data['module_doc']}

## Classes

"""
        
        for class_info in doc_data['classes']:
            md_content += f"""### {class_info['name']}

{class_info['doc']}

#### Methods

"""
            for method in class_info['methods']:
                md_content += f"""##### {method['name']}

{method['doc']}

"""
        
        md_content += "## Functions\n\n"
        
        for func in doc_data['functions']:
            md_content += f"""### {func['name']}

{func['doc']}

"""
        
        return md_content
    
    def _generate_docs_index(self, output_path: Path, modules: List[str]):
        """Generate documentation index."""
        index_content = """# SOC Platform API Documentation

This documentation was automatically generated from the source code.

## Modules

"""
        
        for module in modules:
            doc_file = f"{module.replace('.', '_')}.md"
            index_content += f"- [{module}]({doc_file})\n"
        
        (output_path / "index.md").write_text(index_content)


class PerformanceProfiler:
    """Performance profiling and optimization tools."""
    
    def __init__(self):
        self.console = Console()
        self.profile_data: Dict[str, List[float]] = {}
    
    def profile_operation(self, operation_name: str):
        """Decorator for profiling operations."""
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = (time.time() - start_time) * 1000
                    self.record_timing(operation_name, duration)
            
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = (time.time() - start_time) * 1000
                    self.record_timing(operation_name, duration)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    def record_timing(self, operation: str, duration_ms: float):
        """Record operation timing."""
        if operation not in self.profile_data:
            self.profile_data[operation] = []
        
        self.profile_data[operation].append(duration_ms)
        
        # Keep only recent data
        if len(self.profile_data[operation]) > 1000:
            self.profile_data[operation] = self.profile_data[operation][-500:]
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate performance analysis report."""
        report = {}
        
        for operation, timings in self.profile_data.items():
            if not timings:
                continue
            
            report[operation] = {
                "count": len(timings),
                "avg_ms": sum(timings) / len(timings),
                "min_ms": min(timings),
                "max_ms": max(timings),
                "total_ms": sum(timings)
            }
        
        return report
    
    def display_performance_report(self):
        """Display performance report in console."""
        report = self.generate_performance_report()
        
        if not report:
            self.console.print("[yellow]No performance data available[/yellow]")
            return
        
        perf_table = Table(title="Performance Profile")
        perf_table.add_column("Operation", style="cyan")
        perf_table.add_column("Count", justify="right")
        perf_table.add_column("Avg (ms)", justify="right", style="green")
        perf_table.add_column("Min (ms)", justify="right")
        perf_table.add_column("Max (ms)", justify="right", style="red")
        perf_table.add_column("Total (ms)", justify="right")
        
        for operation, stats in sorted(report.items(), key=lambda x: x[1]['avg_ms'], reverse=True):
            perf_table.add_row(
                operation,
                str(stats['count']),
                f"{stats['avg_ms']:.1f}",
                f"{stats['min_ms']:.1f}",
                f"{stats['max_ms']:.1f}",
                f"{stats['total_ms']:.1f}"
            )
        
        self.console.print(perf_table)


# Pre-built workflow definitions for analysts
def create_case_investigation_workflow() -> AnalystWorkflow:
    """Create standard case investigation workflow."""
    
    async def analyze_case_step(**kwargs):
        progress = kwargs.get('progress')
        task = kwargs.get('task')
        case_id = kwargs.get('case_id', 'CASE-123456')
        
        if progress:
            progress.update(task, completed=25, description="Loading case data...")
            await asyncio.sleep(0.5)
            progress.update(task, completed=50, description="Analyzing entities...")
            await asyncio.sleep(0.8)
            progress.update(task, completed=75, description="Generating insights...")
            await asyncio.sleep(0.3)
            progress.update(task, completed=100, description="Analysis complete")
        
        return {"case_id": case_id, "risk_score": 7.5, "entities": 15}
    
    async def enrich_entities_step(**kwargs):
        progress = kwargs.get('progress')
        task = kwargs.get('task')
        
        if progress:
            progress.update(task, completed=30, description="Enriching entities...")
            await asyncio.sleep(1.0)
            progress.update(task, completed=100, description="Enrichment complete")
        
        return {"enriched_count": 12, "threat_indicators": 3}
    
    async def find_similar_cases_step(**kwargs):
        progress = kwargs.get('progress')
        task = kwargs.get('task')
        
        if progress:
            progress.update(task, completed=50, description="Searching similar cases...")
            await asyncio.sleep(1.2)
            progress.update(task, completed=100, description="Search complete")
        
        return {"similar_cases": 4, "top_similarity": 0.87}
    
    async def build_timeline_step(**kwargs):
        progress = kwargs.get('progress')
        task = kwargs.get('task')
        
        if progress:
            progress.update(task, completed=40, description="Building timeline...")
            await asyncio.sleep(0.9)
            progress.update(task, completed=100, description="Timeline ready")
        
        return {"timeline_events": 23, "duration_hours": 6}
    
    steps = [
        WorkflowStep(
            step_id="analyze_case",
            name="Analyze Case",
            description="Perform initial case analysis",
            action_func=analyze_case_step,
            hotkey="a",
            estimated_duration_ms=2000
        ),
        WorkflowStep(
            step_id="enrich_entities",
            name="Enrich Entities", 
            description="Enrich case entities with threat intelligence",
            action_func=enrich_entities_step,
            hotkey="e",
            prerequisites=["analyze_case"],
            estimated_duration_ms=3000
        ),
        WorkflowStep(
            step_id="find_similar_cases",
            name="Find Similar Cases",
            description="Search for related cases",
            action_func=find_similar_cases_step,
            hotkey="s",
            prerequisites=["analyze_case"],
            estimated_duration_ms=2500
        ),
        WorkflowStep(
            step_id="build_timeline",
            name="Build Timeline",
            description="Construct event timeline",
            action_func=build_timeline_step,
            hotkey="t",
            prerequisites=["analyze_case", "enrich_entities"],
            estimated_duration_ms=1500
        )
    ]
    
    return AnalystWorkflow(
        workflow_id="case_investigation",
        name="Case Investigation Workflow",
        description="Standard workflow for investigating security cases",
        steps=steps,
        shortcuts={"a": "analyze_case", "e": "enrich_entities", "s": "find_similar_cases", "t": "build_timeline"},
        auto_advance=False,
        progress_tracking=True
    )


# Main CLI entry point
@click.group()
def cli():
    """SOC Platform CLI - Enhanced Developer and Analyst Experience."""
    pass


@cli.command()
@click.option('--interactive', '-i', is_flag=True, help='Start interactive session')
@click.option('--workflow', '-w', help='Start specific workflow')
def analyst(interactive, workflow):
    """Start analyst interface."""
    interface = FastAnalystInterface()
    
    # Register workflows
    interface.register_workflow(create_case_investigation_workflow())
    
    if interactive:
        asyncio.run(interface.start_interactive_session())
    elif workflow:
        asyncio.run(interface.start_workflow(workflow))
    else:
        interface.display_welcome_screen()


@cli.command()
@click.option('--workspace', '-w', required=True, help='Workspace path')
def dev_setup(workspace):
    """Setup development workspace."""
    toolkit = DeveloperToolkit()
    toolkit.create_development_workspace(workspace)


@cli.command()
@click.option('--config', '-c', required=True, help='Configuration file path')
def validate_config(config):
    """Validate configuration file."""
    manager = ConfigurationManager()
    valid = manager.validate_config(config)
    if not valid:
        click.echo("Configuration validation failed", err=True)
        exit(1)
    click.echo("Configuration is valid")


@cli.command()
@click.option('--modules', '-m', multiple=True, required=True, help='Modules to document')
@click.option('--output', '-o', default='docs/api', help='Output directory')
def generate_docs(modules, output):
    """Generate API documentation."""
    doc_gen = DocumentationGenerator()
    doc_gen.generate_api_docs(list(modules), output)


@cli.command()
def performance_report():
    """Show performance profiling report."""
    profiler = PerformanceProfiler()
    profiler.display_performance_report()


if __name__ == "__main__":
    cli()