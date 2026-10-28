from modules.task_orchestration import TaskManager

class TaskCatalog:
    def __init__(self, db_path=None):
        self.db_path = db_path

    def plan(self, workflow_key, context=None):
        if workflow_key not in TASK_CATALOG:
            raise ValueError(f"Workflow '{workflow_key}' not found in catalog.")

        workflow = TASK_CATALOG[workflow_key]
        manager = TaskManager(db_path=self.db_path)
        track = manager.create_track(
            workflow["name"],
            description=workflow["description"],
            main_goal=workflow["description"],
            context=context,
        )
        tasks = []
        previous_task_id = None
        for title, description, objective, required_tools, validation_criteria in workflow["tasks"]:
            task_id = manager.add_task(
                track["track_id"],
                title,
                description,
                objective,
                dependencies=[previous_task_id] if previous_task_id else [],
                required_tools=required_tools,
                expected_output=objective,
                validation_criteria=validation_criteria,
            )
            tasks.append(
                {
                    "task_id": task_id,
                    "title": title,
                    "description": description,
                    "success": objective,
                    "required_tools": required_tools,
                    "validation_criteria": validation_criteria,
                }
            )
            previous_task_id = task_id

        return {
            "track_id": track["track_id"],
            "name": workflow["name"],
            "status": track["status"],
            "tasks": tasks,
        }

