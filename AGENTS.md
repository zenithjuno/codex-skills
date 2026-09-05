<!-- grill-to-build:exam-parallel-workflow:start -->
## Active staged build: exam-parallel-workflow

- Control file: `docs/plans/active/exam-parallel-workflow/BUILD-CONTROL-exam-parallel-workflow.md`
- Begin build work by reading that control file first.
- Read only the current plan stage and its named contract sections.
- At stage close and on every approved CHG, reconcile the registered current-truth surfaces: state what became true AND what stopped being true.
- Never bulk-read the control home's `history/` or discover controls by glob.
- Edit only paths declared by the current stage; classify extra paths first. **Never touch `thai-math-docx/` or any other skill folder** (DEC-010).
- Run the stage's declared focused and regression checks before its PASS GATE.
- Checkpoint only managed paths after the stage passes, and only on explicit user ask.
<!-- grill-to-build:exam-parallel-workflow:end -->
