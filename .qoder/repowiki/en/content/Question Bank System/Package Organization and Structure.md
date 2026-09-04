# Package Organization and Structure

<cite>
**Referenced Files in This Document**
- [questions/bank/README.md](file://questions/bank/README.md)
- [questions/schema.json](file://questions/schema.json)
- [web/vite/bank-reader.ts](file://web/vite/bank-reader.ts)
- [questions/bank/1/package.json](file://questions/bank/1/package.json)
- [questions/bank/2/package.json](file://questions/bank/2/package.json)
- [questions/bank/10/package.json](file://questions/bank/10/package.json)
- [questions/bank/15/package.json](file://questions/bank/15/package.json)
- [questions/bank/1/verbal/001.json](file://questions/bank/1/verbal/001.json)
- [questions/bank/1/kuantitatif/001.json](file://questions/bank/1/kuantitatif/001.json)
- [questions/bank/1/pemecahan_masalah/001.json](file://questions/bank/1/pemecahan_masalah/001.json)
- [questions/bank/15/verbal/001.json](file://questions/bank/15/verbal/001.json)
- [questions/bank/15/kuantitatif/001.json](file://questions/bank/15/kuantitatif/001.json)
- [questions/bank/15/pemecahan_masalah/001.json](file://questions/bank/15/pemecahan_masalah/001.json)
- [questions/bank/15/verbal/023.json](file://questions/bank/15/verbal/023.json)
- [questions/bank/15/kuantitatif/025.json](file://questions/bank/15/kuantitatif/025.json)
- [questions/bank/15/kuantitatif/024.json](file://questions/bank/15/kuantitatif/024.json)
- [web/package.json](file://web/package.json)
- [scripts/bump_version.py](file://scripts/bump_version.py)
- [questions/generator/README.md](file://questions/generator/README.md)
</cite>

## Update Summary
**Changes Made**
- Added documentation for Package 15 'TBS LPDP Try Out — Paket 15' as the most challenging package in the question bank system
- Updated package structure examples to include the new hard-mode package with 60 questions across three subtests
- Enhanced difficulty calibration examples showing the progression from easy to hard modes
- Updated workflow documentation to reflect the addition of the latest package

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)
10. [Appendices](#appendices)

## Introduction
This document explains the package organization and structure of the question bank system used by the TBS LPDP application. It covers how numbered packages are organized under questions/bank, how subtest categories (verbal, kuantitatif, pemecahan_masalah) are structured, how images and assets are managed, and how metadata is defined via package.json per package. It also documents naming conventions for question files, Git-based versioning strategy, and workflows for adding or updating packages while maintaining consistency across large collections. The system now includes 15 distinct packages, with Package 15 representing the most challenging tier featuring hard-mode difficulty calibration.

## Project Structure
The question bank is a content repository rooted at questions/bank. Each numbered directory represents one test package and contains:
- A package.json manifest describing the package's identity and metadata.
- Three subtest directories: verbal, kuantitatif, pemecahan_masalah.
- An images folder for figures referenced by questions.

```mermaid
graph TB
Bank["questions/bank"] --> Pkg1["Package #1"]
Bank --> Pkg2["Package #2"]
Bank --> Pkg10["Package #10"]
Bank --> Pkg15["Package #15 - Hard Mode"]
Pkg1 --> M1["package.json"]
Pkg1 --> V1["verbal/"]
Pkg1 --> K1["kuantitatif/"]
Pkg1 --> PM1["pemecahan_masalah/"]
Pkg1 --> I1["images/"]
Pkg15 --> M15["package.json"]
Pkg15 --> V15["verbal/ (23 questions)"]
Pkg15 --> K15["kuantitatif/ (25 questions)"]
Pkg15 --> PM15["pemecahan_masalah/ (12 questions)"]
Pkg15 --> I15["images/"]
V1 --> QV["*.json questions"]
K1 --> QK["*.json questions"]
PM1 --> QPM["*.json questions"]
I1 --> IMG["image assets"]
V15 --> QV15["23 verbal questions"]
K15 --> QK15["25 quantitative questions"]
PM15 --> QPM15["12 problem-solving questions"]
I15 --> IMG15["image assets"]
```

**Diagram sources**
- [web/vite/bank-reader.ts:189-293](file://web/vite/bank-reader.ts#L189-L293)
- [questions/bank/1/package.json:1-10](file://questions/bank/1/package.json#L1-L10)
- [questions/bank/15/package.json:1-10](file://questions/bank/15/package.json#L1-L10)

**Section sources**
- [questions/bank/README.md:1-3](file://questions/bank/README.md#L1-L3)
- [web/vite/bank-reader.ts:189-293](file://web/vite/bank-reader.ts#L189-L293)

## Core Components
- Package manifests: One package.json per numbered package defines stable identifiers and human-readable metadata consumed during compilation.
- Question files: One JSON file per question under each subtest directory, following a strict schema.
- Image assets: Optional images stored under each package's images directory and referenced by relative paths from the package root.
- Schema validation: A central JSON schema enforces field types, allowed values, and image path patterns.
- Bank reader: A build-time module that scans the bank, compiles it into an internal representation, computes versions from Git history, and handles images either as URLs (dev) or inline data URIs (published).

Key responsibilities:
- Maintain consistent IDs derived from paths to ensure stability and reproducibility.
- Enforce subtest-specific constraints and option structures.
- Compute deterministic release digests per package based on manifest and all question content.

**Updated** Package 15 demonstrates the hard-mode difficulty calibration with an average difficulty index of 2.45, featuring 60 total questions distributed across verbal reasoning (23), quantitative reasoning (25), and problem-solving (12) subtests.

**Section sources**
- [questions/schema.json:1-98](file://questions/schema.json#L1-L98)
- [web/vite/bank-reader.ts:159-293](file://web/vite/bank-reader.ts#L159-L293)
- [questions/bank/1/verbal/001.json:1-29](file://questions/bank/1/verbal/001.json#L1-L29)
- [questions/bank/1/kuantitatif/001.json:1-44](file://questions/bank/1/kuantitatif/001.json#L1-L44)
- [questions/bank/1/pemecahan_masalah/001.json:1-44](file://questions/bank/1/pemecahan_masalah/001.json#L1-L44)
- [questions/bank/15/package.json:1-10](file://questions/bank/15/package.json#L1-L10)

## Architecture Overview
The bank is read once during development or build time and transformed into a single artifact consumed by the exam engine. The process integrates Git history to compute stable versions and supports two image modes: URL-based serving in development and inline base64 in published builds.

```mermaid
sequenceDiagram
participant Dev as "Developer"
participant Reader as "bank-reader.ts"
participant FS as "Filesystem"
participant Git as "Git History"
participant Engine as "Exam Engine"
Dev->>Reader : Run dev/build
Reader->>Git : Read commits for bank directory
Git-->>Reader : Commit log with affected files
Reader->>FS : List package dirs (numbered)
Reader->>FS : Read package.json per package
Reader->>FS : Enumerate subtest folders and *.json
Reader->>FS : Read each question JSON
Reader->>FS : If image present, read bytes and MIME
alt Dev mode
Reader-->>Engine : {packages, questions} + image URLs
else Published mode
Reader-->>Engine : {packages, questions} + inline images
end
Note over Reader,Engine : Release digest computed from manifest + questions + images
```

**Diagram sources**
- [web/vite/bank-reader.ts:78-125](file://web/vite/bank-reader.ts#L78-L125)
- [web/vite/bank-reader.ts:159-293](file://web/vite/bank-reader.ts#L159-L293)

## Detailed Component Analysis

### Package Manifests (per package)
Each package has a package.json containing:
- id: numeric package identifier
- title: human-readable package name
- description: summary of contents and timing
- difficulty: easy | medium | hard
- ai_model, ai_company, ai_model_description: provenance metadata about generation

These fields are read by the bank reader to populate package-level metadata and contribute to the release digest.

**Updated** Package 15 exemplifies the hard-mode configuration with advanced AI model integration using Qwen3.8-Max from Alibaba Cloud, specifically designed for generating challenging test questions with sophisticated logical, verbal, and mathematical reasoning capabilities.

Examples:
- Package 1 manifest (easy mode)
- Package 2 manifest (medium mode)
- Package 10 manifest (medium-hard mode)
- Package 15 manifest (hard mode)

**Section sources**
- [questions/bank/1/package.json:1-10](file://questions/bank/1/package.json#L1-L10)
- [questions/bank/2/package.json:1-10](file://questions/bank/2/package.json#L1-L10)
- [questions/bank/10/package.json:1-10](file://questions/bank/10/package.json#L1-L10)
- [questions/bank/15/package.json:1-10](file://questions/bank/15/package.json#L1-L10)
- [web/vite/bank-reader.ts:194-202](file://web/vite/bank-reader.ts#L194-L202)

### Question Files and Naming Conventions
- Location: questions/bank/<package>/<subtest>/<NNN>.json
- Subtests: verbal, kuantitatif, pemecahan_masalah
- File numbering: zero-padded three-digit sequence (e.g., 001.json)
- Stable ID: <package>-<subtest>-<NNN>, enforced by schema pattern
- Required fields include id, package, subtest, number, type, question_text, image, passage, options, correct_option, explanations, difficulty, source, verified
- Options: exactly five items keyed A–E; each with text
- Explanations: object with keys A–E and non-empty strings
- Image path: relative to package root, must match images/*.(png|jpg|jpeg|svg|webp) or null
- Difficulty: easy | medium | hard

**Updated** Package 15 demonstrates the full spectrum of difficulty calibration, ranging from easy foundational questions to complex hard-mode problems requiring advanced analytical thinking. The package features sophisticated question types including reading comprehension passages, geometric calculations with visual aids, and combinatorial probability problems.

Examples:
- Verbal question example (Package 1)
- Quantitative question example (Package 1)
- Problem-solving question example (Package 1)
- Hard-mode verbal question (Package 15)
- Complex quantitative problem (Package 15)
- Advanced problem-solving challenge (Package 15)

**Section sources**
- [questions/schema.json:7-96](file://questions/schema.json#L7-L96)
- [questions/bank/1/verbal/001.json:1-29](file://questions/bank/1/verbal/001.json#L1-L29)
- [questions/bank/1/kuantitatif/001.json:1-44](file://questions/bank/1/kuantitatif/001.json#L1-L44)
- [questions/bank/1/pemecahan_masalah/001.json:1-44](file://questions/bank/1/pemecahan_masalah/001.json#L1-L44)
- [questions/bank/15/verbal/023.json:1-44](file://questions/bank/15/verbal/023.json#L1-L44)
- [questions/bank/15/kuantitatif/025.json:1-44](file://questions/bank/15/kuantitatif/025.json#L1-L44)
- [questions/bank/15/kuantitatif/024.json:1-44](file://questions/bank/15/kuantitatif/024.json#L1-L44)

### Asset Management (Images)
- Images live under each package's images directory.
- Questions reference images using a relative path from the package root.
- During development, images are served via a mock endpoint using a content-addressed key (package/imageSha/filename).
- In published builds, images are inlined as data URIs to keep the bank self-contained.
- Allowed formats: png, jpg, jpeg, svg, webp.

**Updated** Package 15 incorporates sophisticated geometric diagrams and visual aids, particularly in quantitative reasoning questions involving triangles, circular paths, and spatial relationships, demonstrating the effective use of SVG graphics for complex mathematical concepts.

```mermaid
flowchart TD
Start(["Question with image"]) --> CheckImg{"Has image path?"}
CheckImg --> |No| Skip["Skip asset handling"]
CheckImg --> |Yes| ReadImg["Read image bytes and determine MIME"]
ReadImg --> Mode{"Build mode"}
Mode --> |Dev| URL["Create /__mock/image/{pkg}/{sha}/{name}"]
Mode --> |Published| Inline["Inline as data:<mime>;base64,..."]
URL --> End(["Compiled question"])
Inline --> End
Skip --> End
```

**Diagram sources**
- [web/vite/bank-reader.ts:220-234](file://web/vite/bank-reader.ts#L220-234)
- [questions/schema.json:57-61](file://questions/schema.json#L57-L61)

**Section sources**
- [web/vite/bank-reader.ts:220-234](file://web/vite/bank-reader.ts#L220-234)
- [questions/schema.json:57-61](file://questions/schema.json#L57-L61)

### Versioning Strategy (Git-based)
- Versions are derived from Git history over the bank directory, not counters.
- For each file and its ancestor directories, the reader counts commits to compute a revision number and last-updated timestamp.
- Package-level and question-level versions are included in the compiled output.
- Latest commit timestamp is exposed when available.

```mermaid
flowchart TD
A["Scan git log for bank dir"] --> B["Parse commits and touched files"]
B --> C["Build revisions map per path and ancestors"]
C --> D["For each question/package, assign version and updatedAt"]
D --> E["Include versions in compiled bank"]
```

**Diagram sources**
- [web/vite/bank-reader.ts:78-125](file://web/vite/bank-reader.ts#L78-L125)
- [web/vite/bank-reader.ts:186-187](file://web/vite/bank-reader.ts#L186-L187)
- [web/vite/bank-reader.ts:236-251](file://web/vite/bank-reader.ts#L236-L251)
- [web/vite/bank-reader.ts:272-284](file://web/vite/bank-reader.ts#L272-L284)

**Section sources**
- [web/vite/bank-reader.ts:78-125](file://web/vite/bank-reader.ts#L78-L125)
- [web/vite/bank-reader.ts:186-187](file://web/vite/bank-reader.ts#L186-L187)
- [web/vite/bank-reader.ts:236-251](file://web/vite/bank-reader.ts#L236-L251)
- [web/vite/bank-reader.ts:272-284](file://web/vite/bank-reader.ts#L272-L284)

### Workflow for Adding or Updating Packages
Adding a new package:
1. Create a new numbered directory under questions/bank (next integer).
2. Add a package.json with id, title, description, difficulty, and AI provenance fields.
3. Create subtest directories: verbal, kuantitatif, pemecahan_masalah.
4. Add question JSON files named with zero-padded numbers (e.g., 001.json) under each subtest.
5. Place any images under the package's images directory and reference them via relative paths.
6. Validate the bank using the generator tools before committing.

Updating an existing package:
- Edit package.json or question files as needed.
- Ensure IDs remain unchanged to preserve stability.
- Re-run validation and rebuild to verify correctness.

Publishing considerations:
- Use the generator tooling to validate and optionally publish content-addressed releases.
- The bank reader computes a release_id per package based on manifest and all question content, ensuring immutability.

**Updated** Package 15 serves as a comprehensive example of best practices for creating challenging test packages, demonstrating proper difficulty calibration, sophisticated question design, and effective use of AI-generated content with human verification.

**Section sources**
- [web/vite/bank-reader.ts:189-293](file://web/vite/bank-reader.ts#L189-L293)
- [questions/generator/README.md:9-24](file://questions/generator/README.md#L9-L24)

### Consistency Guidelines and Best Practices
- Follow the schema strictly: required fields, enum values, and array sizes must be exact.
- Keep IDs stable: they derive from path and must never change after publication.
- Use consistent numbering: zero-padded three digits per subtest.
- Limit images to supported formats and place them under images/.
- Provide explanations for all options (A–E) with meaningful text.
- Mark difficulty consistently and set verified appropriately.
- Use generator scripts for computable types to ensure deterministic answers and high-quality distractors.
- Validate the entire bank before pushing changes.

**Updated** Package 15 demonstrates advanced consistency practices including sophisticated difficulty calibration (average index 2.45), comprehensive explanation quality, and proper integration of AI-generated content with human verification processes.

**Section sources**
- [questions/schema.json:7-96](file://questions/schema.json#L7-L96)
- [questions/generator/README.md:9-24](file://questions/generator/README.md#L9-L24)

## Dependency Analysis
The bank reader depends on:
- Filesystem access to enumerate packages, manifests, and questions.
- Git history to compute versions and timestamps.
- The JSON schema for validation (used by external validators).
- Web package configuration for build/dev flows.

```mermaid
graph LR
Reader["bank-reader.ts"] --> FS["Filesystem"]
Reader --> Git["Git"]
Reader --> Schema["Schema (validation)"]
Reader --> WebPkg["web/package.json (build context)"]
```

**Diagram sources**
- [web/vite/bank-reader.ts:1-6](file://web/vite/bank-reader.ts#L1-L6)
- [web/vite/bank-reader.ts:78-125](file://web/vite/bank-reader.ts#L78-L125)
- [web/package.json:1-46](file://web/package.json#L1-L46)

**Section sources**
- [web/vite/bank-reader.ts:1-6](file://web/vite/bank-reader.ts#L1-L6)
- [web/package.json:1-46](file://web/package.json#L1-L46)

## Performance Considerations
- Reading the bank is a one-time operation during dev/build; avoid repeated scans in hot paths.
- In dev mode, serve images via URL endpoints to avoid embedding large assets in memory.
- In published mode, inline images to produce a self-contained artifact; this increases bundle size but improves offline performance.
- Sorting questions by number ensures deterministic ordering and stable outputs.
- Using Git history provides accurate versioning without additional bookkeeping.

**Updated** Package 15's larger question count (60 questions vs. typical 40-50 in other packages) demonstrates efficient asset management and optimized loading strategies for comprehensive test coverage.

## Troubleshooting Guide
Common issues and resolutions:
- Missing package.json in a numbered directory: the reader skips it; ensure every intended package includes a valid manifest.
- Invalid question JSON: schema validation will fail; check required fields, enums, and array sizes.
- Incorrect image path: must be relative to the package root and use allowed extensions; otherwise, validation fails.
- No Git history available: the reader falls back to file mtimes for versions; ensure your environment has Git for accurate versioning.
- Duplicate or out-of-order numbering: sort by number to maintain expected order; keep filenames sequential.

Validation and publishing tools:
- Use the generator's validate_bank script to catch schema and blueprint violations before committing.
- Use push_to_supabase to upload content-addressed images and publish immutable releases.

**Section sources**
- [web/vite/bank-reader.ts:169-171](file://web/vite/bank-reader.ts#L169-L171)
- [web/vite/bank-reader.ts:189-198](file://web/vite/bank-reader.ts#L189-L198)
- [questions/schema.json:7-96](file://questions/schema.json#L7-L96)
- [questions/generator/README.md:9-24](file://questions/generator/README.md#L9-L24)

## Conclusion
The question bank system uses a clear, hierarchical structure with numbered packages and standardized subtest directories. A strict schema and Git-based versioning ensure stability and reproducibility. The bank reader compiles the repository into a format suitable for both development and production, handling images flexibly. Following the naming conventions, validation practices, and workflow guidelines helps maintain consistency and scalability as the collection grows.

**Updated** Package 15 represents the pinnacle of the question bank system's evolution, showcasing advanced difficulty calibration, sophisticated question design, and effective integration of AI-generated content with human oversight. With 60 carefully crafted questions across three subtests, it provides comprehensive preparation for the most challenging aspects of the TBS LPDP examination.

## Appendices

### App Versioning and Dependencies
- The web application uses a standard package.json with dependencies for Supabase, React, Tauri plugins, and build tooling.
- A helper script updates version fields across Tauri and web artifacts to keep app versions synchronized.

**Section sources**
- [web/package.json:1-46](file://web/package.json#L1-L46)
- [scripts/bump_version.py:1-124](file://scripts/bump_version.py#L1-L124)