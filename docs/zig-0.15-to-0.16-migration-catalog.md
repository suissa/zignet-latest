# Zig 0.15 → 0.16 migration catalog

Status: release-note-derived catalog, not an exhaustive compiler diff. Zig 0.16.0 was released 2026-04-14. For every candidate example, pin the exact compiler version and verify it with that compiler. The source of truth is the [official 0.16.0 release notes](https://ziglang.org/download/0.16.0/release-notes.html).

## Version provenance

The project describes ZigNet's existing corpus as Zig 0.13, 0.14 and 0.15 (13,756 examples). Therefore the migration baseline for this project is primarily 0.15.x. Some individual features below have a more specific historical origin; don't infer that every change first appeared in 0.16.

| Area | Previous behavior / version | Zig 0.16 behavior | Main scenarios to cover |
|---|---|---|---|
| I/O interface | 0.15.x APIs commonly performed I/O through global/implicit standard-library functions | I/O operations use an explicit `Io` instance; `Io.Threaded` provides familiar threaded behavior | file read/write, directory traversal, sockets/HTTP, timers, cancellation, threaded vs event-loop implementations, passing Io through helpers |
| `main` initialization | Traditional entry point and explicit setup common in 0.15.x | “Juicy main”: accept `std.process.Init` (or `Init.Minimal`) for preinitialized allocator, Io and process facilities | minimal CLI, allocator selection, arena lifetime, I/O, environment/arguments, graceful exit |
| Async/concurrency primitives | Prior versions lacked this complete new standard-library interface in this form | `Future`, `Group`, `Queue(T)`, `Select`, `Batch`, `Clock`, `Duration`, `Timestamp`, `Timeout` introduced/expanded around the new Io model | fan-out/fan-in, bounded queue backpressure, cancellation, timeout, race/select, batching, time-unit safety |
| C translation | `@cImport` used libclang-based translation and was normal legacy workflow | `@cImport` is deprecated for future removal; translation is moving toward build-system-managed C translation; implementation now based on aro/translate-c | translate headers, include paths, build.zig integration, multiple headers, migration of existing C bindings, diagnose translator differences |
| Type construction | `@Type` and helpers such as `std.meta.Int` used to construct types | `@Type` replaced by individual type-creating builtins, including `@EnumLiteral`, `@Int`, `@Tuple`, `@Pointer`, `@Fn`, `@Struct` and related builtins | comptime-generated integer/tuple/pointer/function/struct/union/enum types, field metadata, replacing meta helpers |
| `switch` prongs | Some result-typed literals and captures were more restricted | Decl literals and other result-typed expressions can be prong items; union tag captures allowed for all prongs; special unreachable error prongs supported | tagged unions, packed values, enum literals, error sets, result-typed comparisons, capture/discard rules |
| Packed union equality | Equality could require wrapping packed union in packed struct | Packed unions can be compared directly | equality/inequality, bit representations, tests for backing integer values |
| Packed union backing integer | Explicit backing integer available for packed structs, not packed unions | `packed union(T)` may specify backing integer | protocol layouts, bit fields, ABI-sensitive representations, explicit integer widths |
| Extern ABI types | Inferred enum tags / packed backing integers could be accepted as extern types | Such inferred backing/tag types are no longer valid extern types | exported structs/globals/functions, C ABI boundaries, add explicit `enum(T)` or `packed struct(T)` / `packed union(T)` |
| Zero-bit tuple fields | A rule introduced in 0.14.0 unintentionally promoted zero-bit tuple fields to comptime | 0.16 reverts that behavior; field isn't implicitly a comptime field, though value may still be comptime-known | tuple `void` fields, `@typeInfo`, type equivalence, runtime tuple with comptime-known zero-bit member |
| Standard library container initialization | `BitSet` / `EnumSet` used `initEmpty` / `initFull` | Use declaration literals instead | empty/full bitsets, enum sets, initialization migration |
| `math.sign` | Older return type could be broader than necessary | Returns the smallest integer type fitting possible values | signed/unsigned inputs, generic callers, inferred result type |
| `tar.extract` | Extraction behavior had path traversal risk | Extraction sanitizes path traversal | archive extraction, malicious `../` paths, absolute paths, safe destination handling |
| Windows root certificates | Certificate fetching required more manual handling | Automatic fetching of root certificates is triggered on Windows | HTTPS clients, clean Windows install, certificate bootstrap |
| `ucontext_t` and related POSIX types | Standard library exposed types/functions for non-local control flow and machine-state inspection | Related types/functions removed from stdlib; signal context types should be purpose-built for use case | POSIX ports, signal handlers, coroutine-like legacy code, architecture-specific context structs |
| Debug information / stack traces | Stack-trace APIs and internals had limitations and inconsistent assumptions | Debug-info and stack-trace APIs reworked; inline callers included in more traces, better crash traces across targets | crash reports, DebugAllocator, inline functions, Windows PDB, missing frame pointers |
| Type resolution | More dependency-loop errors and incremental/non-incremental inconsistencies | Type resolution reworked; generally more permissive, but some formerly accepted recursive layout/alignment patterns now error | comptime dependency graphs, recursive type layouts, alignment queries, incremental compilation |
| Incremental compilation | Less mature; could over-analyze and behave inconsistently | Improved substantially, remains disabled by default due to known bugs; opt in with `-fincremental` | watch-mode iteration, build errors, LLVM/self-hosted backends, regression tests |
| ELF linker | Self-hosted ELF linker not default in many configurations | New ELF linker enabled by default for self-hosted backend targeting ELF; not feature-complete | Linux builds, incremental linking, verify fallback/limitations |
| CLI error formatting | `--prominent-compile-errors` existed | Replaced by `--error-style minimal`; `--multiline-errors` added with `indent`, `newline`, `none` | CI logs, multiline diagnostics, migration of build scripts |
| Package metadata | Package `name` string accepted and fingerprint could be absent | `name` must be enum literal and `fingerprint` required in package dependencies | build.zig.zon dependency migration, reproducibility, duplicate versions |
| Dependency cache | Package cache behavior less focused on compressed canonical artifacts | Package files filtered using `paths`, then canonical compressed cache artifact created | package paths, cache reproducibility, shared cache, dependency debugging |
| Targets / platforms | Support varied by target and toolchain | New native-tested targets and initial LoongArch32 support; Solaris/AIX/z/OS support removed; additional Mac Catalyst cross-compilation | cross-compilation matrices, unsupported-target diagnostics, libc assumptions |
| Backends / toolchain | Prior LLVM and self-hosted backend capabilities | LLVM upgraded to 21.1.0; incremental LLVM compilation added; loop vectorization disabled due to upstream regression; x86/wasm backend improvements | build configuration, performance expectations, debug info, target backend tests |
| libc/toolchain headers | Earlier bundled libc versions | musl 1.2.5, glibc 2.43 cross-compile availability, Linux 6.19 headers, macOS 26.4 headers and related libc source consolidation | C interop, cross-compilation, libc symbol availability, target-specific tests |

## Dataset scenario matrix

For each row, generate examples across these dimensions where applicable:

1. Minimal positive example, idiomatic production example, generic/comptime example.
2. API used directly vs passed through a helper vs wrapped in a struct.
3. Single operation vs error path vs cleanup/cancellation path.
4. Explicit types vs inferred types; const vs var; empty/single/multiple items.
5. Standalone file vs build-system/package context vs C ABI boundary.
6. Correct 0.15 input → correct 0.16 migration; explain-only question; generate-new-code request; diagnose-invalid-migration request.
7. Near-miss negative examples: plausible but obsolete 0.15 API, wrong lifetime, omitted Io, implicit extern backing type, invalid package metadata.
8. Semantically different solutions: threaded vs event-loop style, local helper vs injected dependency, eager vs batched work, different error-handling approaches.

Do not create variants that differ only in identifiers, whitespace or literal constants. Each example must cover a distinct semantic decision, control-flow branch, type shape, ownership/lifetime constraint, error case or user intent.

## Required validation

- Pin and record `zig version` for every compile/test.
- Run `zig fmt --check` (or format then compare).
- Compile runnable examples with `zig build-exe` / `zig test` using Zig 0.16.0.
- Compile migration baselines with the declared 0.15.x version where applicable.
- A code fragment that cannot compile alone must include a complete harness or be marked `snippet_only` with its missing context described.
- Store compiler stdout/stderr and exit code in validation metadata.
- Never label an example compiler-validated without actually running the relevant compiler.
- Keep a held-out test split by underlying scenario/template, not random near-duplicates.

## Official source

- [Zig 0.16.0 release notes](https://ziglang.org/download/0.16.0/release-notes.html)
- [Zig 0.15.1 release notes](https://ziglang.org/download/0.15.1/release-notes.html)
- [0.16.0 announcement](https://ziglang.org/news/0.16.0-released/)
