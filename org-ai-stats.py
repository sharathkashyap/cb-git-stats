#!/usr/bin/env python3
"""
GitHub Repository AI Code Pattern Analyzer
Analyzes a specific GitHub repository to identify AI-generated code
based on structural and stylistic patterns.
"""

import os
import re
import json
import argparse
import ast
import time
import threading
from pathlib import Path
from typing import Dict, List, Tuple, Set
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import subprocess
import requests
from collections import defaultdict, Counter
import multiprocessing
from urllib.parse import urlparse

class AICodePatternAnalyzer:
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or min(multiprocessing.cpu_count(), 8)
        self.start_time = None
        
        # AI-generated code patterns
        self.ai_patterns = {
            'python': {
                'verbose_docstrings': r'"""[\s\S]{200,}?"""',
                'generic_variable_names': r'\b(data|result|output|response|item|element|value|temp|tmp)\b',
                'excessive_type_hints': r':\s*[A-Z][a-zA-Z]*\[.*?\]',
                'boilerplate_error_handling': r'try:\s*\n.*?\nexcept.*?:\s*\n.*?pass',
                'generic_function_names': r'def\s+(process_|handle_|get_|set_|create_|update_|delete_)',
                'redundant_comments': r'#\s*(This|Here|Now|Then|First|Next|Finally)',
                'verbose_logging': r'logging\.(debug|info|warning|error)\(',
                'over_engineered': r'class\s+\w+Factory|class\s+\w+Builder|class\s+\w+Manager',
                'lambda_overuse': r'lambda\s+[^:]*:',
                'unnecessary_comprehensions': r'\[[^\]]{50,}\]'
            },
            'javascript': {
                'async_everywhere': r'async\s+\w+\s*\(',
                'excessive_destructuring': r'const\s*\{[^}]{30,}\}',
                'generic_variable_names': r'\b(data|result|response|item|element|value|temp|output)\b',
                'arrow_function_overuse': r'=>\s*\{[^}]*\}',
                'try_catch_boilerplate': r'try\s*\{[\s\S]*?\}\s*catch\s*\([^)]*\)\s*\{[\s\S]*?\}',
                'console_log_debugging': r'console\.log\(',
                'generic_function_names': r'(handle|process|get|set|create|update|delete)\w*\s*[=:]',
                'unnecessary_spread': r'\.\.\.\w+',
                'promise_chains': r'\.then\s*\([^)]*\)\s*\.then',
                'callback_hell': r'function\s*\([^)]*\)\s*\{[\s\S]*?function\s*\([^)]*\)\s*\{'
            },
            'java': {
                'excessive_abstractions': r'(abstract|interface)\s+\w+',
                'generic_variable_names': r'\b(data|result|response|item|element|value|temp|obj)\b',
                'boilerplate_getters_setters': r'(public\s+\w+\s+get\w+|public\s+void\s+set\w+)',
                'unnecessary_null_checks': r'if\s*\([^)]*!=\s*null\)',
                'verbose_exception_handling': r'catch\s*\([^)]*Exception[^)]*\)',
                'generic_class_names': r'class\s+\w*(Manager|Handler|Processor|Factory|Builder)',
                'redundant_interfaces': r'implements\s+\w+Interface',
                'unnecessary_boxing': r'Integer\.valueOf|Boolean\.valueOf|Double\.valueOf',
                'verbose_constructors': r'public\s+\w+\([^)]{50,}\)',
                'singleton_pattern': r'private\s+static\s+\w+\s+instance'
            },
            'typescript': {
                'excessive_interfaces': r'interface\s+\w+\s*\{[^}]{100,}\}',
                'any_type_overuse': r':\s*any\b',
                'generic_variable_names': r'\b(data|result|response|item|element|value|temp|output)\b',
                'unnecessary_type_assertions': r'as\s+\w+',
                'verbose_generics': r'<[^>]{30,}>',
                'enum_overuse': r'enum\s+\w+\s*\{[^}]*\}',
                'utility_type_overuse': r'Partial<|Required<|Pick<|Omit<'
            },
            'cpp': {
                'unnecessary_templates': r'template\s*<[^>]+>',
                'generic_variable_names': r'\b(data|result|temp|tmp|ptr|val)\b',
                'excessive_namespaces': r'namespace\s+\w+\s*\{',
                'auto_overuse': r'\bauto\s+\w+',
                'smart_pointer_overuse': r'std::(unique_ptr|shared_ptr|weak_ptr)',
                'verbose_constructors': r'\w+::\w+\([^)]{50,}\)',
                'unnecessary_const': r'const\s+\w+\s+const'
            },
            'general': {
                'repetitive_structure': r'(\w+)\s*[=:]\s*\1',
                'magic_numbers': r'\b(100|1000|10000|256|512|1024|999|9999)\b',
                'placeholder_values': r'(TODO|FIXME|XXX|HACK|NOTE)',
                'long_parameter_lists': r'\([^)]{80,}\)',
                'deep_nesting': r'(\s{12,}|\t{4,})',
                'copy_paste_patterns': r'(.{30,})\n[\s\S]*?\1',
                'generic_naming': r'\b(tmp|temp|data|info|util|helper|manager|handler)\b',
                'excessive_comments': r'#.*|//.*|\*.*',
                'long_lines': r'^.{120,}$',
                'empty_catch_blocks': r'(catch|except).*?\{\s*\}|except.*?:\s*pass'
            }
        }
        
        self.results = {
            'repository_info': {},
            'analysis_summary': {
                'total_files': 0,
                'analyzed_files': 0,
                'total_lines': 0,
                'ai_pattern_lines': 0,
                'ai_percentage': 0,
                'analysis_time': 0,
                'files_per_second': 0
            },
            'pattern_details': defaultdict(int),
            'language_breakdown': defaultdict(lambda: {'total_lines': 0, 'ai_pattern_lines': 0, 'files': 0}),
            'file_analysis': [],
            'top_ai_files': []
        }

    def get_repo_info(self, repo_url: str, github_token: str = None) -> Dict:
        """Get repository information from GitHub API."""
        # Parse repo URL to extract owner and name
        if 'github.com' in repo_url:
            parts = repo_url.rstrip('/').split('/')
            owner = parts[-2]
            repo_name = parts[-1].replace('.git', '')
        else:
            return {'name': 'local_repo', 'full_name': 'local/repo'}
        
        if github_token:
            headers = {'Authorization': f'token {github_token}'}
            api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
            
            try:
                response = requests.get(api_url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'name': data.get('name', repo_name),
                        'full_name': data.get('full_name', f"{owner}/{repo_name}"),
                        'description': data.get('description', ''),
                        'language': data.get('language', ''),
                        'size': data.get('size', 0),
                        'stars': data.get('stargazers_count', 0),
                        'forks': data.get('forks_count', 0),
                        'created_at': data.get('created_at', ''),
                        'updated_at': data.get('updated_at', '')
                    }
            except Exception as e:
                print(f"Could not fetch repo info: {e}")
        
        return {'name': repo_name, 'full_name': f"{owner}/{repo_name}"}

    def clone_repository(self, repo_url: str, target_dir: str = None) -> Path:
        """Clone repository to local directory."""
        if target_dir is None:
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            target_dir = f"./temp_analysis/{repo_name}"
        
        repo_path = Path(target_dir)
        
        if repo_path.exists():
            print(f"Repository already exists at {repo_path}")
            try:
                # Try to update
                subprocess.run(['git', 'pull'], cwd=repo_path, capture_output=True, check=True)
                print("Repository updated")
            except subprocess.CalledProcessError:
                print("Could not update repository, using existing version")
        else:
            print(f"Cloning repository to {repo_path}")
            repo_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                subprocess.run(['git', 'clone', repo_url, str(repo_path)], 
                             capture_output=True, check=True)
                print("Repository cloned successfully")
            except subprocess.CalledProcessError as e:
                print(f"Failed to clone repository: {e}")
                return None
        
        return repo_path

    def detect_language(self, file_path: Path) -> str:
        """Detect programming language from file extension."""
        ext_to_lang = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.cc': 'cpp',
            '.cxx': 'cpp',
            '.c': 'cpp',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala'
        }
        
        return ext_to_lang.get(file_path.suffix.lower(), 'general')

    def analyze_python_ast(self, code: str) -> Dict[str, int]:
        """Advanced Python AST analysis for AI patterns."""
        patterns = defaultdict(int)
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                # Overly verbose docstrings
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and ast.get_docstring(node):
                    docstring = ast.get_docstring(node)
                    if len(docstring) > 300:
                        patterns['verbose_docstrings'] += 1
                
                # Generic function names
                if isinstance(node, ast.FunctionDef):
                    generic_prefixes = ['process', 'handle', 'get', 'set', 'create', 'update', 'delete', 'manage']
                    if any(node.name.lower().startswith(prefix) for prefix in generic_prefixes):
                        patterns['generic_function_names'] += 1
                
                # Excessive exception handling
                if isinstance(node, ast.Try) and len(node.handlers) > 2:
                    patterns['excessive_exception_handling'] += 1
                
                # Generic variable names
                if isinstance(node, ast.Name):
                    generic_names = ['data', 'result', 'response', 'item', 'element', 'value', 'temp', 'tmp']
                    if node.id in generic_names:
                        patterns['generic_variable_names'] += 1
                
                # Lambda overuse
                if isinstance(node, ast.Lambda):
                    patterns['lambda_overuse'] += 1
                
                # Nested function definitions (over-engineering)
                if isinstance(node, ast.FunctionDef):
                    nested_functions = [n for n in ast.walk(node) if isinstance(n, ast.FunctionDef) and n != node]
                    if len(nested_functions) > 2:
                        patterns['nested_functions'] += 1
                        
        except SyntaxError:
            pass
            
        return patterns

    def analyze_file_patterns(self, file_path: Path) -> Tuple[int, int, Dict, float]:
        """Analyze a single file for AI patterns."""
        start_time = time.time()
        
        try:
            # Quick file size check
            file_size = file_path.stat().st_size
            if file_size > 10 * 1024 * 1024:  # Skip files > 10MB
                return 0, 0, {}, 0.0
                
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()
        except Exception:
            return 0, 0, {}, 0.0
        
        if not code.strip():
            return 0, 0, {}, 0.0
        
        language = self.detect_language(file_path)
        lines = code.split('\n')
        total_lines = len(lines)
        
        if total_lines < 5:  # Skip very small files
            return total_lines, 0, {}, time.time() - start_time
        
        all_patterns = defaultdict(int)
        
        # Compile and apply patterns
        pattern_sources = []
        if language in self.ai_patterns:
            pattern_sources.extend(self.ai_patterns[language].items())
        pattern_sources.extend(self.ai_patterns['general'].items())
        
        # Single pass regex analysis
        for pattern_name, pattern_regex in pattern_sources:
            try:
                matches = re.findall(pattern_regex, code, re.MULTILINE | re.DOTALL)
                if matches:
                    all_patterns[pattern_name] += len(matches)
            except re.error:
                continue
        
        # Quick complexity metrics
        all_patterns.update(self.analyze_complexity_fast(lines))
        
        # AST analysis for Python (limited to reasonable file sizes)
        if language == 'python' and total_lines < 10000:
            try:
                ast_patterns = self.analyze_python_ast(code)
                for k, v in ast_patterns.items():
                    all_patterns[k] += v
            except:
                pass
        
        # Calculate AI pattern score
        pattern_score = sum(all_patterns.values())
        
        # More sophisticated AI line estimation
        if pattern_score == 0:
            ai_pattern_lines = 0
        elif pattern_score < 5:
            ai_pattern_lines = min(pattern_score, total_lines // 10)
        else:
            # Higher pattern density suggests more AI involvement
            density_factor = min(pattern_score / (total_lines / 100), 0.8)
            ai_pattern_lines = int(total_lines * density_factor)
        
        analysis_time = time.time() - start_time
        return total_lines, ai_pattern_lines, dict(all_patterns), analysis_time

    def analyze_complexity_fast(self, lines: List[str]) -> Dict[str, int]:
        """Fast complexity analysis."""
        patterns = defaultdict(int)
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
                
            # Long lines
            if len(line) > 120:
                patterns['long_lines'] += 1
            
            # Deep nesting
            indent = len(line) - len(line.lstrip())
            if indent > 16:
                patterns['deep_nesting'] += 1
            
            # Excessive comments
            if stripped.startswith('#') or stripped.startswith('//'):
                patterns['excessive_comments'] += 1
        
        return patterns

    def analyze_repository(self, repo_path: Path, use_parallel: bool = True) -> Dict:
        """Analyze repository for AI patterns."""
        print(f"\n🔍 Analyzing repository: {repo_path.name}")
        self.start_time = time.time()
        
        # Reset results
        for key in ['analysis_summary', 'pattern_details', 'language_breakdown', 'file_analysis']:
            if key == 'analysis_summary':
                self.results[key] = {
                    'total_files': 0, 'analyzed_files': 0, 'total_lines': 0,
                    'ai_pattern_lines': 0, 'ai_percentage': 0, 'analysis_time': 0,
                    'files_per_second': 0
                }
            elif key in ['pattern_details', 'language_breakdown']:
                self.results[key] = defaultdict(int) if key == 'pattern_details' else defaultdict(lambda: {'total_lines': 0, 'ai_pattern_lines': 0, 'files': 0})
            else:
                self.results[key] = []
        
        # Collect code files
        code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.cc', '.cxx', '.c', 
            '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.m', '.h'
        }
        
        skip_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'target', 
                    'build', 'dist', '.next', 'coverage', 'vendor'}
        
        files_to_analyze = []
        total_files = 0
        
        for file_path in repo_path.rglob('*'):
            if file_path.is_file():
                total_files += 1
                if (file_path.suffix.lower() in code_extensions and
                    not any(skip_dir in file_path.parts for skip_dir in skip_dirs)):
                    files_to_analyze.append(file_path)
        
        self.results['analysis_summary']['total_files'] = total_files
        print(f"📁 Found {total_files} total files, {len(files_to_analyze)} code files to analyze")
        
        if not files_to_analyze:
            print("❌ No code files found to analyze")
            return self.results
        
        # Process files
        if use_parallel and len(files_to_analyze) > 20:
            print(f"🚀 Using parallel processing with {self.max_workers} workers")
            self._analyze_parallel(files_to_analyze, repo_path)
        else:
            print("📝 Using sequential processing")
            self._analyze_sequential(files_to_analyze, repo_path)
        
        # Finalize results
        self._finalize_results()
        return self.results

    def _analyze_parallel(self, files_to_analyze: List[Path], repo_path: Path):
        """Parallel file analysis."""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.analyze_file_patterns, file_path): file_path 
                      for file_path in files_to_analyze}
            
            for i, future in enumerate(futures):
                if i % 50 == 0 and i > 0:
                    self._print_progress(i, len(files_to_analyze))
                
                try:
                    file_path = futures[future]
                    total_lines, ai_lines, patterns, file_time = future.result(timeout=60)
                    self._process_file_result(file_path, total_lines, ai_lines, patterns, repo_path)
                except Exception as e:
                    print(f"    ❌ Error analyzing {futures[future].name}: {e}")

    def _analyze_sequential(self, files_to_analyze: List[Path], repo_path: Path):
        """Sequential file analysis."""
        for i, file_path in enumerate(files_to_analyze):
            if i % 25 == 0 and i > 0:
                self._print_progress(i, len(files_to_analyze))
            
            total_lines, ai_lines, patterns, file_time = self.analyze_file_patterns(file_path)
            self._process_file_result(file_path, total_lines, ai_lines, patterns, repo_path)

    def _process_file_result(self, file_path: Path, total_lines: int, ai_lines: int, 
                           patterns: Dict, repo_path: Path):
        """Process individual file analysis result."""
        self.results['analysis_summary']['analyzed_files'] += 1
        self.results['analysis_summary']['total_lines'] += total_lines
        self.results['analysis_summary']['ai_pattern_lines'] += ai_lines
        
        language = self.detect_language(file_path)
        self.results['language_breakdown'][language]['total_lines'] += total_lines
        self.results['language_breakdown'][language]['ai_pattern_lines'] += ai_lines
        self.results['language_breakdown'][language]['files'] += 1
        
        for pattern, count in patterns.items():
            self.results['pattern_details'][pattern] += count
        
        # Track individual file results
        relative_path = file_path.relative_to(repo_path)
        ai_percentage = (ai_lines / total_lines * 100) if total_lines > 0 else 0
        
        file_result = {
            'path': str(relative_path),
            'language': language,
            'total_lines': total_lines,
            'ai_pattern_lines': ai_lines,
            'ai_percentage': ai_percentage,
            'patterns_found': len(patterns),
            'top_patterns': sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:3]
        }
        
        self.results['file_analysis'].append(file_result)

    def _print_progress(self, current: int, total: int):
        """Print analysis progress."""
        elapsed = time.time() - self.start_time
        rate = current / elapsed if elapsed > 0 else 0
        eta = (total - current) / rate if rate > 0 else 0
        
        print(f"    📊 Progress: {current}/{total} files "
              f"({current/total*100:.1f}%) - {rate:.1f} files/sec - ETA: {eta:.0f}s")

    def _finalize_results(self):
        """Calculate final statistics."""
        summary = self.results['analysis_summary']
        summary['analysis_time'] = time.time() - self.start_time
        
        if summary['total_lines'] > 0:
            summary['ai_percentage'] = (summary['ai_pattern_lines'] / summary['total_lines']) * 100
        
        if summary['analysis_time'] > 0:
            summary['files_per_second'] = summary['analyzed_files'] / summary['analysis_time']
        
        # Generate top AI files
        self.results['top_ai_files'] = sorted(
            self.results['file_analysis'],
            key=lambda x: x['ai_percentage'],
            reverse=True
        )[:20]

    def generate_report(self) -> str:
        """Generate comprehensive analysis report."""
        report = []
        summary = self.results['analysis_summary']
        repo_info = self.results.get('repository_info', {})
        
        # Header
        report.append("=" * 80)
        report.append("🤖 AI Code Pattern Analysis Report")
        report.append("=" * 80)
        
        # Repository info
        if repo_info:
            report.append(f"📁 Repository: {repo_info.get('full_name', 'Unknown')}")
            if repo_info.get('description'):
                report.append(f"📝 Description: {repo_info['description']}")
            if repo_info.get('language'):
                report.append(f"🔤 Primary Language: {repo_info['language']}")
            if repo_info.get('stars'):
                report.append(f"⭐ Stars: {repo_info['stars']:,}")
            report.append("")
        
        # Analysis summary
        report.append("📊 ANALYSIS SUMMARY")
        report.append("-" * 40)
        report.append(f"Total files in repository: {summary['total_files']:,}")
        report.append(f"Code files analyzed: {summary['analyzed_files']:,}")
        report.append(f"Total lines of code: {summary['total_lines']:,}")
        report.append(f"Lines with AI patterns: {summary['ai_pattern_lines']:,}")
        report.append(f"AI pattern coverage: {summary['ai_percentage']:.2f}%")
        report.append(f"Analysis time: {summary['analysis_time']:.1f} seconds")
        report.append(f"Processing rate: {summary['files_per_second']:.1f} files/second")
        report.append("")
        
        # Language breakdown
        if self.results['language_breakdown']:
            report.append("🔤 LANGUAGE BREAKDOWN")
            report.append("-" * 30)
            sorted_langs = sorted(self.results['language_breakdown'].items(),
                                key=lambda x: x[1]['total_lines'], reverse=True)
            
            for language, data in sorted_langs:
                if data['total_lines'] > 0:
                    pct = (data['ai_pattern_lines'] / data['total_lines']) * 100
                    report.append(f"  {language.capitalize()}: {data['ai_pattern_lines']:,}/"
                                f"{data['total_lines']:,} lines ({pct:.1f}%) - {data['files']} files")
            report.append("")
        
        # Top patterns
        if self.results['pattern_details']:
            report.append("🎯 TOP AI PATTERNS DETECTED")
            report.append("-" * 35)
            top_patterns = sorted(self.results['pattern_details'].items(),
                                key=lambda x: x[1], reverse=True)[:15]
            
            for pattern, count in top_patterns:
                pattern_name = pattern.replace('_', ' ').title()
                report.append(f"  {pattern_name}: {count:,} occurrences")
            report.append("")
        
        # Top AI files
        if self.results['top_ai_files']:
            report.append("📄 FILES WITH HIGHEST AI PATTERN DENSITY")
            report.append("-" * 45)
            
            for file_data in self.results['top_ai_files'][:10]:
                if file_data['ai_percentage'] > 5:  # Only show files with significant AI patterns
                    report.append(f"  {file_data['path']}")
                    report.append(f"    Language: {file_data['language'].capitalize()}")
                    report.append(f"    AI Pattern Coverage: {file_data['ai_percentage']:.1f}%")
                    report.append(f"    Lines: {file_data['ai_pattern_lines']:,}/{file_data['total_lines']:,}")
                    if file_data['top_patterns']:
                        patterns = [f"{p[0].replace('_', ' ')}: {p[1]}" 
                                  for p in file_data['top_patterns'][:2]]
                        report.append(f"    Top Patterns: {', '.join(patterns)}")
                    report.append("")
        
        # Footer
        report.append("=" * 80)
        report.append("ℹ️  ANALYSIS NOTES")
        report.append("-" * 20)
        report.append("• Analysis based on structural and stylistic code patterns")
        report.append("• AI pattern detection uses heuristics and may include false positives")
        report.append("• Higher pattern density suggests potential AI assistance")
        report.append("• Manual review recommended for verification")
        report.append("=" * 80)
        
        return '\n'.join(report)

