# Test Specification: Spec Analysis & Execution Planning

## Overview

Tests validate spec discovery, parsing, status filtering, dependency
analysis, and execution plan construction. Uses fixture spec pack
directories with known structures. Property tests verify ordering
invariants with Hypothesis.

## Test Cases

### TS-13-1: Discover specs in campaign directory

**Requirement:** 13-REQ-1.1, 13-REQ-1.2
**Type:** unit
**Description:** Verify spec discovery finds all spec pack folders.

**Preconditions:**
- Temporary campaign directory with two spec folders:
  `01_base_app/` and `02_feature/`.

**Input:**
- Call discovery on the campaign directory.

**Expected:**
- Returns 2 `SpecMeta` objects.
- First has spec_id=1, second has spec_id=2.

**Assertion pseudocode:**
```
metas = discover_specs(campaign_dir)
ASSERT len(metas) == 2
ASSERT metas[0].spec_id == 1
ASSERT metas[1].spec_id == 2
```

---

### TS-13-2: Specs sorted by numeric prefix

**Requirement:** 13-REQ-1.3
**Type:** unit
**Description:** Verify discovered specs are in ascending numeric order.

**Preconditions:**
- Campaign with folders: `03_third/`, `01_first/`, `02_second/`.

**Input:**
- Call discovery.

**Expected:**
- Order is: spec_id 1, 2, 3.

**Assertion pseudocode:**
```
metas = discover_specs(campaign_dir)
ids = [m.spec_id for m in metas]
ASSERT ids == [1, 2, 3]
```

---

### TS-13-3: Parse spec pack loads all artifacts

**Requirement:** 13-REQ-2.1, 13-REQ-2.2, 13-REQ-2.3, 13-REQ-2.4, 13-REQ-2.5, 13-REQ-5.2
**Type:** unit
**Description:** Verify all spec artifacts are parsed into models.

**Preconditions:**
- Fixture spec pack with valid `requirements.json`, `test_spec.json`,
  `tasks.json`, and `prd.md`.

**Input:**
- `SpecParser.parse(spec_meta)`.

**Expected:**
- Returns `ParsedSpec` with non-null requirements, test_spec, tasks.
- `prd_text` is non-empty.

**Assertion pseudocode:**
```
parsed = SpecParser().parse(spec_meta)
ASSERT parsed.requirements is not None
ASSERT parsed.test_spec is not None
ASSERT parsed.tasks is not None
ASSERT len(parsed.prd_text) > 0
```

---

### TS-13-4: Only active specs included in plan

**Requirement:** 13-REQ-3.1
**Type:** unit
**Description:** Verify non-active specs are filtered out.

**Preconditions:**
- Campaign with two specs: `01_active/` (status=active),
  `02_draft/` (status=draft).

**Input:**
- `build_execution_plan(campaign_dir)`.

**Expected:**
- Plan contains only spec 01.

**Assertion pseudocode:**
```
plan = build_execution_plan(campaign_dir)
ASSERT plan.count == 1
ASSERT plan.specs[0].meta.spec_name == "active"
```

---

### TS-13-5: Non-active spec logs warning

**Requirement:** 13-REQ-3.2
**Type:** unit
**Description:** Verify skipped specs produce a log warning.

**Preconditions:**
- Campaign with one draft spec.

**Input:**
- `build_execution_plan(campaign_dir)`.

**Expected:**
- Warning log contains spec name and status "draft".

**Assertion pseudocode:**
```
with capture_logs() as logs:
    plan = build_execution_plan(campaign_dir)
ASSERT any("draft" in log and "skipped" in log for log in logs)
```

---

### TS-13-6: Dependency ordering respected

**Requirement:** 13-REQ-4.1, 13-REQ-4.2
**Type:** unit
**Description:** Verify dependent specs come after their dependencies.

**Preconditions:**
- Campaign with `01_base/` and `02_feature/` where 02 depends on 01.

**Input:**
- `build_execution_plan(campaign_dir)`.

**Expected:**
- Plan order: 01_base before 02_feature.

**Assertion pseudocode:**
```
plan = build_execution_plan(campaign_dir)
names = [s.meta.spec_name for s in plan.specs]
ASSERT names.index("base") < names.index("feature")
```

---

### TS-13-7: Cycle detection raises error

**Requirement:** 13-REQ-4.3
**Type:** unit
**Description:** Verify circular dependencies are caught.

**Preconditions:**
- Campaign where spec A depends on B and B depends on A.

**Input:**
- `build_execution_plan(campaign_dir)`.

**Expected:**
- Raises `DependencyCycleError`.