TASK_CATALOG = {
    "business_finder": {
        "name": "OSM Business Finder",
        "description": "Find businesses in a defined area that do not list a website.",
        "tasks": [
            ("Define search scope", "Confirm the business category, geographic area, result limit, and output format.", "The search scope is explicit and approved.", ["planning"], ["Category and area are defined"]),
            ("Search OpenStreetMap", "Query the Overpass API using the approved scope.", "Place results are collected.", ["osm_api"], ["API response is captured"]),
            ("Filter businesses without websites", "Keep only results where no website is listed.", "The candidate list contains only businesses without listed websites.", ["analysis"], ["Website field was checked"]),
            ("Save businesses without websites", "Write the candidate list to a timestamped CSV report.", "A report exists with business details.", ["filesystem"], ["CSV report exists"]),
            ("Verify and report results", "Summarize count and API restrictions.", "The user receives a transparent result summary.", ["verification", "reporting"], ["Count and limitations are reported"]),
        ],
    },
    "project_health_check": {
        "name": "Project Health Check",
        "description": "Inspect the project, dependencies, tests, and diagnostics.",
        "tasks": [
            ("Inspect project structure", "List source files, configuration, and entry points.", "Project structure is documented.", ["filesystem"], ["Relevant files identified"]),
            ("Review dependencies and configuration", "Check requirements and runtime configuration for risks.", "Configuration risks are recorded.", ["analysis"], ["Dependencies reviewed"]),
            ("Run tests and diagnostics", "Execute the available test suite and collect failures.", "Test results are captured.", ["validation"], ["Tests or clear blockers reported"]),
            ("Report project health", "Summarize findings and recommend the highest-value fixes.", "A prioritized health report is ready.", ["reporting"], ["Findings have priorities"]),
        ],
    },
    "run_test_suite": {
        "name": "Run Test Suite",
        "description": "Run tests, classify failures, and report next steps.",
        "tasks": [
            ("Discover tests", "Find the configured test files and commands.", "The test scope is known.", ["filesystem"], ["Test files identified"]),
            ("Execute tests", "Run the focused or full test suite.", "The suite has completed or a blocker is recorded.", ["execution"], ["Command result captured"]),
            ("Classify failures", "Separate product failures, environment issues, and flaky results.", "Failures have actionable categories.", ["analysis"], ["Each failure is classified"]),
            ("Publish test report", "Summarize pass rate, failures, and recommended fixes.", "A concise test report is available.", ["reporting"], ["Report includes next steps"]),
        ],
    },
    "feature_plan": {
        "name": "Feature Plan",
        "description": "Convert a feature request into milestones and implementation steps.",
        "tasks": [
            ("Clarify requirements", "Define scope, constraints, users, and acceptance criteria.", "Requirements are explicit.", ["analysis"], ["Acceptance criteria exist"]),
            ("Design the solution", "Choose the affected modules and data or UI flow.", "A technical approach is documented.", ["architecture"], ["Affected modules identified"]),
            ("Break work into milestones", "Order implementation, testing, and rollout tasks.", "A dependency-aware plan exists.", ["planning"], ["Milestones are ordered"]),
            ("Review plan with user", "Ask for approval before implementation begins.", "The user has approved or changed the plan.", ["feedback"], ["Feedback is recorded"]),
        ],
    },
    "bug_fix": {
        "name": "Bug Fix",
        "description": "Locate a bug, propose a focused patch, and verify the behavior.",
        "tasks": [
            ("Reproduce the bug", "Capture the failing input, behavior, and error output.", "The failure is reproducible or documented as blocked.", ["debugging"], ["Failure evidence exists"]),
            ("Find the root cause", "Trace the controlling code path and identify the defect.", "A root cause is stated.", ["analysis"], ["Root cause is linked to code"]),
            ("Implement the smallest fix", "Change only the code needed to correct the behavior.", "The patch addresses the root cause.", ["implementation"], ["Patch is scoped"]),
            ("Verify the fix", "Run a regression test and check related behavior.", "The regression passes.", ["validation"], ["Regression evidence exists"]),
        ],
    },
    "module_refactor": {
        "name": "Module Refactor",
        "description": "Improve code structure while preserving behavior.",
        "tasks": [
            ("Map current behavior", "Record public functions, callers, and existing tests.", "Behavioral boundaries are known.", ["analysis"], ["Callers identified"]),
            ("Design refactor boundaries", "Choose a small change that reduces complexity.", "The refactor has a clear boundary.", ["architecture"], ["No unrelated scope included"]),
            ("Apply refactor", "Implement the structural change without changing the contract.", "The module is cleaner and compatible.", ["implementation"], ["Public behavior preserved"]),
            ("Run regression checks", "Run tests and inspect the diff for accidental changes.", "Regression checks pass.", ["validation"], ["Tests and review complete"]),
        ],
    },
    "dependency_audit": {
        "name": "Dependency Audit",
        "description": "Review packages for outdated, unused, or risky dependencies.",
        "tasks": [
            ("Inventory dependencies", "Read dependency manifests and imports.", "The dependency inventory is complete.", ["filesystem"], ["Declared and used packages listed"]),
            ("Check versions and compatibility", "Compare versions with the supported runtime and project code.", "Compatibility concerns are recorded.", ["analysis"], ["Runtime compatibility checked"]),
            ("Identify cleanup candidates", "Mark unused, duplicate, or unnecessary dependencies.", "Cleanup candidates are separated from required packages.", ["analysis"], ["Candidates have evidence"]),
            ("Approve dependency changes", "Present proposed upgrades or removals for user approval.", "No package change happens without approval.", ["feedback"], ["Approval decision recorded"]),
        ],
    },
    "documentation_generator": {
        "name": "Documentation Generator",
        "description": "Generate or update documentation from the current codebase.",
        "tasks": [
            ("Inspect public interfaces", "Find entry points, modules, commands, and configuration.", "The documentation scope is known.", ["analysis"], ["Public interfaces listed"]),
            ("Draft documentation", "Write setup, usage, and architecture guidance.", "A complete draft exists.", ["writing"], ["Setup and usage are covered"]),
            ("Check examples", "Verify commands and examples against the repository.", "Examples are accurate or marked clearly.", ["validation"], ["Examples checked"]),
            ("Review and publish", "Show the documentation diff and record approval.", "Documentation is ready to publish.", ["feedback"], ["User review recorded"]),
        ],
    },
    "project_backup": {
        "name": "Project Backup",
        "description": "Create a timestamped backup while excluding environments and secrets.",
        "tasks": [
            ("Define backup scope", "Select project files and exclude caches, virtual environments, and secrets.", "The backup scope is approved.", ["planning"], ["Exclusions are explicit"]),
            ("Create backup archive", "Write a timestamped archive to a safe destination.", "The archive is created.", ["filesystem"], ["Archive exists"]),
            ("Verify archive contents", "Check that expected files are present and sensitive files are absent.", "The archive passes content checks.", ["validation"], ["Inclusion and exclusion checks pass"]),
            ("Report backup location", "Provide the path, size, and verification result.", "The user can find the backup.", ["reporting"], ["Location and status reported"]),
        ],
    },
    "git_change_assistant": {
        "name": "Git Change Assistant",
        "description": "Review repository changes and prepare a safe commit summary.",
        "tasks": [
            ("Inspect repository status", "Review branch, remotes, and changed files.", "The repository state is known.", ["git"], ["Status and branch captured"]),
            ("Review the diff", "Summarize behavioral changes and flag risks.", "The diff has a focused review.", ["analysis"], ["Risks are identified"]),
            ("Suggest commit message", "Create a concise commit message matching the actual changes.", "A truthful message is ready.", ["writing"], ["Message matches diff"]),
            ("Confirm next Git action", "Ask whether to commit, push, or only leave the review prepared.", "The user chooses the next action.", ["feedback"], ["No write action without approval"]),
        ],
    },
    "feature_implementation": {
        "name": "Feature Implementation Workflow",
        "description": "Plan, implement, test, verify, and report a requested feature.",
        "tasks": [
            ("Define acceptance criteria", "Translate the request into observable success conditions.", "Acceptance criteria are agreed.", ["analysis"], ["Criteria are testable"]),
            ("Create implementation plan", "Identify files, dependencies, and ordered changes.", "The plan is approved.", ["planning"], ["Plan has dependencies"]),
            ("Implement the feature", "Make the smallest coherent code change.", "The requested behavior exists.", ["implementation"], ["Feature is implemented"]),
            ("Add regression tests", "Cover the normal path and important edge cases.", "Tests cover the new behavior.", ["testing"], ["Regression tests exist"]),
            ("Verify and report", "Run checks, inspect results, and summarize remaining risks.", "The feature is verified or blocked with evidence.", ["verification"], ["Results and risks reported"]),
        ],
    },
    "cold_outreach": {
        "name": "Cold Outreach Planner",
        "description": "Convert business leads into personalized outreach drafts.",
        "tasks": [
            ("Load business leads", "Read the most recent business finder CSV report.", "Leads are loaded into memory.", ["filesystem"], ["CSV data parsed"]),
            ("Research contact persons", "Web search for business owners or managers.", "Contact names identified.", ["web_search"], ["Names found"]),
            ("Draft personalized messages", "Create tailored proposals based on the missing website.", "Drafts are generated.", ["writing"], ["Custom messages ready"]),
            ("Save outreach list", "Export leads and drafts to a new CSV.", "Outreach report is saved.", ["filesystem"], ["Final CSV exists"]),
        ],
    },
    "competitor_monitor": {
        "name": "Competitor Monitor",
        "description": "Analyze competitors in a region to find market gaps.",
        "tasks": [
            ("Scan local competitors", "Identify top-rated businesses in the category.", "Competitor list is created.", ["osm_api"], ["Top businesses found"]),
            ("Analyze ratings and reviews", "Extract key complaints and strengths from reviews.", "Sentiment analysis is complete.", ["analysis"], ["Gaps identified"]),
            ("Identify market gaps", "Determine what services are missing or poor.", "Gap analysis is documented.", ["analysis"], ["Opportunity identified"]),
            ("Generate strategy report", "Recommend a unique value proposition.", "Strategy report is ready.", ["reporting"], ["Strategy presented"]),
        ],
    },
    "automated_pr_reviewer": {
        "name": "Automated PR Reviewer",
        "description": "Review current git changes for bugs and style issues.",
        "tasks": [
            ("Capture current diff", "Extract all uncommitted changes.", "Diff is captured.", ["git"], ["Code changes isolated"]),
            ("Static analysis check", "Scan for obvious bugs, unused vars, or style style violations.", "Analysis is complete.", ["analysis"], ["Issues flagged"]),
            ("Generate improvement suggestions", "Propose specific refactors or fixes.", "Suggestions are ready.", ["writing"], ["Actionable feedback exists"]),
            ("Final review summary", "Provide a 'Ready to Commit' or 'Needs Work' status.", "Review is presented to user.", ["reporting"], ["Status reported"]),
        ],
    },
    "smart_file_organizer": {
        "name": "Smart File Organizer",
        "description": "Categorize and move files based on content and metadata.",
        "tasks": [
            ("Scan target directory", "Identify all files in the specified folder.", "File list is complete.", ["filesystem"], ["Files identified"]),
            ("Analyze file content", "Determine category based on extension and content.", "Categories are assigned.", ["analysis"], ["Categories mapped"]),
            ("Propose organization plan", "List which files move to which folders.", "Plan is ready for approval.", ["planning"], ["Move list prepared"]),
            ("Execute file moves", "Physically move files into structured folders.", "Files are organized.", ["filesystem"], ["Organization complete"]),
        ],
    },
    "deep_work_scheduler": {
        "name": "Deep Work Scheduler",
        "description": "Organize a focused work session based on priority tasks.",
        "tasks": [
            ("Inventory high-priority tasks", "Scan the task database for HIGH priority items.", "Priority list is ready.", ["database"], ["Tasks filtered"]),
            ("Estimate time requirements", "Allocate time blocks for each task.", "Time estimates are made.", ["analysis"], ["Duration assigned"]),
            ("Design session schedule", "Create a schedule with Pomodoro breaks.", "Schedule is designed.", ["planning"], ["Calendar ready"]),
            ("Present deep work plan", "Notify the user of the focused block.", "Plan is presented.", ["reporting"], ["Schedule reported"]),
        ],
    },
    "research_synthesizer": {
        "name": "Research Synthesizer",
        "description": "Gather web data on a topic and synthesize it into a knowledge note.",
        "tasks": [
            ("Execute broad search", "Gather top results from the web for the topic.", "Sources are collected.", ["web_search"], ["URL list ready"]),
            ("Summarize key findings", "Extract core arguments and data from sources.", "Synthesis is complete.", ["analysis"], ["Summaries ready"]),
            ("Cross-reference facts", "Identify consensus and contradictions.", "Fact-check is complete.", ["analysis"], ["Verified facts"]),
            ("Save to developer memory", "Store the final synthesis as a permanent fact.", "Memory is updated.", ["database"], ["Note saved"]),
        ],
    },
}