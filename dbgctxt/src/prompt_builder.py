import sys
from datetime import datetime
from pathlib import Path
from typing import List, Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))

from utils.data_structures import RichContext, FixPayload, RootCauseCorrelation, FixSuggestion

CONTEXT_WINDOW_LINES = 50


class ToonPayloadGenerator:
    
    def construct_fix_request(
        self,
        rich_failures: List[RichContext],
        root_cause_analysis: Optional[List[RootCauseCorrelation]] = None,
        fix_suggestions: Optional[List[FixSuggestion]] = None
    ) -> str:
        payload = FixPayload(
            timestamp=datetime.now().isoformat(),
            status="needs_fix",
            message="Test failures detected requiring code repair.",
            total_failures=len(rich_failures),
            contexts=rich_failures,
            root_cause_analysis=self._format_root_cause_analysis(root_cause_analysis),
            fix_suggestions=self._format_fix_suggestions(fix_suggestions)
        )
        
        return self._serialize_toon(payload)
    
    def construct_success_notice(self) -> str:
        payload = FixPayload(
            timestamp=datetime.now().isoformat(),
            status="success",
            message="All tests passed.",
            total_failures=0,
            contexts=[]
        )
        
        return self._serialize_toon(payload)
    
    def _serialize_toon(self, payload: FixPayload) -> str:
        lines = []
        
        lines.append(f'timestamp: "{payload.timestamp}"')
        lines.append(f'status: "{payload.status}"')
        lines.append(f'message: "{payload.message}"')
        lines.append(f'total_failures: {payload.total_failures}')
        
        if payload.root_cause_analysis:
            lines.append('')
            lines.append('root_cause_analysis:')
            for rca in payload.root_cause_analysis:
                lines.append(f'  {{failure_id: "{rca["failure_id"]}", primary_cause: "{rca["primary_cause"]}", confidence: {rca["confidence"]}}}')
        
        if payload.fix_suggestions:
            lines.append('')
            lines.append('fix_suggestions:')
            lines.append(f'  [{len(payload.fix_suggestions)}] {{priority, action, effort, confidence}}')
            for fix in payload.fix_suggestions:
                action = fix['action'].replace('"', '\\"')
                lines.append(f'  {fix["priority"]} | "{action}" | {fix["effort"]} | {fix["confidence"]}')
        
        if payload.contexts:
            lines.append('')
            lines.append(f'[{len(payload.contexts)}] {{test_id, error_type, source_file, line_number, error_message}}')
            
            for ctx in payload.contexts:
                failure = ctx.failure
                test_id = failure.test_id.replace('"', '\\"')
                error_type = failure.error_type.replace('"', '\\"')
                source_file = failure.source_file.replace('"', '\\"')
                line_number = failure.line_number
                error_message = failure.error_message.replace('"', '\\"').replace('\n', '\\n')
                
                lines.append(f'{test_id} | {error_type} | {source_file} | {line_number} | {error_message}')
                
                error_class = ctx.error_class
                
                if error_class == 'import':
                    lines.extend(self._format_import_context(ctx))
                elif error_class == 'runtime':
                    lines.extend(self._format_runtime_context(ctx))
                elif error_class == 'assertion':
                    lines.extend(self._format_assertion_context(ctx))
                elif error_class == 'test_infra':
                    lines.extend(self._format_test_infra_context(ctx))
                elif error_class == 'config':
                    lines.extend(self._format_config_context(ctx))
                elif error_class == 'lint':
                    lines.extend(self._format_lint_context(ctx))
                else:
                    lines.extend(self._format_default_context(ctx))
                
                lines.append('')
        
        return '\n'.join(lines)
    
    def _format_import_context(self, ctx: RichContext) -> List[str]:
        lines = []
        lines.append('')
        lines.append('# === TIER 1: Import Errors ===')
        lines.append('error_class: "import"')
        
        if ctx.import_chain:
            lines.append('')
            lines.append('import_chain:')
            for item in ctx.import_chain:
                resolved = 'True' if item.get('resolved') else 'False'
                lines.append('  [{module, import_file, resolved, error}]')
                lines.append(f'  {item.get("module", "")} | {item.get("import_file", "")} | {resolved} | {item.get("error", "")} | ')
        
        if ctx.search_paths:
            lines.append('')
            lines.append('module_search_paths:')
            for item in ctx.search_paths:
                exists = 'True' if item.get('exists') else 'False'
                lines.append('  [{path, exists}]')
                lines.append(f'  {item.get("path", "")} | {exists} | ')
        
        return lines
    
    def _format_runtime_context(self, ctx: RichContext) -> List[str]:
        lines = []
        lines.append('')
        lines.append('# === TIER 2: Runtime Errors ===')
        lines.append('error_class: "runtime"')
        
        if ctx.stack_trace:
            lines.append('')
            lines.append('stack_trace:')
            for item in ctx.stack_trace:
                lines.append('  [{file, line, function, code_snippet}]')
                lines.append(f'  {item.get("file", "")} | {item.get("line", "")} | {item.get("function", "")} | {item.get("code_snippet", "")} | ')
        
        lines.append('')
        lines.append('error_location:')
        lines.append(f'  {{function: "{self._get_function_name(ctx.stack_trace)}", line: {ctx.failure.line_number}}}')
        
        lines.append('')
        lines.append('--- RELATED CODE ---')
        code_snippet = self._extract_code_context(ctx.related_code, ctx.failure.line_number)
        lines.append(code_snippet)
        lines.append('--- END CODE ---')
        
        return lines
    
    def _format_assertion_context(self, ctx: RichContext) -> List[str]:
        lines = []
        lines.append('')
        lines.append('# === TIER 3: Assertion Errors ===')
        lines.append('error_class: "assertion"')
        
        if ctx.expected_vs_actual:
            lines.append('')
            lines.append('expected_vs_actual:')
            eva = ctx.expected_vs_actual
            lines.append(f'  {{expected: "{eva.get("expected", "")}", actual: "{eva.get("actual", "")}"}}')
        
        if ctx.call_context:
            lines.append('')
            lines.append('call_context:')
            cc = ctx.call_context
            lines.append(f'  {{function: "{cc.get("function", "")}", parameters: "{cc.get("parameters", "")}"}}')
        
        lines.append('')
        lines.append('--- RELATED CODE ---')
        code_snippet = self._extract_code_context(ctx.related_code, ctx.failure.line_number)
        lines.append(code_snippet)
        lines.append('--- END CODE ---')
        
        return lines
    
    def _format_test_infra_context(self, ctx: RichContext) -> List[str]:
        lines = []
        lines.append('')
        lines.append('# === TIER 4: Test Infrastructure Errors ===')
        lines.append('error_class: "test_infra"')
        
        if ctx.missing_resources:
            lines.append('')
            lines.append('missing_resources:')
            for item in ctx.missing_resources:
                lines.append('  [{path, expected_usage}]')
                lines.append(f'  {item.get("path", "")} | {item.get("expected_usage", "")} | ')
        
        lines.append('')
        lines.append('--- RELATED CODE ---')
        code_snippet = self._extract_code_context(ctx.related_code, ctx.failure.line_number)
        lines.append(code_snippet)
        lines.append('--- END CODE ---')
        
        return lines
    
    def _format_config_context(self, ctx: RichContext) -> List[str]:
        lines = []
        lines.append('')
        lines.append('# === TIER 5: Configuration/Environment Errors ===')
        lines.append('error_class: "config"')
        
        if ctx.config_state:
            lines.append('')
            lines.append('config_state:')
            cs = ctx.config_state
            lines.append(f'  {{provider: "{cs.get("provider", "")}", model: "{cs.get("model", "")}", error: "{cs.get("error", "")}"}}')
        
        if ctx.missing_vars:
            lines.append('')
            lines.append('missing_vars:')
            lines.append(f'  [{", ".join(ctx.missing_vars)}]')
        
        return lines
    
    def _format_lint_context(self, ctx: RichContext) -> List[str]:
        lines = []
        lines.append('')
        lines.append('# === TIER 6: Linting/QA Errors ===')
        lines.append('error_class: "lint"')
        
        if ctx.rule_info:
            lines.append('')
            lines.append('rule_info:')
            ri = ctx.rule_info
            lines.append(f'  {{rule_id: "{ri.get("rule_id", "")}", severity: "{ri.get("severity", "")}", description: "{ri.get("description", "")}"}}')
        
        return lines
    
    def _format_default_context(self, ctx: RichContext) -> List[str]:
        lines = []
        lines.append('')
        lines.append('--- RELATED CODE ---')
        code_snippet = self._extract_code_context(ctx.related_code, ctx.failure.line_number)
        lines.append(code_snippet)
        lines.append('--- END CODE ---')
        return lines
    
    def _get_function_name(self, stack_trace: List[Dict[str, Any]]) -> str:
        if stack_trace:
            return stack_trace[0].get('function', 'unknown')
        return 'unknown'
    
    def _extract_code_context(self, full_code: str, target_line: int) -> str:
        if not full_code:
            return "No code available"
        
        lines = full_code.split('\n')
        
        start_line = max(0, target_line - CONTEXT_WINDOW_LINES // 2)
        end_line = min(len(lines), target_line + CONTEXT_WINDOW_LINES // 2)
        
        context_lines = []
        for i in range(start_line, end_line):
            prefix = ">>> " if (i + 1) == target_line else "    "
            context_lines.append(f"{prefix}{i + 1:4d} | {lines[i]}")
        
        return '\n'.join(context_lines)
    
    def save_payload(self, payload: str, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(payload)
    
    def _format_root_cause_analysis(
        self,
        root_cause_analysis: Optional[List[RootCauseCorrelation]]
    ) -> Optional[List[Dict[str, Any]]]:
        if not root_cause_analysis:
            return None
        
        return [
            {
                'failure_id': rca.failure_id,
                'primary_cause': rca.primary_cause,
                'confidence': rca.confidence,
                'secondary_causes': rca.secondary_causes,
                'evidence': rca.evidence
            }
            for rca in root_cause_analysis
        ]
    
    def _format_fix_suggestions(
        self,
        fix_suggestions: Optional[List[FixSuggestion]]
    ) -> Optional[List[Dict[str, Any]]]:
        if not fix_suggestions:
            return None
        
        return [
            {
                'priority': fix.priority,
                'action': fix.action,
                'effort': fix.effort,
                'confidence': fix.confidence,
                'evidence': fix.evidence
            }
            for fix in fix_suggestions
        ]