**Assertion pseudocode:**
```
ASSERT_RAISES DependencyCycleError:
    build_execution_plan(campaign_dir)
```

---

### TS-13-8: Execution plan is serializable

**Requirement:** 13-REQ-5.3
**Type:** unit
**Description:** Verify ExecutionPlan can be serialized to JSON.

**Preconditions:**
- Valid execution plan with one spec.

**Input:**
- `plan.model_dump_json()`.

**Expected:**
- Returns valid JSON string.

**Assertion pseudocode:**
```
plan = build_execution_plan(campaign_dir)
json_str = plan.model_dump_json()
parsed = json.loads(json_str)
ASSERT "specs" in parsed
ASSERT "count" in parsed
```

---

### TS-13-9: Spec filter restricts plan

**Requirement:** 13-REQ-6.2
**Type:** unit
**Description:** Verify spec_filter limits which specs appear in the plan.

**Preconditions:**
- Campaign with 3 active specs: 01, 02, 03.

**Input:**
- `build_execution_plan(campaign_dir, spec_filter=["01_base"])`.

**Expected:**
- Plan contains only spec 01.

**Assertion pseudocode:**
```
plan = build_execution_plan(campaign_dir, spec_filter=["base"])
ASSERT plan.count == 1
```

---

### TS-13-10: Build plan entry point logs steps

**Requirement:** 13-REQ-6.1
**Type:** unit
**Description:** Verify the build function logs discovery, parsing,
validation, and sorting steps.

**Preconditions:**
- Campaign with one valid active spec.

**Input:**
- `build_execution_plan(campaign_dir)`.

**Expected:**
- Log output contains entries for "discover", "parse", "sort" or similar.

**Assertion pseudocode:**
```
with capture_logs() as logs:
    plan = build_execution_plan(campaign_dir)
ASSERT any("discover" in log for log in logs)
ASSERT any("parse" in log or "parsed" in log for log in logs)
```

## Property Test Cases

### TS-13-P1: Topological order respects all dependencies

**Property:** Property 1 from design.md
**Validates:** 13-REQ-4.2
**Type:** property
**Description:** For any valid DAG, every dependency appears before
its dependent in the plan.

**For any:** Directed acyclic graph of 2-6 specs with random edges
**Invariant:** For every edge (A, B) where B depends on A, A's index
in the plan is less than B's index.

**Assertion pseudocode:**
```
FOR ANY dag IN random_dags(min_nodes=2, max_nodes=6):
    plan = topological_sort(dag)
    FOR EACH edge (A, B) IN dag.edges:
        ASSERT plan.index(A) < plan.index(B)
```

---

### TS-13-P2: Active-only filtering is complete

**Property:** Property 2 from design.md
**Validates:** 13-REQ-3.1, 13-REQ-3.3
**Type:** property
**Description:** The plan never contains non-active specs.

**For any:** Campaign with specs having random statuses from
{draft, active, sealed, superseded, archived}
**Invariant:** Every spec in the plan has status `active`.

**Assertion pseudocode:**
```
FOR ANY statuses IN lists(sampled_from(["draft", "active", "sealed"])):
    plan = build_plan_from_specs_with_statuses(statuses)
    FOR EACH spec IN plan.specs:
        ASSERT spec.meta.status == "active"
```

---

### TS-13-P3: Stable sort by numeric prefix

**Property:** Property 3 from design.md
**Validates:** 13-REQ-4.4
**Type:** property
**Description:** Unrelated specs are ordered by numeric prefix.

**For any:** Set of specs with no dependencies between them
**Invariant:** The plan orders them by ascending spec_id.

**Assertion pseudocode:**
```
FOR ANY spec_ids IN lists(integers(min_value=1, max_value=100), unique=True):
    plan = build_plan_no_deps(spec_ids)
    result_ids = [s.meta.spec_id for s in plan.specs]
    ASSERT result_ids == sorted(result_ids)
```

---

### TS-13-P4: Cycle detection is reliable

**Property:** Property 4 from design.md
**Validates:** 13-REQ-4.3
**Type:** property
**Description:** Any graph with a cycle raises DependencyCycleError.

**For any:** Directed graph of 2-5 specs with at least one cycle
**Invariant:** `build_execution_plan` raises `DependencyCycleError`.

**Assertion pseudocode:**
```
FOR ANY cyclic_graph IN random_cyclic_graphs(min_nodes=2, max_nodes=5):
    ASSERT_RAISES DependencyCycleError:
        topological_sort(cyclic_graph)
```

## Edge Case Tests

### TS-13-E1: Empty campaign directory

