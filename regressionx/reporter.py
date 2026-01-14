from .domain import Case

class MarkdownReporter:
    def __init__(self, filename: str = "report.md"):
        self.filename = filename
        self.results = []

    def add_result(self, case: Case, base_res, cand_res, cmp_result):
        """
        Adds a result to the report.
        Arg types are flexible to allow for both real and mock objects.
        """
        self.results.append({
            "case": case,
            "base": base_res,
            "cand": cand_res,
            "diff": cmp_result
        })

    def generate(self):
        """
        Generates the Markdown report.
        """
        total = len(self.results)
        passed = sum(1 for r in self.results if r["diff"].match)
        failed = total - passed
        
        md = [
            "# RegressionX Report",
            "",
            f"**Total:** {total} | **Passed:** {passed} | **Failed:** {failed}",
            "",
            "## Summary",
            "| Case | Status |",
            "| :--- | :--- |"
        ]
        
        # Summary Table
        for r in self.results:
            case = r["case"]
            diff = r["diff"]
            status_text = "PASSED" if diff.match else "FAILED"
            md.append(f"| {case.name} | {status_text} |")
            
        md.append("")
        md.append("## Failure Details")
        
        has_failures = False
        for r in self.results:
            case = r["case"]
            diff = r["diff"]
            
            if not diff.match:
                has_failures = True
                md.append(f"### {case.name}")
                
                for err in diff.errors:
                    md.append(f"- [Struct] {err}")
                for d in diff.diffs:
                    md.append(f"- [Content] {d}")
                    
                # Also check execution errors
                if r["base"].returncode != 0:
                     md.append(f"- [Exec] Baseline Failed: RG={r['base'].returncode}")
                if r["cand"].returncode != 0:
                     md.append(f"- [Exec] Candidate Failed: RG={r['cand'].returncode}")
                md.append("")
                
        if not has_failures:
            md.append("No failures detected.")
        
        with open(self.filename, "w", encoding="utf-8") as f:
            f.write("\n".join(md))