def main():
    parser = argparse.ArgumentParser(
        description='Analyze a specific GitHub repository for AI code patterns',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze remote repository
  python script.py https://github.com/owner/repo --token your_token
  
  # Analyze local repository
  python script.py /path/to/local/repo
  
  # Generate JSON output
  python script.py https://github.com/owner/repo --json -o results.json
  
  # Use sequential processing
  python script.py /path/to/repo --sequential
        """
    )
    
    parser.add_argument('repository', help='GitHub repository URL or local path')
    parser.add_argument('--token', help='GitHub API token (for remote repositories)')
    parser.add_argument('--output', '-o', help='Output file for the report')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    parser.add_argument('--max-workers', type=int, help='Maximum worker threads')
    parser.add_argument('--sequential', action='store_true', help='Use sequential processing')
    parser.add_argument('--clone-dir', help='Directory to clone repository (default: ./temp_analysis)')
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = AICodePatternAnalyzer(args.max_workers)
    
    # Determine if it's a URL or local path
    repo_input = args.repository
    if repo_input.startswith(('http://', 'https://', 'git@')):
        # Remote repository
        print(f"🌐 Processing remote repository: {repo_input}")
        
        # Get repo info
        repo_info = analyzer.get_repo_info(repo_input, args.token)
        analyzer.results['repository_info'] = repo_info
        
        # Clone repository
        repo_path = analyzer.clone_repository(repo_input, args.clone_dir)
        if not repo_path:
            print("❌ Failed to clone repository")
            return 1
    else:
        # Local repository
        repo_path = Path(repo_input)
        if not repo_path.exists():
            print(f"❌ Local path does not exist: {repo_path}")
            return 1
        
        print(f"📁 Processing local repository: {repo_path}")
        analyzer.results['repository_info'] = {'name': repo_path.name, 'full_name': str(repo_path)}
    
    # Analyze repository
    print(f"\n🚀 Starting analysis...")
    results = analyzer.analyze_repository(repo_path, use_parallel=not args.sequential)
    
    # Generate output
    if args.json:
        output = json.dumps(results, indent=2, default=str)
    else:
        output = analyzer.generate_report()
    
    # Save or print results
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"📄 Report saved to: {args.output}")
    else:
        print(output)
    
    # Cleanup if we cloned the repository
    if repo_input.startswith(('http://', 'https://', 'git@')) and repo_path.exists():
        import shutil
        try:
            shutil.rmtree(repo_path.parent, ignore_errors=True)
            print(f"🧹 Cleaned up temporary files")
        except:
            pass
    
    return 0

if __name__ == "__main__":
    exit(main())