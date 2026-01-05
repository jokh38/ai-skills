#!/usr/bin/env python3
"""
Code Review Analyzer - Main Entry Point

Orchestrates tree-sitter, ctags, and ripgrep analysis to generate
comprehensive codebase structure and insights.

Usage:
    python run_code_review.py --workspace /path/to/project --pattern "**/*.py"
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from treesitter_analyzer import TreeSitterAnalyzer
from ctags_indexer import CtagsIndexer
from ripgrep_searcher import RipgrepSearcher
from astgrep_analyzer import AstGrepAnalyzer
from ugrep_searcher import UgrepSearcher
from toon_serializer import ToonSerializer


class CodeReviewAnalyzer:
    """Main analyzer that orchestrates all analysis tools."""

    def __init__(
        self,
        workspace: str,
        pattern: str = "**/*.py",
        language: str = "python",
        user_request: str = "",
        verbose: bool = False,
        max_files: int = 20,
        max_hotspots: int = 15,
        max_apis: int = 20,
        max_search_results: int = 100,
        enable_astgrep: bool = True,
        enable_ugrep: bool = True,
    ):
        """
        Initialize code review analyzer.

        Args:
            workspace: Project directory to analyze
            pattern: File glob pattern to analyze
            language: Primary programming language
            user_request: Original user request for context
            verbose: Enable verbose logging
            max_files: Maximum number of files to include in results
            max_hotspots: Maximum number of complexity hotspots
            max_apis: Maximum number of public APIs to list
            max_search_results: Maximum search results per pattern
            enable_astgrep: Enable ast-grep structural analysis (optional)
            enable_ugrep: Enable ugrep advanced search (optional)
        """
        self.workspace = Path(workspace).resolve()
        self.pattern = pattern
        self.language = language
        self.user_request = user_request
        self.verbose = verbose
        self.max_files = max_files
        self.max_hotspots = max_hotspots
        self.max_apis = max_apis
        self.max_search_results = max_search_results
        self.enable_astgrep = enable_astgrep
        self.enable_ugrep = enable_ugrep

        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
        )

        self.logger = logging.getLogger(__name__)

        # Initialize analyzers
        self.tree_analyzer = TreeSitterAnalyzer(str(self.workspace))
        self.ctags_indexer = CtagsIndexer(str(self.workspace))
        self.rg_searcher = RipgrepSearcher(str(self.workspace))

        # New: ast-grep analyzer (optional)
        if enable_astgrep:
            try:
                self.ast_grep = AstGrepAnalyzer(str(self.workspace))
                self.has_astgrep = self.ast_grep.available
            except Exception:
                self.has_astgrep = False
                self.logger.warning(
                    "ast-grep not available, skipping structural analysis"
                )
        else:
            self.has_astgrep = False
            self.logger.info("ast-grep disabled by user configuration")

        # New: ugrep searcher (optional)
        if enable_ugrep:
            try:
                self.ugrep_searcher = UgrepSearcher(str(self.workspace))
                self.has_ugrep = self.ugrep_searcher.available
            except Exception:
                self.has_ugrep = False
                self.logger.warning("ugrep not available, skipping advanced search")
        else:
            self.has_ugrep = False
            self.logger.info("ugrep disabled by user configuration")

        # Results storage
        self.results = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "workspace": str(self.workspace),
            "user_request": user_request,
            "codebase_summary": {},
            "structure_analysis": {},
            "definition_index": {},
            "pattern_findings": {},
            "code_quality": {},
            "recommendations": [],
            "integration_points": [],
        }

    def _omit_empty(self, data: Dict) -> Dict:
        """Remove keys with empty values ([], {}, '', None) from dict."""
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                cleaned = self._omit_empty(value)
                if cleaned:  # Only include non-empty dicts
                    result[key] = cleaned
            elif isinstance(value, list):
                if value:  # Only include non-empty lists
                    result[key] = value
            elif value is not None and value != "":
                result[key] = value
        return result

    def analyze(self) -> Dict[str, Any]:
        """
        Run complete analysis pipeline.

        Returns:
            Dictionary with all analysis results
        """
        self.logger.info(f"Starting code review analysis of {self.workspace}")
        self.logger.info(f"Pattern: {self.pattern}, Language: {self.language}")

        # Check if workspace exists and has code
        if not self._validate_workspace():
            self.logger.error("Invalid workspace or no code to analyze")
            return self.results

        # Stage 1: Tree-sitter Analysis
        self.logger.info("=== Stage 1: Tree-sitter Analysis ===")
        tree_results = self._run_tree_sitter_analysis()

        # Stage 2: Ctags Indexing
        self.logger.info("=== Stage 2: Ctags Indexing ===")
        ctags_results = self._run_ctags_analysis()

        # Stage 3: Ripgrep Pattern Search
        self.logger.info("=== Stage 3: Ripgrep Pattern Search ===")
        rg_results = self._run_ripgrep_analysis(tree_results)

        # Stage 3.5: ast-grep Structural Patterns (optional)
        astgrep_results = {}
        if self.has_astgrep:
            self.logger.info("=== Stage 3.5: ast-grep Structural Analysis ===")
            astgrep_results = self._run_astgrep_analysis()

        # Stage 3.6: ugrep Advanced Search (optional)
        ugrep_results = {}
        if self.has_ugrep:
            self.logger.info("=== Stage 3.6: ugrep Advanced Search ===")
            ugrep_results = self._run_ugrep_analysis()

        # Stage 4: Synthesis
        self.logger.info("=== Stage 4: Synthesis ===")
        self._synthesize_results(
            tree_results, ctags_results, rg_results, astgrep_results, ugrep_results
        )

        self.logger.info("Analysis complete!")
        return self.results

    def _validate_workspace(self) -> bool:
        """Validate that workspace exists and contains code."""
        if not self.workspace.exists():
            self.logger.error(f"Workspace does not exist: {self.workspace}")
            return False

        if not self.workspace.is_dir():
            self.logger.error(f"Workspace is not a directory: {self.workspace}")
            return False

        # Check for code files
        files = list(self.workspace.glob(self.pattern))
        if not files:
            self.logger.warning(f"No files matching pattern {self.pattern}")
            # This is a greenfield project - skip analysis
            self.results["codebase_summary"]["note"] = (
                "Greenfield project - no existing code to analyze"
            )
            return False

        self.logger.info(f"Found {len(files)} files to analyze")
        return True

    def _run_tree_sitter_analysis(self) -> Dict[str, Any]:
        """Run tree-sitter analysis."""
        try:
            results = self.tree_analyzer.analyze_directory(self.pattern)
            self.logger.info(
                f"Tree-sitter found {results.get('total_functions', 0)} functions, "
                f"{results.get('total_classes', 0)} classes"
            )
            return results
        except Exception as e:
            self.logger.error(f"Tree-sitter analysis failed: {e}")
            return {}

    def _run_ctags_analysis(self) -> Dict[str, Any]:
        """Run ctags analysis."""
        try:
            if self.ctags_indexer.generate_tags(self.pattern):
                summary = self.ctags_indexer.get_summary()
                self.logger.info(f"Ctags indexed {summary['total_symbols']} symbols")
                return {
                    "summary": summary,
                    "public_apis": self.ctags_indexer.get_public_apis(),
                    "internal_functions": self.ctags_indexer.get_internal_functions(),
                }
            else:
                self.logger.warning("Ctags indexing failed")
                return {}
        except Exception as e:
            self.logger.error(f"Ctags analysis failed: {e}")
            return {}

    def _run_ripgrep_analysis(self, tree_results: Dict) -> Dict[str, Any]:
        """Run ripgrep analysis."""
        try:
            results = {
                "test_files": self.rg_searcher.get_test_files(),
                "error_patterns": self.rg_searcher.search_error_patterns(self.language),
                "technical_debt": self.rg_searcher.search_todo_fixme(),
                "security_patterns": self.rg_searcher.search_security_patterns(),
            }

            # Prefer AST-based import graph from tree-sitter if available
            if (
                tree_results.get("import_graph")
                and tree_results["import_graph"].get("source") == "ast"
            ):
                results["import_graph"] = tree_results["import_graph"]
                self.logger.info("Using AST-based import graph from tree-sitter")
            else:
                # Fallback to regex-based ripgrep import graph
                results["import_graph"] = self.rg_searcher.get_import_graph(
                    self.language
                )
                self.logger.info("Using regex-based import graph from ripgrep")

            self.logger.info(
                f"Ripgrep found {results['test_files']['count']} test files, "
                f"{results['technical_debt']['total_count']} TODO/FIXME items"
            )
            return results
        except Exception as e:
            self.logger.error(f"Ripgrep analysis failed: {e}")
            return {}

    def _run_astgrep_analysis(self) -> Dict[str, Any]:
        """Run ast-grep structural pattern analysis."""
        try:
            patterns = self.ast_grep.find_common_patterns(self.language)

            pattern_count = sum(len(matches) for matches in patterns.values())
            self.logger.info(
                f"ast-grep found {pattern_count} pattern matches across {len(patterns)} patterns"
            )

            return {
                "structural_patterns": {
                    "tool": "ast-grep",
                    "patterns": patterns,
                    "total_matches": pattern_count,
                }
            }
        except Exception as e:
            self.logger.error(f"ast-grep analysis failed: {e}")
            return {}

    def _run_ugrep_analysis(self) -> Dict[str, Any]:
        """Run ugrep advanced search analysis."""
        try:
            results = {
                "archive_search": [],
                "fuzzy_search": [],
                "documentation_search": {},
            }

            # Search for common patterns in archives
            archive_matches = self.ugrep_searcher.search_archives(
                "TODO", max_results=20
            )
            if archive_matches:
                results["archive_search"] = archive_matches

            # Fuzzy search for common typos
            fuzzy_matches = self.ugrep_searcher.fuzzy_search(
                "functon", distance=2, max_results=20
            )
            if fuzzy_matches:
                results["fuzzy_search"] = fuzzy_matches

            # Documentation search (enhanced feature for Option B)
            doc_keywords = [
                "API",
                "usage",
                "example",
                "tutorial",
                "guide",
                "configuration",
            ]
            doc_findings = self.ugrep_searcher.search_documentation(
                doc_keywords, max_results=10
            )
            if doc_findings.get("total", 0) > 0:
                results["documentation_search"] = doc_findings

            self.logger.info(
                f"ugrep found {len(archive_matches)} archive matches, "
                f"{len(fuzzy_matches)} fuzzy matches, "
                f"{doc_findings.get('total', 0)} documentation findings"
            )

            return results

        except Exception as e:
            self.logger.error(f"ugrep analysis failed: {e}")
            return {}

    def _synthesize_results(
        self,
        tree_results: Dict,
        ctags_results: Dict,
        rg_results: Dict,
        astgrep_results: Dict = {},
        ugrep_results: Dict = {},
    ):
        """Synthesize all results into final structure."""

        # Codebase Summary (always include - core metadata)
        self.results["codebase_summary"] = {
            "total_files": len(tree_results.get("files", [])),
            "total_functions": tree_results.get("total_functions", 0),
            "total_classes": tree_results.get("total_classes", 0),
            "total_symbols": ctags_results.get("summary", {}).get("total_symbols", 0),
            "primary_language": self.language,
        }

        # Structure Analysis
        structure = {
            "files": tree_results.get("files", [])[: self.max_files],
            "design_patterns": self._identify_design_patterns(tree_results, rg_results),
            "entry_points": tree_results.get("entry_points", []),
            "file_purposes": tree_results.get("file_purposes", []),
            "key_abstractions": self._extract_key_abstractions(tree_results),
        }
        self.results["structure_analysis"] = self._omit_empty(structure)

        # Definition Index
        definition = {
            "public_apis": ctags_results.get("public_apis", [])[: self.max_apis],
            "internal_functions": ctags_results.get("internal_functions", [])[
                : self.max_hotspots
            ],
            "symbol_categories": ctags_results.get("summary", {}).get("categories", {}),
        }
        self.results["definition_index"] = self._omit_empty(definition)

        # Pattern Findings
        patterns = {
            "existing_tests": rg_results.get("test_files", {}),
            "error_handling": rg_results.get("error_patterns", {}),
            "technical_debt": rg_results.get("technical_debt", {}),
            "import_graph": rg_results.get("import_graph", {}),
            "call_graph": tree_results.get("call_graph", []),
        }

        # Add ast-grep results if available and non-empty
        if astgrep_results and astgrep_results.get("structural_patterns"):
            patterns["structural_patterns"] = astgrep_results["structural_patterns"]

        # Add ugrep results if available and non-empty
        if ugrep_results:
            cleaned_ugrep = self._omit_empty(ugrep_results)
            if cleaned_ugrep:
                patterns["ugrep_findings"] = cleaned_ugrep

        self.results["pattern_findings"] = self._omit_empty(patterns)

        # Code Quality
        quality = {
            "complexity_hotspots": tree_results.get("complexity_hotspots", [])[
                : min(10, self.max_hotspots)
            ],
            "security_concerns": self._format_security_concerns(
                rg_results.get("security_patterns", {})
            ),
            "test_coverage_estimate": self._estimate_test_coverage(
                tree_results, rg_results
            ),
        }
        self.results["code_quality"] = self._omit_empty(quality)

        # Recommendations (keep even if empty - provides feedback)
        self.results["recommendations"] = self._generate_recommendations(
            tree_results, ctags_results, rg_results
        )

        # Integration Points (only include if non-empty)
        integration = self._identify_integration_points(rg_results)
        if integration:
            self.results["integration_points"] = integration
        else:
            # Remove key entirely if empty
            self.results.pop("integration_points", None)

    def _identify_design_patterns(
        self, tree_results: Dict, rg_results: Dict
    ) -> List[Dict]:
        """Identify design patterns used in codebase."""
        patterns = []

        # Simple pattern detection based on class/function names
        all_files = tree_results.get("files", [])

        for file_info in all_files:
            classes = file_info.get("classes", [])

            for cls in classes:
                name = cls.get("name", "")

                # Singleton pattern
                if "singleton" in name.lower() or name.endswith("Manager"):
                    patterns.append(
                        {
                            "pattern": "Singleton",
                            "location": f"{file_info['path']}:{cls.get('line', 0)}",
                            "element": name,
                        }
                    )

                # Factory pattern
                elif "factory" in name.lower() or name.endswith("Factory"):
                    patterns.append(
                        {
                            "pattern": "Factory",
                            "location": f"{file_info['path']}:{cls.get('line', 0)}",
                            "element": name,
                        }
                    )

                # Observer pattern
                elif "observer" in name.lower() or "listener" in name.lower():
                    patterns.append(
                        {
                            "pattern": "Observer",
                            "location": f"{file_info['path']}:{cls.get('line', 0)}",
                            "element": name,
                        }
                    )

        return patterns[: min(10, self.max_hotspots)]

    def _extract_key_abstractions(self, tree_results: Dict) -> List[Dict]:
        """
        Extract key abstractions (main classes with responsibilities).

        Returns list of {class, file, responsibility, key_methods}.
        """
        abstractions = []

        for file_info in tree_results.get("files", []):
            file_path = file_info.get("path", "")
            docstring = file_info.get("docstring", "")

            for cls in file_info.get("classes", []):
                name = cls.get("name", "")
                methods = cls.get("methods", [])

                # Infer responsibility from class name or file docstring
                responsibility = self._infer_responsibility(name, docstring)

                # Get key public methods (non-dunder, non-private)
                key_methods = [
                    m
                    for m in methods
                    if not m.startswith("_") or m.startswith("__init__")
                ][:5]

                abstractions.append(
                    {
                        "class": name,
                        "file": file_path,
                        "responsibility": responsibility,
                        "key_methods": ",".join(key_methods) if key_methods else "-",
                    }
                )

        # Sort by likely importance (classes with more methods first)
        return abstractions[: self.max_apis]

    def _infer_responsibility(self, class_name: str, docstring: str) -> str:
        """Infer class responsibility from name or docstring."""
        # Use docstring if available
        if docstring:
            return docstring[:60]

        # Infer from class name patterns
        name_lower = class_name.lower()

        if "analyzer" in name_lower:
            return "Analyzes code or data"
        elif "serializer" in name_lower:
            return "Serializes data to output format"
        elif "parser" in name_lower:
            return "Parses input data"
        elif "handler" in name_lower:
            return "Handles events or requests"
        elif "manager" in name_lower:
            return "Manages resources or state"
        elif "factory" in name_lower:
            return "Creates instances"
        elif "builder" in name_lower:
            return "Builds complex objects"
        elif "service" in name_lower:
            return "Provides business logic"
        elif "repository" in name_lower:
            return "Data access layer"
        elif "controller" in name_lower:
            return "Handles request routing"
        elif "validator" in name_lower:
            return "Validates data"
        elif "indexer" in name_lower:
            return "Indexes data for lookup"
        elif "searcher" in name_lower:
            return "Searches through data"
        else:
            return f"{class_name} implementation"

    def _format_security_concerns(self, security_data: Dict) -> List[Dict]:
        """Format security findings."""
        concerns = []

        for finding in security_data.get("findings", []):
            concerns.append(
                {
                    "severity": finding["severity"],
                    "type": finding["type"].replace("_", " ").title(),
                    "location": f"{finding['file']}:{finding['line']}",
                    "recommendation": self._get_security_recommendation(
                        finding["type"]
                    ),
                }
            )

        return concerns[: self.max_hotspots]

    def _get_security_recommendation(self, issue_type: str) -> str:
        """Get recommendation for security issue."""
        recommendations = {
            "sql_injection_risk": "Use parameterized queries or ORM",
            "hardcoded_secrets": "Move secrets to environment variables or secret manager",
            "eval_usage": "Avoid eval(); use safer alternatives like ast.literal_eval",
            "pickle_usage": "Use safer serialization like JSON; validate pickle sources",
            "shell_injection": "Use subprocess with list arguments, not string concatenation",
        }
        return recommendations.get(issue_type, "Review and fix security issue")

    def _estimate_test_coverage(self, tree_results: Dict, rg_results: Dict) -> str:
        """Estimate test coverage based on test files vs source files."""
        total_files = len(tree_results.get("files", []))
        test_count = rg_results.get("test_files", {}).get("count", 0)

        if total_files == 0:
            return "Unknown"

        ratio = test_count / total_files if total_files > 0 else 0

        if ratio >= 0.8:
            return "High (estimated >80%)"
        elif ratio >= 0.5:
            return "Medium (estimated 50-80%)"
        elif ratio >= 0.2:
            return "Low (estimated 20-50%)"
        else:
            return "Very Low (estimated <20%)"

    def _generate_recommendations(
        self, tree_results: Dict, ctags_results: Dict, rg_results: Dict
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Complexity recommendations
        hotspots = tree_results.get("complexity_hotspots", [])
        if len(hotspots) > 5:
            recommendations.append(
                f"Refactor {len(hotspots)} complex functions (complexity >10) to improve maintainability"
            )

        # Test coverage recommendations
        test_count = rg_results.get("test_files", {}).get("count", 0)
        total_files = len(tree_results.get("files", []))
        if total_files > 0 and test_count / total_files < 0.5:
            recommendations.append(
                f"Increase test coverage: only {test_count} test files for {total_files} source files"
            )

        # Technical debt recommendations
        debt_count = rg_results.get("technical_debt", {}).get("total_count", 0)
        if debt_count > 10:
            recommendations.append(
                f"Address {debt_count} TODO/FIXME items to reduce technical debt"
            )

        # Security recommendations
        security_issues = rg_results.get("security_patterns", {}).get("total_issues", 0)
        if security_issues > 0:
            recommendations.append(
                f"Fix {security_issues} potential security issues identified"
            )

        # Default recommendation
        if not recommendations:
            recommendations.append(
                "Codebase appears healthy. Continue following best practices."
            )

        return recommendations

    def _identify_integration_points(self, rg_results: Dict) -> List[Dict]:
        """Identify external integration points."""
        integration_points = []

        # Check imports for common frameworks/services
        external_deps = rg_results.get("import_graph", {}).get(
            "external_dependencies", []
        )

        # Database integrations
        db_libs = {"sqlalchemy", "pymongo", "psycopg2", "mysql", "redis"}
        db_found = [
            dep for dep in external_deps if any(db in dep.lower() for db in db_libs)
        ]
        if db_found:
            integration_points.append(
                {
                    "type": "Database",
                    "libraries": db_found[:5],
                }
            )

        # Web frameworks
        web_libs = {"flask", "django", "fastapi", "express", "react", "vue"}
        web_found = [
            dep for dep in external_deps if any(web in dep.lower() for web in web_libs)
        ]
        if web_found:
            integration_points.append(
                {
                    "type": "Web Framework",
                    "libraries": web_found[:5],
                }
            )

        # External APIs
        api_libs = {"requests", "httpx", "axios", "boto3", "stripe"}
        api_found = [
            dep for dep in external_deps if any(api in dep.lower() for api in api_libs)
        ]
        if api_found:
            integration_points.append(
                {
                    "type": "External APIs",
                    "libraries": api_found[:5],
                }
            )

        return integration_points

    def cleanup(self):
        """Cleanup temporary files."""
        try:
            self.ctags_indexer.cleanup()
        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")
