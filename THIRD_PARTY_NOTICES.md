# Third-party tools and services

The toolkit adapters do not relicense the servers, CLIs, models or services they
connect to. Dependency metadata fixes the working arrangement; users obtain the
actual components from the original distributions. Keep their notices when
redistributing their code or binaries.

- **gopls v0.23.0**, Go tools: BSD-style license. The adapter is deliberately
  tied to this version's reference output.
  [Source license](https://github.com/golang/tools/blob/gopls/v0.23.0/LICENSE).
- **deadcode**, Go tools v0.50.0: BSD-style license.
  [Source license](https://github.com/golang/tools/blob/v0.50.0/LICENSE).
- **GitNexus 1.6.12:** PolyForm Noncommercial 1.0.0. Its permitted-purpose and
  notice requirements remain applicable, including when installed separately.
  Required Notice: Copyright Abhigyan Patwari (https://github.com/abhigyanpatwari/GitNexus)
  [Exact release license](https://github.com/abhigyanpatwari/GitNexus/blob/v1.6.12/LICENSE).
- **Repomix 1.18.1:** MIT. [Repository](https://github.com/yamadashy/repomix).
- **ast-grep CLI 0.45.3:** MIT. [Repository](https://github.com/ast-grep/ast-grep).
- **Gas City v1.5.0:** MIT.
  [Exact release license](https://github.com/gastownhall/gascity/blob/v1.5.0/LICENSE).
- **Beads v1.3.1:** MIT.
  [Exact release license](https://github.com/gastownhall/beads/blob/v1.3.1/LICENSE).
- **Dolt v2.4.2:** Apache-2.0.
  [Exact release license](https://github.com/dolthub/dolt/blob/v2.4.2/LICENSE).
- **Codex rust-v0.162.0-alpha.2:** Apache-2.0, with upstream NOTICE.
  [License](https://github.com/openai/codex/blob/rust-v0.162.0-alpha.2/LICENSE),
  [NOTICE](https://github.com/openai/codex/blob/rust-v0.162.0-alpha.2/NOTICE).
- **Gas City roles pack:** imported by its public repository and exact recorded
  ref, not vendored here. This is a separate repository; verify its applicable
  terms before use or redistribution rather than applying the runtime's MIT
  license to it automatically.
- **Context7:** separately operated remote MCP service.
  [Public service](https://context7.com/). Its access and service terms are
  independent of this toolkit's source license.

The npm package locks include transitive dependency metadata and integrity
values. Consult each installed package's own license and notices; the names
above do not assert one license for the entire transitive tree. Go, Node and
the user's Codex/model access are separately installed prerequisites.