**Requirement:** 13-REQ-1.E1
**Type:** unit
**Description:** Verify empty campaign produces empty plan.

**Preconditions:**
- Empty temporary directory.

**Input:**
- `build_execution_plan(empty_dir)`.

**Expected:**
- Returns plan with count=0 and empty specs list.

**Assertion pseudocode:**
```
plan = build_execution_plan(empty_dir)
ASSERT plan.count == 0
ASSERT plan.specs == []
```

---

### TS-13-E2: Non-spec folders ignored

**Requirement:** 13-REQ-1.E2
**Type:** unit
**Description:** Verify folders not matching NN_name are skipped.

**Preconditions:**
- Campaign with `01_valid/` and `notes/` and `.git/`.

**Input:**
- Discover specs.

**Expected:**
- Only `01_valid` is discovered.

**Assertion pseudocode:**
```
metas = discover_specs(campaign_dir)
ASSERT len(metas) == 1
ASSERT metas[0].spec_name == "valid"
```

---

### TS-13-E3: Missing JSON artifact raises SpecParseError

**Requirement:** 13-REQ-2.E1
**Type:** unit
**Description:** Verify missing required files are caught.

**Preconditions:**
- Spec folder with `prd.md` but no `requirements.json`.

**Input:**
- `SpecParser().parse(spec_meta)`.

**Expected:**
- Raises `SpecParseError` mentioning `requirements.json`.

**Assertion pseudocode:**
```
ASSERT_RAISES SpecParseError:
    SpecParser().parse(meta_without_requirements)
```

---

### TS-13-E4: Invalid JSON raises SpecParseError

**Requirement:** 13-REQ-2.E2
**Type:** unit
**Description:** Verify malformed JSON is caught.

**Preconditions:**
- Spec folder with `requirements.json` containing `{invalid`.

**Input:**
- `SpecParser().parse(spec_meta)`.

**Expected:**
- Raises `SpecParseError`.

**Assertion pseudocode:**
```
write_file(spec_dir / "requirements.json", "{invalid")
ASSERT_RAISES SpecParseError:
    SpecParser().parse(spec_meta)
```

---

### TS-13-E5: Missing prd.md warns and uses empty string

**Requirement:** 13-REQ-2.E3
**Type:** unit
**Description:** Verify missing PRD is handled gracefully.

**Preconditions:**
- Spec folder with JSON artifacts but no `prd.md`.

**Input:**
- `SpecParser().parse(spec_meta)`.

**Expected:**
- `parsed.prd_text` equals `""`.
- Warning logged about missing `prd.md`.

**Assertion pseudocode:**
```
with capture_logs() as logs:
    parsed = SpecParser().parse(spec_meta_no_prd)
ASSERT parsed.prd_text == ""
ASSERT any("prd.md" in log for log in logs)
```

---

### TS-13-E6: External dependency treated as satisfied

**Requirement:** 13-REQ-4.E1
**Type:** unit
**Description:** Verify dependencies on specs outside the campaign
don't block execution.

**Preconditions:**
- Campaign with spec 02 depending on spec 01, but spec 01 not present.

**Input:**
- `build_execution_plan(campaign_dir)`.

**Expected:**
- Plan includes spec 02.
- Warning logged about missing dependency.

**Assertion pseudocode:**
```
with capture_logs() as logs:
    plan = build_execution_plan(campaign_dir)
ASSERT plan.count == 1
ASSERT any("dependency" in log and "not found" in log for log in logs)
```

---

### TS-13-E7: Campaign directory does not exist

**Requirement:** 13-REQ-6.E1
**Type:** unit
**Description:** Verify nonexistent directory raises FileNotFoundError.

**Preconditions:**
- None.

**Input:**
- `build_execution_plan(Path("/nonexistent"))`.

**Expected:**
- Raises `FileNotFoundError`.

**Assertion pseudocode:**
```
ASSERT_RAISES FileNotFoundError:
    build_execution_plan(Path("/nonexistent"))
```

### TS-13-E8: Missing status field treated as draft

**Requirement:** 13-REQ-3.E1
**Type:** unit
**Description:** Verify a spec with missing or invalid status is treated
as draft and skipped with a warning.

**Preconditions:**
- Campaign with one spec whose status field is absent or set to an
  unrecognised value (e.g. `null` or `"bogus"`).

**Input:**
- `build_execution_plan(campaign_dir)`.

**Expected:**
- Plan does not contain the spec (treated as draft, therefore skipped).
- Warning logged mentioning the spec name and that status defaulted to
  `draft`.

