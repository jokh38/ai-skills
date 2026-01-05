
Base context: spec.md, cd_structure.toon
 spec.md: features and functions
 cd_structure.toon: file structure, module lists, import graphs, variables, dependencies

on a specific module, it needs spec_stage1.md and cd_structure_stage1.toon 
TDD (on atomic module, starting by check diff from zgit + new branch)
 red: 
  input: spec_stage1.md and cd_structure_stage1.toon 
  validation1: All files are created compared with cd_structure.toon
  validation2: test code fails not halted by errors. 

 green:
  input: spec_stage1.md and cd_structure_stage1.toon 
  validation: every code should pass the test with properly functioning.

 blue:
  input: spec_stage1.md and cd_structure_stage1.toon 
  validation: merging the feature into the codebase.

In every process, it should guanrantee the following
 No bug (using tools: cdscan, cdqa, dbgctxt)
 TOON format (using tool: pydantic_toon)
 agentic LLM calling + forced workflow (https://github.com/PrefectHQ/ControlFlow)
 semantic error tracking (using vectorwave)