**Assertion pseudocode:**
```
with capture_logs() as logs:
    plan = build_execution_plan(campaign_dir)
ASSERT plan.count == 0
ASSERT any("draft" in log and spec_name in log for log in logs)
```

---

### TS-13-E9: No dependency specs ordered by prefix

**Requirement:** 13-REQ-4.E2
**Type:** unit
**Description:** Verify specs with no dependencies are ordered by numeric prefix.

**Preconditions:**
- Campaign with 3 active specs, no dependencies: 03, 01, 02.

**Input:**
- `build_execution_plan(campaign_dir)`.

**Expected:**
- Plan order: 01, 02, 03.

**Assertion pseudocode:**
```
plan = build_execution_plan(campaign_dir)
ids = [s.meta.spec_id for s in plan.specs]
ASSERT ids == [1, 2, 3]
```

---

### TS-13-E10: Empty plan has count zero

**Requirement:** 13-REQ-5.E1
**Type:** unit
**Description:** Verify empty execution plan has zero count and empty list.

**Preconditions:**
- Campaign with only draft specs (no active specs).

**Input:**
- `build_execution_plan(campaign_dir)`.

**Expected:**
- `plan.count == 0`, `plan.specs == []`.

**Assertion pseudocode:**
```
plan = build_execution_plan(all_draft_campaign_dir)
ASSERT plan.count == 0
ASSERT plan.specs == []
```

---

## Integration Smoke Tests

### TS-13-SMOKE-1: Build plan from example specs

**Execution Path:** Path 1 from design.md
**Description:** Verify end-to-end plan building using the repo's example
spec packs.

**Setup:** Use `examples/golang_service/service_mvp/` as campaign directory
(contains real spec packs with valid JSON artifacts).

**Trigger:** `build_execution_plan(Path("examples/golang_service/service_mvp/"))`

**Expected side effects:**
- Returns an `ExecutionPlan` with at least one spec.
- Each spec has non-null requirements, test_spec, and tasks.
- Specs are in valid topological order.

**Must NOT satisfy with:** Mocking afspec discovery or I/O functions —
real filesystem reads must execute.

**Assertion pseudocode:**
```
plan = build_execution_plan(Path("examples/golang_service/service_mvp/"))
ASSERT plan.count >= 1
FOR EACH spec IN plan.specs:
    ASSERT spec.requirements is not None
    ASSERT spec.tasks is not None
```

## Coverage Matrix

| Requirement | Test Spec Entry | Type |
|-------------|-----------------|------|
| 13-REQ-1.1 | TS-13-1 | unit |
| 13-REQ-1.3 | TS-13-2 | unit |
| 13-REQ-1.E1 | TS-13-E1 | unit |
| 13-REQ-1.E2 | TS-13-E2 | unit |
| 13-REQ-2.1 | TS-13-3 | unit |
| 13-REQ-2.2 | TS-13-3 | unit |
| 13-REQ-2.3 | TS-13-3 | unit |
| 13-REQ-2.4 | TS-13-3 | unit |
| 13-REQ-2.5 | TS-13-3 | unit |
| 13-REQ-2.E1 | TS-13-E3 | unit |
| 13-REQ-2.E2 | TS-13-E4 | unit |
| 13-REQ-2.E3 | TS-13-E5 | unit |
| 13-REQ-3.1 | TS-13-4 | unit |
| 13-REQ-3.2 | TS-13-5 | unit |
| 13-REQ-3.3 | TS-13-4 | unit |
| 13-REQ-3.E1 | TS-13-E8 | unit |
| 13-REQ-4.2 | TS-13-6 | unit |
| 13-REQ-4.3 | TS-13-7 | unit |
| 13-REQ-4.4 | TS-13-P3 | property |
| 13-REQ-4.E1 | TS-13-E6 | unit |
| 13-REQ-4.E2 | TS-13-E9 | unit |
| 13-REQ-5.1 | TS-13-8 | unit |
| 13-REQ-5.3 | TS-13-8 | unit |
| 13-REQ-5.E1 | TS-13-E10 | unit |
| 13-REQ-6.1 | TS-13-10 | unit |
| 13-REQ-6.2 | TS-13-9 | unit |
| 13-REQ-6.E1 | TS-13-E7 | unit |
| Property 1 | TS-13-P1 | property |
| Property 2 | TS-13-P2 | property |
| Property 3 | TS-13-P3 | property |
| Property 4 | TS-13-P4 | property |
| Path 1 | TS-13-SMOKE-1 | integration |
| 13-REQ-1.2 | TS-13-1 | unit |
| 13-REQ-4.1 | TS-13-6 | unit |
| 13-REQ-5.2 | TS-13-3 | unit |
